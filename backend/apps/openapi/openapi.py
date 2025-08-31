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
日期: 2025/01/30
版本: 1.0.0
"""

# 标准库导入
import asyncio
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional

# 第三方库导入
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlbot_xpack.db import Depends

# 本地模块导入
from apps.chat.curd.chat import (
    create_chat,
    get_chat_chart_data,
    get_chat_record_by_id,
    list_chats,
    delete_chat
)
from apps.chat.models.chat_model import CreateChat, ChatQuestion, Chat
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
from apps.system.crud.user import authenticate
from apps.system.schemas.system_schema import BaseUserDTO
from common.core.config import settings
from common.core.deps import SessionDep, CurrentUser, Trans, CurrentAssistant
from common.core.security import create_access_token
from common.utils.utils import SQLBotLogUtil

# 创建 OpenAPI 路由实例
router = APIRouter(tags=["openapi"], prefix="/openapi")


def _create_access_token_with_expiry(user_dict: dict) -> tuple[str, str]:
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


def _validate_user_status(user: BaseUserDTO, trans: Trans) -> None:
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
    _validate_user_status(user, trans)

    # 创建访问令牌和过期时间
    access_token, expire_time = _create_access_token_with_expiry(user.to_dict())

    # 处理聊天会话创建请求
    chat_id: Optional[int] = None
    if request.create_chat:
        chat = create_chat(session, user, CreateChat(origin=1), False)
        chat_id = chat.id

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
async def chat(
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
async def get_data(session: SessionDep, chat: OpenChat):
    """
    获取聊天记录数据

    根据聊天记录ID获取相关的图表数据。

    Args:
        session: 数据库会话依赖
        chat: 聊天对象，包含图表记录ID

    Returns:
        聊天记录对应的图表数据
    """

    def _fetch_chart_data() -> dict:
        """内部函数：执行数据库查询获取图表数据"""
        return get_chat_chart_data(
            chart_record_id=chat.chat_record_id,
            session=session
        )

    # 使用异步线程执行数据库查询
    return await asyncio.to_thread(_fetch_chart_data)


@router.post("/getRecommend", dependencies=[Depends(common_headers)])
async def get_recommend(
        session: SessionDep,
        current_user: CurrentUser,
        chat: OpenChat,
        current_assistant: CurrentAssistant
):
    """
    流式生成推荐问题

    基于指定的聊天记录，异步生成推荐问题并以流式方式返回结果。

    Args:
        session: 数据库会话依赖
        current_user: 当前认证用户信息
        chat: 聊天对象，包含聊天记录ID
        current_assistant: 当前使用的AI助手信息

    Returns:
        StreamingResponse: 流式响应，包含生成的推荐问题

    Raises:
        HTTPException: 当聊天记录不存在或处理异常时抛出相应错误
    """
    try:
        chat_record_id = chat.chat_record_id
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


@router.post("/clean", summary="清理",
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

        # 提交事务
        _commit_transaction(session)

        return _create_clean_response(
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


def _get_chats_to_clean(
        session: SessionDep,
        current_user: CurrentUser,
        clean: OpenClean
) -> list[Chat]:
    """
    获取需要清理的聊天记录列表
    
    Args:
        session: 数据库会话
        current_user: 当前用户
        clean: 清理对象
        
    Returns:
        聊天记录列表
    """
    if clean.chat_ids:
        # 清理指定的聊天记录
        chat_list = session.query(Chat).filter(
            Chat.id.in_(clean.chat_ids),
            Chat.create_by == current_user.id,
            Chat.oid == current_user.oid
        ).all()
    else:
        # 清理所有聊天记录
        chat_list = list_chats(session, current_user)

    return chat_list


def _execute_cleanup(session: SessionDep, chat_list: list[Chat]) -> tuple[int, int, list]:
    """
    执行清理操作
    
    Args:
        session: 数据库会话
        chat_list: 聊天记录列表
        
    Returns:
        tuple: (成功数量, 失败数量, 失败记录列表)
    """
    success_count = 0
    failed_count = 0
    failed_records = []

    for chat in chat_list:
        try:
            delete_chat(session=session, chart_id=chat.id)
            success_count += 1
        except Exception as e:
            failed_count += 1
            failed_records.append({
                "chat_id": chat.id,
                "error": str(e)
            })
            SQLBotLogUtil.info(f"删除聊天记录失败 [{chat.id}]: {str(e)}")

    return success_count, failed_count, failed_records


def _commit_transaction(session: SessionDep) -> None:
    """
    提交数据库事务
    
    Args:
        session: 数据库会话
        
    Raises:
        HTTPException: 当事务提交失败时抛出异常
    """
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"事务提交失败: {str(e)}"
        )


def _create_clean_response(
        success_count: int,
        failed_count: int,
        total_count: int,
        failed_records: Optional[list] = None
) -> dict:
    """
    创建清理操作的响应结果
    
    Args:
        success_count: 成功数量
        failed_count: 失败数量
        total_count: 总数量
        failed_records: 失败记录列表
        
    Returns:
        响应结果字典
    """
    response = {
        "message": "聊天记录清理完成",
        "success_count": success_count,
        "failed_count": failed_count,
        "total_count": total_count
    }

    if failed_records:
        response["failed_records"] = failed_records

    return response

# 注释掉的代码块 - 保留供参考
# @router.post("/recommend_questions_sync/{chat_record_id}",
#              dependencies=[Depends(common_headers)])
# async def recommend_questions_sync(session: SessionDep, current_user: CurrentUser, chat_record_id: int,
#                                    current_assistant: CurrentAssistant):
#     """
#     同步生成推荐问题
#
#     基于指定的聊天记录，同步生成推荐问题并直接返回完整结果。
#     与流式版本不同，此接口会等待所有处理完成后一次性返回结果。
#
#     Args:
#         session (SessionDep): 数据库会话依赖
#         current_user (CurrentUser): 当前认证用户信息
#         chat_record_id (int): 聊天记录ID
#         current_assistant (CurrentAssistant): 当前使用的AI助手信息
#
#     Returns:
#         dict: 包含推荐问题内容的字典对象
#
#     Raises:
#         HTTPException: 当聊天记录不存在或处理异常时抛出相应错误
#     """
#     try:
#         # 获取聊天记录
#         record = get_chat_record_by_id(session, chat_record_id)
#
#         # 验证聊天记录是否存在
#         if not record:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Chat record with id {chat_record_id} not found"
#             )
#
#         # 创建问题请求对象
#         request_question = ChatQuestion(
#             chat_id=record.chat_id,
#             question=record.question if record.question else ''
#         )
#
#         # 创建 LLMService 实例
#         llm_service = await LLMService.create(current_user, request_question, current_assistant, True)
#
#         # 设置聊天记录
#         llm_service.set_record(record)
#
#         # 直接执行推荐问题生成任务并获取完整结果（注意：这里去掉了 await）
#         result = list(llm_service.run_recommend_questions_task())
#
#         # 提取最终的推荐问题内容
#         recommended_questions = ""
#         for item in result:
#             if item.get("type") == "recommended_question":
#                 recommended_questions = item.get("content", "")
#                 break
#
#         # 直接返回最终结果
#         return {
#             "content": recommended_questions,
#             "type": "recommended_question"
#         }
#
#     except Exception as e:
#         # 打印异常堆栈信息用于调试
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=str(e)
#         )

# @router.post("/get_datasource_info", summary="获取数据源信息",
#              description="根据数据源名称获取数据源信息",
#              dependencies=[Depends(common_headers)])
# async def get_datasource_info(session: SessionDep, user: CurrentUser, request: DataSourceRequest) -> List[
#     CoreDatasource]:
#     """
#     根据数据源名称获取数据源信息
#
#     该接口用于获取指定名称的数据源详细信息，仅限已认证用户访问。
#
#     Args:
#         session (SessionDep): 数据库会话依赖，用于执行数据库操作
#         user (CurrentUser): 当前认证用户信息，确保接口访问权限
#         request (DataSourceRequest): 包含数据源名称的请求体对象
#
#     Returns:
#         List[CoreDatasource]: 返回指定名称的数据源信息列表
#
#     Note:
#         - 该接口使用 POST 方法但通过请求体传递参数
#         - 需要有效的用户认证令牌才能访问
#         - 数据源名称在请求体中以 JSON 格式传递
#     """
#     return get_datasource_by_name_or_id(session=session, user=user, query=request)
