from datetime import datetime, timedelta, timezone
from datetime import datetime, timedelta, timezone
from typing import Optional

# 第三方库导入
from fastapi import HTTPException

# 本地模块导入
from apps.chat.curd.chat import (
    list_chats,
    delete_chat
)
from apps.chat.models.chat_model import Chat
from apps.openapi.models.openapiModels import (
    OpenClean
)
from apps.system.schemas.system_schema import BaseUserDTO
from common.core.config import settings
from common.core.deps import SessionDep, CurrentUser, Trans
from common.core.security import create_access_token
from common.utils.utils import SQLBotLogUtil


def commit_transaction(session: SessionDep) -> None:
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


def create_clean_response(
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


def get_chats_to_clean(
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


def execute_cleanup(session: SessionDep, chat_list: list[Chat]) -> tuple[int, int, list]:
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


def create_access_token_with_expiry(user_dict: dict) -> tuple[str, str]:
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
