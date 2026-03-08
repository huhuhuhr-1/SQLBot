# Author: Junjun
# Date: 2025/9/24
from typing import List, Optional

from fastapi import APIRouter, Path, Body
from pydantic import BaseModel

from apps.datasource.models.datasource import CoreDatasource, CoreTable, CoreField, FieldObj
from apps.datasource.crud.table import get_tables_by_ds_id
from apps.datasource.crud.field import get_fields_by_table_id
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.deps import SessionDep
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import LogConfig, system_log

router = APIRouter(tags=["Table Relation"], prefix="/table_relation")


def _infer_edges(session: SessionDep, ds_id: int, table_ids: Optional[List[int]] = None) -> List[dict]:
    """Infer FK-like edges from field naming (xxx_id -> referenced table.id)."""
    tables: List[CoreTable] = get_tables_by_ds_id(session, ds_id)
    if table_ids is not None:
        table_id_set = set(table_ids)
        tables = [t for t in tables if t.id in table_id_set]
    if not tables:
        return []

    # table_id -> list[CoreField]
    table_fields = {}
    for t in tables:
        table_fields[t.id] = get_fields_by_table_id(session, t.id, FieldObj())

    # table_name (lower) -> table (first match)
    name_to_table = {}
    for t in tables:
        key = (t.table_name or "").strip().lower()
        if key and key not in name_to_table:
            name_to_table[key] = t

    edges: List[dict] = []
    seen = set()

    for t in tables:
        fields = table_fields.get(t.id, [])
        for f in fields:
            fname = (f.field_name or "").strip()
            if not fname.endswith("_id") or len(fname) <= 3:
                continue
            prefix = fname[:-3].lower()
            if not prefix:
                continue
            # possible referenced table names (singular/plural)
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
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "shape": "edge",
                "source": {"cell": t.id, "port": f.id},
                "target": {"cell": ref_table.id, "port": ref_id_field.id},
            })
    return edges


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


@router.post("/infer/{ds_id}", response_model=List, summary=f"{PLACEHOLDER_PREFIX}tr_infer")
@require_permissions(permission=SqlbotPermission(role=['ws_admin'], keyExpression="ds_id", type='ds'))
async def infer_relation(
    session: SessionDep,
    ds_id: int = Path(..., description=f"{PLACEHOLDER_PREFIX}ds_id"),
    body: InferRelationBody = Body(default=None),
):
    """Infer table relations from field naming (e.g. user_id -> users.id). Returns suggested edges."""
    ds = session.get(CoreDatasource, ds_id)
    if not ds:
        raise ValueError("no datasource")
    table_ids = body.table_ids if body else None
    return _infer_edges(session, ds_id, table_ids)
