# Author: Junjun
# Date: 2025/9/24
from typing import List

from fastapi import APIRouter, Path

from apps.datasource.models.datasource import CoreDatasource
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.deps import SessionDep
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import LogConfig, system_log
router = APIRouter(tags=["Table Relation"], prefix="/table_relation")


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
