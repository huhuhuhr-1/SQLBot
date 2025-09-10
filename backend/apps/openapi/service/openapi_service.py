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
from apps.openapi.models.openapiModels import IntentPayload, OpenChatQuestion
from apps.system.schemas.system_schema import BaseUserDTO
from common.core.config import settings
from common.core.db import get_session
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
    提取用户问题中的意图，转化为 IntentPayload 对象。
    核心原则：search 字段必须存在且贴近用户原意，仅做必要规范化，作为后续数据查询的主输入。
    analysis 和 predict 为附加意图，可为空。
    """
    system_prompt = (
        "你是一个意图结构化助手。请将用户问题转化为标准的 JSON 格式，用于驱动数据查询与分析系统。\n\n"
        "### 输出格式要求\n"
        "只输出以下结构的 JSON，不要任何解释：\n"
        "{\n"
        '  "search": "<字符串，表示用户想要查询的具体数据内容。必须非空，且尽可能贴近用户原意，仅做必要规范化>",\n'
        '  "analysis": "<字符串，表示是否需要进行归因、对比、总结等分析。若无则为\"\">",\n'
        '  "predict": "<字符串，表示是否需要预测未来趋势或数值。若无则为\"\">"\n'
        "}\n\n"
        "### 规则说明\n"
        "1. **search 字段（必填）**：\n"
        "- 必须提取出用户真正想查的数据对象或指标\n"
        "- 可对用户语言进行轻微规范化（如补全省略、去除语气词），但不得改变原意\n"
        "- 示例：\n"
        "  - '销售额为啥降了？' → search: '销售额下降的情况'\n"
        "  - '最近订单多吗？' → search: '最近的订单数量'\n"
        "  - '预测下季度增长' → search: '下季度的增长情况'\n\n"
        "2. **analysis 字段**：\n"
        "- 如果问题包含‘为什么’、‘原因’、‘哪个好’、‘总结’等，说明需要分析\n"
        "- 提取分析目标，例如：'销售额下降的原因'\n\n"
        "3. **predict 字段**：\n"
        "- 如果明确提到‘预测’、‘估算’、‘未来’等，才填写\n"
        "- 否则留空\n\n"
        "### 重要提醒\n"
        "- search 必须非空！所有问题都能转化为一个查询目标\n"
        "- 所有字段值必须是字符串\n"
        "- 不要添加额外字段或注释"
    )

    human_prompt = f"用户问题：{question}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]

    try:
        response = llm.invoke(messages)
        return IntentPayload.from_llm(response.content.strip())
    except Exception as e:
        raise RuntimeError(f"意图识别失败：{str(e)}")


async def merge_streaming_chunks(stream,
                                 llm_service: LLMService = None,
                                 payload: IntentPayload = None,
                                 request_question: OpenChatQuestion = None) -> AsyncGenerator[str, None]:
    """
    合并流式输出的数据块

    规则:
    1. 对于 'predict-result' 和 'analysis-result' 类型的数据块不进行合并
    2. 对于其他类型，如果数据块中 reasoning_content 不为空，则不合并
    3. 对于其他相同类型的连续数据块，且 reasoning_content 为空，合并其 content 字段
    4. 每个数据块都是 'data:{json_data}' 格式
    5. 当收到 'finish' 类型时，调用 get_data 获取图表数据并发送

    Args:
        request_question: 用户问题
        payload: 意图识别
        stream: 输入的流式数据生成器
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
                    if recorded_id is not None:
                        try:
                            chart_data = None
                            for session in get_session():
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

                            data_finish_chunk = {
                                "content": recorded_id,
                                "type": "data-finish"
                            }

                            yield f"data:{orjson.dumps(data_finish_chunk).decode()}\n\n"

                            # 替换原有的分析处理代码
                            # 示例：从某个地方获取 payload
                            if llm_service is not None:
                                # 从数据库获取完整的聊天记录
                                stmt = select(ChatRecord).where(and_(ChatRecord.id == recorded_id))
                                record = None
                                question = None
                                for session in get_session():
                                    result = session.execute(stmt)
                                    record = result.scalar_one_or_none()
                                    question = record.question
                                # 执行分析
                                if record and record.chart:
                                    # 分析
                                    if request_question.analysis and hasattr(payload,
                                                                             'analysis') and payload.analysis != "":
                                        record.question = payload.analysis
                                        # 执行分析任务
                                        llm_service.run_analysis_or_predict_task_async('analysis', record)
                                        # 获取分析结果流
                                        analysis_stream = llm_service.await_result()
                                        # 处理分析流
                                        async for analysis_chunk in _stream_generator(analysis_stream):
                                            yield analysis_chunk
                                    # 执行预测任务
                                    if request_question.predict and hasattr(payload,
                                                                            'predict') and payload.predict != "":
                                        record.question = payload.predict
                                        # 执行分析任务
                                        llm_service.run_analysis_or_predict_task_async('predict', record)
                                        # 获取分析结果流
                                        predict_stream = llm_service.await_result()
                                        # 处理分析流
                                        async for predict_chunk in _stream_generator(predict_stream):
                                            yield predict_chunk
                                    if request_question.recommend:
                                        #  推荐
                                        llm_service.run_recommend_questions_task_async()
                                        record.question = question
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
