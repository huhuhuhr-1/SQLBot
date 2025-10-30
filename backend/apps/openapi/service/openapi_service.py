import json
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, AsyncGenerator, Tuple, List
from langchain.chat_models.base import BaseChatModel
import orjson
from fastapi import HTTPException
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy import and_
from sqlmodel import select

from apps.chat.curd.chat import get_chat_chart_data, delete_chat, list_chats
from apps.chat.models.chat_model import ChatRecord, Chat, ChatQuestion
from apps.openapi.models.openapiModels import IntentPayload, OpenChatQuestion, OpenClean, OpenChat, \
    AnalysisIntentPayload
from apps.openapi.service.openapi_llm import LLMService
from apps.openapi.service.openapi_prompt import chat_sys_intention, analysis_intention_question, analysis_question
from apps.system.schemas.system_schema import BaseUserDTO
from common.core.config import settings
from common.core.db import get_session
from common.core.deps import SessionDep, CurrentUser, CurrentAssistant
from common.core.deps import Trans
from common.core.security import create_access_token
from common.utils.utils import SQLBotLogUtil
from starlette.responses import StreamingResponse


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


def chat_identify_intent(llm: BaseChatModel, question: str) -> IntentPayload:
    """
    提取用户问题中的意图，转化为 IntentPayload 对象。
    核心原则：search 字段必须存在且贴近用户原意，仅做必要规范化，作为后续数据查询的主输入。
    analysis 和 predict 为附加意图，可为空。
    """
    system_prompt = chat_sys_intention()

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


def analysis_identify_intent(llm: BaseChatModel, question: str) -> AnalysisIntentPayload:
    system_prompt = analysis_intention_question()

    human_prompt = f"用户分析诉求：{question}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]

    try:
        response = llm.invoke(messages)
        return AnalysisIntentPayload.from_llm(response.content.strip())
    except Exception as e:
        raise RuntimeError(f"意图识别失败：{str(e)}")


async def merge_streaming_chunks(stream,
                                 llm_service: LLMService = None,
                                 payload: IntentPayload = None,
                                 chat_question: OpenChatQuestion = None) -> AsyncGenerator[str, None]:
    """
    合并流式输出的数据块

    规则:
    1. 对于 'predict-result' 和 'analysis-result' 类型的数据块不进行合并
    2. 对于其他类型，如果数据块中 reasoning_content 不为空，则不合并
    3. 对于其他相同类型的连续数据块，且 reasoning_content 为空，合并其 content 字段
    4. 每个数据块都是 'data:{json_data}' 格式
    5. 当收到 'finish' 类型时，调用 get_data 获取图表数据并发送

    Args:
        chat_question: 用户问题
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
                                    if record is not None:
                                        question = record.question
                                        break
                                if record is None:
                                    SQLBotLogUtil.warning(
                                        f"未找到聊天记录 {recorded_id}，跳过后续分析/预测流程"
                                    )
                                    warning_chunk = {
                                        'type': 'warning',
                                        'content': f'Chat record {recorded_id} not found'
                                    }
                                    yield f"data:{orjson.dumps(warning_chunk).decode()}\n\n"
                                elif record.chart:
                                    # 分析
                                    if chat_question.analysis and hasattr(payload,
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
                                    if chat_question.predict and hasattr(payload,
                                                                         'predict') and payload.predict != "":
                                        record.question = payload.predict
                                        # 执行分析任务
                                        llm_service.run_analysis_or_predict_task_async('predict', record)
                                        # 获取分析结果流
                                        predict_stream = llm_service.await_result()
                                        # 处理分析流
                                        async for predict_chunk in _stream_generator(predict_stream):
                                            yield predict_chunk
                                    if chat_question.recommend:
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


def _get_chats_to_clean(
        session: SessionDep,
        current_user: CurrentUser,
        clean: OpenClean
) -> List[Chat]:
    """
    获取要清理的聊天记录列表

    Args:
        session: 数据库会话依赖
        current_user: 当前认证用户信息
        clean: 清理对象

    Returns:
        List[Chat]: 要清理的聊天记录列表
    """
    if clean.chat_ids:
        # 如果指定了特定的聊天ID，则只清理这些聊天记录
        stmt = select(Chat).where(
            and_(
                Chat.id.in_(clean.chat_ids),
                Chat.create_by == current_user.id
            )
        )
        return list(session.exec(stmt))
    else:
        # 否则清理当前用户的所有聊天记录
        return list_chats(session, current_user)


def _execute_cleanup(
        session: SessionDep,
        chat_list: List[Chat]
) -> tuple[int, int, list]:
    """
    执行聊天记录清理操作

    Args:
        session: 数据库会话依赖
        chat_list: 要清理的聊天记录列表

    Returns:
        tuple[int, int, list]: (成功数, 失败数, 失败记录列表)
    """
    success_count = 0
    failed_count = 0
    failed_records = []

    for chat in chat_list:
        try:
            # 删除聊天记录相关的所有数据
            delete_chat(session, chat.id)
            success_count += 1
        except Exception as e:
            failed_count += 1
            failed_records.append({
                "chat_id": chat.id,
                "error": str(e)
            })
            SQLBotLogUtil.error(f"删除聊天记录 {chat.id} 失败: {str(e)}")

    return success_count, failed_count, failed_records


def _create_clean_response(success_count: int, failed_count: int, total_count: int) -> Dict[str, Any]:
    """
    创建清理操作的响应结果

    Args:
        success_count: 成功清理的记录数
        failed_count: 失败的记录数
        total_count: 总记录数

    Returns:
        Dict[str, Any]: 响应结果字典
    """
    return {
        "message": f"清理完成，总共 {total_count} 条记录，成功 {success_count} 条，失败 {failed_count} 条",
        "success_count": success_count,
        "failed_count": failed_count,
        "total_count": total_count
    }


async def _run_analysis_or_predict(
        current_user: CurrentUser,
        chat_record: OpenChat,
        current_assistant: CurrentAssistant,
        task_type: str
):
    """
    运行分析或预测任务的通用逻辑。

    Args:
        current_user: 当前认证用户信息
        chat_record: 聊天对象，包含聊天记录ID
        current_assistant: 当前使用的AI助手信息
        task_type: 任务类型 ('analysis' 或 'predict')

    Returns:
        StreamingResponse: 流式响应，包含生成的结果
    """
    record = None
    if chat_record.chat_record_id is not None:
        chat_record_id = chat_record.chat_record_id

        for session in get_session():
            record = await get_chat_record(session, chat_record_id)

        if not record.chart:
            raise HTTPException(
                status_code=500,
                detail=f"Chat record with id {chat_record_id} has not generated chart, do not support to analyze it"
            )

        # 更新问题内容（如果提供）
        if chat_record.question:
            record.question = chat_record.question

        request_question = OpenChatQuestion(
            chat_id=record.chat_id,
            question=record.question,
            my_promote=chat_record.my_promote,
            my_schema=chat_record.my_schema,
            every=chat_record.every,
            history_open=chat_record.history_open,
            no_reasoning=chat_record.no_reasoning
        )
    else:
        if not chat_record.chat_id or not chat_record.chat_data_object or not chat_record.db_id:
            raise HTTPException(
                status_code=500,
                detail=f"Chat record with chat_id or chat_data_object or db_id is not provided!"
            )
        record = ChatRecord()
        record.question = chat_record.question
        record.chat_id = chat_record.chat_id
        record.datasource = chat_record.db_id
        record.engine_type = ''
        record.ai_modal_id = -1
        record.create_by = -1
        record.chart = ''
        if isinstance(chat_record.chat_data_object, str):
            record.data = chat_record.chat_data_object
        else:
            record.data = orjson.dumps(chat_record.chat_data_object).decode()
        record.analysis_record_id = -1

        request_question = OpenChatQuestion(
            chat_id=record.chat_id,
            question=record.question,
            my_promote=chat_record.my_promote,
            my_schema=chat_record.my_schema,
            every=chat_record.every,
            history_open=chat_record.history_open,
            no_reasoning=chat_record.no_reasoning,
            db_id=chat_record.db_id
        )

    try:
        payload = None
        llm_service = await LLMService.create(
            current_user,
            request_question,
            current_assistant)
        if task_type == 'analysis':
            if chat_record.my_promote is None and chat_record.intent:
                payload: Optional[AnalysisIntentPayload] = (
                    analysis_identify_intent(llm_service.llm, request_question.question)
                )
            # 记录意图识别结果
            if payload is None:
                payload = AnalysisIntentPayload(
                    intent="分析",
                    role="数据分析师",
                    task=request_question.question,
                )
            SQLBotLogUtil.info(f"意图识别详情 - 原始输入: '{request_question.question}', "
                               f"意图: '{payload.intent}', "
                               f"角色: '{payload.role}', "
                               f"任务: '{payload.task}'")
        data_str = None
        if chat_record.chat_data_object is not None:
            data_str = json.dumps(chat_record.chat_data_object, ensure_ascii=False)
        llm_service.run_analysis_or_predict_task_async(task_type, record, data_str, payload)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")


async def merge_plan_streaming_chunks(stream, plan_executor: 'PlanExecutor' = None) -> AsyncGenerator[str, None]:
    """
    合并Plan接口流式输出的数据块

    Args:
        stream: 输入的流式数据生成器
        plan_executor: Plan执行器实例（可选）

    Yields:
        合并后的数据块
    """
    async for chunk in stream:
        try:
            # 检查chunk的类型，如果是PlanResponse对象
            if hasattr(chunk, 'plan_id'):  # PlanResponse对象
                response_data = {
                    "type": "plan_result",
                    "plan_id": chunk.plan_id,
                    "status": chunk.status,
                    "steps": [step.dict() for step in chunk.steps],
                    "result": chunk.result,
                    "error": chunk.error
                }
                yield f"data:{orjson.dumps(response_data).decode()}\n\n"
            elif isinstance(chunk, dict) and 'type' in chunk and chunk['type'] == 'step_status':
                # 如果是步骤状态
                step_data = {
                    "type": "step_status",
                    "step": chunk['step'].dict() if hasattr(chunk['step'], 'dict') else chunk['step']
                }
                yield f"data:{orjson.dumps(step_data).decode()}\n\n"
            elif isinstance(chunk, str):
                # 如果是字符串格式的chunk，直接输出
                if chunk.startswith('data:'):
                    yield chunk
                else:
                    # 包装为标准格式
                    yield f"data:{orjson.dumps({'type': 'info', 'content': chunk}).decode()}\n\n"
            else:
                # 其他类型的chunk
                yield f"data:{orjson.dumps({'type': 'chunk', 'data': str(chunk)}).decode()}\n\n"

        except Exception as e:
            error_chunk = {
                "type": "error",
                "content": f"处理Plan流式数据块时出错: {str(e)}"
            }
            yield f"data:{orjson.dumps(error_chunk).decode()}\n\n"


def is_safe_sql(sql: str) -> bool:
    """
    仅禁止执行删除或修改数据的 SQL。
    允许 SELECT、SHOW、DESCRIBE、EXPLAIN 等安全语句。
    """
    import re
    if not sql or not isinstance(sql, str):
        return False

    sql_lower = sql.strip().lower()

    # 允许的安全命令（白名单）
    safe_prefixes = ('select', 'show', 'describe', 'explain', 'with')
    if sql_lower.startswith(safe_prefixes):
        # 检查是否出现明显的破坏性关键字
        forbidden = [
            r'\bdelete\b',
            r'\bupdate\b',
            r'\binsert\b',
            r'\bdrop\b',
            r'\btruncate\b',
            r'\balter\b',
            r'\bcreate\b',
            r'\breplace\b',
        ]
        for pattern in forbidden:
            if re.search(pattern, sql_lower):
                return False
        return True
    else:
        # 不是安全命令开头的，默认不允许
        return False
