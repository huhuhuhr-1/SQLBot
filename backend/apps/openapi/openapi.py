"""
OpenAPI 模块

该模块提供了 SQLBot 的 OpenAPI 接口，包括：
- 用户认证和令牌管理
- 数据源查询和管理
- 聊天对话接口
- 推荐问题生成

主要功能：
1. 用户登录认证并获取访问令牌
2. 查询用户可访问的数据源列表
3. 根据名称获取特定数据源信息
4. 支持流式响应的聊天对话
5. 基于历史记录的推荐问题生成

作者: huhuhuhr
日期: 2025/09/03
版本: 1.0.0
"""

# 标准库导入
import asyncio
import traceback
from typing import Optional

# 第三方库导入
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select
from sqlbot_xpack.db import Depends

# 本地模块导入
from apps.chat.curd.chat import (
    create_chat,
    get_chat_chart_data,
    get_chat_record_by_id
)
from apps.chat.models.chat_model import ChatRecord
from apps.chat.models.chat_model import CreateChat, ChatQuestion
from apps.chat.task.llm import LLMService
from apps.datasource.crud.datasource import get_datasource_list
from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id, bind_datasource
from apps.openapi.models.openapiModels import (
    TokenRequest,
    OpenToken,
    DataSourceRequest,
    common_headers,
    OpenChatQuestion,
    OpenClean,
    OpenChat
)
from apps.openapi.service.operapi_service import (
    create_clean_response,
    commit_transaction,
    get_chats_to_clean,
    execute_cleanup,
    validate_user_status,
    create_access_token_with_expiry)
from apps.system.crud.user import authenticate
from apps.system.schemas.system_schema import BaseUserDTO
from common.core.deps import SessionDep, CurrentUser, Trans, CurrentAssistant
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


@router.post("/chat", summary="聊天",
             description="给定一个提示，模型将返回一条或多条预测消息",
             dependencies=[Depends(common_headers)])
async def getChat(
        session: SessionDep,
        current_user: CurrentUser,
        request_question: OpenChatQuestion,
        current_assistant: CurrentAssistant
):
    """
    创建聊天完成（Create Chat Completion）

    给定一个对话历史和用户输入，模型将返回一条或多条预测消息。
    此接口遵循OpenAI Chat Completions API规范，支持流式响应。

    Args:
        session: 数据库会话依赖
        current_user: 当前认证用户信息
        request_question: 包含问题内容的请求对象
        current_assistant: 当前使用的AI助手信息

    Returns:
        StreamingResponse: 流式响应对象，包含模型生成的回复内容

    Raises:
        HTTPException: 当处理过程中出现异常时抛出500错误
    """
    # 获取数据源信息
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

    try:
        # 绑定数据源到聊天会话
        await bind_datasource(datasource, request_question, session)

        # 创建LLM服务实例
        llm_service = await LLMService.create(
            current_user,
            request_question,
            current_assistant
        )

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

    # 返回流式响应
    return StreamingResponse(
        llm_service.await_result(),
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
        session: SessionDep,
        current_user: CurrentUser,
        chat_record: OpenChat,
        current_assistant: CurrentAssistant
):
    """
    流式生成推荐问题

    基于指定的聊天记录，异步生成推荐问题并以流式方式返回结果。

    Args:
        session: 数据库会话依赖
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
        record = get_chat_record_by_id(session, chat_record_id)
        # 验证聊天记录是否存在
        if not record:
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
        chat_list = get_chats_to_clean(session, current_user, clean)

        if not chat_list:
            return create_clean_response(0, 0, 0)

        # 执行清理操作
        success_count, failed_count, failed_records = execute_cleanup(
            session,
            chat_list
        )

        # 提交事务
        commit_transaction(session)

        return create_clean_response(
            success_count,
            failed_count,
            len(chat_list),
            failed_records
        )

    except Exception as e:
        session.rollback()
        SQLBotLogUtil.error(f"清理聊天记录异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"清理聊天记录时发生错误: {str(e)}"
        )


@router.post("/getAnalysis", dependencies=[Depends(common_headers)])
async def get_analysis(
        session: SessionDep,
        current_user: CurrentUser,
        chat_record: OpenChat,
        current_assistant: CurrentAssistant):
    """
    获取聊天记录的分析结果。
    """
    record: ChatRecord | None = None
    chat_record_id = chat_record.chat_record_id

    stmt = select(ChatRecord.id, ChatRecord.question, ChatRecord.chat_id, ChatRecord.datasource, ChatRecord.engine_type,
                  ChatRecord.ai_modal_id, ChatRecord.create_by, ChatRecord.chart, ChatRecord.data).where(
        and_(ChatRecord.id == chat_record_id))
    result = session.execute(stmt)
    for r in result:
        record = ChatRecord(id=r.id, question=r.question, chat_id=r.chat_id, datasource=r.datasource,
                            engine_type=r.engine_type, ai_modal_id=r.ai_modal_id, create_by=r.create_by, chart=r.chart,
                            data=r.data)

    if not record:
        raise HTTPException(
            status_code=400,
            detail=f"Chat record with id {chat_record_id} not found"
        )

    if not record.chart:
        raise HTTPException(
            status_code=500,
            detail=f"Chat record with id {chat_record_id} has not generated chart, do not support to analyze it"
        )

    request_question = ChatQuestion(chat_id=record.chat_id, question=record.question)

    try:
        llm_service = await LLMService.create(current_user, request_question, current_assistant)
        llm_service.run_analysis_or_predict_task_async('analysis', record)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")


@router.post("/getPredict", dependencies=[Depends(common_headers)])
async def get_predict(
        session: SessionDep,
        current_user: CurrentUser,
        chat_record: OpenChat,
        current_assistant: CurrentAssistant):
    """
    获取聊天记录的预测结果。
    """
    record: ChatRecord | None = None
    chat_record_id = chat_record.chat_record_id

    stmt = select(ChatRecord.id, ChatRecord.question, ChatRecord.chat_id, ChatRecord.datasource, ChatRecord.engine_type,
                  ChatRecord.ai_modal_id, ChatRecord.create_by, ChatRecord.chart, ChatRecord.data).where(
        and_(ChatRecord.id == chat_record_id))
    result = session.execute(stmt)
    for r in result:
        record = ChatRecord(id=r.id, question=r.question, chat_id=r.chat_id, datasource=r.datasource,
                            engine_type=r.engine_type, ai_modal_id=r.ai_modal_id, create_by=r.create_by, chart=r.chart,
                            data=r.data)

    if not record:
        raise HTTPException(
            status_code=400,
            detail=f"Chat record with id {chat_record_id} not found"
        )

    if not record.chart:
        raise HTTPException(
            status_code=500,
            detail=f"Chat record with id {chat_record_id} has not generated chart, do not support to analyze it"
        )

    request_question = ChatQuestion(chat_id=record.chat_id, question=record.question)

    try:
        llm_service = await LLMService.create(current_user, request_question, current_assistant)
        llm_service.run_analysis_or_predict_task_async('predict', record)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")
