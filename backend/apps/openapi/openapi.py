import asyncio
import hashlib
import json
import os
import traceback
import uuid

import orjson
from sqlalchemy import text
from typing import Optional

from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, File, Form
from sqlbot_xpack.file_utils import UploadFile
from starlette.responses import StreamingResponse
from apps.chat.curd.chat import get_chat_record_by_id, get_chat_chart_data, create_chat
from apps.chat.models.chat_model import CreateChat
from apps.datasource.api.datasource import insert_pg
from apps.datasource.crud.datasource import get_datasource_list, create_ds, getTables, update_table_and_fields
from apps.datasource.models.datasource import CreateDatasource, CoreDatasource, TableObj, CoreTable
from apps.datasource.utils.utils import aes_encrypt
from apps.db.engine import get_engine_conn
from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id, bind_datasource
from apps.openapi.models.openapiModels import TokenRequest, OpenToken, DataSourceRequest, OpenChatQuestion, \
    OpenChat, OpenClean, common_headers, IntentPayload, DbBindChat
from apps.openapi.service.openapi_llm import LLMService
from apps.openapi.service.openapi_service import merge_streaming_chunks, create_access_token_with_expiry, \
    chat_identify_intent, _get_chats_to_clean, _create_clean_response, \
    _execute_cleanup, \
    _run_analysis_or_predict

from apps.openapi.service.openapi_db import delete_ds, upload_excel_and_create_datasource_service
from apps.system.crud.user import authenticate
from apps.system.schemas.system_schema import BaseUserDTO
from common.core.config import settings
from common.core.db import get_session
from common.core.deps import SessionDep, CurrentUser, CurrentAssistant, Trans
from common.utils.utils import SQLBotLogUtil

router = APIRouter(tags=["openapi"], prefix="/openapi")
path = settings.EXCEL_PATH


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
        chat_question: OpenChatQuestion,
        current_assistant: CurrentAssistant
):
    """
    创建聊天完成（Create Chat Completion）

    给定一个对话历史和用户输入，模型将返回一条或多条预测消息。
    此接口遵循OpenAI Chat Completions API规范，支持流式响应。

    Args:
        current_user: 当前认证用户信息
        chat_question: 包含问题内容的请求对象
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
                query=DataSourceRequest(id=chat_question.db_id)
            )
            if datasource:
                # 绑定数据源到聊天会话
                await bind_datasource(datasource, chat_question.chat_id, session, current_user)
                break
            else:
                raise HTTPException(
                    status_code=500,
                    detail="数据源未找到"
                )

        # 创建LLM服务实例
        llm_service = await LLMService.create(
            current_user,
            chat_question,
            current_assistant,
            no_reasoning=chat_question.no_reasoning,
            embedding=True
        )
        # 如果存在意图检测，则进行意图识别
        payload: Optional[IntentPayload] = (
            chat_identify_intent(llm_service.llm, chat_question.question)
            if chat_question.intent is True else None
        )

        # 记录意图识别结果
        if payload:
            SQLBotLogUtil.info(f"意图识别详情 - 原始输入: '{chat_question.question}', "
                               f"搜索意图: '{payload.search}', "
                               f"分析意图: '{payload.analysis}', "
                               f"预测意图: '{payload.predict}'")
        else:
            SQLBotLogUtil.info(
                f"未识别到意图 - 输入: '{chat_question.question}', 未识别到有效意图")
            if chat_question.analysis or chat_question.predict:
                payload = IntentPayload(
                    search=chat_question.question,
                    analysis=chat_question.question if chat_question.analysis else "",
                    predict=chat_question.question if chat_question.predict else ""
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
        stream = llm_service.await_result()
        # 返回经过合并处理的流式响应
        return StreamingResponse(
            merge_streaming_chunks(stream=stream,
                                   llm_service=llm_service,
                                   payload=payload,
                                   chat_question=chat_question),
            media_type="text/event-stream"
        )
    except Exception as e:
        # 记录异常信息用于调试
        SQLBotLogUtil.error(f"聊天接口异常: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"聊天处理失败: {str(e)}"
        )


async def to_async(gen):
    for item in gen:
        yield item


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


@router.post("/createRecordAndBindDb")
async def bind_data_source(session: SessionDep, current_user: CurrentUser, db_bind_chat: DbBindChat):
    """
    绑定数据源并开始聊天

    根据指定的数据源ID和用户输入，创建一个新的聊天记录并开始聊天。

    Args:
        session: 数据库会话依赖
        current_user: 当前认证用户信息
        db_bind_chat: 包含数据源ID和用户输入的请求对象

    Returns:
        创建的聊天记录对象

    Raises:
        HTTPException: 当处理过程中出现异常时抛出500错误
    """
    try:
        create_chat_obj = CreateChat(
            datasource=db_bind_chat.db_id,
            question=db_bind_chat.title
        )
        return create_chat(session, current_user, create_chat_obj)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


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
        chat_question = OpenChatQuestion(
            chat_id=record.chat_id,
            question=record.question if record.question else ''
        )

        # 创建LLM服务实例并设置推荐问题模式
        llm_service = await LLMService.create(
            current_user,
            chat_question,
            current_assistant,
            no_reasoning=chat_record.no_reasoning,
            embedding=True
        )

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


@router.post("/uploadExcelAndCreateDatasource", response_model=CoreDatasource)
async def upload_excel_and_create_datasource(
        session: SessionDep,
        trans: Trans,
        user: CurrentUser,
        file: UploadFile = File(...),
):
    ALLOWED_EXTENSIONS = {"xlsx", "xls", "csv"}
    if not file.filename.lower().endswith(tuple(ALLOWED_EXTENSIONS)):
        raise HTTPException(status_code=400, detail="Only support .xlsx/.xls/.csv")

    os.makedirs(path, exist_ok=True)
    filename = f"{file.filename.split('.')[0]}_{hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:10]}.{file.filename.split('.')[1]}"
    save_path = os.path.join(path, filename)

    with open(save_path, "wb") as f:
        f.write(await file.read())

    def inner():
        try:
            return upload_excel_and_create_datasource_service(session, trans, user, save_path, file.filename)
        finally:
            if os.path.exists(save_path):
                os.remove(save_path)
                SQLBotLogUtil.info(f"🧹 临时文件已删除：{save_path}")

    return await asyncio.to_thread(inner)


@router.post(
    "/deleteDatasource",
    summary="根据 ID 删除数据源",
    description="删除指定数据源及其关联的表、字段记录。",
    dependencies=[Depends(common_headers)],
)
async def delete_datasource_by_id(session: SessionDep, id: int):
    """
    删除数据源：
    - 对 Excel 类型，自动 DROP 物理表；
    - 清理 CoreTable/CoreField 记录；
    - 日志可追溯。
    """

    def inner():
        return delete_ds(session, id)

    return await asyncio.to_thread(inner)
