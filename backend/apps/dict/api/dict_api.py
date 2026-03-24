from typing import List, Optional

from fastapi import APIRouter, Query

from apps.dict.curd.dict_crud import (
    delete_binding,
    delete_dict,
    enable_dict,
    get_dict_detail,
    list_dict_options,
    page_binding,
    page_dict,
    save_binding,
    save_dict,
)
from apps.dict.models.dict_model import BizDictBindingSave, BizDictSave
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import LogConfig, system_log
from common.core.deps import SessionDep, CurrentUser, Trans

router = APIRouter(tags=["Dictionary"], prefix="/system/dict")


@router.get("/page/{current_page}/{page_size}", summary=f"{PLACEHOLDER_PREFIX}get_dict_page")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def dict_pager(
    session: SessionDep,
    current_user: CurrentUser,
    current_page: int,
    page_size: int,
    keyword: Optional[str] = Query(None, description="搜索名称或编码"),
):
    cp, ps, total, pages, data = page_dict(session, current_page, page_size, keyword, current_user.oid)
    return {
        "current_page": cp,
        "page_size": ps,
        "total_count": total,
        "total_pages": pages,
        "data": data,
    }


@router.get("/options", summary=f"{PLACEHOLDER_PREFIX}list_dict_options")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def dict_options(session: SessionDep, current_user: CurrentUser):
    return list_dict_options(session, current_user.oid)


@router.get("/binding/page/{current_page}/{page_size}", summary=f"{PLACEHOLDER_PREFIX}get_dict_binding_page")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def binding_pager(
    session: SessionDep,
    current_user: CurrentUser,
    current_page: int,
    page_size: int,
    datasource_id: Optional[int] = Query(None),
    dict_id: Optional[int] = Query(None),
):
    cp, ps, total, pages, data = page_binding(
        session, current_page, page_size, current_user.oid, datasource_id, dict_id
    )
    return {
        "current_page": cp,
        "page_size": ps,
        "total_count": total,
        "total_pages": pages,
        "data": data,
    }


@router.put("/binding", response_model=int, summary=f"{PLACEHOLDER_PREFIX}save_dict_binding")
@require_permissions(permission=SqlbotPermission(role=['ws_admin'], type='ds', keyExpression="info.datasource_id"))
@system_log(
    LogConfig(
        operation_type=OperationType.CREATE_OR_UPDATE,
        module=OperationModules.BIZ_DICTIONARY,
        resource_id_expr="info.id",
        result_id_expr="result_self",
    )
)
async def binding_put(session: SessionDep, current_user: CurrentUser, trans: Trans, info: BizDictBindingSave):
    return save_binding(session, info, current_user.oid, trans)


@router.delete("/binding", summary=f"{PLACEHOLDER_PREFIX}delete_dict_binding")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
@system_log(
    LogConfig(
        operation_type=OperationType.DELETE,
        module=OperationModules.BIZ_DICTIONARY,
        resource_id_expr="id_list",
    )
)
async def binding_delete(session: SessionDep, current_user: CurrentUser, id_list: List[int]):
    delete_binding(session, id_list, current_user.oid)


@router.get("/{dict_id}/detail", summary=f"{PLACEHOLDER_PREFIX}get_dict_detail")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def dict_detail(session: SessionDep, current_user: CurrentUser, dict_id: int):
    return get_dict_detail(session, dict_id, current_user.oid)


@router.put("", response_model=int, summary=f"{PLACEHOLDER_PREFIX}save_dict")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
@system_log(
    LogConfig(
        operation_type=OperationType.CREATE_OR_UPDATE,
        module=OperationModules.BIZ_DICTIONARY,
        resource_id_expr="info.id",
        result_id_expr="result_self",
    )
)
async def dict_put(session: SessionDep, current_user: CurrentUser, trans: Trans, info: BizDictSave):
    return save_dict(session, info, current_user.oid, trans)


@router.delete("", summary=f"{PLACEHOLDER_PREFIX}delete_dict")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
@system_log(
    LogConfig(
        operation_type=OperationType.DELETE,
        module=OperationModules.BIZ_DICTIONARY,
        resource_id_expr="id_list",
    )
)
async def dict_delete(session: SessionDep, current_user: CurrentUser, id_list: List[int]):
    delete_dict(session, id_list, current_user.oid)


@router.get("/{dict_id}/enable/{enabled}", summary=f"{PLACEHOLDER_PREFIX}enable_dict")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
@system_log(
    LogConfig(
        operation_type=OperationType.UPDATE_STATUS,
        module=OperationModules.BIZ_DICTIONARY,
        resource_id_expr="dict_id",
    )
)
async def dict_enable(session: SessionDep, current_user: CurrentUser, trans: Trans, dict_id: int, enabled: bool):
    enable_dict(session, dict_id, enabled, current_user.oid, trans)
