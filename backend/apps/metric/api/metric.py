import re
from typing import Any, Optional

import orjson
from fastapi import APIRouter, HTTPException, Query
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from apps.ai_model.model_factory import create_llm
from apps.datasource.crud.table import get_tables_by_ds_id
from apps.datasource.models.datasource import CoreDatasource, CoreField
from apps.metric.curd import metric as metric_crud
from apps.metric.models.metric_model import CoreMetric, MetricInfo
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.deps import SessionDep, CurrentUser, Trans

router = APIRouter(tags=["Metric"], prefix="/system/metric")


class MetricSuggestBody(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    datasource_id: Optional[int] = Field(default=None, description="可选，传入则把该库已同步的表名提供给模型参考")


class MetricCandidate(BaseModel):
    id: int
    code: str
    name: str
    metric_kind: str


class MetricAdvancedSuggestBody(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    datasource_id: Optional[int] = Field(default=None, description="可选，传入则按数据源过滤候选指标")
    metric_kind: str = Field(..., description="atomic / derived / composite")


def _ai_message_text(resp: Any) -> str:
    c = getattr(resp, "content", resp)
    if isinstance(c, list):
        parts = []
        for x in c:
            if isinstance(x, dict):
                parts.append(str(x.get("text", x.get("content", ""))))
            else:
                parts.append(str(x))
        return "".join(parts)
    return str(c or "")


_COUNT_TABLE_DOT_ID = re.compile(
    r"COUNT\s*\(\s*[`\"]?(\w+)[`]?\.[`\"]?id[`\"]?\s*\)",
    re.IGNORECASE,
)


def _demote_count_table_id_to_star(measure_sql: str, description: str) -> str:
    """口语「次数/条数」类常见误写 COUNT(foo.id) → COUNT(*)。"""
    if not measure_sql or not description:
        return measure_sql
    if not any(
        k in description
        for k in (
            "次数",
            "条数",
            "执行",
            "笔数",
            "场次",
            "多少",
            "总共",
            "频次",
            "how many",
            "number of",
            "count of",
            "executions",
            "runs",
            "times",
        )
    ):
        return measure_sql
    return _COUNT_TABLE_DOT_ID.sub("COUNT(*)", measure_sql)


def _infer_time_grain_hint(description: str) -> Optional[str]:
    """用户口语里的「每日/按日」等无法写进 measure_sql，落到 expansion_hint / time_grain_hint 注入。"""
    s = description.strip()
    if not s:
        return None
    sl = s.lower()
    if any(
        k in s
        for k in (
            "每日",
            "按日",
            "每天",
            "日粒度",
            "单日",
            "逐日",
            "按天",
            "天粒度",
        )
    ):
        return (
            "按自然日统计：与问题中的日期范围配合时，SQL 需按日历日分组或筛选（选用表中合适的日期/时间字段），"
            "使结果体现「每日」粒度。measure_sql 仅为 SELECT 列表中的聚合表达式，本身不含 GROUP BY。"
        )
    if any(k in sl for k in ("daily", "per day", "by day", "day over day")):
        return (
            "Aggregate or filter by calendar day using an appropriate date/datetime column; "
            "measure_sql is only the SELECT-list aggregate expression (no GROUP BY inside it)."
        )
    return None


def _parse_suggest_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    data = orjson.loads(text)
    if not isinstance(data, dict):
        raise ValueError("not an object")
    return data


def _advanced_candidate_lines(cands: list[CoreMetric], kind_filter: Optional[str] = None) -> str:
    arr = []
    for m in cands:
        if kind_filter and m.metric_kind != kind_filter:
            continue
        arr.append(f"- code={m.code}, name={m.name}, kind={m.metric_kind}")
    return "\n".join(arr[:120])


_SUGGEST_DERIVED_SYSTEM = """你是 SQLBot 指标配置助手（派生指标模式）。
请只输出一个 JSON 对象，不要其它文字。键含义：
- code: 英文蛇形命名，小写字母数字下划线，最长 64
- name: 指标名称
- aliases: 字符串数组（0~5）
- description: 一行说明（可选）
- base_metric_code: 必填，必须从「候选基础指标」列表里选择一个 code
- modifiers: JSON 对象（可选），例如 {"time_grain":"day"} 或 {"filters":[...]}
- expansion_hint: 字符串或 null，用于补充时间粒度、分组筛选口径

规则：
1) base_metric_code 只能从候选列表里选，不可臆造。
2) 用户说“每日/按天”等时，在 modifiers 或 expansion_hint 中体现时间粒度。
3) 不要输出 measure_sql / expression / components。"""

_SUGGEST_COMPOSITE_SYSTEM = """你是 SQLBot 指标配置助手（复合指标模式）。
请只输出一个 JSON 对象，不要其它文字。键含义：
- code: 英文蛇形命名，小写字母数字下划线，最长 64
- name: 指标名称
- aliases: 字符串数组（0~5）
- description: 一行说明（可选）
- expression: 复合表达式，使用 {{M1}}/{{M2}}... 占位符
- components: 数组，每项为 {"slot_code":"M1","child_metric_code":"xxx"}；child_metric_code 必须来自候选列表

规则：
1) child_metric_code 只能从候选列表里选，不可臆造。
2) expression 中必须只引用 components 里声明过的 slot_code。
3) 不要输出 measure_sql / base_metric_code / modifiers。"""


_SUGGEST_SYSTEM = """你是 SQLBot 指标配置助手。用户多为业务人员，用自然语言描述「想统计什么」。
请只输出一个 JSON 对象，不要其它文字。键含义：
- code: 英文蛇形命名，小写字母数字下划线，最长 64
- name: 简短中文或英文显示名
- measure_sql: 仅 SQL「表达式片段」，可放在 SELECT 列表里，不要整句 SELECT ... FROM，不要分号
- aliases: 字符串数组，0～5 个用户口头会问的说法
- description: 一行说明（可选）
- used_table: 字符串或 null。与 measure_sql 主统计对象一致；若上文已给出「已同步表名」列表，则必须是列表中某一项的原样字符串
- used_field: 字符串或 null。非 COUNT(*) 类度量时的主列名（不含表前缀）；若上文已给出「已同步字段名」列表，则必须是 used_table 下字段列表中的某一项
- expansion_hint: 字符串或 null。**时间粒度、分组/筛选口径**写在这里（如「按自然日分组」「按周汇总」），**不要**写进 measure_sql。用户提到每日/按天/按月等时必须填写；未涉及时间粒度则为 null

【次数 / 条数 / 执行次数 / 笔数 / 场次】类需求（数「有多少条记录」、一行代表一次事件）：
- 优先使用 **COUNT(*)**，不要把度量写成 **COUNT(某表.id)** 或 COUNT(主键列)，除非用户明确要数「非空主键个数」（极少见）。
- 正确示例：任务执行日志一行一次执行 → measure_sql 为 `COUNT(*)`，used_table 填实际日志表名，used_field 为 null。
- 错误示例：用户说「每日任务执行次数」却输出 `COUNT(execution_records.id)` —— 表名常是臆造的，且语义上应数行数用 COUNT(*)。
- 用户说「每日…」「按天…」时：measure_sql 仍为 `COUNT(*)` 等**纯聚合片段**；在 expansion_hint 中说明「需按日历日分组/筛选」，并在 aliases、description 中体现「每日」说法。

【金额 / 数量累加】类：用 SUM(表.列) 等，列名从业务推断，表名必须来自已同步列表（若有列表）。

【耗时 / 时长 / duration / 用时】类需求：
- 如果字段列表中存在明显的「duration/耗时/用时/时长/执行时长」字段，优先直接使用它的聚合（如 SUM(duration)），不要发散去发明 start_time/end_time 再相减。
- 仅当字段列表中完全没有对应耗时字段时，才允许用“开始-结束”差值（并确保 used_table/used_field 能在字段列表中对应到真实字段）。 

若上文提供了「已同步表名」列表：
- measure_sql 里出现的每个表名必须与列表中某项**完全一致**，禁止编造列表中不存在的表名（如 execution_records、task_run 等未出现时严禁使用）。"""


@router.post("/suggest", summary=f"{PLACEHOLDER_PREFIX}metric_suggest")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def suggest_metric(body: MetricSuggestBody, session: SessionDep, current_user: CurrentUser):
    try:
        llm = await create_llm(use_tool=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    synced_table_names: list[str] = []
    synced_fields_by_table: dict[str, list[str]] = {}
    schema_hint = ""
    if body.datasource_id is not None:
        ds = session.get(CoreDatasource, body.datasource_id)
        if ds is not None and ds.oid == current_user.oid:
            tbls = get_tables_by_ds_id(session, body.datasource_id)[:30]
            synced_table_names = [t.table_name for t in tbls if getattr(t, "table_name", None)]
            if synced_table_names:
                table_ids = [t.id for t in tbls if getattr(t, "id", None)]
                if table_ids:
                    rows = (
                        session.query(CoreField)
                        .filter(CoreField.table_id.in_(table_ids))
                        .order_by(CoreField.table_id.asc(), CoreField.field_index.asc())
                        .all()
                    )
                    table_id_to_name = {t.id: t.table_name for t in tbls if getattr(t, "id", None)}
                    for r in rows:
                        tn = table_id_to_name.get(r.table_id)
                        if not tn:
                            continue
                        synced_fields_by_table.setdefault(tn, []).append(r.field_name)

                # 为了降低幻觉，只给与「耗时」相关的字段候选（其余字段只取前几个兜底）。
                desc_lower = body.description.strip().lower()
                duration_keywords = (
                    "耗时",
                    "用时",
                    "时长",
                    "duration",
                    "elapsed",
                    "execution_time",
                    "execution time",
                    "total_time",
                    "run_time",
                    "耗用",
                )
                wants_duration = any(k in desc_lower for k in duration_keywords)

                def _field_score(fn_lower: str) -> int:
                    # 数值越大越优先
                    score = 0
                    if "duration" in fn_lower or "耗时" in fn_lower or "用时" in fn_lower or "时长" in fn_lower:
                        score += 5
                    if "elapsed" in fn_lower or "execution" in fn_lower or "time" in fn_lower:
                        score += 2
                    return score

                max_tables = 18
                max_fields_per_table = 18
                lines: list[str] = []
                for t in tbls[:max_tables]:
                    tn = t.table_name
                    all_fields = synced_fields_by_table.get(tn, [])
                    if not all_fields:
                        continue
                    if wants_duration:
                        picked = [
                            f
                            for f in all_fields
                            if any(k in f.lower() for k in ("duration", "elapsed", "execution", "time"))
                            or any(k in f for k in ("耗时", "用时", "时长"))
                        ]
                        if not picked:
                            # 兜底：按字段名优先级取前几个
                            picked = sorted(all_fields, key=lambda x: _field_score(str(x).lower()), reverse=True)[:max_fields_per_table]
                    else:
                        picked = all_fields[:max_fields_per_table]
                    picked = [p for p in picked if p]
                    if picked:
                        lines.append(f"- {tn}: {', '.join(picked[:max_fields_per_table])}")

                if lines:
                    schema_hint = (
                        "\n\n【数据源已同步的表名与字段名（用于 measure_sql / used_table / used_field；禁止臆造）】\n"
                        + "\n".join(lines)
                        + "\n\n【自检】输出前检查：① used_table 必须出现在上述表名；② used_field 必须出现在 used_table 对应字段列表中；③ 若涉及「耗时/时长」，优先用 duration/耗时/用时/时长 字段聚合。"
                    )

    try:
        msg = HumanMessage(
            content=f"{_SUGGEST_SYSTEM}{schema_hint}\n\n用户描述：\n{body.description.strip()}"
        )
        resp = await llm.ainvoke([msg])
        text = _ai_message_text(resp)
        data = _parse_suggest_json(text)
    except orjson.JSONDecodeError as e:
        raise HTTPException(
            status_code=502,
            detail="模型返回无法解析为 JSON，请重试或改用「本地模板」",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    code = str(data.get("code") or "").strip()[:128]
    name = str(data.get("name") or "").strip()[:255]
    measure_sql = str(data.get("measure_sql") or "").strip()
    measure_sql = _demote_count_table_id_to_star(measure_sql, body.description.strip())
    if not code or not name or not measure_sql:
        raise HTTPException(
            status_code=502,
            detail="模型未返回完整的 code / name / measure_sql，请重试",
        )
    aliases = data.get("aliases")
    if not isinstance(aliases, list):
        aliases = []
    aliases = [str(a).strip() for a in aliases if str(a).strip()][:8]
    desc = data.get("description")
    description = str(desc).strip()[:2000] if desc is not None else ""
    def _opt_str(v) -> Optional[str]:
        if v is None or v == "":
            return None
        s = str(v).strip()
        if not s or s.lower() == "null":
            return None
        return s[:256]

    def _opt_str_long(v, max_len: int) -> Optional[str]:
        if v is None or v == "":
            return None
        s = str(v).strip()
        if not s or s.lower() == "null":
            return None
        return s[:max_len]

    used_table = _opt_str(data.get("used_table"))
    used_field = _opt_str(data.get("used_field"))
    if re.search(r"COUNT\s*\(\s*\*\s*\)", measure_sql, re.I) and used_field and str(used_field).lower() == "id":
        used_field = None
    if synced_table_names and used_table:
        if used_table not in synced_table_names:
            by_lower = {x.lower(): x for x in synced_table_names}
            canon = by_lower.get(used_table.lower())
            used_table = canon if canon else None

    # used_field 兜底校验：必须出现在 used_table 对应的字段列表中
    if used_table and used_field:
        fields = synced_fields_by_table.get(used_table, [])
        if fields:
            by_lower = {f.lower(): f for f in fields}
            canon_field = by_lower.get(str(used_field).lower())
            if canon_field:
                used_field = canon_field
            else:
                used_field = None

    expansion_hint = _opt_str_long(data.get("expansion_hint"), 1024) or _infer_time_grain_hint(
        body.description.strip()
    )
    return {
        "code": code,
        "name": name,
        "measure_sql": measure_sql,
        "aliases": aliases,
        "description": description or None,
        "used_table": used_table,
        "used_field": used_field,
        "expansion_hint": expansion_hint,
    }


@router.post("/suggest/advanced", summary=f"{PLACEHOLDER_PREFIX}metric_suggest_advanced")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def suggest_metric_advanced(body: MetricAdvancedSuggestBody, session: SessionDep, current_user: CurrentUser):
    kind = (body.metric_kind or "").strip()
    if kind not in ("atomic", "derived", "composite"):
        raise HTTPException(status_code=400, detail="metric_kind must be atomic/derived/composite")
    if kind == "atomic":
        return await suggest_metric(
            MetricSuggestBody(description=body.description, datasource_id=body.datasource_id),
            session,
            current_user,
        )

    try:
        llm = await create_llm(use_tool=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    stmt = select(CoreMetric).where(CoreMetric.oid == current_user.oid, CoreMetric.enabled == True)
    rows = session.execute(stmt).scalars().all()
    rows = [m for m in rows if metric_crud._ds_match(m, body.datasource_id)]
    if not rows:
        raise HTTPException(status_code=400, detail="当前数据源下没有可用指标，请先创建原子指标")

    if kind == "derived":
        base_lines = _advanced_candidate_lines(rows, "atomic")
        if not base_lines:
            raise HTTPException(status_code=400, detail="派生指标至少需要 1 个原子指标作为基础指标")
        msg = HumanMessage(
            content=(
                f"{_SUGGEST_DERIVED_SYSTEM}\n\n"
                f"【候选基础指标（只能从中选择 base_metric_code）】\n{base_lines}\n\n"
                f"用户描述：\n{body.description.strip()}"
            )
        )
        try:
            resp = await llm.ainvoke([msg])
            data = _parse_suggest_json(_ai_message_text(resp))
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        base_code = str(data.get("base_metric_code") or "").strip()
        code_set = {m.code for m in rows if m.metric_kind == "atomic"}
        if base_code not in code_set:
            raise HTTPException(status_code=502, detail="模型返回的 base_metric_code 不在候选列表中")
        aliases = data.get("aliases") if isinstance(data.get("aliases"), list) else []
        modifiers = data.get("modifiers") if isinstance(data.get("modifiers"), dict) else None
        expansion_hint = data.get("expansion_hint")
        expansion_hint = str(expansion_hint).strip()[:1024] if expansion_hint else None
        return {
            "code": str(data.get("code") or "").strip()[:128],
            "name": str(data.get("name") or "").strip()[:255],
            "aliases": [str(a).strip() for a in aliases if str(a).strip()][:8],
            "description": (str(data.get("description") or "").strip()[:2000] or None),
            "base_metric_code": base_code,
            "modifiers": modifiers,
            "expansion_hint": expansion_hint or _infer_time_grain_hint(body.description.strip()),
        }

    # composite
    cand_lines = _advanced_candidate_lines(rows, None)
    msg = HumanMessage(
        content=(
            f"{_SUGGEST_COMPOSITE_SYSTEM}\n\n"
            f"【候选子指标（只能从中选择 child_metric_code）】\n{cand_lines}\n\n"
            f"用户描述：\n{body.description.strip()}"
        )
    )
    try:
        resp = await llm.ainvoke([msg])
        data = _parse_suggest_json(_ai_message_text(resp))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    code_set = {m.code for m in rows}
    comps_in = data.get("components") if isinstance(data.get("components"), list) else []
    comps = []
    for c in comps_in[:8]:
        if not isinstance(c, dict):
            continue
        slot = str(c.get("slot_code") or "").strip()
        child_code = str(c.get("child_metric_code") or "").strip()
        if slot and child_code and child_code in code_set:
            comps.append({"slot_code": slot, "child_metric_code": child_code})
    if not comps:
        raise HTTPException(status_code=502, detail="模型未返回有效 components（或 child_metric_code 不在候选内）")
    aliases = data.get("aliases") if isinstance(data.get("aliases"), list) else []
    return {
        "code": str(data.get("code") or "").strip()[:128],
        "name": str(data.get("name") or "").strip()[:255],
        "aliases": [str(a).strip() for a in aliases if str(a).strip()][:8],
        "description": (str(data.get("description") or "").strip()[:2000] or None),
        "expression": str(data.get("expression") or "").strip()[:2000],
        "components": comps,
    }


@router.get("/page/{current_page}/{page_size}", summary=f"{PLACEHOLDER_PREFIX}metric_page")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def get_page(
    session: SessionDep,
    current_user: CurrentUser,
    current_page: int,
    page_size: int,
    name: Optional[str] = Query(None),
    metric_kind: Optional[str] = Query(None),
    datasource_id: Optional[int] = Query(None, description="仅返回绑定该数据源的指标"),
):
    cp, ps, total, pages, data = metric_crud.page_metric(
        session, current_page, page_size, current_user.oid, name, metric_kind, datasource_id
    )
    return {
        "current_page": cp,
        "page_size": ps,
        "total_count": total,
        "total_pages": pages,
        "data": [d.model_dump() for d in data],
    }


@router.get("/options/list", summary=f"{PLACEHOLDER_PREFIX}metric_options")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def list_options(
    session: SessionDep,
    current_user: CurrentUser,
    datasource_ids: Optional[str] = Query(
        None, description="逗号分隔的数据源 ID，仅返回与这些数据源有交集的指标"
    ),
):
    ids: list[int] = []
    if datasource_ids and datasource_ids.strip():
        for p in datasource_ids.split(","):
            p = p.strip()
            if p.isdigit():
                ids.append(int(p))
    return {"data": metric_crud.list_metric_options(session, current_user.oid, ids)}


@router.put("", summary=f"{PLACEHOLDER_PREFIX}metric_save")
@require_permissions(
    permission=SqlbotPermission(role=["ws_admin"], type="ds", keyExpression="info.datasource_ids")
)
async def save_or_update(session: SessionDep, current_user: CurrentUser, trans: Trans, info: MetricInfo):
    try:
        if info.id:
            return metric_crud.update_metric(session, info, current_user.oid).model_dump()
        return metric_crud.create_metric(session, info, current_user.oid).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("", summary=f"{PLACEHOLDER_PREFIX}metric_delete")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def delete_metrics(session: SessionDep, current_user: CurrentUser, trans: Trans, id_list: list[int]):
    try:
        metric_crud.delete_metric(session, id_list, current_user.oid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{id}/enable/{enabled}", summary=f"{PLACEHOLDER_PREFIX}metric_enable")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def toggle_enable(session: SessionDep, current_user: CurrentUser, trans: Trans, id: int, enabled: bool):
    try:
        metric_crud.enable_metric(session, id, enabled, current_user.oid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
