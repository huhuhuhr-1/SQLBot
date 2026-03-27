# apps/openapi/llm_examples.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncGenerator
import json
import asyncio

from apps.openapi.llm.my_llm import LLMManager
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.output_parsers import PydanticOutputParser
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool

router = APIRouter(tags=["demo"], prefix="/demo")


# 数据模型定义
class QuestionRequest(BaseModel):
    question: str
    mode: str = "normal"  # normal, stream, chain, chain-stream, structured, agent
    context: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: float = 0.7


class PersonData(BaseModel):
    name: str
    age: Optional[int] = None
    occupation: Optional[str] = None
    skills: List[str] = []


# 工具定义
@tool
def get_weather(location: str) -> str:
    """获取天气信息"""
    return f"{location}当前天气晴朗，温度25°C"


@tool
def search_knowledge(query: str) -> str:
    """搜索知识库"""
    return f"关于'{query}'的搜索结果：相关信息3条"


# 示例1：基础问答
@router.post("/ask")
async def basic_qa(request: QuestionRequest):
    """基础问答功能"""
    try:
        llm = await LLMManager.get_default_llm()
        response = await llm.ainvoke(request.question)
        return {"answer": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 示例2：流式问答
@router.post("/ask-stream")
async def stream_qa(request: QuestionRequest):
    """流式问答功能"""

    async def generate_response():
        try:
            llm = await LLMManager.get_default_llm()
            async for chunk in llm.astream(request.question):
                if chunk.content:
                    yield f"data: {json.dumps({'content': chunk.content})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate_response(), media_type="text/event-stream")


# 示例3：Chain模式
@router.post("/ask-chain")
async def chain_qa(request: QuestionRequest):
    """使用Chain的问答功能"""
    try:
        llm = await LLMManager.get_default_llm()

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个 helpful 的助手，请用中文回答问题。"),
            ("user", "{question}")
        ])

        chain = prompt | llm | StrOutputParser()
        response = await chain.ainvoke({"question": request.question})

        return {"answer": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 示例4：结构化数据提取
@router.post("/extract-data")
async def extract_structured_data(request: QuestionRequest):
    """提取结构化数据"""
    try:
        llm = await LLMManager.get_default_llm()

        parser = PydanticOutputParser(pydantic_object=PersonData)

        prompt = ChatPromptTemplate.from_template(
            "从以下文本中提取个人信息，如果某些信息找不到，请使用默认值：\n"
            "文本：{text}\n"
            "输出格式要求：{format_instructions}\n"
            "注意：\n"
            "1. age字段必须是数字，如果找不到请填0\n"
            "2. occupation字段必须是字符串，如果找不到请填'未知'\n"
            "3. skills字段可以为空列表\n"
            "4. 严格按照JSON格式输出，不要添加其他内容"
        )

        chain = prompt | llm | parser
        result = await chain.ainvoke({
            "text": request.question,
            "format_instructions": parser.get_format_instructions()
        })

        return result.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 示例5：带记忆的对话
@router.post("/chat-with-memory")
async def chat_with_memory(request: ChatRequest):
    """带记忆的对话"""
    try:
        llm = await LLMManager.get_default_llm()

        memory = ConversationBufferMemory(memory_key="history", return_messages=True)

        # 添加历史消息到记忆中
        for msg in request.messages[:-1]:
            if msg.role == "user":
                memory.chat_memory.add_user_message(msg.content)
            else:
                memory.chat_memory.add_ai_message(msg.content)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个 helpful 的助手，请用中文回答问题。"),
            ("placeholder", "{history}"),
            ("user", "{input}"),
        ])

        chain = prompt | llm
        response = await chain.ainvoke({
            "input": request.messages[-1].content,
            "history": memory.chat_memory.messages
        })

        return {"answer": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 示例6：使用工具的智能代理
@router.post("/agent")
async def agent_with_tools(request: QuestionRequest):
    """使用工具的智能代理"""
    try:
        llm = await LLMManager.get_default_llm()

        tools = [get_weather, search_knowledge]

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个 helpful 的助手，可以使用提供的工具来回答问题。"),
            ("user", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        response = await agent_executor.ainvoke({"input": request.question})

        return {"answer": response["output"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 示例7：并行处理
@router.post("/parallel-process")
async def parallel_processing(request: QuestionRequest):
    """并行处理多个任务"""
    try:
        llm = await LLMManager.get_default_llm()

        # 定义多个处理任务
        tasks = [
            llm.ainvoke(f"请总结以下内容：{request.question}"),
            llm.ainvoke(f"请提取关键词：{request.question}"),
            llm.ainvoke(f"请分析情感倾向：{request.question}")
        ]

        # 并行执行
        results = await asyncio.gather(*tasks)

        return {
            "summary": results[0].content,
            "keywords": results[1].content,
            "sentiment": results[2].content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
