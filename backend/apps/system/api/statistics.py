from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import and_, case, func, or_, select

from apps.chat.models.chat_model import Chat, ChatRecord
from apps.datasource.models.datasource import CoreDatasource
from apps.system.models.user import UserModel
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from common.core.deps import CurrentUser, SessionDep
from common.core.pagination import Paginator
from common.core.schemas import PaginationParams, PaginatedResponse


class OverviewMetrics(BaseModel):
    total_queries: int = 0
    success_queries: int = 0
    failed_queries: int = 0
    success_rate: float = 0.0
    active_users: int = 0
    active_datasources: int = 0
    active_chats: int = 0
    avg_duration_seconds: Optional[float] = None


class DatasourceStats(BaseModel):
    datasource_id: Optional[int] = None
    datasource_name: Optional[str] = None
    total_queries: int = 0
    success_queries: int = 0
    failed_queries: int = 0
    success_rate: float = 0.0
    active_users: int = 0


class UserStats(BaseModel):
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    total_queries: int = 0
    success_queries: int = 0
    failed_queries: int = 0
    success_rate: float = 0.0
    active_datasources: int = 0


class DailyTrendPoint(BaseModel):
    date: datetime
    total_queries: int
    success_queries: int
    failed_queries: int


class StatisticsOverviewResponse(BaseModel):
    overview: OverviewMetrics
    by_datasource: List[DatasourceStats]
    by_user: List[UserStats]
    daily_trend: List[DailyTrendPoint]


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


router = APIRouter(tags=["system_statistics"], prefix="/system/statistics")


def _build_common_filters(
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
):
    filters = [Chat.oid == current_user.oid]
    if start_time is not None:
        filters.append(ChatRecord.create_time >= start_time)
    if end_time is not None:
        filters.append(ChatRecord.create_time <= end_time)
    return filters


@router.get(
    "/overview",
    response_model=StatisticsOverviewResponse,
    summary=f"{PLACEHOLDER_PREFIX}system_statistics_overview",
)
@require_permissions(permission=SqlbotPermission(role=["admin", "ws_admin"]))
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
    """
    管理员统计分析总览：
    - 基于当前工作空间（oid）的 chat / chat_record
    - 可按时间范围过滤
    """
    filters = _build_common_filters(current_user, start_time, end_time)

    # 概览指标
    success_cond = and_(ChatRecord.finish.is_(True), ChatRecord.error.is_(None))
    failed_cond = or_(ChatRecord.finish.is_(False), ChatRecord.error.is_not(None))

    overview_stmt = (
        select(
            func.count(ChatRecord.id),
            func.coalesce(func.sum(case((success_cond, 1), else_=0)), 0),
            func.coalesce(func.sum(case((failed_cond, 1), else_=0)), 0),
            func.count(func.distinct(ChatRecord.create_by)),
            func.count(func.distinct(ChatRecord.datasource)),
            func.count(func.distinct(ChatRecord.chat_id)),
            func.avg(
                func.extract(
                    "epoch", ChatRecord.finish_time - ChatRecord.create_time
                )
            ),
        )
        .join(Chat, ChatRecord.chat_id == Chat.id)
        .where(*filters)
    )

    (
        total_queries,
        success_queries,
        failed_queries,
        active_users,
        active_datasources,
        active_chats,
        avg_duration_seconds,
    ) = session.exec(overview_stmt).one()

    total_queries = int(total_queries or 0)
    success_queries = int(success_queries or 0)
    failed_queries = int(failed_queries or 0)
    active_users = int(active_users or 0)
    active_datasources = int(active_datasources or 0)
    active_chats = int(active_chats or 0)
    avg_duration_val: Optional[float] = (
        float(avg_duration_seconds) if avg_duration_seconds is not None else None
    )

    success_rate = float(success_queries) / float(total_queries) if total_queries else 0.0

    overview = OverviewMetrics(
        total_queries=total_queries,
        success_queries=success_queries,
        failed_queries=failed_queries,
        success_rate=success_rate,
        active_users=active_users,
        active_datasources=active_datasources,
        active_chats=active_chats,
        avg_duration_seconds=avg_duration_val,
    )

    # 按数据源聚合
    ds_stmt = (
        select(
            ChatRecord.datasource.label("datasource_id"),
            CoreDatasource.name.label("datasource_name"),
            func.count(ChatRecord.id).label("total_queries"),
            func.coalesce(
                func.sum(case((success_cond, 1), else_=0)), 0
            ).label("success_queries"),
            func.coalesce(
                func.sum(case((failed_cond, 1), else_=0)), 0
            ).label("failed_queries"),
            func.count(func.distinct(ChatRecord.create_by)).label("active_users"),
        )
        .join(Chat, ChatRecord.chat_id == Chat.id)
        .join(
            CoreDatasource,
            ChatRecord.datasource == CoreDatasource.id,
            isouter=True,
        )
        .where(*filters)
        .group_by(ChatRecord.datasource, CoreDatasource.name)
        .order_by(func.count(ChatRecord.id).desc())
    )

    ds_rows = session.exec(ds_stmt).all()
    by_datasource: List[DatasourceStats] = []
    for row in ds_rows:
        (
            datasource_id,
            datasource_name,
            ds_total,
            ds_success,
            ds_failed,
            ds_active_users,
        ) = row
        ds_total = int(ds_total or 0)
        ds_success = int(ds_success or 0)
        ds_failed = int(ds_failed or 0)
        ds_active_users = int(ds_active_users or 0)
        ds_success_rate = float(ds_success) / float(ds_total) if ds_total else 0.0
        by_datasource.append(
            DatasourceStats(
                datasource_id=datasource_id,
                datasource_name=datasource_name,
                total_queries=ds_total,
                success_queries=ds_success,
                failed_queries=ds_failed,
                success_rate=ds_success_rate,
                active_users=ds_active_users,
            )
        )

    # 按用户聚合
    user_stmt = (
        select(
            ChatRecord.create_by.label("user_id"),
            UserModel.name.label("user_name"),
            func.count(ChatRecord.id).label("total_queries"),
            func.coalesce(
                func.sum(case((success_cond, 1), else_=0)), 0
            ).label("success_queries"),
            func.coalesce(
                func.sum(case((failed_cond, 1), else_=0)), 0
            ).label("failed_queries"),
            func.count(func.distinct(ChatRecord.datasource)).label(
                "active_datasources"
            ),
        )
        .join(Chat, ChatRecord.chat_id == Chat.id)
        .join(UserModel, ChatRecord.create_by == UserModel.id, isouter=True)
        .where(*filters)
        .group_by(ChatRecord.create_by, UserModel.name)
        .order_by(func.count(ChatRecord.id).desc())
    )

    user_rows = session.exec(user_stmt).all()
    by_user: List[UserStats] = []
    for row in user_rows:
        (
            user_id,
            user_name,
            u_total,
            u_success,
            u_failed,
            u_active_ds,
        ) = row
        u_total = int(u_total or 0)
        u_success = int(u_success or 0)
        u_failed = int(u_failed or 0)
        u_active_ds = int(u_active_ds or 0)
        u_success_rate = float(u_success) / float(u_total) if u_total else 0.0
        by_user.append(
            UserStats(
                user_id=user_id,
                user_name=user_name,
                total_queries=u_total,
                success_queries=u_success,
                failed_queries=u_failed,
                success_rate=u_success_rate,
                active_datasources=u_active_ds,
            )
        )

    # 按天趋势
    day_expr = func.date_trunc("day", ChatRecord.create_time).label("date")
    trend_stmt = (
        select(
            day_expr,
            func.count(ChatRecord.id).label("total_queries"),
            func.coalesce(
                func.sum(case((success_cond, 1), else_=0)), 0
            ).label("success_queries"),
            func.coalesce(
                func.sum(case((failed_cond, 1), else_=0)), 0
            ).label("failed_queries"),
        )
        .join(Chat, ChatRecord.chat_id == Chat.id)
        .where(*filters)
        .group_by(day_expr)
        .order_by(day_expr.asc())
    )

    trend_rows = session.exec(trend_stmt).all()
    daily_trend: List[DailyTrendPoint] = [
        DailyTrendPoint(
            date=row.date,
            total_queries=int(row.total_queries or 0),
            success_queries=int(row.success_queries or 0),
            failed_queries=int(row.failed_queries or 0),
        )
        for row in trend_rows
    ]

    return StatisticsOverviewResponse(
        overview=overview,
        by_datasource=by_datasource,
        by_user=by_user,
        daily_trend=daily_trend,
    )


def _record_filters(
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    user_id: Optional[int],
    datasource_id: Optional[int],
    failed_only: bool,
):
    filters = [Chat.oid == current_user.oid]
    if start_time is not None:
        filters.append(ChatRecord.create_time >= start_time)
    if end_time is not None:
        filters.append(ChatRecord.create_time <= end_time)
    if user_id is not None:
        filters.append(ChatRecord.create_by == user_id)
    if datasource_id is not None:
        filters.append(ChatRecord.datasource == datasource_id)
    if failed_only:
        filters.append(or_(ChatRecord.finish.is_(False), ChatRecord.error.is_not(None)))
    return filters


@router.get(
    "/records",
    response_model=PaginatedResponse[RecordItem],
    summary=f"{PLACEHOLDER_PREFIX}system_statistics_records",
)
@require_permissions(permission=SqlbotPermission(role=["admin", "ws_admin"]))
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
    filters = _record_filters(
        current_user, start_time, end_time, user_id, datasource_id, failed_only
    )
    stmt = (
        select(
            ChatRecord.id,
            ChatRecord.chat_id,
            ChatRecord.create_time,
            ChatRecord.create_by,
            UserModel.name.label("user_name"),
            ChatRecord.datasource.label("datasource_id"),
            CoreDatasource.name.label("datasource_name"),
            ChatRecord.question,
            ChatRecord.finish,
            ChatRecord.error,
        )
        .join(Chat, ChatRecord.chat_id == Chat.id)
        .join(UserModel, ChatRecord.create_by == UserModel.id, isouter=True)
        .join(
            CoreDatasource,
            ChatRecord.datasource == CoreDatasource.id,
            isouter=True,
        )
        .where(*filters)
        .order_by(ChatRecord.create_time.desc())
    )
    pagination = PaginationParams(page=page, size=size)
    paginator = Paginator(session)
    page_result = await paginator.get_paginated_response(stmt, pagination)
    # Truncate question/error and map to RecordItem
    items = []
    for row in page_result.items:
        if isinstance(row, dict):
            q = row.get("question") or ""
            e = row.get("error") or ""
            items.append(
                RecordItem(
                    id=row.get("id"),
                    chat_id=row.get("chat_id"),
                    create_time=row.get("create_time"),
                    create_by=row.get("create_by"),
                    user_name=row.get("user_name"),
                    datasource_id=row.get("datasource_id"),
                    datasource_name=row.get("datasource_name"),
                    question=(q[:80] + "…") if len(q) > 80 else (q or None),
                    finish=bool(row.get("finish")),
                    error=(e[:200] + "…") if len(e) > 200 else (e or None),
                )
            )
        else:
            items.append(RecordItem.model_validate(row))
    return PaginatedResponse[RecordItem](
        items=items,
        total=page_result.total,
        page=page_result.page,
        size=page_result.size,
        total_pages=page_result.total_pages,
    )

