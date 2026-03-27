from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field as PydanticField
from sqlalchemy import Column, Text, BigInteger, DateTime, Identity, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field


class CoreMetric(SQLModel, table=True):
    __tablename__ = "core_metric"

    id: Optional[int] = Field(sa_column=Column(BigInteger, Identity(always=True), primary_key=True))
    oid: int = Field(sa_column=Column(BigInteger, nullable=False), default=1)
    create_time: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=False), nullable=True))
    enabled: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True))
    code: str = Field(max_length=128)
    name: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    aliases: Optional[List[str]] = Field(sa_column=Column(JSONB, nullable=False), default_factory=list)
    terminology_root_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    metric_kind: str = Field(max_length=16)
    specific_ds: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True))
    datasource_ids: Optional[List[int]] = Field(sa_column=Column(JSONB, nullable=False), default_factory=list)
    measure_sql: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    base_metric_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    modifiers: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    expansion_hint: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    expression: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))


class MetricComponent(SQLModel, table=True):
    __tablename__ = "metric_component"

    id: Optional[int] = Field(sa_column=Column(BigInteger, Identity(always=True), primary_key=True))
    parent_metric_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    child_metric_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    slot_code: str = Field(max_length=64)


class MetricComponentItem(BaseModel):
    slot_code: str
    child_metric_id: int


class MetricInfo(BaseModel):
    id: Optional[int] = None
    create_time: Optional[datetime] = None
    enabled: bool = True
    code: str
    name: str
    description: Optional[str] = None
    aliases: List[str] = PydanticField(default_factory=list)
    terminology_root_id: Optional[int] = None
    metric_kind: str
    specific_ds: bool = True
    datasource_ids: List[int] = PydanticField(default_factory=list)
    measure_sql: Optional[str] = None
    base_metric_id: Optional[int] = None
    modifiers: Optional[dict] = None
    expansion_hint: Optional[str] = None
    expression: Optional[str] = None
    components: List[MetricComponentItem] = PydanticField(default_factory=list)
