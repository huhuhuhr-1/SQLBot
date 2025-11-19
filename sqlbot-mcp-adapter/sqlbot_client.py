"""
SQLBot HTTP 客户端工具类

提供 SQLBot API 的 HTTP 调用功能，包括认证、数据源管理等。
"""

import json
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
from fastapi import HTTPException, Body
from pydantic import BaseModel, Field

from config import settings

logger = logging.getLogger(__name__)


class TokenResponse(BaseModel):
    """令牌响应模型"""
    access_token: str
    token_type: str = "bearer"
    expire: str
    chat_id: Optional[str] = None

    @classmethod
    def validate_chat_id(cls, v):
        """验证 chat_id 字段，允许字符串或整数"""
        if v is None:
            return None
        return str(v)


class DatabaseInfo(BaseModel):
    """数据库信息模型"""
    id: int
    name: str
    description: str
    type: str
    type_name: str
    create_time: datetime
    create_by: int
    status: str
    num: str
    oid: int


class DatabaseListResponse(BaseModel):
    """数据库列表响应模型"""
    databases: list[DatabaseInfo]
    count: int


class ChatRequest(BaseModel):
    """聊天请求模型"""
    question: str = Field(..., description="用户问题")
    chat_id: int = Field(..., description="聊天ID")
    db_id: int = Field(..., description="数据库ID")
    history_open: Optional[bool] = Body(default=False, description='历史信息打开')


class DataSourceRequest(BaseModel):
    """数据源查询请求模型"""
    name: str = Field(..., description="数据源名称")


class DataSourceDetailResponse(BaseModel):
    """数据源详细信息响应模型"""
    type_name: str
    name: str
    description: str
    create_time: datetime
    status: str
    oid: int
    embedding: str  # 向量嵌入，通常很长
    type: str
    id: int
    configuration: str
    create_by: int
    num: str
    table_relation: Optional[str] = None


class ChatRecordRequest(BaseModel):
    """聊天记录请求模型"""
    chat_record_id: int = Field(..., description="聊天记录ID")


class ChatRecordResponse(BaseModel):
    """聊天记录响应模型"""
    # 由于返回的是空字典 {}，使用通用的字典模型
    # 实际字段需要根据实际的聊天记录数据来确定
    pass


class ChatStreamResponse(BaseModel):
    """聊天流式响应基类"""
    type: str = Field(..., description="响应类型")


class ChatIdResponse(ChatStreamResponse):
    """聊天ID响应"""
    type: str = "id"
    id: int


class ChatBriefResponse(ChatStreamResponse):
    """聊天简述响应"""
    type: str = "brief"
    brief: str


class ChatContentResponse(ChatStreamResponse):
    """聊天内容响应"""
    type: str
    content: str
    reasoning_content: str = ""


class ChatInfoResponse(ChatStreamResponse):
    """聊天信息响应"""
    type: str = "info"
    msg: str


class ChatSqlResponse(ChatStreamResponse):
    """聊天SQL响应"""
    type: str = "sql"
    content: str


class ChatDataFinishResponse(ChatStreamResponse):
    """聊天数据完成响应"""
    type: str = "data-finish"
    content: int


class ChatFinishResponse(ChatStreamResponse):
    """聊天完成响应"""
    type: str = "finish"


class SQLBotHTTPClient:
    """SQLBot HTTP 客户端

    封装了与 SQLBot API 的所有 HTTP 交互，包括认证管理、错误处理等。
    """

    def __init__(self, base_url: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        """初始化 SQLBot HTTP 客户端

        Args:
            base_url: SQLBot API 基础 URL，默认从环境变量获取
            username: 用户名，默认从环境变量获取
            password: 密码，默认从环境变量获取
        """
        self.base_url = base_url or os.getenv("SQLBOT_BASE_URL", "http://localhost:8000/api/v1")
        self.username = username or os.getenv("SQLBOT_USERNAME", "admin")
        self.password = password or os.getenv("SQLBOT_PASSWORD", "SQLBot@123456")

        # 缓存令牌
        self._cached_token: Optional[TokenResponse] = None

        logger.info(f"SQLBot HTTP Client initialized with base URL: {self.base_url}")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发起 HTTP 请求的通用方法

        Args:
            method: HTTP 方法 (GET, POST, PUT, DELETE)
            endpoint: API 端点
            **kwargs: httpx 请求参数

        Returns:
            API 响应数据

        Raises:
            HTTPException: 请求失败时抛出
        """
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            try:
                logger.debug(f"Making {method} request to {url}")

                response = await client.request(method, url, **kwargs)
                logger.info(f"Response status: {response.status_code}")

                if response.status_code != 200:
                    error_msg = f"Request failed: {response.text}"
                    logger.error(error_msg)
                    raise HTTPException(status_code=response.status_code, detail=error_msg)

                result = response.json()
                logger.debug(f"Response data: {result}")

                if result.get("code") != 0:
                    error_msg = result.get("msg", "Unknown error")
                    logger.error(f"API error: {error_msg}")
                    raise HTTPException(status_code=400, detail=f"API error: {error_msg}")

                return result.get("data", {})

            except httpx.RequestError as e:
                error_msg = f"Request error: {str(e)}"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)

    async def get_token(self, create_chat: bool = True) -> TokenResponse:
        """获取 SQLBot 访问令牌

        Args:
            create_chat: 是否创建聊天会话

        Returns:
            TokenResponse: 令牌信息

        Raises:
            HTTPException: 获取令牌失败时抛出
        """
        if not self.username or not self.password:
            error_msg = "SQLBot username or password not configured"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"Getting token for user: {self.username}, create_chat={create_chat}")

        request_data = {
            "username": self.username,
            "password": self.password,
            "create_chat": create_chat
        }

        data = await self._make_request(
            "POST",
            "/openapi/getToken",
            json=request_data
        )

        try:
            # 处理 chat_id 字段的数据类型转换
            token_data = data.copy()
            if 'chat_id' in token_data and token_data['chat_id'] is not None:
                token_data['chat_id'] = str(token_data['chat_id'])

            token_response = TokenResponse(**token_data)
            self._cached_token = token_response
            logger.info("Successfully retrieved and cached token")
            return token_response
        except Exception as e:
            error_msg = f"Invalid token response format: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    async def get_database_list(self) -> DatabaseListResponse:
        """获取数据源列表

        Returns:
            DatabaseListResponse: 数据库列表信息

        Raises:
            HTTPException: 获取数据源列表失败时抛出
        """
        logger.info("Getting database list")

        # 确保有可用的令牌
        token = await self._get_valid_token()
        headers = {"X-Sqlbot-Token": token.access_token}

        data = await self._make_request(
            "GET",
            "/openapi/getDataSourceList",
            headers=headers
        )

        try:
            # 处理不同的响应格式
            if isinstance(data, dict) and "databases" in data:
                database_list = DatabaseListResponse(**data)
            elif isinstance(data, list):
                # 如果直接返回数据库列表
                database_list = DatabaseListResponse(
                    databases=[DatabaseInfo(**db) for db in data],
                    count=len(data)
                )
            else:
                error_msg = f"Unexpected response format: {type(data)}"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)

            logger.info(f"Successfully retrieved {database_list.count} databases")
            return database_list

        except Exception as e:
            error_msg = f"Invalid database list response format: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    async def chat_stream(self, question: str, chat_id: int, db_id: int):
        """发起聊天请求并返回流式响应

        Args:
            question: 用户问题
            chat_id: 聊天ID
            db_id: 数据库ID

        Yields:
            dict: 流式响应数据

        Raises:
            HTTPException: 聊天请求失败时抛出
        """
        logger.info(f"Starting chat stream: question='{question}', chat_id={chat_id}, db_id={db_id}")

        # 确保有可用的令牌
        token = await self._get_valid_token()
        headers = {"X-Sqlbot-Token": token.access_token, "Content-Type": "application/json"}

        request_data = ChatRequest(question=question, chat_id=chat_id, db_id=db_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                logger.info(f"Sending chat request to {self.base_url}/openapi/chat")

                async with client.stream(
                        "POST",
                        f"{self.base_url}/openapi/chat",
                        headers=headers,
                        json=request_data.model_dump()
                ) as response:
                    logger.info(f"Chat response status: {response.status_code}")

                    if response.status_code != 200:
                        # 读取错误响应内容
                        error_content = await response.aread()
                        error_msg = f"Chat request failed: {error_content.decode('utf-8', errors='ignore')}"
                        logger.error(error_msg)
                        raise HTTPException(status_code=response.status_code, detail=error_msg)

                    # 处理流式响应
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        # 解析 SSE 格式的数据 (data: {json})
                        if line.startswith('data:'):
                            data_str = line[6:].strip()  # 移除 'data:' 前缀
                            if not data_str:
                                continue

                            try:
                                # 解析 JSON 数据
                                data = json.loads(data_str)
                                logger.debug(f"Chat stream data: {data}")
                                yield data

                            except json.JSONDecodeError as e:
                                # 尝试修复常见的问题：可能数据被截断或格式不正确
                                try:
                                    # 尝试添加缺失的大括号
                                    if not data_str.startswith('{'):
                                        data_str = '{' + data_str
                                    if not data_str.endswith('}'):
                                        data_str = data_str + '}'
                                    data = json.loads(data_str)
                                    logger.debug(f"Chat stream data (fixed): {data}")
                                    yield data
                                except:
                                    logger.debug(f"Skipping unparseable data: {data_str}")
                                continue

            except httpx.RequestError as e:
                error_msg = f"Chat request error: {str(e)}"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
            except Exception as e:
                error_msg = f"Error in chat stream: {str(e)}"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)

    async def get_data_source_by_name(self, name: str) -> DataSourceDetailResponse:
        """通过名称获取数据源详细信息

        Args:
            name: 数据源名称

        Returns:
            DataSourceDetailResponse: 数据源详细信息

        Raises:
            HTTPException: 获取数据源信息失败时抛出
        """
        logger.info(f"Getting data source by name: {name}")

        # 确保有可用的令牌
        token = await self._get_valid_token()
        headers = {"X-Sqlbot-Token": token.access_token, "Content-Type": "application/json"}

        request_data = DataSourceRequest(name=name)

        data = await self._make_request(
            "POST",
            "/openapi/getDataSourceByIdOrName",
            headers=headers,
            json=request_data.model_dump()
        )

        try:
            # 检查数据源是否存在
            if data is None:
                error_msg = f"Data source '{name}' not found"
                logger.warning(error_msg)
                raise HTTPException(status_code=404, detail=error_msg)

            # 直接返回数据源详情响应
            data_source_detail = DataSourceDetailResponse(**data)
            logger.info(f"Successfully retrieved data source: {data_source_detail.name}")
            return data_source_detail
        except HTTPException:
            # 重新抛出 HTTPException
            raise
        except Exception as e:
            error_msg = f"Invalid data source response format: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    async def get_chat_record(self, chat_record_id: int) -> Dict[str, Any]:
        """获取聊天记录

        Args:
            chat_record_id: 聊天记录ID

        Returns:
            Dict[str, Any]: 聊天记录数据

        Raises:
            HTTPException: 获取聊天记录失败时抛出
        """
        logger.info(f"Getting chat record: chat_record_id={chat_record_id}")

        # 确保有可用的令牌
        token = await self._get_valid_token()
        headers = {"X-Sqlbot-Token": token.access_token, "Content-Type": "application/json"}

        request_data = ChatRecordRequest(chat_record_id=chat_record_id)

        data = await self._make_request(
            "POST",
            "/openapi/getData",
            headers=headers,
            json=request_data.model_dump()
        )

        try:
            # 直接返回聊天记录数据
            logger.info(f"Successfully retrieved chat record: chat_record_id={chat_record_id}")
            return data
        except Exception as e:
            error_msg = f"Error getting chat record: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    async def _get_valid_token(self) -> TokenResponse:
        """获取有效的令牌，如果缓存无效则重新获取

        Returns:
            TokenResponse: 有效的令牌
        """
        # 这里可以添加令牌有效性检查逻辑
        # 目前简单使用缓存的令牌，如果没有则获取新令牌
        if self._cached_token is None:
            return await self.get_token(create_chat=False)

        # TODO: 添加令牌过期检查
        # 可以检查令牌的 expire 字段，如果即将过期则重新获取

        return self._cached_token

    def clear_token_cache(self):
        """清除令牌缓存"""
        self._cached_token = None
        logger.info("Token cache cleared")


# 全局 HTTP 客户端实例
_sqlbot_client: Optional[SQLBotHTTPClient] = None


def get_sqlbot_client() -> SQLBotHTTPClient:
    """获取 SQLBot HTTP 客户端单例实例

    Returns:
        SQLBotHTTPClient: 客户端实例
    """
    global _sqlbot_client
    if _sqlbot_client is None:
        _sqlbot_client = SQLBotHTTPClient(
            base_url=settings.sqlbot_base_url,
            username=settings.sqlbot_username,
            password=settings.sqlbot_password
        )
    return _sqlbot_client


def create_sqlbot_client(base_url: str, username: str, password: str) -> SQLBotHTTPClient:
    """创建自定义配置的 SQLBot HTTP 客户端实例

    Args:
        base_url: SQLBot API 基础 URL
        username: 用户名
        password: 密码

    Returns:
        SQLBotHTTPClient: 客户端实例
    """
    return SQLBotHTTPClient(base_url=base_url, username=username, password=password)
