# -*- coding: utf-8 -*-
"""
@Time    : 2025/11/10 16:42
@Author  : chenshu
@FileName: plan_agent.py
@Description:
"""
import asyncio
import json
import re
from typing import Any, Optional

from langchain.agents import AgentExecutor
from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from sqlmodel import Session

from apps.openapi.agent.analysis_componet.analysis_tool import GetDataTool, InsightTool, SaveInsightTool, DataTransTool, \
    FinalAnswerTool
from apps.openapi.agent.analysis_componet.data_model import AnalysisContext
from apps.openapi.models.openapiModels import OpenChatQuestion
from apps.openapi.service.openapi_llm import LLMService
from common.core.deps import CurrentUser, CurrentAssistant
from common.utils.utils import SQLBotLogUtil


class LLMServiceWrapper:
    """
    包装openapi_llm.LLMService，提供工具化接口
    """

    def __init__(self,
                 session: Session,
                 current_user: CurrentUser,
                 chat_question: OpenChatQuestion,
                 current_assistant: CurrentAssistant
                 ):
        self.current_user = current_user
        self.chat_question = chat_question
        self.current_assistant = current_assistant
        self.llm_service = None
        self.history = None
        self.session = session

    async def initialize_service(self):
        """初始化LLMService"""
        self.llm_service = await LLMService.create(
            session=self.session,
            current_user=self.current_user,
            chat_question=self.chat_question,
            current_assistant=self.current_assistant,
            no_reasoning=self.chat_question.no_reasoning,
            embedding=True
        )
        self.history = self.llm_service.init_for_plan(self.session)


class PlanAgent:
    def __init__(self,
                 session: Session,
                 current_user: CurrentUser,
                 chat_question: OpenChatQuestion,
                 current_assistant: CurrentAssistant,
                 max_steps: Optional[int] = None,
                 queue: asyncio.Queue = None,
                 llm: Any = None
                 ):
        self.current_user = current_user
        self.chat_question = chat_question
        self.question = self.chat_question.question
        # 用户可选传入 max_steps 作为迭代次数上限；未传则由复杂度自动推断
        self._override_max_steps = max_steps
        self.max_steps = max_steps or 20
        self.current_assistant = current_assistant

        self.llm = llm
        # 初始化LLMService包装器
        self.llm_service_wrapper = LLMServiceWrapper(
            session=session,
            current_user=current_user,
            chat_question=chat_question,
            current_assistant=current_assistant)

        # 上下文信息
        self.context = None

        # 消息队列
        self.queue = queue

        # 工具过程类推送统一为 process，最终报告由 final_answer 推 report
        self.message_type = "process"
        self.session = session
        self.execution_plan = None

    @staticmethod
    def _contains_any(text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def classify_task_type(self) -> dict:
        question = (self.question or "").strip()
        normalized_question = question.lower()

        if self._contains_any(question, ["预测", "预估", "未来", "下周", "下月", "明年"]):
            return {
                "task_type": "forecast",
                "query_mode": "time_series",
                "answer_granularity": "time_series_metric",
                "allow_detail_rows": False,
                "required_result_shape": "按时间排序的时序指标结果",
                "required_fields": ["时间字段", "预测相关指标"],
                "forbidden_query_shapes": ["无时间字段的静态汇总", "与预测无关的明细列表"],
                "reason": "问题包含未来/预测诉求，需要时序数据作为输入",
            }

        if self._contains_any(question, ["原因", "归因", "为什么", "驱动因素", "影响因素", "根因", "诊断"]):
            return {
                "task_type": "diagnosis",
                "query_mode": "diagnostic",
                "answer_granularity": "evidence_then_drilldown",
                "allow_detail_rows": False,
                "required_result_shape": "先给异常或差异证据，再下钻验证原因",
                "required_fields": ["异常/差异维度", "关键指标", "必要的验证字段"],
                "forbidden_query_shapes": ["只有总量没有拆解维度", "与主问题无关的泛化统计"],
                "reason": "问题包含原因/诊断语义，需要证据与下钻配合",
            }

        if self._contains_any(question, ["趋势", "变化", "波动", "环比", "同比"]):
            return {
                "task_type": "trend",
                "query_mode": "time_series",
                "answer_granularity": "time_bucket_metric",
                "allow_detail_rows": False,
                "required_result_shape": "按时间粒度聚合后的趋势结果",
                "required_fields": ["时间字段", "趋势指标"],
                "forbidden_query_shapes": ["不含时间字段的静态明细", "与趋势无关的明细快照"],
                "reason": "问题包含趋势/变化语义，应优先生成时间序列结果",
            }

        if self._contains_any(question, ["对比", "比较", "差异", "分别"]):
            return {
                "task_type": "compare",
                "query_mode": "aggregate",
                "answer_granularity": "comparable_groups",
                "allow_detail_rows": False,
                "required_result_shape": "可直接比较的分组结果",
                "required_fields": ["对比维度", "对比指标"],
                "forbidden_query_shapes": ["只有总计没有对比对象", "不能形成比较口径的明细"],
                "reason": "问题强调对象/时间段差异，需要并列可比结果",
            }

        if re.search(r"(top\s*\d+|前\d+|排名|排行|最高|最低)", normalized_question, re.IGNORECASE):
            return {
                "task_type": "ranking",
                "query_mode": "aggregate",
                "answer_granularity": "ordered_groups",
                "allow_detail_rows": False,
                "required_result_shape": "带排序依据的分组结果",
                "required_fields": ["排序维度", "排序指标"],
                "forbidden_query_shapes": ["缺少排序字段", "无序的明细列表"],
                "reason": "问题强调排序/TopN，需要返回可排序的结果集",
            }

        if re.search(r"(最后一次|最近一次|最新一条|最后一条|最近一条|最新|当前状态|详情|明细|执行情况|记录)", question):
            # 区分单实体最新一条 vs 每实体最近一条
            if re.search(r"(每个|每任务|每[个只]?[实体任务订单用户]|按\s*\S+\s*取\s*最近|各\s*\S+\s*的\s*最近)", question):
                return {
                    "task_type": "snapshot",
                    "query_mode": "detail",
                    "answer_granularity": "latest_record_per_entity",
                    "allow_detail_rows": True,
                    "required_result_shape": "按实体分组，每组返回最近一条或当前有效的记录，最终结果行数受上限约束",
                    "required_fields": ["实体标识字段", "判定最近一次的时间字段", "状态/结果字段"],
                    "forbidden_query_shapes": ["先统计次数再猜测最新状态", "只返回聚合指标不返回记录字段", "未按实体去重导致多行同实体"],
                    "reason": "问题在询问每个实体的最新/最后一次，应按实体取最近一条",
                }
            return {
                "task_type": "snapshot",
                "query_mode": "detail",
                "answer_granularity": "single_latest_record",
                "allow_detail_rows": True,
                "required_result_shape": "仅返回最近一条或当前有效的记录，结果应为 1 行",
                "required_fields": ["判定最近一次的时间字段", "状态/结果字段"],
                "forbidden_query_shapes": ["先统计次数再猜测最新状态", "只返回聚合指标不返回记录字段", "返回多行而非单条最新"],
                "reason": "问题在询问单条最新/最后一次/当前状态，应直接返回 1 条记录",
            }

        if self._contains_any(question, ["次数", "数量", "总数", "总量", "均值", "平均", "占比", "比例"]):
            return {
                "task_type": "aggregate",
                "query_mode": "aggregate",
                "answer_granularity": "grouped_metric",
                "allow_detail_rows": False,
                "required_result_shape": "按维度聚合后的指标结果",
                "required_fields": ["分组维度", "聚合指标"],
                "forbidden_query_shapes": ["无必要的大量明细行", "与指标无关的记录详情"],
                "reason": "问题显式要求统计指标，适合聚合查询",
            }

        return {
            "task_type": "aggregate",
            "query_mode": "aggregate",
            "answer_granularity": "direct_evidence",
            "allow_detail_rows": False,
            "required_result_shape": "能直接回答主问题的最小证据集",
            "required_fields": ["主问题涉及的核心字段"],
            "forbidden_query_shapes": ["与主问题无关的扩展统计", "重复查询"],
            "reason": "问题未体现明显的趋势/预测/快照语义，默认按直接证据回答",
        }

    def classify_question(self) -> dict:
        question = (self.question or "").strip()
        score = 0
        reasons = []

        if len(question) >= 25:
            score += 1
            reasons.append("问题描述较长，需要先做口径约束")

        if self._contains_any(question, ["趋势", "变化", "波动", "环比", "同比"]):
            score += 1
            reasons.append("包含趋势/变化分析")

        if self._contains_any(question, ["异常", "风险", "问题点", "突变", "波动大"]):
            score += 2
            reasons.append("包含异常或风险识别")

        if self._contains_any(question, ["原因", "归因", "为什么", "驱动因素", "影响因素"]):
            score += 2
            reasons.append("包含归因/原因判断")

        if self._contains_any(question, ["预测", "预估", "未来", "下周", "下月", "明年"]):
            score += 3
            reasons.append("包含预测诉求")

        if self._contains_any(question, ["对比", "比较", "差异", "分别", "Top", "TOP", "排名"]):
            score += 1
            reasons.append("包含对比或排名")

        if len(re.findall(r"[、，,和及以及并且并]|同时", question)) >= 3:
            score += 1
            reasons.append("问题包含多个并列分析对象")

        if score >= 5:
            complexity = "deep"
            max_steps = 12
        elif score >= 2:
            complexity = "medium"
            max_steps = 8
        else:
            complexity = "simple"
            max_steps = 4

        # 如用户通过 API 传入了 max_steps，则以用户配置为准
        if self._override_max_steps and self._override_max_steps > 0:
            max_steps = self._override_max_steps

        return {
            "complexity": complexity,
            "max_steps": max_steps,
            "reasons": reasons or ["问题单一，按简单路径直接回答"],
        }

    def build_execution_plan(self) -> dict:
        profile = self.classify_question()
        task_profile = self.classify_task_type()
        question = (self.question or "").strip()
        complexity = profile["complexity"]

        subquestions = [
            "确认问题口径、时间范围和主事实数据源",
        ]
        if task_profile["task_type"] == "snapshot":
            subquestions.extend([
                "明确“最近一次/最后一次/当前”应由哪个时间字段或有效状态判定",
                "一次取回能直接回答主问题的最新记录字段，避免先转成次数或趋势",
                "整理记录级证据、口径和局限",
            ])
        elif complexity == "simple":
            subquestions.extend([
                "一次取数直接回答主问题，避免无关扩展",
                "整理结论、口径和局限",
            ])
        else:
            if self._contains_any(question, ["趋势", "变化", "波动", "环比", "同比"]):
                subquestions.append("确认关键指标在时间维度上的变化趋势")
            if self._contains_any(question, ["对比", "比较", "差异", "分别", "Top", "TOP", "排名"]):
                subquestions.append("比较关键维度之间的差异或排序")
            if self._contains_any(question, ["异常", "风险", "问题点", "突变"]):
                subquestions.append("定位异常点并量化异常幅度")
            if self._contains_any(question, ["原因", "归因", "为什么", "驱动因素", "影响因素"]):
                subquestions.append("验证可能的归因线索，只保留有证据支撑的解释")
            if self._contains_any(question, ["预测", "预估", "未来", "下周", "下月", "明年"]):
                subquestions.append("判断是否具备预测条件，并在条件满足时给出预测结论")
            if len(subquestions) == 1:
                subquestions.append("围绕主问题补充一个必要的验证子问题，避免结论单薄")
            subquestions.append("汇总结论与局限，输出最终报告")

        # 去重并限制长度，保持执行收敛
        dedup_subquestions = []
        for item in subquestions:
            if item not in dedup_subquestions:
                dedup_subquestions.append(item)

        return {
            "main_question": question,
            "complexity": complexity,
            "max_steps": profile["max_steps"],
            "task_type": task_profile["task_type"],
            "query_mode": task_profile["query_mode"],
            "answer_granularity": task_profile["answer_granularity"],
            "allow_detail_rows": task_profile["allow_detail_rows"],
            "required_result_shape": task_profile["required_result_shape"],
            "required_fields": task_profile["required_fields"],
            "forbidden_query_shapes": task_profile["forbidden_query_shapes"],
            "reason_summary": [task_profile["reason"], *profile["reasons"]],
            "subquestions": dedup_subquestions[:4 if complexity != "deep" else 5],
            "stop_rules": [
                "若当前证据已足够回答主问题，则立即收敛，不为凑步骤继续查询",
                "禁止重复查询同一指标、同一时间窗、同一粒度的数据",
                "简单问题优先一次取数回答，复杂问题也必须围绕子问题推进",
            ],
        }

    def plan_to_markdown(self, plan: dict) -> str:
        subquestions = "\n".join(
            f"{idx + 1}. {item}" for idx, item in enumerate(plan.get("subquestions", []))
        )
        reasons = "\n".join(f"- {item}" for item in plan.get("reason_summary", []))
        stop_rules = "\n".join(f"- {item}" for item in plan.get("stop_rules", []))
        return (
            f"### 任务拆解\n"
            f"- 复杂度：`{plan.get('complexity', 'medium')}`\n"
            f"- 任务类型：`{plan.get('task_type', 'aggregate')}` / 查询模式：`{plan.get('query_mode', 'aggregate')}`\n"
            f"- 最大执行步数：`{plan.get('max_steps', self.max_steps)}`\n"
            f"- 主问题：{plan.get('main_question', self.question)}\n\n"
            f"### 复杂度判断依据\n{reasons}\n\n"
            f"### 子问题\n{subquestions}\n\n"
            f"### 收敛规则\n{stop_rules}\n"
        )

    async def execute_plan(self):
        """
        执行规划的主要方法，返回一个异步生成器用于流式响应
        """
        try:
            # 初始化LLMService
            await self.llm_service_wrapper.initialize_service()
            self.execution_plan = self.build_execution_plan()
            self.max_steps = self.execution_plan["max_steps"]
            self.chat_question.analysis_complexity = self.execution_plan["complexity"]
            self.chat_question.analysis_main_question = self.question
            self.chat_question.analysis_plan = self.execution_plan

            await self.queue.put({
                "type": "plan",
                "content": self.plan_to_markdown(self.execution_plan),
                "plan": self.execution_plan,
            })
            await self.queue.put({
                "type": "stage",
                "content": f"当前阶段：任务拆解（{self.execution_plan['complexity']}）",
                "stage": "plan",
            })

            self.context = AnalysisContext(
                llm_service=self.llm_service_wrapper.llm_service,
                message_type=self.message_type,
                is_chart_output=self.chat_question.is_chart_output,
                queue=self.queue,
                max_data_size=getattr(self.chat_question, 'max_data_length', None) or 1000,
                answer_granularity=(self.execution_plan or {}).get("answer_granularity"),
            )

            # 创建LangChain Agent使用的工具
            tools = [
                GetDataTool(context=self.context, session=self.session),
                InsightTool(context=self.context, session=self.session),
                SaveInsightTool(context=self.context, session=self.session),
                DataTransTool(context=self.context, session=self.session),
                FinalAnswerTool(context=self.context, session=self.session),
            ]

            # 使用自定义提示词
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.chat_question.plan_prompt()),
                # ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])

            # 创建agent
            agent = create_tool_calling_agent(llm=self.llm,
                                              tools=tools,
                                              prompt=prompt)

            # 创建executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=self.max_steps,
                early_stopping_method="force",
                return_intermediate_steps=True,
                handle_parsing_errors="工具调用失败，请重新调用工具并返回纯文本结果"
            )

            await self.analysis(agent_executor)

            await self.queue.put({
                **self.create_result(message_type="finish"),
                "chat_id": self.chat_question.chat_id,
            })

            return None

        except Exception as e:
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("执行规划出错")

            await self.queue.put(self.create_result(content=str(e), message_type='error'))

            return None

    def get_message_content(self, chunk):
        try:
            content = chunk["messages"][0].content
            return content
        except Exception as e:
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("获取message的content失败")
            return ""

    def process_thought_string(self, text: str):
        new_text = text.strip()

        # 情况1: 以Thought:开头并以</think>结尾
        if new_text.startswith("Thought:") and new_text.endswith("</think>"):
            content = f"\n#### 思考过程\n{new_text[8:-8]}\n"  # 去掉"Thought:"和"</think>"
            return content

        # 情况2: 以Thought:开头且</think>在中间
        elif new_text.startswith("Thought:") and "</think>" in new_text:
            think_end = new_text.find("</think>")
            # 提取Thought:和</think>之间的内容
            thought_content = new_text[8:think_end]  # 去掉"Thought:"，保留到</think>之前
            # 提取</think>之后的内容
            remaining_content = new_text[think_end + 8:]  # 跳过"</think>"的8个字符
            return f"\n#### 思考过程\n{thought_content}\n\n{remaining_content}\n"

        # 情况3: 以Thought:开头但没有</think>
        elif new_text.startswith("Thought:"):
            content = new_text[8:]  # 只去掉"Thought:"
            return f"\n#### 思考过程\n{content}\n"

        # 其他情况：返回原字符串
        else:
            return text

    def create_result(self,
                      reasoning_content="",
                      content="",
                      message_type=None):
        if message_type is None:
            message_type = self.message_type

        content = self.process_thought_string(content)

        return {"reasoning_content": reasoning_content,
                "content": content,
                "type": message_type}

    async def analysis(self, agent_executor):
        # 对用户仅推送「过程」类片段（默认 UI 收起）；不再逐步推送「分析步骤 1…N」
        await self.queue.put(self.create_result(
            content=(
                f"**分析意图**：{self.question}\n\n"
                f"**执行模式**：`{self.execution_plan['complexity'] if self.execution_plan else 'medium'}`，"
                f"最多 `{self.max_steps}` 步。\n\n"
                f"*取数与推理过程见下方折叠区域，最终以报告为准。*\n"
            ),
            message_type="process",
        ))

        async for chunk in agent_executor.astream({"input": self.question}):
            if "steps" in chunk.keys():
                continue
            elif "actions" in chunk.keys():
                content = self.get_message_content(chunk)
                if len(content) != 0:
                    await self.queue.put(self.create_result(content=content, message_type="process"))
            elif "output" in chunk.keys():
                content = self.get_message_content(chunk)
                if len(content) != 0:
                    await self.queue.put(self.create_result(content=content, message_type="process"))
            else:
                continue
