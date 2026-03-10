"""
自定义提示词表模型，与 alembic 046_add_custom_prompt 一致。
供设置-自定义提示词页 CRUD 使用，不依赖 xpack。
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import Column, BigInteger, DateTime, Text, Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field


class CustomPromptTypeEnum(str, Enum):
    GENERATE_SQL = "GENERATE_SQL"
    ANALYSIS = "ANALYSIS"
    PREDICT_DATA = "PREDICT_DATA"


class CustomPrompt(SQLModel, table=True):
    __tablename__ = "custom_prompt"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger(), primary_key=True, autoincrement=True))
    oid: Optional[int] = Field(default=None, sa_column=Column(BigInteger(), nullable=True))
    type: Optional[str] = Field(default=None, sa_column=Column(String(20), nullable=True))
    create_time: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(), nullable=True))
    name: Optional[str] = Field(default=None, max_length=255, nullable=True)
    prompt: Optional[str] = Field(default=None, sa_column=Column(Text(), nullable=True))
    specific_ds: Optional[bool] = Field(default=None, sa_column=Column(Boolean(), nullable=True))
    datasource_ids: Optional[List[int]] = Field(default=None, sa_column=Column(JSONB(), nullable=True))
    is_full_template: Optional[bool] = Field(default=False, sa_column=Column(Boolean(), nullable=True))
