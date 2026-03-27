"""
深度分析 LangGraph 执行引擎。

约定：每个节点内必须先集中计算本节点依赖的 state 派生量（如 steps_used、max_iterations 等），
再在后续逻辑中只读使用；禁止在未赋值前引用，避免 UnboundLocalError。
"""
import asyncio
import json
import re
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph
from sqlmodel import Session

from apps.ai_model.model_factory import create_llm
from apps.openapi.agent.analysis_componet.analysis_tool import (
    DataTransTool,
    FinalAnswerTool,
    GetDataTool,
    InsightTool,
    SaveInsightTool,
)
from apps.openapi.agent.analysis_componet.data_model import AnalysisContext
from apps.openapi.agent.plan_agent import PlanAgent
from apps.openapi.models.openapiModels import OpenChatQuestion
from apps.openapi.service.openapi_llm import LLMService
from common.core.deps import CurrentAssistant, CurrentUser
from common.utils.utils import SQLBotLogUtil


class DeepAnalysisState(TypedDict, total=False):
    """LangGraph 状态，用于跟踪深度分析执行过程。"""

    question: str
    chat_id: int
    plan: Dict[str, Any]
    # 子任务相关
    subtasks: List[str]
    task_status: List[Dict[str, Any]]
    current_task_index: int
    # 步数与终止控制
    steps_used: int
    max_steps: int
    finished: bool
    error: Optional[str]
    # SQL 去重（规范化后的 SQL 签名列表）
    sql_history: List[str]
    # 反思节点结果（可选）
    reflect_done: bool
    need_more_data: bool
    # 本轮执行的增量信号（供 reflect 判断）
    last_insights_len: int
    last_tool_events_len: int
    last_new_insights: int
    last_has_bad_get_data: bool
    # 子任务重试控制
    task_retry_counts: Dict[int, int]
    # 重规划控制（避免死循环）
    need_replan: bool
    replan_count: int


class DeepAnalysisGraphRunner:
    """
    使用 LangGraph 承载深度分析执行逻辑的协调器。

    说明：
    - 对外仍然暴露一个 `run()` 协程，供 openapi 路由在线程内调用；
    - 内部通过 StateGraph 将 “规划 / 执行 / 收敛” 拆分为显式节点；
    - 现阶段尽量复用 PlanAgent 的规划逻辑和已有工具链，避免大面积重写。
    """

    def __init__(
        self,
            session: Session,
            current_user: CurrentUser,
            chat_question: OpenChatQuestion,
            current_assistant: CurrentAssistant,
            queue: asyncio.Queue,
            max_steps: Optional[int] = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.chat_question = chat_question
        self.current_assistant = current_assistant
        self.queue = queue
        self.max_steps = max_steps or 20

        self.llm_service: Optional[LLMService] = None
        self.context: Optional[AnalysisContext] = None
        self.tools: List[Any] = []

    async def _init_llm_service(self) -> None:
        """
        初始化 LLMService 与 AnalysisContext。

        这里不复用 PlanAgent.LLMServiceWrapper，以免引入不必要的依赖耦合。
        """
        self.llm_service = await LLMService.create(
            session=self.session,
            current_user=self.current_user,
            chat_question=self.chat_question,
            current_assistant=self.current_assistant,
            no_reasoning=self.chat_question.no_reasoning,
            embedding=True,
        )
        # 初始化用于规划/分析的 history
        try:
            self.llm_service.init_for_plan(self.session)
        except Exception as e:  # noqa: BLE001
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("初始化 LLMService plan history 失败")

        self.context = AnalysisContext(
            llm_service=self.llm_service,
            message_type="process",
            is_chart_output=self.chat_question.is_chart_output,
            queue=self.queue,
            max_data_size=getattr(self.chat_question, "max_data_length", None) or 1000,
            answer_granularity=None,
        )

        self.tools = [
            GetDataTool(context=self.context, session=self.session),
            InsightTool(context=self.context, session=self.session),
            SaveInsightTool(context=self.context, session=self.session),
            DataTransTool(context=self.context, session=self.session),
            FinalAnswerTool(context=self.context, session=self.session),
        ]

    async def _plan_node(self, state: DeepAnalysisState) -> DeepAnalysisState:
        """
        规划节点：复用 PlanAgent 的 build_execution_plan 逻辑，生成 execution_plan 并推送 plan/stage。
        """
        question = state.get("question") or self.chat_question.question
        # 仅用于借用 classify / build_execution_plan，不实际执行 agent
        plan_agent = PlanAgent(
            session=self.session,
            current_user=self.current_user,
            chat_question=self.chat_question,
            current_assistant=self.current_assistant,
            max_steps=self.max_steps,
            queue=self.queue,
            llm=None,
        )
        plan_agent.question = question
        execution_plan = plan_agent.build_execution_plan()

        # 动态修订（V1）：在不推翻基础计划的前提下，结合 schema 对「子问题/取数约束」做一次 LLM 修订
        # - 目标：减少模板化子问题，让 subquestions/required_fields 更贴近 db_schema
        # - 失败：解析异常则直接回退基础计划
        try:
            schema_text = getattr(self.chat_question, "db_schema", "") or ""
            llm = await create_llm(use_tool=False)
            from langchain_core.messages import HumanMessage, SystemMessage

            system_prompt = (
                "你是资深数据分析师与数据建模专家。你将基于用户问题与数据库 Schema，修订一个深度分析执行计划。\n"
                "要求：只输出一个 JSON 对象（不要 Markdown），字段仅允许如下键：\n"
                "- subquestions: string[]（3-5 条，具体可执行，尽量与 schema 字段/表名对齐）\n"
                "- required_fields: string[]（需要的字段/维度/指标，必须能在 schema 中找到或明确来自哪个表）\n"
                "- forbidden_query_shapes: string[]（需要避免的取数形态）\n"
                "- required_result_shape: string（期望结果形态，便于验证）\n"
                "强约束：不得编造不存在的表/字段；若 schema 信息不足，请在 required_fields 里写明“需要补充的字段/口径信息”。"
            )
            human_prompt = (
                f"用户问题：{question}\n\n"
                f"数据库 Schema：\n{schema_text}\n\n"
                f"基础计划（JSON）：\n{json.dumps(execution_plan, ensure_ascii=False, indent=2)}\n\n"
                "请输出修订后的 JSON。"
            )
            resp = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)])
            content = getattr(resp, "content", "") if resp is not None else ""
            m = re.search(r"\{.*\}", content, flags=re.S)
            if m:
                patch = json.loads(m.group(0))
                if isinstance(patch, dict):
                    for k in ("subquestions", "required_fields", "forbidden_query_shapes", "required_result_shape"):
                        if k in patch and patch[k]:
                            execution_plan[k] = patch[k]
        except Exception:
            # 动态修订失败不影响主流程
            pass

        # 将规划结果写回 chat_question，保持与旧实现兼容
        complexity = execution_plan.get("complexity") or "medium"
        self.chat_question.analysis_complexity = complexity
        self.chat_question.analysis_main_question = question
        self.chat_question.analysis_plan = execution_plan

        await self.queue.put(
            {
                "type": "plan",
                "content": plan_agent.plan_to_markdown(execution_plan),
                "plan": execution_plan,
            }
        )
        await self.queue.put(
            {
                "type": "stage",
                "content": f"当前阶段：任务拆解（{complexity}）",
                "stage": "plan",
            }
        )

        # 初始化 LLMService & 工具上下文
        await self._init_llm_service()
        if self.context is not None:
            self.context.answer_granularity = execution_plan.get("answer_granularity")

        state["plan"] = execution_plan
        # 初始化子任务与状态列表
        subtasks: List[str] = execution_plan.get("subquestions") or []
        state["subtasks"] = subtasks
        state["task_status"] = [{"done": False, "reason": ""} for _ in subtasks]
        state["max_steps"] = execution_plan.get("max_steps", self.max_steps)
        state.setdefault("steps_used", 0)
        state.setdefault("current_task_index", 0)
        state.setdefault("sql_history", [])
        state.setdefault("task_retry_counts", {})
        state["need_more_data"] = False
        state["need_replan"] = False
        state.setdefault("replan_count", 0)
        state["finished"] = False
        return state

    async def _execute_node(
        self,
        state: DeepAnalysisState,
        subtask: Optional[str] = None,
    ) -> DeepAnalysisState:
        """
        执行节点：在当前规划下运行多步 Agent。

        为了与现有行为兼容，这里仍然使用 LangChain Agent + tools，
        但通过 LangGraph 的 state 显式记录 steps_used 与错误信息。
        """
        from langchain.agents import create_agent
        from langchain_core.messages import AIMessage, HumanMessage as HM

        if self.llm_service is None or self.context is None:
            await self._init_llm_service()

        # 同步 sql_history 到 context，供 GetDataTool 去重
        if self.context is not None:
            self.context.sql_history = list(state.get("sql_history") or [])

        # 本节点所需参数在此处一次性计算，后续只读使用，禁止在未定义前引用
        execution_plan = state.get("plan") or {}
        max_steps = int(state.get("max_steps") or self.max_steps)
        steps_used = int(state.get("steps_used") or 0)
        remaining = max(0, max_steps - steps_used)
        max_iterations_this_turn = max(1, min(remaining, 6))
        # 执行前抓取可观测长度，用于 reflect 增量判断
        insights_before = len(getattr(self.context, "insights", []) or []) if self.context is not None else 0
        events_before = len(getattr(self.context, "tool_events", []) or []) if self.context is not None else 0

        llm = await create_llm()

        inner_agent = create_agent(
            model=llm,
            tools=self.tools,
            system_prompt=self.chat_question.plan_prompt(),
        )

        # 向前端推送一条“执行模式/子任务”说明，保持与旧实现体验一致，并显式标注当前子任务
        complexity_label = execution_plan.get("complexity") or "medium"
        if subtask:
            intro = (
                f"**当前子任务**：{subtask}\n\n"
                f"**执行模式**：`{complexity_label}`，"
                f"最多 `{max_steps}` 步（全局）。\n\n"
                f"*本轮仅围绕该子任务进行取数与分析，禁止超前解决其他子问题。*\n"
            )
        else:
            intro = (
                f"**分析意图**：{self.chat_question.question}\n\n"
                f"**执行模式**：`{complexity_label}`，"
                f"最多 `{max_steps}` 步。\n\n"
                f"*取数与推理过程见下方折叠区域，最终以报告为准。*\n"
            )
        if self.context is not None:
            await self.queue.put(
                self.context.create_result(
                    content=intro,
                    message_type="process",
                )
            )

        try:
            if subtask:
                retry_note = ""
                idx = int(state.get("current_task_index") or 0)
                retry_counts = state.get("task_retry_counts") or {}
                if retry_counts.get(idx, 0) > 0:
                    retry_note = (
                        "\n\n补充要求：上一轮证据不足/结果异常，请换一种取数口径或下钻维度重新获取证据；"
                        "避免重复查询同语义 SQL；尽量产出可验证洞察并保存。"
                    )
                user_input = (
                    f"{self.chat_question.question}\n\n"
                    f"当前子任务：{subtask}\n"
                    f"请只围绕当前子任务进行取数和分析，禁止回答尚未到达的其他子问题。"
                    f"{retry_note}"
                )
            else:
                user_input = self.chat_question.question

            iteration_count = 0
            async for event in inner_agent.astream_events(
                {"messages": [HM(content=user_input)]},
                version="v2",
            ):
                kind = event.get("event", "")
                data = event.get("data", {})

                if kind == "on_tool_end":
                    steps_used += 1
                    iteration_count += 1

                if kind == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and isinstance(chunk, AIMessage):
                        text = chunk.content
                        if isinstance(text, str) and text.strip() and self.context is not None:
                            await self.queue.put(
                                self.context.create_result(
                                    content=text,
                                    message_type="process",
                                )
                            )

                if steps_used >= max_steps or iteration_count >= max_iterations_this_turn:
                    break

            state["steps_used"] = steps_used
            # 写回 sql_history 供下一轮/节点使用
            if self.context is not None:
                state["sql_history"] = list(getattr(self.context, "sql_history", []) or [])
                # 写回可观测增量信号给 reflect
                insights_after = len(getattr(self.context, "insights", []) or [])
                events_after = len(getattr(self.context, "tool_events", []) or [])
                new_insights = max(0, insights_after - insights_before)
                new_events = max(0, events_after - events_before)
                has_bad = False
                try:
                    evs = (getattr(self.context, "tool_events", []) or [])[max(0, events_after - new_events):]
                    for ev in evs:
                        if isinstance(ev, dict) and ev.get("tool") == "get_data" and ev.get("status") in ("error", "empty", "dedup"):
                            has_bad = True
                            break
                except Exception:
                    has_bad = False
                state["last_insights_len"] = insights_after
                state["last_tool_events_len"] = events_after
                state["last_new_insights"] = new_insights
                state["last_has_bad_get_data"] = has_bad
            return state
        except Exception as e:  # noqa: BLE001
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("深度分析执行节点出错")
            state["error"] = str(e)
            return state

    async def _final_node(self, state: DeepAnalysisState) -> DeepAnalysisState:
        """
        收敛节点：发送 finish 消息，并将 chat_id 一并写入，保持与旧实现兼容。
        """
        if self.context is not None:
            await self.queue.put(
                self.context.create_result(
                    content="深度分析已完成。",
                    message_type="process",
                )
            )

        await self.queue.put(
            {
                "reasoning_content": "",
                "content": "",
                "type": "finish",
                "chat_id": self.chat_question.chat_id,
            }
        )
        state["finished"] = True
        return state

    async def _decide_task_node(self, state: DeepAnalysisState) -> DeepAnalysisState:
        """
        任务选择节点：目前仅作为路由决策的占位节点，实际跳转逻辑由 conditional edges 控制。

        后续可以在这里加入基于 task_status 的更加精细的任务切换规则。
        """
        return state

    async def _execute_task_node(self, state: DeepAnalysisState) -> DeepAnalysisState:
        """
        执行子任务节点：从 subtasks 中取出当前子任务，调用 _execute_node 完成一轮针对性的分析，
        并将该子任务标记为已执行（current_task_index 由 reflect 节点推进）。
        """
        subtasks: List[str] = state.get("subtasks") or []
        idx = int(state.get("current_task_index") or 0)

        current_subtask: Optional[str] = None
        if 0 <= idx < len(subtasks):
            current_subtask = subtasks[idx]

        new_state = await self._execute_node(state, subtask=current_subtask)

        if 0 <= idx < len(subtasks):
            status: List[Dict[str, Any]] = new_state.get("task_status") or [
                {"done": False, "reason": ""} for _ in subtasks
            ]
            while len(status) < len(subtasks):
                status.append({"done": False, "reason": ""})
            status[idx] = {
                "done": True,
                "reason": "已针对该子任务执行一轮分析",
            }
            new_state["task_status"] = status
            # 不在此处推进 current_task_index，交给 _reflect_node 决定是否推进或再执行一轮

        return new_state

    async def _reflect_node(self, state: DeepAnalysisState) -> DeepAnalysisState:
        """
        反思节点：根据步数与收敛规则决定是否推进到下一子任务，或强制收敛。
        若 steps_used >= max_steps - 1 则强制不再继续取数，直接标记当前子任务完成并交由 decide 转 final。
        """
        steps_used = int(state.get("steps_used") or 0)
        max_steps = int(state.get("max_steps") or 0)
        subtasks: List[str] = state.get("subtasks") or []
        idx = int(state.get("current_task_index") or 0)

        # 硬收敛：步数即将用尽时不再为当前子任务补数据
        if max_steps > 0 and steps_used >= max_steps - 1:
            state["need_more_data"] = False
            state["reflect_done"] = True
            if idx < len(subtasks):
                state["current_task_index"] = idx + 1
            return state

        # 智能反思：基于“本轮是否新增洞察”与“get_data 是否出现空/错/重复”决定是否重试
        new_insights = int(state.get("last_new_insights") or 0)
        has_bad = bool(state.get("last_has_bad_get_data"))
        retry_counts = state.get("task_retry_counts") or {}
        cur_retry = int(retry_counts.get(idx, 0) or 0)
        max_retries = 1
        replan_count = int(state.get("replan_count") or 0)
        max_replans = 1

        if idx < len(subtasks):
            # 规则：若本轮没有新增洞察，且出现空/错/重复取数信号，则优先重试当前子任务一次
            if (new_insights <= 0 and has_bad) and cur_retry < max_retries:
                retry_counts[idx] = cur_retry + 1
                state["task_retry_counts"] = retry_counts
                state["need_more_data"] = True
                state["reflect_done"] = True
                if self.context is not None:
                    await self.queue.put(
                        self.context.create_result(
                            content=(
                                f"\n**子任务 {idx + 1}/{len(subtasks)} 证据不足**："
                                "检测到空/错误/重复取数且未形成新洞察，触发重试（换口径/下钻维度）。\n"
                            ),
                            message_type="process",
                        )
                    )
                return state

            # 若重试仍无洞察且仍出现坏信号，则触发一次 replan（回到 planning，重新生成子任务）
            if (new_insights <= 0 and has_bad) and cur_retry >= max_retries and replan_count < max_replans:
                state["need_more_data"] = False
                state["need_replan"] = True
                state["reflect_done"] = True
                state["replan_count"] = replan_count + 1
                state["current_task_index"] = 0
                state["task_retry_counts"] = {}
                if self.context is not None:
                    await self.queue.put(
                        self.context.create_result(
                            content=(
                                "\n**触发重规划**：当前子任务多次未形成有效洞察且取数存在空/错误/重复信号，"
                                "将回到规划阶段，基于 schema 与已有线索重新生成子任务。\n"
                            ),
                            message_type="process",
                        )
                    )
                return state

            # 否则推进到下一项
            state["need_more_data"] = False
            state["need_replan"] = False
            state["reflect_done"] = True
            state["current_task_index"] = idx + 1
            if self.context is not None:
                await self.queue.put(
                    self.context.create_result(
                        content=f"\n**子任务 {idx + 1}/{len(subtasks)} 已完成**，进入下一项。\n",
                        message_type="process",
                    )
                )
            return state

        if not subtasks and idx == 0:
            # 无子任务时只执行了一轮整题分析，推进以便 decide 进入 report
            state["need_more_data"] = False
            state["reflect_done"] = True
            state["current_task_index"] = 1
            return state

        state["need_more_data"] = False
        state["reflect_done"] = True
        return state

    async def _report_node(self, state: DeepAnalysisState) -> DeepAnalysisState:
        """
        报告节点：在进入 final 前必执行一次，根据已沉淀的洞察与规划生成结构化最终报告，
        保证「结论观点明确、过程可回溯」：即使用户未调用 final_answer 工具也会有一份完整报告。
        """
        question = state.get("question") or (self.chat_question.question or "")
        plan = state.get("plan") or {}
        plan_summary = (
            f"- 复杂度：{plan.get('complexity', 'medium')}\n"
            f"- 子问题：{chr(10).join(plan.get('subquestions') or [])}"
        )
        insights_list = getattr(self.context, "insights", None) if self.context else None
        insights_text = ""
        if insights_list:
            for i, item in enumerate(insights_list, 1):
                inc = item if isinstance(item, dict) else {}
                insight = inc.get("insight")
                proc = inc.get("analysis_process", "")
                if isinstance(insight, list):
                    insight = "；".join(str(x) for x in insight)
                insights_text += f"\n### 洞察 {i}\n- 结论：{insight or ''}\n- 过程：{proc}\n"

        system_prompt = (
            "你正在生成深度分析的最终报告。输出必须是面向用户的 Markdown，且必须依次包含以下六级标题与内容：\n"
            "## 1. 问题与口径\n（问题、时间范围、主数据源与指标说明）\n"
            "## 2. 核心结论\n（3～5 条 bullet，每条观点明确、可追溯）\n"
            "## 3. 数据支撑\n（表格或关键数据摘要 + 简短解释）\n"
            "## 4. 风险与异常\n（如有）\n"
            "## 5. 建议\n（可执行的具体建议）\n"
            "## 6. 局限\n（数据或分析范围限制）\n"
            "要求：中文、无代码；每条结论需与下方「已沉淀洞察」对应；若洞察较少则基于问题与规划做合理归纳。"
        )
        user_prompt = (
            f"**主问题**：{question}\n\n**规划摘要**：\n{plan_summary}\n\n**已沉淀洞察**：{insights_text or '（暂无已保存洞察，请基于主问题与规划归纳）'}"
        )

        try:
            llm = await create_llm(use_tool=False)
            from langchain_core.messages import HumanMessage, SystemMessage
            response = await llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
            report_content = getattr(response, "content", None) or str(response)
        except Exception as e:  # noqa: BLE001
            SQLBotLogUtil.error(e)
            report_content = (
                f"## 1. 问题与口径\n{question}\n\n"
                f"## 2. 核心结论\n- 分析因生成报告时异常而未能完整输出，请查看上方「取数与推理过程」中的沉淀结论。\n\n"
                f"## 3. 数据支撑\n见上方过程与保存的分析结果。\n\n"
                f"## 4. 风险与异常\n报告生成异常：{e}\n\n## 5. 建议\n重试或查看过程详情。\n\n## 6. 局限\n-"
            )

        if self.context is not None:
            await self.queue.put(
                self.context.create_result(content="当前阶段：汇总报告", message_type="stage")
            )
            await self.queue.put(
                self.context.create_result(content=report_content, message_type="report")
            )
        return state

    def _build_graph(self) -> Any:
        """
        构建 LangGraph StateGraph。

        当前版本拓扑：
        plan -> decide_task ⇄ (execute_task -> reflect) -> report -> final (END)
        report 节点保证在结束前必生成一份结构化最终报告，便于过程可回溯、结论明确。
        """
        graph = StateGraph(DeepAnalysisState)

        # 包装节点为无参函数形式以便传入外部依赖
        async def plan_node(state: DeepAnalysisState) -> DeepAnalysisState:
            return await self._plan_node(state)

        async def decide_task_node(state: DeepAnalysisState) -> DeepAnalysisState:
            return await self._decide_task_node(state)

        async def execute_task_node(state: DeepAnalysisState) -> DeepAnalysisState:
            # 如果已出现错误，直接跳到最终节点，由 conditional edges 处理
            if state.get("error"):
                return state
            return await self._execute_task_node(state)

        async def final_node(state: DeepAnalysisState) -> DeepAnalysisState:
            return await self._final_node(state)

        async def reflect_node(state: DeepAnalysisState) -> DeepAnalysisState:
            return await self._reflect_node(state)

        async def report_node(state: DeepAnalysisState) -> DeepAnalysisState:
            return await self._report_node(state)

        # 节点名不可与 state 键重名（如 "plan" 与 state["plan"] 冲突），故用 planning
        graph.add_node("planning", plan_node)
        graph.add_node("decide_task", decide_task_node)
        graph.add_node("execute_task", execute_task_node)
        graph.add_node("reflect", reflect_node)
        graph.add_node("report", report_node)
        graph.add_node("final", final_node)

        graph.set_entry_point("planning")
        graph.add_edge("planning", "decide_task")

        # 根据当前状态决定从 decide_task 跳转到 execute_task 还是 report（收敛时先报告再结束）
        def route_from_decide(state: DeepAnalysisState) -> str:
            if state.get("error"):
                return "report"
            steps_used = int(state.get("steps_used") or 0)
            max_steps = int(state.get("max_steps") or 0)
            if max_steps > 0 and steps_used >= max_steps:
                return "report"
            if state.get("need_replan"):
                return "planning"
            # 若 reflect 判断需要补证据/重试当前子任务，则继续 execute_task
            if state.get("need_more_data"):
                return "execute_task"
            subtasks: List[str] = state.get("subtasks") or []
            idx = int(state.get("current_task_index") or 0)
            # 无子任务时也执行一次（相当于整题一次 run），之后 idx 被 reflect 设为 1，下一轮会进 report
            if not subtasks:
                return "execute_task"
            if idx >= len(subtasks):
                return "report"
            return "execute_task"

        graph.add_conditional_edges(
            "decide_task",
            route_from_decide,
            {
                "planning": "planning",
                "execute_task": "execute_task",
                "report": "report",
            },
        )

        # 执行完当前子任务后进入反思，再回到 decide_task；收敛时先报告再结束
        graph.add_edge("execute_task", "reflect")
        graph.add_edge("reflect", "decide_task")
        graph.add_edge("report", "final")
        graph.add_edge("final", END)

        return graph.compile()

    async def run(self) -> None:
        """
        外部调用入口：根据 chat_question 构造初始状态并运行图。
        """
        app = self._build_graph()
        initial_state: DeepAnalysisState = {
            "question": self.chat_question.question,
            "chat_id": int(self.chat_question.chat_id or 0),
            "steps_used": 0,
            "max_steps": int(self.max_steps),
            "sql_history": [],
        }
        await app.ainvoke(initial_state)

