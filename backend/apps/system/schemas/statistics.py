"""Statistics API schemas: overview, trend, top, failure analysis, user detailed, records."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ----- Overview -----
class OverviewMetrics(BaseModel):
    total_queries: int = 0
    success_queries: int = 0
    failed_queries: int = 0
    success_rate: float = 0.0
    active_users: int = 0
    active_datasources: int = 0
    active_chats: int = 0
    avg_duration_seconds: Optional[float] = None
    total_users: int = 0
    total_datasources: int = 0
    total_tokens: int = 0
    duration_p50_seconds: Optional[float] = None
    duration_p90_seconds: Optional[float] = None
    duration_p99_seconds: Optional[float] = None


class DatasourceStats(BaseModel):
    datasource_id: Optional[int] = None
    datasource_name: Optional[str] = None
    total_queries: int = 0
    success_queries: int = 0
    failed_queries: int = 0
    success_rate: float = 0.0
    active_users: int = 0
    avg_duration_seconds: Optional[float] = None
    total_tokens: int = 0


class UserStats(BaseModel):
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    total_queries: int = 0
    success_queries: int = 0
    failed_queries: int = 0
    success_rate: float = 0.0
    active_datasources: int = 0
    avg_duration_seconds: Optional[float] = None
    total_tokens: int = 0


class DailyTrendPoint(BaseModel):
    date: datetime
    total_queries: int
    success_queries: int
    failed_queries: int
    avg_duration_seconds: Optional[float] = None
    total_tokens: int = 0
    success_rate: float = 0.0


class StatisticsOverviewResponse(BaseModel):
    overview: OverviewMetrics
    by_datasource: List[DatasourceStats]
    by_user: List[UserStats]
    daily_trend: List[DailyTrendPoint]


# ----- Trend (standalone) -----
class TrendPoint(BaseModel):
    date: datetime
    total_queries: int
    success_queries: int
    failed_queries: int
    avg_duration_seconds: Optional[float] = None
    total_tokens: int = 0
    success_rate: float = 0.0


class StatisticsTrendResponse(BaseModel):
    trend: List[TrendPoint]


# ----- Datasource TOP -----
class DatasourceTopItem(BaseModel):
    datasource_id: Optional[int] = None
    datasource_name: Optional[str] = None
    value: int = 0
    sort_key: str = "total_queries"


class StatisticsDatasourceTopResponse(BaseModel):
    items: List[DatasourceTopItem]


# ----- Datasource detailed -----
class DatasourceDetailedItem(BaseModel):
    datasource_id: Optional[int] = None
    datasource_name: Optional[str] = None
    total_queries: int = 0
    success_queries: int = 0
    failed_queries: int = 0
    success_rate: float = 0.0
    active_users: int = 0
    avg_duration_seconds: Optional[float] = None
    total_tokens: int = 0


class StatisticsDatasourceDetailedResponse(BaseModel):
    items: List[DatasourceDetailedItem]
    total: int
    page: int
    size: int
    total_pages: int


# ----- Failure analysis -----
class FailureReasonItem(BaseModel):
    error_type: str
    count: int
    sample_message: Optional[str] = None


class FailureByDatasourceItem(BaseModel):
    datasource_id: Optional[int] = None
    datasource_name: Optional[str] = None
    failed_count: int = 0


class FailureByHourItem(BaseModel):
    hour: int
    failed_count: int


class StatisticsFailureAnalysisResponse(BaseModel):
    by_reason: List[FailureReasonItem]
    by_datasource: List[FailureByDatasourceItem]
    by_hour: List[FailureByHourItem]


# ----- User detailed -----
class UserDetailedItem(BaseModel):
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    total_queries: int = 0
    success_queries: int = 0
    failed_queries: int = 0
    success_rate: float = 0.0
    active_datasources: int = 0
    avg_duration_seconds: Optional[float] = None
    total_tokens: int = 0


class StatisticsUserDetailedResponse(BaseModel):
    items: List[UserDetailedItem]
    total: int
    page: int
    size: int
    total_pages: int


# ----- Records (enhanced) -----
class RecordItem(BaseModel):
    id: Optional[int] = None
    chat_id: Optional[int] = None
    create_time: Optional[datetime] = None
    create_by: Optional[int] = None
    user_name: Optional[str] = None
    datasource_id: Optional[int] = None
    datasource_name: Optional[str] = None
    question: Optional[str] = None
    finish: bool = False
    error: Optional[str] = None
    error_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    total_tokens: Optional[int] = None
