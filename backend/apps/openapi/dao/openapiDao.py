"""
OpenAPI 数据访问对象模块

该模块提供了 OpenAPI 相关的数据库操作功能，包括：
- 数据源查询和管理
- 聊天会话与数据源绑定

作者: huhuhuhr
日期: 2025/08/30
版本: 1.0.0
"""

from typing import Optional, List

from sqlalchemy import and_
from sqlmodel import select

from apps.chat.models.chat_model import Chat, ChatRecord
from apps.datasource.models.datasource import CoreDatasource
from apps.openapi.models.openapiModels import DataSourceRequest, OpenChatQuestion
from common.core.deps import SessionDep, CurrentUser


def get_datasource_by_name_or_id(
        session: SessionDep,
        user: CurrentUser,
        query: DataSourceRequest
) -> Optional[CoreDatasource]:
    """
    根据数据源名称或ID查询数据源信息
    
    Args:
        session: 数据库会话依赖
        user: 当前用户信息
        query: 数据源查询请求对象
        
    Returns:
        Optional[CoreDatasource]: 找到的数据源对象，如果未找到则返回 None
        
    Raises:
        ValueError: 当查询条件验证失败时抛出异常
    """
    # 验证查询条件
    query.validate_query_fields_manual()

    # 获取当前用户的工作空间ID，默认为1
    current_oid = user.oid if user.oid is not None else 1

    # 构建查询条件列表
    conditions = [CoreDatasource.oid == current_oid]

    # 如果提供了名称，添加名称查询条件
    if query.name is not None:
        conditions.append(CoreDatasource.name == query.name)

    # 如果提供了ID，添加ID查询条件
    if query.id is not None:
        conditions.append(CoreDatasource.id == query.id)

    # 执行查询并返回第一个匹配结果
    statement = select(CoreDatasource).where(and_(*conditions))
    return session.exec(statement).first()


async def bind_datasource(
        datasource: CoreDatasource,
        chat_id: int,
        session: SessionDep
) -> None:
    """
    将数据源绑定到聊天会话
    
    Args:
        datasource: 要绑定的数据源对象
        request_question: 聊天问题请求对象
        session: 数据库会话依赖
        
    Note:
        此函数会修改聊天会话的数据源关联，并提交事务
    """
    # 获取聊天会话对象
    chat: Chat = session.get(Chat, chat_id)

    # 设置数据源ID
    chat.datasource = datasource.id

    # 将修改后的聊天对象添加到会话中
    session.add(chat)

    # 提交事务
    session.commit()


def get_all_datasources(
        session: SessionDep,
        user: CurrentUser
) -> List[CoreDatasource]:
    """
    获取当前用户工作空间下的所有数据源
    
    Args:
        session: 数据库会话依赖
        user: 当前用户信息

    Returns:
        List[CoreDatasource]: 数据源列表
    """
    # 获取当前用户的工作空间ID，默认为1
    current_oid = user.oid if user.oid is not None else 1

    # 构建查询条件
    conditions = [CoreDatasource.oid == current_oid]

    # 执行查询并返回所有匹配结果
    statement = select(CoreDatasource).where(and_(*conditions))
    return session.exec(statement).all()


def select_one(
        session: SessionDep,
        user: CurrentUser
) -> Optional[CoreDatasource]:
    """
    根据数据源名称或ID查询数据源信息

    Args:
        session: 数据库会话依赖
        user: 当前用户信息

    Returns:
        Optional[CoreDatasource]: 找到的数据源对象，如果未找到则返回 None

    Raises:
        ValueError: 当查询条件验证失败时抛出异常
    """

    # 获取当前用户的工作空间ID，默认为1
    current_oid = user.oid if user.oid is not None else 1

    # 构建查询条件列表
    conditions = [CoreDatasource.oid == current_oid]

    # 执行查询并返回第一个匹配结果
    statement = select(CoreDatasource).where(and_(*conditions))
    return session.exec(statement).first()
