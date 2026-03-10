"""Statistics aggregation: overview, trend, top, failure analysis, user detailed, records."""

import json
from datetime import datetime
from typing import Any, List, Optional, Tuple

from sqlalchemy import Integer, Text, and_, case, cast, func, or_, select
from sqlmodel import Session

from apps.chat.models.chat_model import Chat, ChatRecord, ChatLog, OperationEnum
from apps.datasource.models.datasource import CoreDatasource
from apps.system.models.user import UserModel
from apps.system.schemas.statistics import (
    DatasourceDetailedItem,
    OverviewMetrics,
    DailyTrendPoint,
    TrendPoint,
    DatasourceTopItem,
    FailureReasonItem,
    FailureByDatasourceItem,
    FailureByHourItem,
    UserDetailedItem,
    RecordItem,
)
from common.core.deps import CurrentUser


def _oid(current_user: CurrentUser) -> int:
    return current_user.oid if current_user.oid is not None else 1


def build_common_filters(
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
):
    filters = [Chat.oid == _oid(current_user)]
    if start_time is not None:
        filters.append(ChatRecord.create_time >= start_time)
    if end_time is not None:
        filters.append(ChatRecord.create_time <= end_time)
    return filters


success_cond = and_(ChatRecord.finish.is_(True), ChatRecord.error.is_(None))
failed_cond = or_(ChatRecord.finish.is_(False), ChatRecord.error.is_not(None))


def parse_error_type(error: Optional[str]) -> str:
    if not error or not error.strip():
        return "unknown"
    s = error.strip()
    if s.startswith("{"):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict) and "type" in obj:
                return str(obj["type"]) or "unknown"
        except Exception:
            pass
    return "unknown"


def aggregate_tokens_for_record_ids(session: Session, record_ids: List[int]) -> dict:
    if not record_ids:
        return {}
    log_stmt = select(ChatLog.pid, ChatLog.token_usage).where(
        and_(
            ChatLog.pid.in_(record_ids),
            ChatLog.local_operation.is_(False),
            ChatLog.operate != OperationEnum.GENERATE_RECOMMENDED_QUESTIONS,
            ChatLog.token_usage.is_not(None),
        )
    )
    rows = session.exec(log_stmt).all()
    out = {}
    for pid, token_usage in rows:
        if not pid or token_usage is None:
            continue
        add = 0
        if isinstance(token_usage, dict) and token_usage and "total_tokens" in token_usage:
            v = token_usage["total_tokens"]
            if isinstance(v, (int, float)):
                add = int(v)
        elif isinstance(token_usage, (int, float)):
            add = int(token_usage)
        if add > 0:
            out[pid] = out.get(pid, 0) + add
    return out


def _percentile(sorted_values: List[float], p: float) -> Optional[float]:
    if not sorted_values:
        return None
    k = (len(sorted_values) - 1) * p / 100.0
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_values) else f
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f]) if c > f else sorted_values[f]


def _scalar(row: Any) -> int:
    """Take first column from Row or return scalar as int."""
    if row is None:
        return 0
    if hasattr(row, "__getitem__") and not isinstance(row, (str, bytes)):
        return int(row[0] or 0)
    return int(row)

def get_total_users_and_datasources(session: Session, oid: int) -> Tuple[int, int]:
    r1 = session.exec(select(func.count(UserModel.id)).where(UserModel.oid == oid)).one()
    r2 = session.exec(select(func.count(CoreDatasource.id)).where(CoreDatasource.oid == oid)).one()
    return _scalar(r1), _scalar(r2)


def _build_filtered_records_cte(
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
):
    filters = build_common_filters(current_user, start_time, end_time)
    return (
        select(
            ChatRecord.id.label("record_id"),
            ChatRecord.chat_id.label("chat_id"),
            ChatRecord.create_by.label("user_id"),
            ChatRecord.datasource.label("datasource_id"),
            ChatRecord.create_time.label("create_time"),
            ChatRecord.finish_time.label("finish_time"),
            ChatRecord.finish.label("finish"),
            ChatRecord.error.label("error"),
        )
        .join(Chat, ChatRecord.chat_id == Chat.id)
        .where(*filters)
        .cte("filtered_records")
    )


def _token_value_expr():
    return case(
        (
            func.jsonb_typeof(ChatLog.token_usage) == "object",
            cast(func.coalesce(ChatLog.token_usage.op("->>")("total_tokens"), "0"), Integer),
        ),
        (
            func.jsonb_typeof(ChatLog.token_usage) == "number",
            cast(cast(ChatLog.token_usage, Text), Integer),
        ),
        else_=0,
    )


def _build_tokens_by_record_cte(records_cte):
    token_value = _token_value_expr()
    return (
        select(
            ChatLog.pid.label("record_id"),
            func.coalesce(func.sum(token_value), 0).label("total_tokens"),
        )
        .select_from(ChatLog)
        .join(records_cte, ChatLog.pid == records_cte.c.record_id)
        .where(
            ChatLog.local_operation.is_(False),
            ChatLog.operate != OperationEnum.GENERATE_RECOMMENDED_QUESTIONS,
            ChatLog.token_usage.is_not(None),
        )
        .group_by(ChatLog.pid)
        .cte("tokens_by_record")
    )


def _duration_expr(records_cte):
    return func.extract("epoch", records_cte.c.finish_time - records_cte.c.create_time)


def _build_order_expr(subquery, order_by: str, default_field: str, desc: bool, tie_breaker: str):
    # 不能用 or 判断：SQLAlchemy 列对象在布尔上下文中会抛 TypeError
    column = getattr(subquery.c, order_by, None)
    if column is None:
        column = getattr(subquery.c, default_field)
    tie_breaker_column = getattr(subquery.c, tie_breaker)
    return [column.desc() if desc else column.asc(), tie_breaker_column.asc()]


def _row_mapping(row: Any):
    return row._mapping if hasattr(row, "_mapping") else row


def get_overview(
    session: Session,
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
) -> Tuple[OverviewMetrics, List[DailyTrendPoint]]:
    oid = _oid(current_user)
    records_cte = _build_filtered_records_cte(current_user, start_time, end_time)
    tokens_cte = _build_tokens_by_record_cte(records_cte)
    duration_expr = _duration_expr(records_cte)

    # Base counts and avg duration
    stmt = (
        select(
            func.count(records_cte.c.record_id),
            func.coalesce(
                func.sum(
                    case(
                        (and_(records_cte.c.finish.is_(True), records_cte.c.error.is_(None)), 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (or_(records_cte.c.finish.is_(False), records_cte.c.error.is_not(None)), 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.count(func.distinct(records_cte.c.user_id)),
            func.count(func.distinct(records_cte.c.datasource_id)),
            func.count(func.distinct(records_cte.c.chat_id)),
            func.avg(duration_expr),
        )
        .select_from(records_cte)
    )
    row = session.exec(stmt).one()
    (
        total_queries,
        success_queries,
        failed_queries,
        active_users,
        active_datasources,
        active_chats,
        avg_duration_seconds,
    ) = row
    total_queries = int(total_queries or 0)
    success_queries = int(success_queries or 0)
    failed_queries = int(failed_queries or 0)
    active_users = int(active_users or 0)
    active_datasources = int(active_datasources or 0)
    active_chats = int(active_chats or 0)
    success_rate = float(success_queries) / float(total_queries) if total_queries else 0.0
    avg_dur = float(avg_duration_seconds) if avg_duration_seconds is not None else None

    total_users, total_datasources = get_total_users_and_datasources(session, oid)

    total_tokens = _scalar(
        session.exec(select(func.coalesce(func.sum(tokens_cte.c.total_tokens), 0))).one()
    )

    # Duration percentiles: fetch durations for finished records
    dur_stmt = (
        select(duration_expr.label("d"))
        .select_from(records_cte)
        .where(records_cte.c.finish_time.is_not(None), records_cte.c.create_time.is_not(None))
    )
    dur_rows = session.exec(dur_stmt).all()
    durations = [float(r[0]) for r in dur_rows if r[0] is not None]
    durations.sort()
    p50 = _percentile(durations, 50)
    p90 = _percentile(durations, 90)
    p99 = _percentile(durations, 99)

    overview = OverviewMetrics(
        total_queries=total_queries,
        success_queries=success_queries,
        failed_queries=failed_queries,
        success_rate=success_rate,
        active_users=active_users,
        active_datasources=active_datasources,
        active_chats=active_chats,
        avg_duration_seconds=avg_dur,
        total_users=total_users,
        total_datasources=total_datasources,
        total_tokens=total_tokens,
        duration_p50_seconds=p50,
        duration_p90_seconds=p90,
        duration_p99_seconds=p99,
    )

    # Daily trend with avg_duration, total_tokens, success_rate
    day_expr = func.date_trunc("day", records_cte.c.create_time).label("date")
    trend_stmt = (
        select(
            day_expr,
            func.count(records_cte.c.record_id).label("total_queries"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(records_cte.c.finish.is_(True), records_cte.c.error.is_(None)), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("success_queries"),
            func.coalesce(
                func.sum(
                    case(
                        (or_(records_cte.c.finish.is_(False), records_cte.c.error.is_not(None)), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("failed_queries"),
            func.avg(duration_expr).label("avg_duration"),
            func.coalesce(func.sum(func.coalesce(tokens_cte.c.total_tokens, 0)), 0).label("total_tokens"),
        )
        .select_from(records_cte)
        .join(tokens_cte, tokens_cte.c.record_id == records_cte.c.record_id, isouter=True)
        .group_by(day_expr)
        .order_by(day_expr.asc())
    )
    trend_rows = session.exec(trend_stmt).all()
    daily_trend = []
    for r in trend_rows:
        date_val, t, s, f, avg_d, total_tokens_day = r
        t, s, f = int(t or 0), int(s or 0), int(f or 0)
        sr = float(s) / float(t) if t else 0.0
        daily_trend.append(
            DailyTrendPoint(
                date=date_val,
                total_queries=t,
                success_queries=s,
                failed_queries=f,
                avg_duration_seconds=float(avg_d) if avg_d is not None else None,
                total_tokens=int(total_tokens_day or 0),
                success_rate=sr,
            )
        )

    return overview, daily_trend


def get_trend(
    session: Session,
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
) -> List[TrendPoint]:
    _, daily_trend = get_overview(session, current_user, start_time, end_time)
    return [
        TrendPoint(
            date=p.date,
            total_queries=p.total_queries,
            success_queries=p.success_queries,
            failed_queries=p.failed_queries,
            avg_duration_seconds=p.avg_duration_seconds,
            total_tokens=p.total_tokens,
            success_rate=p.success_rate,
        )
        for p in daily_trend
    ]


def get_datasource_top(
    session: Session,
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    sort_by: str = "total_queries",
    limit: int = 10,
) -> List[DatasourceTopItem]:
    items, _ = get_datasource_detailed(
        session,
        current_user,
        start_time,
        end_time,
        page=1,
        size=limit,
        keyword=None,
        order_by=sort_by,
        desc=True,
    )
    top_items = []
    for item in items:
        if sort_by == "failed_queries":
            value = item.failed_queries
        elif sort_by == "avg_duration_seconds":
            value = int(item.avg_duration_seconds or 0)
        elif sort_by == "total_tokens":
            value = item.total_tokens
        else:
            value = item.total_queries
        top_items.append(
            DatasourceTopItem(
                datasource_id=item.datasource_id,
                datasource_name=item.datasource_name,
                value=value,
                sort_key=sort_by,
            )
        )
    return top_items


def get_failure_analysis(
    session: Session,
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
) -> Tuple[List[FailureReasonItem], List[FailureByDatasourceItem], List[FailureByHourItem]]:
    filters = build_common_filters(current_user, start_time, end_time)
    failed_filters = filters + [failed_cond]

    # By reason: group by parsed error_type
    stmt = (
        select(ChatRecord.id, ChatRecord.error)
        .join(Chat, ChatRecord.chat_id == Chat.id)
        .where(*failed_filters)
    )
    rows = session.exec(stmt).all()
    reason_counts: dict = {}
    reason_sample: dict = {}
    for rid, err in rows:
        et = parse_error_type(err)
        reason_counts[et] = reason_counts.get(et, 0) + 1
        if et not in reason_sample and err:
            reason_sample[et] = (err[:200] + "…") if len(err or "") > 200 else (err or "")

    by_reason = [
        FailureReasonItem(error_type=k, count=v, sample_message=reason_sample.get(k))
        for k, v in sorted(reason_counts.items(), key=lambda x: -x[1])
    ]

    # By datasource
    ds_fail_stmt = (
        select(
            ChatRecord.datasource.label("datasource_id"),
            CoreDatasource.name.label("datasource_name"),
            func.count(ChatRecord.id).label("failed_count"),
        )
        .join(Chat, ChatRecord.chat_id == Chat.id)
        .join(CoreDatasource, ChatRecord.datasource == CoreDatasource.id, isouter=True)
        .where(*failed_filters)
        .group_by(ChatRecord.datasource, CoreDatasource.name)
        .order_by(func.count(ChatRecord.id).desc())
    )
    ds_fail_rows = session.exec(ds_fail_stmt).all()
    by_datasource = [
        FailureByDatasourceItem(
            datasource_id=r[0],
            datasource_name=r[1],
            failed_count=int(r[2] or 0),
        )
        for r in ds_fail_rows
    ]

    # By hour
    hour_expr = func.extract("hour", ChatRecord.create_time).label("hour")
    hour_stmt = (
        select(hour_expr, func.count(ChatRecord.id).label("failed_count"))
        .join(Chat, ChatRecord.chat_id == Chat.id)
        .where(*failed_filters)
        .group_by(hour_expr)
        .order_by(hour_expr.asc())
    )
    hour_rows = session.exec(hour_stmt).all()
    by_hour = [FailureByHourItem(hour=int(r[0] or 0), failed_count=int(r[1] or 0)) for r in hour_rows]

    return by_reason, by_datasource, by_hour


def get_user_detailed(
    session: Session,
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    page: int = 1,
    size: int = 20,
    keyword: Optional[str] = None,
    order_by: str = "total_queries",
    desc: bool = True,
) -> Tuple[List[UserDetailedItem], int]:
    records_cte = _build_filtered_records_cte(current_user, start_time, end_time)
    tokens_cte = _build_tokens_by_record_cte(records_cte)
    duration_expr = _duration_expr(records_cte)

    aggregated_stmt = (
        select(
            records_cte.c.user_id.label("user_id"),
            UserModel.name.label("user_name"),
            func.count(records_cte.c.record_id).label("total_queries"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(records_cte.c.finish.is_(True), records_cte.c.error.is_(None)), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("success_queries"),
            func.coalesce(
                func.sum(
                    case(
                        (or_(records_cte.c.finish.is_(False), records_cte.c.error.is_not(None)), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("failed_queries"),
            func.count(func.distinct(records_cte.c.datasource_id)).label("active_datasources"),
            func.avg(duration_expr).label("avg_duration_seconds"),
            func.coalesce(func.sum(func.coalesce(tokens_cte.c.total_tokens, 0)), 0).label("total_tokens"),
            case(
                (func.count(records_cte.c.record_id) > 0,
                 func.coalesce(
                     func.sum(
                         case(
                             (and_(records_cte.c.finish.is_(True), records_cte.c.error.is_(None)), 1),
                             else_=0,
                         )
                     ),
                     0,
                 ) * 1.0 / func.count(records_cte.c.record_id)),
                else_=0.0,
            ).label("success_rate"),
        )
        .select_from(records_cte)
        .join(UserModel, records_cte.c.user_id == UserModel.id, isouter=True)
        .join(tokens_cte, tokens_cte.c.record_id == records_cte.c.record_id, isouter=True)
    )
    if keyword:
        aggregated_stmt = aggregated_stmt.where(UserModel.name.ilike(f"%{keyword.strip()}%"))
    aggregated = aggregated_stmt.group_by(records_cte.c.user_id, UserModel.name).subquery()

    total = _scalar(session.exec(select(func.count()).select_from(aggregated)).one())
    order_expr = _build_order_expr(aggregated, order_by, "total_queries", desc, "user_name")
    rows = session.exec(
        select(aggregated)
        .order_by(*order_expr)
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    items = []
    for row in rows:
        mapping = _row_mapping(row)
        total_queries = int(mapping["total_queries"] or 0)
        success_queries = int(mapping["success_queries"] or 0)
        items.append(
            UserDetailedItem(
                user_id=mapping["user_id"],
                user_name=mapping["user_name"],
                total_queries=total_queries,
                success_queries=success_queries,
                failed_queries=int(mapping["failed_queries"] or 0),
                success_rate=float(success_queries) / float(total_queries) if total_queries else 0.0,
                active_datasources=int(mapping["active_datasources"] or 0),
                avg_duration_seconds=float(mapping["avg_duration_seconds"]) if mapping["avg_duration_seconds"] is not None else None,
                total_tokens=int(mapping["total_tokens"] or 0),
            )
        )
    return items, total


def get_datasource_detailed(
    session: Session,
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    page: int = 1,
    size: int = 20,
    keyword: Optional[str] = None,
    order_by: str = "total_queries",
    desc: bool = True,
) -> Tuple[List[DatasourceDetailedItem], int]:
    records_cte = _build_filtered_records_cte(current_user, start_time, end_time)
    tokens_cte = _build_tokens_by_record_cte(records_cte)
    duration_expr = _duration_expr(records_cte)

    aggregated_stmt = (
        select(
            records_cte.c.datasource_id.label("datasource_id"),
            CoreDatasource.name.label("datasource_name"),
            func.count(records_cte.c.record_id).label("total_queries"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(records_cte.c.finish.is_(True), records_cte.c.error.is_(None)), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("success_queries"),
            func.coalesce(
                func.sum(
                    case(
                        (or_(records_cte.c.finish.is_(False), records_cte.c.error.is_not(None)), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("failed_queries"),
            func.count(func.distinct(records_cte.c.user_id)).label("active_users"),
            func.avg(duration_expr).label("avg_duration_seconds"),
            func.coalesce(func.sum(func.coalesce(tokens_cte.c.total_tokens, 0)), 0).label("total_tokens"),
            case(
                (func.count(records_cte.c.record_id) > 0,
                 func.coalesce(
                     func.sum(
                         case(
                             (and_(records_cte.c.finish.is_(True), records_cte.c.error.is_(None)), 1),
                             else_=0,
                         )
                     ),
                     0,
                 ) * 1.0 / func.count(records_cte.c.record_id)),
                else_=0.0,
            ).label("success_rate"),
        )
        .select_from(records_cte)
        .join(CoreDatasource, records_cte.c.datasource_id == CoreDatasource.id, isouter=True)
        .join(tokens_cte, tokens_cte.c.record_id == records_cte.c.record_id, isouter=True)
    )
    if keyword:
        aggregated_stmt = aggregated_stmt.where(CoreDatasource.name.ilike(f"%{keyword.strip()}%"))
    aggregated = aggregated_stmt.group_by(records_cte.c.datasource_id, CoreDatasource.name).subquery()

    total = _scalar(session.exec(select(func.count()).select_from(aggregated)).one())
    order_expr = _build_order_expr(aggregated, order_by, "total_queries", desc, "datasource_name")
    rows = session.exec(
        select(aggregated)
        .order_by(*order_expr)
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    items = []
    for row in rows:
        mapping = _row_mapping(row)
        total_queries = int(mapping["total_queries"] or 0)
        success_queries = int(mapping["success_queries"] or 0)
        items.append(
            DatasourceDetailedItem(
                datasource_id=mapping["datasource_id"],
                datasource_name=mapping["datasource_name"],
                total_queries=total_queries,
                success_queries=success_queries,
                failed_queries=int(mapping["failed_queries"] or 0),
                success_rate=float(success_queries) / float(total_queries) if total_queries else 0.0,
                active_users=int(mapping["active_users"] or 0),
                avg_duration_seconds=float(mapping["avg_duration_seconds"]) if mapping["avg_duration_seconds"] is not None else None,
                total_tokens=int(mapping["total_tokens"] or 0),
            )
        )
    return items, total


def get_records(
    session: Session,
    current_user: CurrentUser,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    user_id: Optional[int],
    datasource_id: Optional[int],
    failed_only: bool,
    page: int,
    size: int,
) -> Tuple[List[RecordItem], int]:
    filters = build_common_filters(current_user, start_time, end_time)
    if user_id is not None:
        filters.append(ChatRecord.create_by == user_id)
    if datasource_id is not None:
        filters.append(ChatRecord.datasource == datasource_id)
    if failed_only:
        filters.append(failed_cond)

    base = (
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
            ChatRecord.finish_time,
        )
        .join(Chat, ChatRecord.chat_id == Chat.id)
        .join(UserModel, ChatRecord.create_by == UserModel.id, isouter=True)
        .join(CoreDatasource, ChatRecord.datasource == CoreDatasource.id, isouter=True)
        .where(*filters)
        .order_by(ChatRecord.create_time.desc())
    )
    count_stmt = select(func.count(ChatRecord.id)).select_from(ChatRecord).join(Chat, ChatRecord.chat_id == Chat.id).where(*filters)
    total = _scalar(session.exec(count_stmt).one())
    page_rows = list(
        session.exec(base.offset((page - 1) * size).limit(size)).all()
    )
    record_ids = [r[0] for r in page_rows]
    token_map = aggregate_tokens_for_record_ids(session, record_ids)

    items = []
    for r in page_rows:
        rid, chat_id, create_time, create_by, user_name, ds_id, ds_name, question, finish, error, finish_time = r
        duration_seconds = None
        if create_time and finish_time:
            try:
                duration_seconds = (finish_time - create_time).total_seconds()
            except Exception:
                pass
        q = question or ""
        e = error or ""
        items.append(
            RecordItem(
                id=rid,
                chat_id=chat_id,
                create_time=create_time,
                create_by=create_by,
                user_name=user_name,
                datasource_id=ds_id,
                datasource_name=ds_name,
                question=(q[:80] + "…") if len(q) > 80 else (q or None),
                finish=bool(finish),
                error=(e[:200] + "…") if len(e) > 200 else (e or None),
                error_type=parse_error_type(error),
                duration_seconds=duration_seconds,
                total_tokens=token_map.get(rid),
            )
        )
    return items, total
