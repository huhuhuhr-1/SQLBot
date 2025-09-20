"""
OpenAPI 数据模型模块

该模块定义了 OpenAPI 接口使用的所有数据模型，包括：
- 请求和响应模型
- 数据验证规则
- 公共头部依赖

作者: huhuhuhr
日期: 2025/01/30
版本: 1.0.0
"""
from dataclasses import dataclass
from typing import Any, Dict, Union
import json
import re
from pydantic import BaseModel, field_validator
from typing import List, Union, Optional

from fastapi import Body, Header
from pydantic import BaseModel, validator

from apps.chat.models.chat_model import AiModelQuestion


class OpenClean(BaseModel):
    """
    聊天记录清理请求模型
    
    用于指定要清理的聊天记录ID列表
    """
    chat_ids: Union[int, List[int]] = Body(
        None,
        description='会话标识或会话标识列表，为空时清理所有记录'
    )

    def get_chat_ids(self) -> List[int]:
        """
        获取标准化的chat_id列表
        
        Returns:
            List[int]: 标准化的聊天ID列表
        """
        if isinstance(self.chat_ids, int):
            return [self.chat_ids]
        return self.chat_ids or []


class OpenChat(BaseModel):
    """
    聊天记录查询请求模型
    
    用于根据聊天记录ID查询相关信息
    """
    chat_record_id: int = Body(..., description='会话聊天消息标识')
    question: str = Body(None, description='问题内容')
    chat_data_object: Any = Body(None, description='分析问题')
    my_promote: str = Body(None, description='自定义提示词')
    my_schema: Optional[str] = Body(None, description='自定义schema')
    intent: Optional[bool] = Body(default=False, description='是否进行意图检测')
    every: Optional[bool] = Body(default=False, description='逐条分析')
    history_open: Optional[bool] = Body(default=True, description='历史信息打开')

    @field_validator('my_promote', 'my_schema', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """将空字符串转换为 None"""
        if v == '':
            return None
        return v


class OpenChatQuestion(AiModelQuestion):
    """
    开放API聊天问题模型
    
    继承自AiModelQuestion，扩展了数据源和聊天会话相关字段
    """
    question: str = Body(..., description='用户问题内容')
    chat_id: int = Body(..., description='聊天会话标识')
    db_id: Optional[int] = Body(None, description='数据源标识')
    my_sql: Optional[str] = Body(None, description='自定义sql')
    my_promote: Optional[str] = Body(None, description='自定义提示词')
    my_schema: Optional[str] = Body(None, description='自定义schema')
    intent: Optional[bool] = Body(default=False, description='是否进行意图检测')
    analysis: Optional[bool] = Body(default=False, description='是否分析')
    predict: Optional[bool] = Body(default=False, description='是否预测')
    recommend: Optional[bool] = Body(default=False, description='是否推荐')
    every: Optional[bool] = Body(default=False, description='逐条分析')
    history_open: Optional[bool] = Body(default=True, description='历史信息打开')

    @field_validator('my_promote', 'my_schema', 'my_sql', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """将空字符串转换为 None"""
        if v == '':
            return None
        return v


class OpenToken(BaseModel):
    """
    开放API访问令牌响应模型
    
    包含用户认证成功后的访问凭证信息
    """
    access_token: str = Body(..., description='访问令牌，格式为 "bearer {token}"')
    token_type: str = Body(default="bearer", description='令牌类型')
    expire: str = Body(..., description='令牌过期时间')
    chat_id: Optional[int] = Body(default=None, description='聊天会话ID，可选')


class TokenRequest(BaseModel):
    """
    令牌请求模型

    用于通过用户名和密码获取访问令牌的请求体数据模型
    
    Attributes:
        username: 用户名
        password: 密码
        create_chat: 是否在登录时创建聊天会话
    """
    username: str = Body(..., description='用户名')
    password: str = Body(..., description='密码')
    create_chat: bool = Body(default=False, description='是否创建聊天会话')


class DataSourceRequest(BaseModel):
    """
    数据源请求模型

    用于接收获取数据源信息接口的参数
    
    Attributes:
        name: 数据源名称（可选）
        id: 数据源ID（可选）
        
    Note:
        name 和 id 至少需要提供一个，不能同时为空
    """
    name: Optional[str] = Body(default=None, description='数据源名称')
    id: Optional[int] = Body(default=None, description='数据源ID')

    @validator('name', 'id')
    def validate_query_fields(cls, v, values):
        """
        验证查询字段
        
        确保至少有一个查询字段不为空
        
        Args:
            v: 当前字段值
            values: 其他字段值
            
        Raises:
            ValueError: 当所有查询字段都为空时抛出异常
        """
        # 如果当前字段为空，检查其他字段是否也为空
        if v is None:
            other_fields = {k: v for k, v in values.items() if k in ['name', 'id']}
            if all(v is None for v in other_fields.values()):
                raise ValueError("name 和 id 不能同时为空")
        return v

    def validate_query_fields_manual(self) -> 'DataSourceRequest':
        """
        验证查询字段（兼容性方法）
        
        Returns:
            DataSourceRequest: 验证后的请求对象
            
        Raises:
            ValueError: 当查询条件验证失败时抛出异常
        """
        if self.name is None and self.id is None:
            raise ValueError("name 和 id 不能同时为空")
        return self


async def common_headers(
        x_sqlbot_token: Optional[str] = Header(
            None,
            alias="X-Sqlbot-Token",
            description="认证 Token"
        ),
        content_type: Optional[str] = Header(
            None,
            alias="Content-Type",
            description="返回体类型，支持 application/json 和 text/event-stream"
        ),
) -> dict:
    """
    公共请求头依赖函数
    
    用于验证和提取公共请求头信息
    
    Args:
        x_sqlbot_token: SQLBot认证令牌
        content_type: 内容类型
        
    Returns:
        dict: 包含请求头信息的字典
    """
    return {
        "X-Sqlbot-Token": x_sqlbot_token,
        "Content-Type": content_type
    }


@dataclass
class AnalysisIntentPayload:
    role: str
    task: str
    intent: str = ""  # 可选，默认空字符串

    @classmethod
    def from_llm(cls, content: Union[str, Dict[str, Any]]) -> "AnalysisIntentPayload":
        """
        将 LLM 返回的 JSON（或包含 JSON 的字符串）解析为 AnalysisIntentPayload。
        若缺失字段，role/task 会回退为空字符串，intent 默认为空字符串。
        """
        if isinstance(content, str):
            # 提取第一段 {...} 作为 JSON（容错处理：剔除多余文本/Markdown）
            m = re.search(r"\{.*\}", content, flags=re.S)
            if not m:
                raise ValueError("LLM 输出中未找到 JSON 对象")
            data = json.loads(m.group(0))
        else:
            data = content

        return cls(
            role=str(data.get("role", "")).strip(),
            task=str(data.get("task", "")).strip(),
            intent=str(data.get("intent", "")).strip(),
        )

    def to_json(self) -> str:
        """序列化为 JSON 字符串（始终包含三个字段）。"""
        return json.dumps(
            {"role": self.role, "task": self.task, "intent": self.intent},
            ensure_ascii=False
        )


@dataclass
class IntentPayload:
    search: str
    analysis: str
    predict: str = ""  # 可选，默认空字符串

    @classmethod
    def from_llm(cls, content: Union[str, Dict[str, Any]]) -> "IntentPayload":
        """
        将 LLM 返回的 JSON（或包含 JSON 的字符串）解析为 IntentPayload。
        若缺失字段，search/analysis 会回退为空字符串，predict 默认为空字符串。
        """
        if isinstance(content, str):
            # 提取第一段 {...} 作为 JSON（容错处理：剔除多余文本/Markdown）
            m = re.search(r"\{.*\}", content, flags=re.S)
            if not m:
                raise ValueError("LLM 输出中未找到 JSON 对象")
            data = json.loads(m.group(0))
        else:
            data = content

        return cls(
            search=str(data.get("search", "")).strip(),
            analysis=str(data.get("analysis", "")).strip(),
            predict=str(data.get("predict", "")).strip(),
        )

    def to_json(self) -> str:
        """序列化为 JSON 字符串（始终包含三个字段）。"""
        return json.dumps(
            {"search": self.search, "analysis": self.analysis, "predict": self.predict},
            ensure_ascii=False
        )
