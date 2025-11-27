# -*- coding: utf-8 -*-
""" 
@Time    : 2025/11/10 16:42
@Author  : chenshu
@FileName: plan_agent.py
@Description: 
"""
import asyncio
from typing import Any

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
                 max_steps=20,
                 queue: asyncio.Queue = None,
                 llm: Any = None
                 ):
        self.current_user = current_user
        self.chat_question = chat_question
        self.question = self.chat_question.question
        self.max_steps = max_steps
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

        # 默认返回的message_type
        self.message_type = "analysis-result"
        self.session = session

    async def execute_plan(self):
        """
        执行规划的主要方法，返回一个异步生成器用于流式响应
        """
        try:
            # 初始化LLMService
            await self.llm_service_wrapper.initialize_service()

            self.context = AnalysisContext(llm_service=self.llm_service_wrapper.llm_service,
                                           message_type=self.message_type,
                                           is_chart_output=self.chat_question.is_chart_output,
                                           queue=self.queue)

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

            await self.queue.put(self.create_result(content=f"\n全部分析结束\n"))
            await self.queue.put(self.create_result(message_type="finish"))

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
        step = 1

        await self.queue.put(self.create_result(content=f"# 分析任务  \n{self.question}  \n"))
        await self.queue.put(self.create_result(content=f"\n# 分析过程  \n"))
        await self.queue.put(self.create_result(content=f"\n## 分析步骤 {step}  \n"))

        async for chunk in agent_executor.astream({"input": self.question}):
            # SQLBotLogUtil.info(chunk)
            # SQLBotLogUtil.info(chunk.keys())

            if "steps" in chunk.keys():
                step += 1
                await self.queue.put(self.create_result(content=f"\n## 分析步骤 {step}  \n"))

            elif "actions" in chunk.keys():
                content = self.get_message_content(chunk)
                if len(content) != 0:
                    await self.queue.put(self.create_result(content=content))

            elif "output" in chunk.keys():
                content = self.get_message_content(chunk)
                if len(content) != 0:
                    await self.queue.put(self.create_result(content=content))
            else:
                continue
