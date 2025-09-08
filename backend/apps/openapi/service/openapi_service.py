from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, AsyncGenerator, Tuple
from langchain.chat_models.base import BaseChatModel
import orjson
from fastapi import HTTPException
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy import and_
from sqlmodel import select

from apps.chat.curd.chat import get_chat_chart_data
from apps.chat.models.chat_model import ChatRecord
from apps.chat.task.llm import LLMService
from apps.openapi.models.openapiModels import IntentPayload
from apps.system.schemas.system_schema import BaseUserDTO
from common.core.config import settings
from common.core.deps import SessionDep
from common.core.deps import Trans
from common.core.security import create_access_token


def validate_user_status(user: BaseUserDTO, trans: Trans) -> None:
    """
    验证用户状态

    Args:
        user: 用户信息对象
        trans: 国际化翻译对象

    Raises:
        HTTPException: 当用户状态不符合要求时抛出异常
    """
    if not user:
        raise HTTPException(
            status_code=400,
            detail=trans('i18n_login.account_pwd_error')
        )

    if not user.oid or user.oid == 0:
        raise HTTPException(
            status_code=400,
            detail=trans('i18n_login.no_associated_ws',
                         msg=trans('i18n_concat_admin'))
        )

    if user.status != 1:
        raise HTTPException(
            status_code=400,
            detail=trans('i18n_login.user_disable',
                         msg=trans('i18n_concat_admin'))
        )


def identify_intent(llm: BaseChatModel, question: str) -> IntentPayload:
    """
    提取用户问题中的意图，转化为 IntentPayload 对象
    """
    intent_messages = [
        SystemMessage(content="""你是一个意图识别助手。请严格按照以下要求输出：

1. 你的任务是根据用户的问题，提取出一个 JSON 数据结构：
{
  "search": "<字符串，表示数据查询意图，必须提取>",
  "analysis": "<字符串，表示数据分析意图，必须提取>",
  "predict": "<字符串，表示趋势预测意图，可为空或省略>"
}

2. 提取逻辑：
- 如果用户的问题涉及查询数据库中的具体数据，填入 "search" 字段；如果没有查询意图，也必须给出空字符串。
- 如果用户的问题涉及数据统计、分析、总结，填入 "analysis" 字段；如果没有分析意图，也必须给出空字符串。
- 如果用户的问题涉及预测未来趋势或数值，填入 "predict" 字段；如果没有预测意图，可填空字符串。

3. 输出要求：
- 只输出 JSON，不要多余解释
- 保证 JSON 可被直接解析
"""),
        HumanMessage(content=f"用户问题：{question}")
    ]

    resp = llm.invoke(intent_messages)
    return IntentPayload.from_llm(resp.content)


async def merge_streaming_chunks(stream, session=None,
                                 llm_service: LLMService = None) -> \
        AsyncGenerator[str, None]:
    """
    合并流式输出的数据块

    规则:
    1. 对于 'predict-result' 和 'analysis-result' 类型的数据块不进行合并
    2. 对于其他类型，如果数据块中 reasoning_content 不为空，则不合并
    3. 对于其他相同类型的连续数据块，且 reasoning_content 为空，合并其 content 字段
    4. 每个数据块都是 'data:{json_data}' 格式
    5. 当收到 'finish' 类型时，调用 get_data 获取图表数据并发送

    Args:
        stream: 输入的流式数据生成器
        session: 数据库会话对象（可选）
        llm_service: LLM服务实例（可选）

    Yields:
        合并后的数据块
    """
    previous_chunk: Optional[Dict[str, Any]] = None
    recorded_id: Optional[int] = None

    # 判断是普通生成器还是异步生成器
    stream_iter = stream if hasattr(stream, '__aiter__') else _async_generator_wrapper(stream)

    try:
        async for chunk in stream_iter:
            # 忽略空行和非数据行
            if not chunk or not chunk.startswith('data:'):
                yield chunk
                continue

            try:
                # 解析数据块
                json_str = chunk[5:]  # 移除 'data:' 前缀
                current_chunk = orjson.loads(json_str)

                # 检查是否是 id 类型，记录 ID 值
                current_type = current_chunk.get('type', '')
                if current_type == 'id':
                    recorded_id = current_chunk.get('id')
                    yield chunk
                    continue

                # 检查是否是 finish 类型
                if current_type == 'finish':
                    # 先发送之前累积的块（如果有）
                    if previous_chunk:
                        yield f"data:{orjson.dumps(previous_chunk).decode()}\n\n"
                        previous_chunk = None

                    # 如果有记录的 ID 且有 session，调用 get_data 获取图表数据并发送
                    if recorded_id is not None and session is not None:
                        try:
                            # 调用内部的 _fetch_chart_data 函数
                            chart_data = get_chat_chart_data(
                                chart_record_id=recorded_id,
                                session=session
                            )

                            chart_data_chunk = {
                                "content": orjson.dumps(chart_data).decode(),
                                "type": "chart-data"
                            }
                            yield f"data:{orjson.dumps(chart_data_chunk).decode()}\n\n"

                            # 替换原有的分析处理代码
                            if llm_service is not None:
                                # 从数据库获取完整的聊天记录
                                stmt = select(ChatRecord).where(and_(ChatRecord.id == recorded_id))
                                result = session.execute(stmt)
                                record = result.scalar_one_or_none()

                                # 执行分析
                                if record and record.chart:
                                    # 执行分析任务
                                    llm_service.run_analysis_or_predict_task_async('analysis', record)
                                    # 获取分析结果流
                                    analysis_stream = llm_service.await_result()

                                    # 处理分析流
                                    async for analysis_chunk in _stream_generator(analysis_stream):
                                        yield analysis_chunk

                                    llm_service.run_recommend_questions_task_async()
                                    llm_service.set_record(record)
                                    recommend_questions_stream = llm_service.await_result()

                                    # 处理推荐问题流
                                    async for record_chunk in _stream_generator(recommend_questions_stream):
                                        yield record_chunk
                        except Exception as e:
                            # 如果获取数据失败，发送错误信息
                            error_chunk = {
                                "content": f"获取图表数据失败: {str(e)}",
                                "type": "error"
                            }
                            yield f"data:{orjson.dumps(error_chunk).decode()}\n\n"

                    # 发送 finish 块
                    yield chunk
                    continue

                # 检查是否需要特殊处理的类型
                no_merge_types = {'predict-result', 'analysis-result', "sql-result"}

                # 检查 reasoning_content 是否为空
                reasoning_content = current_chunk.get('reasoning_content', '')
                has_reasoning = bool(reasoning_content and reasoning_content.strip())

                # 如果没有前一个块，保存当前块
                if previous_chunk is None:
                    if current_type in no_merge_types or has_reasoning:
                        # 不需要合并的类型或包含 reasoning_content 的块直接输出
                        yield chunk
                    else:
                        # 需要合并的类型保存起来
                        previous_chunk = current_chunk
                    continue

                # 获取前一个块的信息
                previous_type = previous_chunk.get('type', '')
                previous_reasoning = previous_chunk.get('reasoning_content', '')
                previous_has_reasoning = bool(previous_reasoning and previous_reasoning.strip())

                # 如果类型不同，或者当前类型是不需要合并的类型，或者任一块包含 reasoning_content
                if (previous_type != current_type or
                        current_type in no_merge_types or
                        previous_type in no_merge_types or
                        has_reasoning or
                        previous_has_reasoning):
                    # 输出前一个块
                    yield f"data:{orjson.dumps(previous_chunk).decode()}\n\n"
                    # 更新previous_chunk
                    if current_type in no_merge_types or has_reasoning:
                        # 不需要合并的类型或包含 reasoning_content 的块直接输出
                        yield chunk
                        previous_chunk = None
                    else:
                        # 需要合并的类型保存起来
                        previous_chunk = current_chunk
                else:
                    # 类型相同且都不包含 reasoning_content，需要合并，合并content字段
                    previous_content = previous_chunk.get('content', '')
                    current_content = current_chunk.get('content', '')
                    previous_chunk['content'] = previous_content + current_content

            except orjson.JSONDecodeError:
                # 如果解析失败，直接输出原始数据
                if previous_chunk:
                    yield f"data:{orjson.dumps(previous_chunk).decode()}\n\n"
                    previous_chunk = None
                yield chunk

        # 输出最后一个块
        if previous_chunk:
            yield f"data:{orjson.dumps(previous_chunk).decode()}\n\n"
    finally:
        # 确保资源被正确清理
        if hasattr(stream_iter, 'aclose'):
            await stream_iter.aclose()


async def _async_generator_wrapper(stream):
    """将普通生成器包装为异步生成器"""
    for item in stream:
        yield item


async def _stream_generator(stream):
    """处理普通或异步生成器流"""
    if hasattr(stream, '__aiter__'):
        async for item in stream:
            yield item
    else:
        for item in stream:
            yield item


async def get_chat_record(session: SessionDep, chat_record_id: int) -> ChatRecord:
    """
    获取指定ID的聊天记录。

    Args:
        session: 数据库会话依赖
        chat_record_id: 聊天记录ID

    Returns:
        ChatRecord: 聊天记录对象

    Raises:
        HTTPException: 当聊天记录不存在时抛出400异常
    """
    # 查询聊天记录
    record = session.get(ChatRecord, chat_record_id)

    # 如果记录不存在，抛出异常
    if not record:
        raise HTTPException(
            status_code=400,
            detail=f"Chat record with id {chat_record_id} not found"
        )

    return record


def create_access_token_with_expiry(user_dict: dict) -> Tuple[str, str]:
    """
    创建访问令牌并计算过期时间

    Args:
        user_dict: 用户信息字典

    Returns:
        tuple: (访问令牌, 过期时间字符串)
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user_dict, expires_delta=access_token_expires)
    expire_time = (datetime.now(timezone.utc) + access_token_expires).strftime("%Y-%m-%d %H:%M:%S")
    return access_token, expire_time
