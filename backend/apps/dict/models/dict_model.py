from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, Text, BigInteger, DateTime, Identity, Boolean
from sqlmodel import SQLModel, Field as SQLField


class BizDict(SQLModel, table=True):
    __tablename__ = "biz_dict"
    id: Optional[int] = SQLField(sa_column=Column(BigInteger, Identity(always=True), primary_key=True))
    oid: int = SQLField(sa_column=Column(BigInteger, nullable=False))
    name: str = SQLField(max_length=255)
    code: str = SQLField(max_length=128)
    description: Optional[str] = SQLField(default=None, sa_column=Column(Text, nullable=True))
    enabled: bool = SQLField(sa_column=Column(Boolean, nullable=False, default=True))
    create_time: Optional[datetime] = SQLField(default=None, sa_column=Column(DateTime(timezone=False), nullable=True))


class BizDictItem(SQLModel, table=True):
    __tablename__ = "biz_dict_item"
    id: Optional[int] = SQLField(sa_column=Column(BigInteger, Identity(always=True), primary_key=True))
    dict_id: int = SQLField(sa_column=Column(BigInteger, nullable=False))
    item_code: str = SQLField(max_length=512)
    item_name: str = SQLField(max_length=512)
    sort: int = SQLField(sa_column=Column(BigInteger, nullable=False, default=0))
    enabled: bool = SQLField(sa_column=Column(Boolean, nullable=False, default=True))


class BizDictBinding(SQLModel, table=True):
    __tablename__ = "biz_dict_binding"
    id: Optional[int] = SQLField(sa_column=Column(BigInteger, Identity(always=True), primary_key=True))
    dict_id: int = SQLField(sa_column=Column(BigInteger, nullable=False))
    datasource_id: int = SQLField(sa_column=Column(BigInteger, nullable=False))
    table_name: str = SQLField(max_length=512)
    column_name: str = SQLField(max_length=512)
    enabled: bool = SQLField(sa_column=Column(Boolean, nullable=False, default=True))


class BizDictItemInfo(BaseModel):
    id: Optional[int] = None
    item_code: str = ""
    item_name: str = ""
    sort: int = 0
    enabled: bool = True


class BizDictSave(BaseModel):
    id: Optional[int] = None
    name: str = ""
    code: str = ""
    description: Optional[str] = None
    enabled: bool = True
    items: List[BizDictItemInfo] = Field(default_factory=list)


class BizDictListRow(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    enabled: bool = True
    create_time: Optional[datetime] = None
    item_count: int = 0


class BizDictDetail(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    enabled: bool = True
    create_time: Optional[datetime] = None
    items: List[BizDictItemInfo] = Field(default_factory=list)


class BizDictBindingSave(BaseModel):
    id: Optional[int] = None
    dict_id: int
    datasource_id: int
    table_name: str
    column_name: str
    enabled: bool = True


class BizDictBindingRow(BaseModel):
    id: int
    dict_id: int
    dict_name: str
    dict_code: str
    datasource_id: int
    datasource_name: Optional[str] = None
    table_name: str
    column_name: str
    enabled: bool = True
