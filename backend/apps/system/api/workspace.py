from typing import Optional, List
from fastapi import APIRouter, HTTPException, Path, Query, Body
from pydantic import BaseModel
from sqlmodel import exists, or_, select, delete as sqlmodel_delete, update as sqlmodel_update
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.crud.user import clean_user_cache
from apps.system.crud.workspace import reset_single_user_oid, reset_user_oid
from apps.system.models.system_model import UserWsModel, WorkspaceBase, WorkspaceEditor, WorkspaceModel
from apps.system.models.user import UserModel
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from apps.system.schemas.system_schema import UserWsBase, UserWsDTO, UserWsEditor, UserWsOption, WorkspaceUser
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import system_log, LogConfig
from common.core.deps import CurrentUser, SessionDep, Trans
from common.core.pagination import Paginator
from common.core.schemas import PaginatedResponse, PaginationParams
from common.utils.time import get_timestamp

router = APIRouter(tags=["system_ws"], prefix="/system/workspace")


class MemberExportItem(BaseModel):
    uid: int
    account: str
    name: str
    weight: int


class MemberExportPayload(BaseModel):
    version: int = 1
    oid: int = 0
    members: List[MemberExportItem] = []


class MemberImportItem(BaseModel):
    account: str
    weight: int = 0


class MemberImportPayload(BaseModel):
    members: List[MemberImportItem] = []


@router.post("/uws/export", response_model=MemberExportPayload, summary="全部导出成员",
             description="导出当前工作空间全部成员（账号、姓名、权重）。")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def uws_export_all(
    session: SessionDep,
    current_user: CurrentUser,
    trans: Trans,
    oid: Optional[int] = Query(None, description="空间ID(仅admin生效)"),
):
    if current_user.isAdmin and oid is not None:
        workspace_id = oid
    else:
        workspace_id = current_user.oid or 1
    stmt = (
        select(UserModel.id, UserModel.account, UserModel.name, UserWsModel.weight)
        .join(UserWsModel, UserModel.id == UserWsModel.uid)
        .where(UserWsModel.oid == workspace_id, UserModel.id != 1)
        .order_by(UserModel.account)
    )
    rows = session.exec(stmt).all()
    members = [
        MemberExportItem(uid=r[0], account=r[1] or "", name=r[2] or "", weight=r[3] or 0)
        for r in rows
    ]
    return MemberExportPayload(version=1, oid=workspace_id, members=members)


@router.post("/uws/import", response_model=List[MemberExportItem], summary="批量导入成员",
             description="合并导入：按账号匹配，存在则更新权重，不存在则加入工作空间。")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
@system_log(LogConfig(operation_type=OperationType.ADD, module=OperationModules.MEMBER))
async def uws_import(
    session: SessionDep,
    current_user: CurrentUser,
    trans: Trans,
    body: MemberImportPayload = Body(...),
    oid: Optional[int] = Query(None, description="空间ID(仅admin生效)"),
):
    if current_user.isAdmin and oid is not None:
        workspace_id = oid
    else:
        workspace_id = current_user.oid or 1
    result = []
    for item in body.members or []:
        if not item.account or not item.account.strip():
            continue
        account = item.account.strip()
        user = session.exec(select(UserModel).where(UserModel.account == account, UserModel.id != 1)).first()
        if not user:
            continue
        uid = user.id
        existing = session.exec(
            select(UserWsModel).where(UserWsModel.uid == uid, UserWsModel.oid == workspace_id)
        ).first()
        try:
            if existing:
                existing.weight = item.weight
                session.add(existing)
                session.commit()
                await clean_user_cache(uid)
            else:
                session.add(
                    UserWsModel(oid=workspace_id, uid=uid, weight=item.weight)
                )
                session.commit()
                await reset_single_user_oid(session, uid, workspace_id)
                await clean_user_cache(uid)
            u = session.get(UserModel, uid)
            result.append(
                MemberExportItem(uid=uid, account=u.account or "", name=u.name or "", weight=item.weight)
            )
        except Exception:
            session.rollback()
            continue
    return result


@router.get("/uws/option/pager/{pageNum}/{pageSize}", response_model=PaginatedResponse[UserWsOption], summary=f"{PLACEHOLDER_PREFIX}ws_user_grid_api", description=f"{PLACEHOLDER_PREFIX}ws_user_grid_api")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def option_pager(
    session: SessionDep,
    current_user: CurrentUser,
    trans: Trans,
    pageNum: int = Path(description=f"{PLACEHOLDER_PREFIX}page_num"),
    pageSize: int = Path(description=f"{PLACEHOLDER_PREFIX}page_size"),
    oid: int = Query(description=f"{PLACEHOLDER_PREFIX}oid"),
    keyword: Optional[str] = Query(None, description=f"{PLACEHOLDER_PREFIX}keyword"),
):
    if not current_user.isAdmin:
        raise Exception(trans('i18n_permission.no_permission', url = ", ", msg = trans('i18n_permission.only_admin')))
    if not oid:
        raise Exception(trans('i18n_miss_args', key = '[oid]'))
    pagination = PaginationParams(page=pageNum, size=pageSize)
    paginator = Paginator(session)
    stmt = select(UserModel.id, UserModel.account, UserModel.name).where(
        ~exists().where(UserWsModel.uid == UserModel.id, UserWsModel.oid == oid),
        UserModel.id != 1
    ).order_by(UserModel.account, UserModel.create_time)
    
    if keyword:
        keyword_pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                UserModel.account.ilike(keyword_pattern),
                UserModel.name.ilike(keyword_pattern),
            )
        )
    return await paginator.get_paginated_response(
        stmt=stmt,
        pagination=pagination,
    )
    
@router.get("/uws/option", response_model=UserWsOption | None, include_in_schema=False)
@require_permissions(permission=SqlbotPermission(role=['ws_admin'])) 
async def option_user(
    session: SessionDep, 
    current_user: CurrentUser,
    trans: Trans,
    keyword: str = Query(description="搜索关键字")
    ):
    if not keyword:
        raise Exception(trans('i18n_miss_args', key = '[keyword]'))
    if (not current_user.isAdmin) and current_user.weight == 0:
        raise Exception(trans('i18n_permission.no_permission', url = '', msg = ''))
    oid = current_user.oid
    
    stmt = select(UserModel.id, UserModel.account, UserModel.name).where(
        ~exists().where(UserWsModel.uid == UserModel.id, UserWsModel.oid == oid),
        UserModel.id != 1
    )
    
    if keyword:
        stmt = stmt.where(
            or_(
                UserModel.account == keyword,
                UserModel.name == keyword,
            )
        )
    return session.exec(stmt).first()


@router.get("/uws/pager/{pageNum}/{pageSize}", response_model=PaginatedResponse[WorkspaceUser], include_in_schema=False)
@require_permissions(permission=SqlbotPermission(role=['ws_admin'])) 
async def pager(
    session: SessionDep,
    current_user: CurrentUser,
    trans: Trans,
    pageNum: int,
    pageSize: int,
    keyword: Optional[str] = Query(None, description="搜索关键字(可选)"),
    oid: Optional[int] = Query(None, description="空间ID(仅admin用户生效)"),
):
    if not current_user.isAdmin and current_user.weight == 0:
        raise Exception(trans('i18n_permission.no_permission', url = '', msg = ''))
    if current_user.isAdmin:
        workspace_id = oid if oid else current_user.oid
    else:
        workspace_id = current_user.oid
    pagination = PaginationParams(page=pageNum, size=pageSize)
    paginator = Paginator(session)
    stmt = select(UserModel.id, UserModel.account, UserModel.name, UserModel.email, UserModel.status, UserModel.create_time, UserModel.oid, UserWsModel.weight).join(
        UserWsModel, UserModel.id == UserWsModel.uid
    ).where(
        UserWsModel.oid == workspace_id,
        UserModel.id != 1
    ).order_by(UserModel.account, UserModel.create_time)
    
    if keyword:
        keyword_pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                UserModel.account.ilike(keyword_pattern),
                UserModel.name.ilike(keyword_pattern),
                UserModel.email.ilike(keyword_pattern)
            )
        )
    return await paginator.get_paginated_response(
        stmt=stmt,
        pagination=pagination,
    )
    

@router.post("/uws", summary=f"{PLACEHOLDER_PREFIX}ws_user_bind_api", description=f"{PLACEHOLDER_PREFIX}ws_user_bind_api")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
@system_log(LogConfig(operation_type=OperationType.ADD, module=OperationModules.MEMBER, resource_id_expr="creator.uid_list",
                      ))
async def create(session: SessionDep, current_user: CurrentUser, trans: Trans, creator: UserWsDTO):
    if not current_user.isAdmin and current_user.weight == 0:
        raise Exception(trans('i18n_permission.no_permission', url = '', msg = ''))
    oid: int = creator.oid if (current_user.isAdmin and creator.oid) else current_user.oid
    weight = creator.weight if (current_user.isAdmin and creator.weight) else 0
    # 判断uid_list以及oid合法性
    db_model_list = [
        UserWsModel.model_validate({
            "oid": oid,
            "uid": uid,
            "weight": weight
        })
        for uid in creator.uid_list
    ]
    for uid in creator.uid_list:
        await reset_single_user_oid(session, uid, oid)
        await clean_user_cache(uid)
        
    session.add_all(db_model_list)

@router.put("/uws", summary=f"{PLACEHOLDER_PREFIX}ws_user_status_api", description=f"{PLACEHOLDER_PREFIX}ws_user_status_api")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.MEMBER, resource_id_expr="editor.uid_list",
                      ))
async def uws_edit(session: SessionDep, trans: Trans, editor: UserWsEditor):
    await edit(session, trans, editor)
    
async def edit(session: SessionDep, trans: Trans, editor: UserWsEditor):
    if not editor.oid or not editor.uid:
        raise Exception(trans('i18n_miss_args', key = '[oid, uid]'))
    db_model = session.exec(select(UserWsModel).where(UserWsModel.uid == editor.uid, UserWsModel.oid == editor.oid)).first()
    if not db_model:
        raise HTTPException("uws not exist")
    if editor.weight == db_model.weight:
        return
    
    db_model.weight = editor.weight
    session.add(db_model)
    
    await clean_user_cache(editor.uid)

@router.delete("/uws", summary=f"{PLACEHOLDER_PREFIX}ws_user_unbind_api", description=f"{PLACEHOLDER_PREFIX}ws_user_unbind_api")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
@system_log(LogConfig(operation_type=OperationType.DELETE, module=OperationModules.MEMBER, resource_id_expr="dto.uid_list",
                      ))
async def delete(session: SessionDep, current_user: CurrentUser, trans: Trans, dto: UserWsBase):
    if not current_user.isAdmin and current_user.weight == 0:
        raise Exception(trans('i18n_permission.no_permission', url = '', msg = ''))
    oid: int = dto.oid if (current_user.isAdmin and dto.oid) else current_user.oid
    db_model_list: list[UserWsModel] = session.exec(select(UserWsModel).where(UserWsModel.uid.in_(dto.uid_list), UserWsModel.oid == oid)).all()
    if not db_model_list:
        raise HTTPException(f"UserWsModel not found")
    for db_model in db_model_list:
        session.delete(db_model)
    
    for uid in dto.uid_list:
        await reset_single_user_oid(session, uid, oid, False)
        await clean_user_cache(uid)
        
@router.get("", response_model=list[WorkspaceModel], summary=f"{PLACEHOLDER_PREFIX}ws_all_api", description=f"{PLACEHOLDER_PREFIX}ws_all_api")
@require_permissions(permission=SqlbotPermission(role=['admin'])) 
async def query(session: SessionDep, trans: Trans):
    list_result = session.exec(select(WorkspaceModel)).all()
    for ws in list_result:
        if ws.name.startswith('i18n'):
            ws.name = trans(ws.name)
    list_result.sort(key=lambda x: x.name)
    return list_result

@router.post("", summary=f"{PLACEHOLDER_PREFIX}ws_create_api", description=f"{PLACEHOLDER_PREFIX}ws_create_api")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.CREATE, module=OperationModules.WORKSPACE, result_id_expr="id",
                      ))
async def add(session: SessionDep, creator: WorkspaceBase):
    db_model = WorkspaceModel.model_validate(creator)
    db_model.create_time = get_timestamp()
    session.add(db_model)
    return db_model
    
@router.put("", summary=f"{PLACEHOLDER_PREFIX}ws_update_api", description=f"{PLACEHOLDER_PREFIX}ws_update_api")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.WORKSPACE, resource_id_expr="editor.id",
                      ))
async def update(session: SessionDep, editor: WorkspaceEditor):
    id = editor.id
    db_model = session.get(WorkspaceModel, id)
    if not db_model:
        raise HTTPException(f"WorkspaceModel with id {id} not found")
    db_model.name = editor.name
    session.add(db_model)

@router.get("/{id}", response_model=WorkspaceModel, summary=f"{PLACEHOLDER_PREFIX}ws_query_api", description=f"{PLACEHOLDER_PREFIX}ws_query_api")
@require_permissions(permission=SqlbotPermission(role=['admin']))    
async def get_one(session: SessionDep, trans: Trans, id: int = Path(description=f"{PLACEHOLDER_PREFIX}oid")):
    db_model = session.get(WorkspaceModel, id)
    if not db_model:
        raise HTTPException(f"WorkspaceModel with id {id} not found")
    if db_model.name.startswith('i18n'):
        db_model.name = trans(db_model.name)
    return db_model

@router.delete("/{id}", summary=f"{PLACEHOLDER_PREFIX}ws_del_api", description=f"{PLACEHOLDER_PREFIX}ws_del_api")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.DELETE, module=OperationModules.WORKSPACE, resource_id_expr="id",
                      ))
async def single_delete(session: SessionDep, current_user: CurrentUser, id: int = Path(description=f"{PLACEHOLDER_PREFIX}oid")):
    if not current_user.isAdmin:
        raise HTTPException("only admin can delete workspace")
    if id == 1:
        raise HTTPException(f"Can not delete default workspace")
    db_model = session.get(WorkspaceModel, id)
    if not db_model:
        raise HTTPException(f"WorkspaceModel with id {id} not found")
    
    if current_user.oid == id:
            current_user.oid = 1  # reset to default workspace
            update_stmt = sqlmodel_update(UserModel).where(UserModel.id == current_user.id).values(oid=1)
            session.exec(update_stmt)
            await clean_user_cache(current_user.id)
    
    user_ws_list = session.exec(select(UserWsModel).where(UserWsModel.oid == id)).all()
    if user_ws_list:
        # clean user cache
        for user_ws in user_ws_list:
            await clean_user_cache(user_ws.uid)
        # reset user default oid
        await reset_user_oid(session, id)
        # delete user_ws
        session.exec(sqlmodel_delete(UserWsModel).where(UserWsModel.oid == id))
        
    session.delete(db_model)


