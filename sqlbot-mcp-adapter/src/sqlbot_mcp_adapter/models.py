"""SQLBot MCP Adapter Data Models."""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    """Token request model."""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    create_chat: bool = Field(default=True, description="是否创建chatId")


class TokenResponse(BaseModel):
    """Token response model."""
    code: int
    data: Optional[dict] = None
    msg: Optional[str] = None


class TokenData(BaseModel):
    """Token data model."""
    access_token: str
    token_type: str
    expire: str
    chat_id: Optional[str] = None


class DataSource(BaseModel):
    """Data source model."""
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


class DataSourceListResponse(BaseModel):
    """Data source list response model."""
    code: int
    data: Optional[List[DataSource]] = None
    msg: Optional[str] = None


class MCPToolCall(BaseModel):
    """MCP tool call model."""
    method: str
    params: dict[str, Any]


class MCPToolResponse(BaseModel):
    """MCP tool response model."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


class MCPError(BaseModel):
    """MCP error model."""
    code: int
    message: str
    data: Optional[Any] = None