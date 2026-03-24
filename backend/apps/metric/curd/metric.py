import datetime
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from apps.metric.models.metric_model import CoreMetric, MetricComponent, MetricInfo, MetricComponentItem

logger = logging.getLogger(__name__)

METRIC_KINDS = frozenset({"atomic", "derived", "composite"})
MAX_METRICS_IN_PROMPT = 12
MAX_EXPAND_DEPTH = 6


def _normalize_ds_ids(raw: Optional[List[int]]) -> List[int]:
    out: List[int] = []
    for x in raw or []:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out


def _ds_match(m: CoreMetric, ds_id: Optional[int]) -> bool:
    """指标按数据源生效：无当前数据源上下文则不命中；数据源必须在指标绑定列表中。"""
    if ds_id is None:
        return False
    ids = _normalize_ds_ids(m.datasource_ids)
    if not ids:
        return False
    return ds_id in ids


def _ds_sets_overlap(a: List[int], b: List[int]) -> bool:
    return bool(set(_normalize_ds_ids(a)) & set(_normalize_ds_ids(b)))


def _metric_to_info(m: CoreMetric, session: Session) -> MetricInfo:
    comps: List[MetricComponentItem] = []
    if m.metric_kind == "composite":
        rows = session.execute(
            select(MetricComponent).where(MetricComponent.parent_metric_id == m.id).order_by(MetricComponent.id)
        ).scalars()
        for r in rows:
            comps.append(MetricComponentItem(slot_code=r.slot_code, child_metric_id=r.child_metric_id))
    return MetricInfo(
        id=m.id,
        create_time=m.create_time,
        enabled=m.enabled,
        code=m.code,
        name=m.name,
        description=m.description,
        aliases=list(m.aliases or []),
        terminology_root_id=m.terminology_root_id,
        metric_kind=m.metric_kind,
        specific_ds=m.specific_ds,
        datasource_ids=list(m.datasource_ids or []),
        measure_sql=m.measure_sql,
        base_metric_id=m.base_metric_id,
        modifiers=m.modifiers,
        expansion_hint=m.expansion_hint,
        expression=m.expression,
        components=comps,
    )


def page_metric(
    session: Session,
    current_page: int,
    page_size: int,
    oid: int,
    name: Optional[str] = None,
    metric_kind: Optional[str] = None,
    datasource_id: Optional[int] = None,
) -> tuple[int, int, int, int, List[MetricInfo]]:
    page_size = max(10, page_size)
    conds = [CoreMetric.oid == oid]
    if name and name.strip():
        kw = f"%{name.strip()}%"
        conds.append(or_(CoreMetric.name.ilike(kw), CoreMetric.code.ilike(kw)))
    if metric_kind and metric_kind in METRIC_KINDS:
        conds.append(CoreMetric.metric_kind == metric_kind)
    if datasource_id is not None:
        conds.append(CoreMetric.datasource_ids.contains([datasource_id]))
    filt = and_(*conds)
    total = session.execute(select(func.count()).select_from(CoreMetric).where(filt)).scalar() or 0
    total_pages = (total + page_size - 1) // page_size if total else 0
    current_page = max(1, min(current_page, total_pages)) if total_pages else 1
    stmt = (
        select(CoreMetric)
        .where(filt)
        .order_by(CoreMetric.create_time.desc())
        .offset((current_page - 1) * page_size)
        .limit(page_size)
    )
    rows = session.execute(stmt).scalars().all()
    return current_page, page_size, total, total_pages, [_metric_to_info(r, session) for r in rows]


def leads_to_metric(session: Session, from_id: int, target_id: int, stack: Optional[set] = None) -> bool:
    if from_id == target_id:
        return True
    if stack is None:
        stack = set()
    if from_id in stack:
        return False
    stack.add(from_id)
    m = session.get(CoreMetric, from_id)
    if not m:
        stack.remove(from_id)
        return False
    if m.metric_kind == "derived" and m.base_metric_id:
        if leads_to_metric(session, m.base_metric_id, target_id, stack):
            stack.remove(from_id)
            return True
    if m.metric_kind == "composite":
        for cid in session.execute(
            select(MetricComponent.child_metric_id).where(MetricComponent.parent_metric_id == from_id)
        ).scalars():
            if leads_to_metric(session, cid, target_id, stack):
                stack.remove(from_id)
                return True
    stack.remove(from_id)
    return False


def _validate_metric(info: MetricInfo, session: Session, oid: int, exclude_id: Optional[int] = None) -> None:
    if info.metric_kind not in METRIC_KINDS:
        raise ValueError("invalid metric_kind")
    ds_ids = _normalize_ds_ids(info.datasource_ids)
    if not ds_ids:
        raise ValueError("at least one datasource is required")
    info.datasource_ids = ds_ids
    info.specific_ds = True
    existing = session.execute(
        select(CoreMetric).where(CoreMetric.oid == oid, CoreMetric.code == info.code)
    ).scalar_one_or_none()
    if existing and (exclude_id is None or existing.id != exclude_id):
        raise ValueError("code already exists in workspace")
    if info.metric_kind == "atomic":
        if not (info.measure_sql and info.measure_sql.strip()):
            raise ValueError("atomic metric requires measure_sql")
    elif info.metric_kind == "derived":
        if not info.base_metric_id:
            raise ValueError("derived metric requires base_metric_id")
        base = session.get(CoreMetric, info.base_metric_id)
        if not base or base.oid != oid:
            raise ValueError("base_metric not found")
        if not _ds_sets_overlap(info.datasource_ids, base.datasource_ids or []):
            raise ValueError("base metric must share at least one datasource with this metric")
    elif info.metric_kind == "composite":
        if not (info.expression and info.expression.strip()):
            raise ValueError("composite metric requires expression")
        if not info.components:
            raise ValueError("composite metric requires components")
        slot_codes = [c.slot_code.strip() for c in info.components]
        if len(slot_codes) != len(set(slot_codes)):
            raise ValueError("duplicate slot_code in components")
        for c in info.components:
            if exclude_id and c.child_metric_id == exclude_id:
                raise ValueError("composite metric cannot reference itself as child")
            child = session.get(CoreMetric, c.child_metric_id)
            if not child or child.oid != oid:
                raise ValueError(f"child metric {c.child_metric_id} not found")
            if not _ds_sets_overlap(info.datasource_ids, child.datasource_ids or []):
                raise ValueError(
                    f"child metric {child.code} must share at least one datasource with this composite metric"
                )
        mid = exclude_id or 0
        for c in info.components:
            if mid and leads_to_metric(session, c.child_metric_id, mid):
                raise ValueError("metric dependency cycle detected")


def create_metric(session: Session, info: MetricInfo, oid: int) -> MetricInfo:
    _validate_metric(info, session, oid, None)
    now = datetime.datetime.now()
    row = CoreMetric(
        oid=oid,
        create_time=now,
        enabled=info.enabled,
        code=info.code.strip(),
        name=info.name.strip(),
        description=info.description,
        aliases=info.aliases or [],
        terminology_root_id=info.terminology_root_id,
        metric_kind=info.metric_kind,
        specific_ds=True,
        datasource_ids=info.datasource_ids,
        measure_sql=info.measure_sql,
        base_metric_id=info.base_metric_id,
        modifiers=info.modifiers,
        expansion_hint=info.expansion_hint,
        expression=info.expression,
    )
    session.add(row)
    session.flush()
    if info.metric_kind == "composite":
        for c in info.components:
            session.add(
                MetricComponent(
                    parent_metric_id=row.id,
                    child_metric_id=c.child_metric_id,
                    slot_code=c.slot_code.strip(),
                )
            )
    session.commit()
    session.refresh(row)
    return _metric_to_info(row, session)


def update_metric(session: Session, info: MetricInfo, oid: int) -> MetricInfo:
    if not info.id:
        raise ValueError("id required")
    row = session.get(CoreMetric, info.id)
    if not row or row.oid != oid:
        raise ValueError("metric not found")
    _validate_metric(info, session, oid, exclude_id=row.id)
    row.enabled = info.enabled
    row.code = info.code.strip()
    row.name = info.name.strip()
    row.description = info.description
    row.aliases = info.aliases or []
    row.terminology_root_id = info.terminology_root_id
    row.metric_kind = info.metric_kind
    row.specific_ds = True
    row.datasource_ids = info.datasource_ids
    row.measure_sql = info.measure_sql
    row.base_metric_id = info.base_metric_id
    row.modifiers = info.modifiers
    row.expansion_hint = info.expansion_hint
    row.expression = info.expression
    session.execute(delete(MetricComponent).where(MetricComponent.parent_metric_id == row.id))
    if info.metric_kind == "composite":
        for c in info.components:
            session.add(
                MetricComponent(
                    parent_metric_id=row.id,
                    child_metric_id=c.child_metric_id,
                    slot_code=c.slot_code.strip(),
                )
            )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _metric_to_info(row, session)


def delete_metric(session: Session, id_list: List[int], oid: int) -> None:
    for mid in id_list:
        row = session.get(CoreMetric, mid)
        if not row or row.oid != oid:
            continue
        used = session.execute(
            select(func.count())
            .select_from(MetricComponent)
            .where(MetricComponent.child_metric_id == mid)
        ).scalar()
        if used and used > 0:
            raise ValueError(f"metric {row.code} is referenced by composite metrics")
        used_base = session.execute(
            select(func.count()).select_from(CoreMetric).where(CoreMetric.base_metric_id == mid)
        ).scalar()
        if used_base and used_base > 0:
            raise ValueError(f"metric {row.code} is base of derived metrics")
        session.execute(delete(MetricComponent).where(MetricComponent.parent_metric_id == mid))
        session.delete(row)
    session.commit()


def list_metric_options(
    session: Session, oid: int, datasource_ids: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    rows = session.execute(
        select(
            CoreMetric.id,
            CoreMetric.code,
            CoreMetric.name,
            CoreMetric.metric_kind,
            CoreMetric.datasource_ids,
        )
        .where(CoreMetric.oid == oid)
        .order_by(CoreMetric.code)
    ).all()
    req = set(_normalize_ds_ids(datasource_ids))
    out: List[Dict[str, Any]] = []
    for r in rows:
        mids = _normalize_ds_ids(r[4])
        if req and not (set(mids) & req):
            continue
        if not req:
            continue
        out.append(
            {
                "id": r[0],
                "code": r[1],
                "name": r[2],
                "metric_kind": r[3],
                "datasource_ids": mids,
            }
        )
    return out


def enable_metric(session: Session, mid: int, enabled: bool, oid: int) -> None:
    row = session.get(CoreMetric, mid)
    if not row or row.oid != oid:
        raise ValueError("metric not found")
    row.enabled = enabled
    session.add(row)
    session.commit()


def _match_question(m: CoreMetric, question: str) -> bool:
    if not question:
        return False
    q = question.lower()
    if m.code and m.code.lower() in q:
        return True
    if m.name and m.name.lower() in q:
        return True
    for a in m.aliases or []:
        if a and str(a).lower() in q:
            return True
    return False


def _collect_closure(session: Session, seeds: List[CoreMetric], max_total: int = MAX_METRICS_IN_PROMPT) -> List[CoreMetric]:
    seen: dict[int, CoreMetric] = {}
    stack = list(seeds)
    while stack and len(seen) < max_total:
        m = stack.pop()
        if m.id in seen:
            continue
        seen[m.id] = m
        if m.metric_kind == "derived" and m.base_metric_id:
            b = session.get(CoreMetric, m.base_metric_id)
            if b and b.enabled:
                stack.append(b)
        if m.metric_kind == "composite":
            for cid in session.execute(
                select(MetricComponent.child_metric_id).where(MetricComponent.parent_metric_id == m.id)
            ).scalars():
                c = session.get(CoreMetric, cid)
                if c and c.enabled:
                    stack.append(c)
    return list(seen.values())


def expand_measure_sql(
    session: Session,
    mid: int,
    cache: dict[int, str],
    visiting: set,
    depth: int,
) -> str:
    if depth > MAX_EXPAND_DEPTH:
        return "/* expand depth limit */"
    if mid in cache:
        return cache[mid]
    if mid in visiting:
        return "/* cycle */"
    visiting.add(mid)
    m = session.get(CoreMetric, mid)
    if not m or not m.enabled:
        visiting.remove(mid)
        return ""
    if m.metric_kind == "atomic":
        s = (m.measure_sql or "").strip()
        cache[mid] = s
        visiting.remove(mid)
        return s
    if m.metric_kind == "derived":
        base_sql = ""
        if m.base_metric_id:
            base_sql = expand_measure_sql(session, m.base_metric_id, cache, visiting, depth + 1)
        mod = json.dumps(m.modifiers or {}, ensure_ascii=False)
        hint = (m.expansion_hint or "").strip()
        s = f"({base_sql}) /* derived:{escape(m.code)} modifiers:{escape(mod)} */"
        if hint:
            s += f" /* hint:{escape(hint)} */"
        cache[mid] = s
        visiting.remove(mid)
        return s
    if m.metric_kind == "composite":
        slots: dict[str, str] = {}
        for comp in session.execute(
            select(MetricComponent)
            .where(MetricComponent.parent_metric_id == m.id)
            .order_by(MetricComponent.id)
        ).scalars():
            slots[comp.slot_code] = expand_measure_sql(
                session, comp.child_metric_id, cache, visiting, depth + 1
            )
        expr = m.expression or ""
        out = expr
        for code, frag in slots.items():
            out = out.replace("{{" + code + "}}", f"({frag})")
        cache[mid] = out
        visiting.remove(mid)
        return out
    visiting.remove(mid)
    return ""


def _metric_xml_block(m: CoreMetric, session: Session) -> str:
    expanded = ""
    if m.metric_kind in ("derived", "composite"):
        cache: dict[str, str] = {}
        expanded = expand_measure_sql(session, m.id, cache, set(), 0)
    lines = [
        f'  <metric kind="{escape(m.metric_kind)}" code="{escape(m.code)}">',
        f"    <name>{escape(m.name)}</name>",
    ]
    if m.description:
        lines.append(f"    <description>{escape(m.description)}</description>")
    if m.aliases:
        lines.append(f"    <aliases>{escape(', '.join(m.aliases))}</aliases>")
    if m.metric_kind == "atomic" and m.measure_sql:
        lines.append(f"    <measure_sql>{escape(m.measure_sql)}</measure_sql>")
    if m.metric_kind == "atomic" and m.expansion_hint:
        lines.append(f"    <time_grain_hint>{escape(m.expansion_hint)}</time_grain_hint>")
    if m.metric_kind == "derived":
        if m.base_metric_id:
            base = session.get(CoreMetric, m.base_metric_id)
            bc = escape(base.code) if base else ""
            lines.append(f'    <base_metric code="{bc}" />')
        if m.modifiers:
            lines.append(f"    <modifiers>{escape(json.dumps(m.modifiers, ensure_ascii=False))}</modifiers>")
        if m.expansion_hint:
            lines.append(f"    <expansion_hint>{escape(m.expansion_hint)}</expansion_hint>")
    if m.metric_kind == "composite" and m.expression:
        lines.append(f"    <expression>{escape(m.expression)}</expression>")
        for comp in session.execute(
            select(MetricComponent)
            .where(MetricComponent.parent_metric_id == m.id)
            .order_by(MetricComponent.id)
        ).scalars():
            ch = session.get(CoreMetric, comp.child_metric_id)
            cc = escape(ch.code) if ch else ""
            lines.append(f'    <slot code="{escape(comp.slot_code)}" child_code="{cc}" />')
    if expanded:
        lines.append(f"    <expanded_sql_hint>{escape(expanded)}</expanded_sql_hint>")
    instr = "当用户问题涉及该指标（名称、别名或编码）时，必须在 SQL 中采用上述 measure_sql 或 expanded_sql_hint 所表达的口径，不得自造公式。"
    if m.metric_kind == "atomic" and m.expansion_hint:
        instr += " 若存在 time_grain_hint，生成 SQL 时必须同时满足其中的时间粒度与分组/筛选要求（例如按日统计则需按日期字段分组或限定在单日）。"
    lines.append(f"    <instruction>{escape(instr)}</instruction>")
    lines.append("  </metric>")
    return "\n".join(lines)


def get_metric_template(
    session: Session,
    question: str,
    oid: Optional[int] = 1,
    datasource: Optional[int] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    if not oid:
        oid = 1
    stmt = select(CoreMetric).where(
        and_(CoreMetric.oid == oid, CoreMetric.enabled == True)
    )
    rows = session.execute(stmt).scalars().all()
    matched = [m for m in rows if _ds_match(m, datasource) and _match_question(m, question)]
    matched = sorted(matched, key=lambda x: x.create_time or datetime.datetime.min, reverse=True)[
        :MAX_METRICS_IN_PROMPT
    ]
    if not matched:
        return "", []
    closure = _collect_closure(session, matched)
    kind_order = {"atomic": 0, "derived": 1, "composite": 2}
    closure.sort(key=lambda x: (kind_order.get(x.metric_kind, 9), x.code or ""))
    blocks = [_metric_xml_block(m, session) for m in closure]
    inner = "\n".join(blocks)
    xml = (
        "<metrics>\n"
        "  <metrics_instruction>以下为工作区配置的业务指标（原子/派生/复合）。"
        "涉及下列指标时，必须严格使用给出的 SQL 口径。</metrics_instruction>\n"
        f"{inner}\n"
        "</metrics>"
    )
    summary = [{"id": m.id, "code": m.code, "name": m.name, "kind": m.metric_kind} for m in closure]
    return xml, summary

