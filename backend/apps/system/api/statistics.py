"""System statistics API: overview, trend, datasource top, failure analysis, user detailed, records."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from apps.system.crud import statistics as stats_crud
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from apps.system.schemas.statistics import (
    StatisticsOverviewResponse,
    StatisticsTrendResponse,
    StatisticsDatasourceTopResponse,
    StatisticsDatasourceDetailedResponse,
    StatisticsFailureAnalysisResponse,
    StatisticsUserDetailedResponse,
    RecordItem,
)
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from common.core.deps import CurrentUser, SessionDep
from common.core.schemas import PaginatedResponse


router = APIRouter(tags=["system_statistics"], prefix="/system/statistics")


@router.get(
    "/overview",
    response_model=StatisticsOverviewResponse,
    summary=f"{PLACEHOLDER_PREFIX}system_statistics_overview",
)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def statistics_overview(
    session: SessionDep,
    current_user: CurrentUser,
    start_time: Optional[datetime] = Query(
        None, description=f"{PLACEHOLDER_PREFIX}statistics_start_time"
    ),
    end_time: Optional[datetime] = Query(
        None, description=f"{PLACEHOLDER_PREFIX}statistics_end_time"
    ),
) -> StatisticsOverviewResponse:
    """管理员统计分析总览：概览指标、按数据源/用户聚合、每日趋势（含 token、耗时分位数）。"""
    overview, daily_trend = stats_crud.get_overview(
        session, current_user, start_time, end_time
    )
    return StatisticsOverviewResponse(
        overview=overview,
        by_datasource=[],
        by_user=[],
        daily_trend=daily_trend,
    )


@router.get(
    "/trend",
    response_model=StatisticsTrendResponse,
    summary=f"{PLACEHOLDER_PREFIX}system_statistics_trend",
)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def statistics_trend(
    session: SessionDep,
    current_user: CurrentUser,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
) -> StatisticsTrendResponse:
    """多指标每日趋势：总问数、成功/失败、平均耗时、Token 消耗、成功率。"""
    trend = stats_crud.get_trend(session, current_user, start_time, end_time)
    return StatisticsTrendResponse(trend=trend)


@router.get(
    "/datasource/top",
    response_model=StatisticsDatasourceTopResponse,
    summary=f"{PLACEHOLDER_PREFIX}system_statistics_datasource_top",
)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def statistics_datasource_top(
    session: SessionDep,
    current_user: CurrentUser,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    sort_by: str = Query(
        "total_queries",
        description="total_queries | failed_queries | avg_duration_seconds | total_tokens",
    ),
    limit: int = Query(10, ge=1, le=50),
) -> StatisticsDatasourceTopResponse:
    """数据源 TOP 排行：按访问次数、失败次数、平均耗时、Token 消耗排序。"""
    items = stats_crud.get_datasource_top(
        session, current_user, start_time, end_time, sort_by=sort_by, limit=limit
    )
    return StatisticsDatasourceTopResponse(items=items)


@router.get(
    "/failure/analysis",
    response_model=StatisticsFailureAnalysisResponse,
    summary=f"{PLACEHOLDER_PREFIX}system_statistics_failure_analysis",
)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def statistics_failure_analysis(
    session: SessionDep,
    current_user: CurrentUser,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
) -> StatisticsFailureAnalysisResponse:
    """失败分析：按原因分类、按数据源排行、按小时分布。"""
    by_reason, by_datasource, by_hour = stats_crud.get_failure_analysis(
        session, current_user, start_time, end_time
    )
    return StatisticsFailureAnalysisResponse(
        by_reason=by_reason,
        by_datasource=by_datasource,
        by_hour=by_hour,
    )


@router.get(
    "/user/detailed",
    response_model=StatisticsUserDetailedResponse,
    summary=f"{PLACEHOLDER_PREFIX}system_statistics_user_detailed",
)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def statistics_user_detailed(
    session: SessionDep,
    current_user: CurrentUser,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="按用户名搜索"),
    order_by: str = Query(
        "total_queries",
        description="total_queries | success_rate | avg_duration_seconds | total_tokens",
    ),
    desc: bool = Query(True),
) -> StatisticsUserDetailedResponse:
    """用户维度详细统计（分页、排序）。"""
    items, total = stats_crud.get_user_detailed(
        session, current_user, start_time, end_time,
        page=page, size=size, keyword=keyword, order_by=order_by, desc=desc,
    )
    total_pages = (total + size - 1) // size
    return StatisticsUserDetailedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.get(
    "/datasource/detailed",
    response_model=StatisticsDatasourceDetailedResponse,
    summary=f"{PLACEHOLDER_PREFIX}system_statistics_datasource_detailed",
)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def statistics_datasource_detailed(
    session: SessionDep,
    current_user: CurrentUser,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="按数据源名称搜索"),
    order_by: str = Query(
        "total_queries",
        description="total_queries | failed_queries | success_rate | avg_duration_seconds | total_tokens",
    ),
    desc: bool = Query(True),
) -> StatisticsDatasourceDetailedResponse:
    """数据源维度详细统计（分页、排序、搜索）。"""
    items, total = stats_crud.get_datasource_detailed(
        session, current_user, start_time, end_time,
        page=page, size=size, keyword=keyword, order_by=order_by, desc=desc,
    )
    total_pages = (total + size - 1) // size
    return StatisticsDatasourceDetailedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.get(
    "/records",
    response_model=PaginatedResponse[RecordItem],
    summary=f"{PLACEHOLDER_PREFIX}system_statistics_records",
)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def statistics_records(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    user_id: Optional[int] = Query(None, description="按用户筛选"),
    datasource_id: Optional[int] = Query(None, description="按数据源筛选"),
    failed_only: bool = Query(False, description="仅失败/异常"),
) -> PaginatedResponse[RecordItem]:
    """问数明细（分页），含 error_type、duration_seconds、total_tokens。"""
    items, total = stats_crud.get_records(
        session, current_user,
        start_time, end_time, user_id, datasource_id, failed_only,
        page=page, size=size,
    )
    total_pages = (total + size - 1) // size
    return PaginatedResponse[RecordItem](
        items=items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )
