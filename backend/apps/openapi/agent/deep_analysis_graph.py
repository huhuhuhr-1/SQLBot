"""
深度分析 LangGraph 执行引擎。

约定：每个节点内必须先集中计算本节点依赖的 state 派生量（如 steps_used、max_iterations 等），
再在后续逻辑中只读使用；禁止在未赋值前引用，避免 UnboundLocalError。
"""
import asyncio
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
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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

        llm = await create_llm()

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.chat_question.plan_prompt()),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_tool_calling_agent(
            llm=llm,
            tools=self.tools,
            prompt=prompt,
        )

        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=max_iterations_this_turn,
            early_stopping_method="force",
            return_intermediate_steps=True,
            handle_parsing_errors="工具调用失败，请重新调用工具并返回纯文本结果",
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
                user_input = (
                    f"{self.chat_question.question}\n\n"
                    f"当前子任务：{subtask}\n"
                    f"请只围绕当前子任务进行取数和分析，禁止回答尚未到达的其他子问题。"
                )
            else:
                user_input = self.chat_question.question

            async for chunk in agent_executor.astream({"input": user_input}):
                if "steps" in chunk:
                    # 仅用于调试，不推给前端
                    continue
                if "actions" in chunk or "output" in chunk:
                    # 简单计为一步
                    steps_used += 1
                    content = ""
                    try:
                        content = chunk["messages"][0].content
                    except Exception:  # noqa: BLE001
                        content = ""
                    if content and self.context is not None:
                        await self.queue.put(
                            self.context.create_result(
                                content=content,
                                message_type="process",
                            )
                        )
                if steps_used >= max_steps:
                    break

            state["steps_used"] = steps_used
            # 写回 sql_history 供下一轮/节点使用
            if self.context is not None:
                state["sql_history"] = list(getattr(self.context, "sql_history", []) or [])
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

        # 默认：当前子任务执行一轮后视为完成，推进到下一项
        state["need_more_data"] = False
        state["reflect_done"] = True
        if idx < len(subtasks):
            state["current_task_index"] = idx + 1
            if self.context is not None:
                await self.queue.put(
                    self.context.create_result(
                        content=f"\n**子任务 {idx + 1}/{len(subtasks)} 已完成**，进入下一项。\n",
                        message_type="process",
                    )
                )
        elif not subtasks and idx == 0:
            # 无子任务时只执行了一轮整题分析，推进以便 decide 进入 final
            state["current_task_index"] = 1

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

