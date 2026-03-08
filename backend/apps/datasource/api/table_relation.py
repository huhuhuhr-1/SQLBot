# Author: Junjun
# Date: 2025/9/24
import re
from typing import List, Optional, Tuple, Union, Dict, Any

from fastapi import APIRouter, Path, Body
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel

from apps.datasource.models.datasource import CoreDatasource, CoreTable, CoreField, FieldObj
from apps.datasource.crud.table import get_tables_by_ds_id
from apps.datasource.crud.field import get_fields_by_table_id
from apps.db.db_fk import get_fk_relations
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from apps.terminology.curd.terminology import get_terminology_template
from common.core.deps import SessionDep
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import LogConfig, system_log

router = APIRouter(tags=["Table Relation"], prefix="/table_relation")

# LLM 推断表关系的 prompt
INFER_RELATION_SYSTEM = """你是一个数据库表关系推断助手。根据给定的表结构（Schema）和可选的术语说明，推断表与表之间的外键/关联关系（用于多表 JOIN）。

规则：
1. 只输出你确信存在的外键或关联关系，不要臆造。
2. 每行一条关系，格式严格为：表名.字段名=引用表名.引用字段名（表名、字段名与 Schema 中完全一致，大小写敏感）。
3. 若没有额外关系可补充，只输出一行：NONE
4. 不要输出任何解释或 JSON，只输出上述格式的行。"""

INFER_RELATION_USER = """<m-schema>
{schema}
</m-schema>
{terminology_block}
请根据以上表结构推断表之间的外键/关联关系（多表 JOIN 时用到的字段对应关系）。每行一条，格式：表名.字段名=引用表名.引用字段名。若无补充则输出 NONE。"""


def _infer_edges_by_fk(ds: CoreDatasource, table_id_set: set, key_to_ids: dict) -> List[dict]:
    """Layer 1: edges from real DB foreign keys."""
    fk_list = get_fk_relations(ds)
    edges = []
    for tname, col_name, ref_tname, ref_col in fk_list:
        tname_l = tname.lower().strip()
        ref_tname_l = ref_tname.lower().strip()
        col_l = col_name.lower().strip()
        ref_col_l = ref_col.lower().strip()
        key_src = (tname_l, col_l)
        key_tgt = (ref_tname_l, ref_col_l)
        if key_src not in key_to_ids or key_tgt not in key_to_ids:
            continue
        src_tid, src_fid = key_to_ids[key_src]
        tgt_tid, tgt_fid = key_to_ids[key_tgt]
        if src_tid not in table_id_set or tgt_tid not in table_id_set:
            continue
        if src_tid == tgt_tid:
            continue
        edges.append({
            "shape": "edge",
            "source": {"cell": src_tid, "port": src_fid},
            "target": {"cell": tgt_tid, "port": tgt_fid},
        })
    return edges


def _infer_edges_by_naming(
    tables: List[CoreTable], table_fields: dict, name_to_table: dict, seen_keys: set
) -> List[dict]:
    """Layer 2: edges from xxx_id -> table.id naming convention."""
    edges = []
    for t in tables:
        fields = table_fields.get(t.id, [])
        for f in fields:
            fname = (f.field_name or "").strip()
            if not fname.endswith("_id") or len(fname) <= 3:
                continue
            prefix = fname[:-3].lower()
            if not prefix:
                continue
            candidates = [prefix, prefix + "s", prefix + "es", prefix + "ies"]
            if prefix.endswith("y"):
                candidates.append(prefix[:-1] + "ies")
            ref_table = None
            for cand in candidates:
                ref_table = name_to_table.get(cand)
                if ref_table is not None:
                    break
            if ref_table is None or ref_table.id == t.id:
                continue
            ref_fields = table_fields.get(ref_table.id, [])
            ref_id_field = None
            for rf in ref_fields:
                if (rf.field_name or "").strip().lower() == "id":
                    ref_id_field = rf
                    break
            if ref_id_field is None and ref_fields:
                ref_id_field = ref_fields[0]
            if ref_id_field is None:
                continue
            key = (t.id, f.id, ref_table.id, ref_id_field.id)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            edges.append({
                "shape": "edge",
                "source": {"cell": t.id, "port": f.id},
                "target": {"cell": ref_table.id, "port": ref_id_field.id},
            })
    return edges


def _build_schema_str_for_llm(
    tables: List[CoreTable],
    table_fields: Dict[int, List[CoreField]],
    ds: CoreDatasource,
) -> str:
    """构建与生成 SQL 一致的 m-schema 格式字符串，供 LLM 推断关系使用。"""
    lines = []
    for t in tables:
        tname = (t.table_name or "").strip()
        comment = (t.custom_comment or "").strip()
        if ds.type not in ("mysql", "es"):
            lines.append(f"# Table: {tname}")
        else:
            lines.append(f"# Table: {tname}")
        if comment:
            lines.append(f", {comment}")
        lines.append("\n[")
        fields = table_fields.get(t.id, [])
        if fields:
            parts = []
            for f in fields:
                fname = (f.field_name or "").strip()
                ftype = (f.field_type or "").strip()
                fcomment = (f.custom_comment or "").strip()
                if fcomment:
                    parts.append(f"({fname}:{ftype}, {fcomment})")
                else:
                    parts.append(f"({fname}:{ftype})")
            lines.append(",\n".join(parts))
        lines.append("\n]\n")
    return "".join(lines)


def _infer_edges(
    session: SessionDep,
    ds_id: int,
    table_ids: Optional[List[int]] = None,
    return_context: bool = False,
) -> Union[List[dict], Tuple[List[dict], Dict[str, Any]]]:
    """Infer edges: Layer 1 real FK + Layer 2 naming, FK takes priority.
    When return_context=True, returns (edges, context) for LLM completion."""
    tables: List[CoreTable] = get_tables_by_ds_id(session, ds_id)
    if table_ids is not None:
        table_id_set = set(table_ids)
        tables = [t for t in tables if t.id in table_id_set]
    else:
        table_id_set = {t.id for t in tables}
    if not tables:
        if return_context:
            return [], {"tables": [], "table_fields": {}, "name_to_table": {}, "key_to_ids": {}, "table_id_set": set()}
        return []

    table_fields = {}
    for t in tables:
        table_fields[t.id] = get_fields_by_table_id(session, t.id, FieldObj(fieldName=None))

    name_to_table = {}
    for t in tables:
        key = (t.table_name or "").strip().lower()
        if key and key not in name_to_table:
            name_to_table[key] = t

    key_to_ids = {}
    for t in tables:
        tname = (t.table_name or "").strip().lower()
        for f in table_fields.get(t.id, []):
            fname = (f.field_name or "").strip().lower()
            if tname and fname:
                key_to_ids[(tname, fname)] = (t.id, f.id)

    def edge_key(e):
        return (e["source"]["cell"], e["source"]["port"], e["target"]["cell"], e["target"]["port"])

    result_map = {}

    ds = session.get(CoreDatasource, ds_id)
    if ds:
        fk_edges = _infer_edges_by_fk(ds, table_id_set, key_to_ids)
        for e in fk_edges:
            result_map[edge_key(e)] = e

    seen_keys = set(result_map.keys())
    naming_edges = _infer_edges_by_naming(tables, table_fields, name_to_table, seen_keys)
    for e in naming_edges:
        k = edge_key(e)
        if k not in result_map:
            result_map[k] = e

    edges = list(result_map.values())
    if return_context:
        context = {
            "tables": tables,
            "table_fields": table_fields,
            "name_to_table": name_to_table,
            "key_to_ids": key_to_ids,
            "table_id_set": table_id_set,
        }
        return edges, context
    return edges


# 匹配 "表名.字段名=引用表.引用字段"，允许空格
_RE_INFER_LINE = re.compile(
    r"^\s*([^\s.]+)\s*\.\s*([^\s=]+)\s*=\s*([^\s.]+)\s*\.\s*([^\s]+)\s*$",
    re.IGNORECASE,
)


def _parse_llm_relation_lines(
    text: str, key_to_ids: Dict[tuple, Tuple[int, int]], table_id_set: set
) -> List[dict]:
    """解析 LLM 返回的每行 '表.字段=引用表.引用字段'，转为 edge 列表。"""
    edges = []
    for line in (text or "").strip().splitlines():
        line = line.strip()
        if not line or line.upper() == "NONE":
            continue
        m = _RE_INFER_LINE.match(line)
        if not m:
            continue
        t1, f1, t2, f2 = m.groups()
        k1 = (t1.strip().lower(), f1.strip().lower())
        k2 = (t2.strip().lower(), f2.strip().lower())
        if k1 not in key_to_ids or k2 not in key_to_ids:
            continue
        src_tid, src_fid = key_to_ids[k1]
        tgt_tid, tgt_fid = key_to_ids[k2]
        if src_tid not in table_id_set or tgt_tid not in table_id_set:
            continue
        if src_tid == tgt_tid and src_fid == tgt_fid:
            continue
        edges.append({
            "shape": "edge",
            "source": {"cell": src_tid, "port": src_fid},
            "target": {"cell": tgt_tid, "port": tgt_fid},
        })
    return edges


async def _infer_edges_llm(
    session: SessionDep,
    ds: CoreDatasource,
    context: Dict[str, Any],
    rule_edges: List[dict],
    llm,
) -> List[dict]:
    """用 LLM 在规则推断基础上补全表关系。返回仅新增的边（与 rule 去重）。"""
    tables = context.get("tables") or []
    table_fields = context.get("table_fields") or {}
    key_to_ids = context.get("key_to_ids") or {}
    table_id_set = context.get("table_id_set") or set()
    if not tables or not key_to_ids:
        return []

    schema_str = _build_schema_str_for_llm(tables, table_fields, ds)
    terminology_str, _ = get_terminology_template(
        session, "表关系 外键 关联 字段", ds.oid, ds.id
    )
    terminology_block = ""
    if terminology_str and terminology_str.strip():
        terminology_block = "<terminologies>\n" + terminology_str.strip() + "\n</terminologies>\n\n"

    user_content = INFER_RELATION_USER.format(
        schema=schema_str,
        terminology_block=terminology_block,
    )

    messages = [SystemMessage(content=INFER_RELATION_SYSTEM), HumanMessage(content=user_content)]
    try:
        response = await llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
    except Exception:
        return []

    llm_edges = _parse_llm_relation_lines(content, key_to_ids, table_id_set)

    def edge_key(e):
        return (e["source"]["cell"], e["source"]["port"], e["target"]["cell"], e["target"]["port"])

    rule_keys = {edge_key(e) for e in rule_edges}
    extra = [e for e in llm_edges if edge_key(e) not in rule_keys]
    return extra


@router.post("/save/{ds_id}", response_model=None, summary=f"{PLACEHOLDER_PREFIX}tr_save")
@require_permissions(permission=SqlbotPermission(role=['ws_admin'], keyExpression="ds_id", type='ds'))
@system_log(LogConfig(operation_type=OperationType.UPDATE_TABLE_RELATION,module=OperationModules.DATASOURCE,resource_id_expr="ds_id"))
async def save_relation(session: SessionDep, relation: List[dict],
                        ds_id: int = Path(..., description=f"{PLACEHOLDER_PREFIX}ds_id")):
    ds = session.get(CoreDatasource, ds_id)
    if ds:
        ds.table_relation = relation
        session.commit()
    else:
        raise Exception("no datasource")
    return True


@router.post("/get/{ds_id}", response_model=List, summary=f"{PLACEHOLDER_PREFIX}tr_get")
@require_permissions(permission=SqlbotPermission(role=['ws_admin'], keyExpression="ds_id", type='ds'))
async def get_relation(session: SessionDep, ds_id: int = Path(..., description=f"{PLACEHOLDER_PREFIX}ds_id")):
    ds = session.get(CoreDatasource, ds_id)
    if ds:
        return ds.table_relation if ds.table_relation else []
    return []


class InferRelationBody(BaseModel):
    table_ids: Optional[List[int]] = None
    use_llm: bool = True  # 规则优先，再使用 LLM 补全关系


@router.post("/infer/{ds_id}", response_model=List, summary=f"{PLACEHOLDER_PREFIX}tr_infer")
@require_permissions(permission=SqlbotPermission(role=['ws_admin'], keyExpression="ds_id", type='ds'))
async def infer_relation(
    session: SessionDep,
    ds_id: int = Path(..., description=f"{PLACEHOLDER_PREFIX}ds_id"),
    body: InferRelationBody = Body(default=None),
):
    """Infer table relations: rule-based (FK + naming) first, then LLM completion. Returns suggested edges."""
    ds = session.get(CoreDatasource, ds_id)
    if not ds:
        raise ValueError("no datasource")
    table_ids = body.table_ids if body else None
    use_llm = body.use_llm if body else True

    if use_llm:
        result = _infer_edges(session, ds_id, table_ids, return_context=True)
        rule_edges, context = result
        try:
            from apps.ai_model.model_factory import create_llm

            llm = await create_llm(use_cache=True, use_tool=False)
            llm_edges = await _infer_edges_llm(session, ds, context, rule_edges, llm)
        except Exception:
            llm_edges = []

        def edge_key(e):
            return (e["source"]["cell"], e["source"]["port"], e["target"]["cell"], e["target"]["port"])

        seen = {edge_key(e) for e in rule_edges}
        for e in llm_edges:
            k = edge_key(e)
            if k not in seen:
                rule_edges.append(e)
                seen.add(k)
        return rule_edges

    return _infer_edges(session, ds_id, table_ids, return_context=False)
