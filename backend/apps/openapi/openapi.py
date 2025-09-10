import asyncio
import traceback
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlmodel import select
from starlette.responses import StreamingResponse

from apps.chat.curd.chat import get_chat_record_by_id, get_chat_chart_data, list_chats, delete_chat, create_chat
from apps.chat.models.chat_model import Chat, ChatQuestion, CreateChat, ChatRecord
from apps.chat.task.llm import LLMService
from apps.datasource.crud.datasource import get_datasource_list
from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id, bind_datasource
from apps.openapi.models.openapiModels import TokenRequest, OpenToken, DataSourceRequest, OpenChatQuestion, \
    OpenChat, OpenClean, common_headers, IntentPayload
from apps.openapi.service.openapi_service import merge_streaming_chunks, get_chat_record, \
    create_access_token_with_expiry, identify_intent
from apps.system.crud.user import authenticate
from apps.system.schemas.system_schema import BaseUserDTO
from common.core.db import get_session
from common.core.deps import SessionDep, CurrentUser, CurrentAssistant, Trans
from common.utils.utils import SQLBotLogUtil

# 创建 OpenAPI 路由实例
router = APIRouter(tags=["openapi"], prefix="/openapi")


@router.post("/getToken", summary="创建认证令牌",
             description="使用用户名和密码创建一个用于API认证的访问令牌")
async def get_token(
        session: SessionDep,
        trans: Trans,
        request: TokenRequest
) -> OpenToken:
    """
    创建认证令牌

    使用用户名和密码创建一个用于API认证的访问令牌。
    此接口遵循标准的认证流程，用于获取后续API调用所需的访问凭证。

    Args:
        session: 数据库会话依赖
        trans: 国际化翻译依赖
        request: 包含用户名和密码的请求体数据

    Returns:
        OpenToken: 包含访问令牌、过期时间和聊天ID的响应对象

    Raises:
        HTTPException: 当认证失败、用户无工作空间关联或用户被禁用时抛出400错误
    """
    # 验证用户身份
    user: BaseUserDTO = authenticate(
        session=session,
        account=request.username,
        password=request.password
    )

    # 验证用户状态
    from apps.openapi.service.openapi_service import validate_user_status
    validate_user_status(user, trans)

    # 创建访问令牌和过期时间
    access_token, expire_time = create_access_token_with_expiry(user.to_dict())

    # 处理聊天会话创建请求
    chat_id: Optional[int] = None
    if request.create_chat:
        record = create_chat(session, user, CreateChat(origin=1), False)
        chat_id = record.id

    # 创建并返回访问令牌
    return OpenToken(
        access_token=f"bearer {access_token}",
        expire=expire_time,
        chat_id=chat_id
    )


@router.get("/getDataSourceList", summary="获取数据源列表",
            description="获取当前用户可访问的数据源列表",
            dependencies=[Depends(common_headers)])
async def get_data_source_list(session: SessionDep, user: CurrentUser):
    """
    获取数据源列表

    获取当前认证用户可访问的所有数据源列表。

    Args:
        session: 数据库会话依赖
        user: 当前认证用户信息

    Returns:
        用户可访问的数据源列表
    """
    return get_datasource_list(session=session, user=user)


@router.post("/getDataSourceByIdOrName", summary="根据ID或名称获取数据源",
             description="根据数据源ID或名称获取特定数据源信息",
             dependencies=[Depends(common_headers)])
async def get_data_source_by_id_or_name(
        session: SessionDep,
        user: CurrentUser,
        request: DataSourceRequest
):
    """
    根据ID或名称获取数据源

    根据数据源ID或名称获取特定数据源信息。

    Args:
        session: 数据库会话依赖
        user: 当前认证用户信息
        request: 数据源查询请求

    Returns:
        数据源信息
    """
    return get_datasource_by_name_or_id(session=session, user=user, query=request)


@router.post("/chat", summary="聊天",
             description="给定一个提示，模型将返回一条或多条预测消息",
             dependencies=[Depends(common_headers)])
async def getChat(
        current_user: CurrentUser,
        request_question: OpenChatQuestion,
        current_assistant: CurrentAssistant
):
    """
    创建聊天完成（Create Chat Completion）

    给定一个对话历史和用户输入，模型将返回一条或多条预测消息。
    此接口遵循OpenAI Chat Completions API规范，支持流式响应。

    Args:
        current_user: 当前认证用户信息
        request_question: 包含问题内容的请求对象
        current_assistant: 当前使用的AI助手信息

    Returns:
        StreamingResponse: 流式响应对象，包含模型生成的回复内容

    Raises:
        HTTPException: 当处理过程中出现异常时抛出500错误
    """
    try:
        # 获取数据源信息
        for session in get_session():
            datasource = get_datasource_by_name_or_id(
                session=session,
                user=current_user,
                query=DataSourceRequest(id=request_question.db_id)
            )
            if not datasource:
                raise HTTPException(
                    status_code=500,
                    detail="数据源未找到"
                )
            # 绑定数据源到聊天会话
            await bind_datasource(datasource, request_question.chat_id, session)

        # 创建LLM服务实例
        llm_service = await LLMService.create(
            current_user,
            request_question,
            current_assistant
        )

        # 如果存在意图检测，则进行意图识别
        payload: Optional[IntentPayload] = (
            identify_intent(llm_service.llm, request_question.question)
            if request_question.intent is True else None
        )

        # 记录意图识别结果
        if payload:
            SQLBotLogUtil.info(f"意图识别详情 - 原始输入: '{request_question.question}', "
                               f"搜索意图: '{payload.search}', "
                               f"分析意图: '{payload.analysis}', "
                               f"预测意图: '{payload.predict}'")
        else:
            SQLBotLogUtil.info(f"意图识别失败 - 原始输入: '{request_question.question}', 未识别到有效意图")
            if request_question.analysis or request_question.predict:
                payload = IntentPayload(
                    search=request_question.question,
                    analysis=request_question.question if request_question.analysis else "",
                    predict=request_question.question if request_question.predict else ""
                )

        # 如果存在意图，则使用意图作为问题
        if payload is not None and payload.search != "":
            llm_service.chat_question.question = payload.search
        else:
            payload = None

        # 初始化聊天记录
        llm_service.init_record()

        # 异步运行任务
        llm_service.run_task_async()

    except Exception as e:
        # 记录异常信息用于调试
        SQLBotLogUtil.error(f"聊天接口异常: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"聊天处理失败: {str(e)}"
        )

    # 返回经过合并处理的流式响应
    return StreamingResponse(
        merge_streaming_chunks(stream=llm_service.await_result(),
                               llm_service=llm_service,
                               payload=payload,
                               request_question=request_question),
        media_type="text/event-stream"
    )


@router.post("/getData", dependencies=[Depends(common_headers)])
async def get_data(session: SessionDep, record_chat: OpenChat):
    """
    获取聊天记录数据

    根据聊天记录ID获取相关的图表数据。

    Args:
        session: 数据库会话依赖
        record_chat: 聊天对象，包含图表记录ID

    Returns:
        聊天记录对应的图表数据
    """

    def _fetch_chart_data() -> dict:
        """内部函数：执行数据库查询获取图表数据"""
        return get_chat_chart_data(
            chart_record_id=record_chat.chat_record_id,
            session=session
        )

    # 使用异步线程执行数据库查询
    return await asyncio.to_thread(_fetch_chart_data)


@router.post("/getRecommend", dependencies=[Depends(common_headers)])
async def get_recommend(
        current_user: CurrentUser,
        chat_record: OpenChat,
        current_assistant: CurrentAssistant
):
    """
    流式生成推荐问题

    基于指定的聊天记录，异步生成推荐问题并以流式方式返回结果。

    Args:
        current_user: 当前认证用户信息
        chat_record: 聊天对象，包含聊天记录ID
        current_assistant: 当前使用的AI助手信息

    Returns:
        StreamingResponse: 流式响应，包含生成的推荐问题

    Raises:
        HTTPException: 当聊天记录不存在或处理异常时抛出相应错误
    """
    try:
        chat_record_id = chat_record.chat_record_id
        # 获取聊天记录
        record = None
        for session in get_session():
            record = get_chat_record_by_id(session, chat_record_id)
        # 验证聊天记录是否存在
        if record is None:
            raise HTTPException(
                status_code=400,
                detail=f"Chat record with id {chat_record_id} not found"
            )

        # 创建问题请求对象
        request_question = ChatQuestion(
            chat_id=record.chat_id,
            question=record.question if record.question else ''
        )

        # 创建LLM服务实例并设置推荐问题模式
        llm_service = await LLMService.create(current_user, request_question, current_assistant, True)

        # 设置聊天记录
        llm_service.set_record(record)

        # 异步运行推荐问题生成任务
        llm_service.run_recommend_questions_task_async()
    except Exception as e:
        # 打印异常堆栈信息用于调试
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    # 返回流式响应
    return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")


@router.post("/deleteChats", summary="清理",
             description="清理当前用户的所有聊天记录",
             dependencies=[Depends(common_headers)])
async def clean_all_chat_record(
        session: SessionDep,
        current_user: CurrentUser,
        clean: OpenClean
):
    """
    清理当前用户的聊天记录

    Args:
        session: 数据库会话依赖
        current_user: 当前认证用户信息
        clean: 清理对象，包含要清理的聊天记录ID列表

    Returns:
        dict: 操作结果，包含成功和失败的记录数
    """
    try:
        # 获取要清理的聊天记录列表
        chat_list = _get_chats_to_clean(session, current_user, clean)

        if not chat_list:
            return _create_clean_response(0, 0, 0)

        # 执行清理操作
        success_count, failed_count, failed_records = _execute_cleanup(
            session,
            chat_list
        )

        # 返回操作结果
        return _create_clean_response(success_count, failed_count, len(chat_list))

    except Exception as e:
        SQLBotLogUtil.error(f"清理聊天记录异常: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"清理聊天记录失败: {str(e)}"
        )


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


@router.post("/analysis", summary="分析",
             description="对指定聊天记录进行分析",
             dependencies=[Depends(common_headers)])
async def analysis_chat_record(
        current_user: CurrentUser,
        chat_record: OpenChat,
        current_assistant: CurrentAssistant
):
    """
    对指定聊天记录进行分析

    Args:
        current_user: 当前认证用户信息
        chat_record: 聊天对象，包含聊天记录ID
        current_assistant: 当前使用的AI助手信息

    Returns:
        StreamingResponse: 流式响应，包含分析结果
    """
    return await _run_analysis_or_predict(current_user, chat_record, current_assistant, 'analysis')


@router.post("/predict", summary="预测",
             description="对指定聊天记录进行预测",
             dependencies=[Depends(common_headers)])
async def predict_chat_record(
        current_user: CurrentUser,
        chat_record: OpenChat,
        current_assistant: CurrentAssistant
):
    """
    对指定聊天记录进行预测

    Args:
        current_user: 当前认证用户信息
        chat_record: 聊天对象，包含聊天记录ID
        current_assistant: 当前使用的AI助手信息

    Returns:
        StreamingResponse: 流式响应，包含预测结果
    """
    return await _run_analysis_or_predict(current_user, chat_record, current_assistant, 'predict')


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
    chat_record_id = chat_record.chat_record_id
    record = None
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

    request_question = ChatQuestion(chat_id=record.chat_id, question=record.question)

    try:
        llm_service = await LLMService.create(current_user, request_question, current_assistant)
        llm_service.run_analysis_or_predict_task_async(task_type, record)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")
