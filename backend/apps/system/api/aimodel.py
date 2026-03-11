import json
from typing import List, Union, Optional

from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Path, Query, Body
from pydantic import BaseModel
from apps.ai_model.model_factory import LLMConfig, LLMFactory
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.ai_model_schema import (
    AiModelConfigItem, AiModelCreator, AiModelEditor, AiModelGridItem,
    AiModelExportItem, AiModelExportPayload,
)
from sqlmodel import func, select, update

from apps.system.models.system_model import AiModelDetail
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.deps import SessionDep, Trans
from common.utils.crypto import sqlbot_decrypt
from common.utils.time import get_timestamp
from common.utils.utils import SQLBotLogUtil, prepare_model_arg

router = APIRouter(tags=["system_model"], prefix="/system/aimodel")
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import LogConfig, system_log

@router.post("/status", include_in_schema=False)
@require_permissions(permission=SqlbotPermission(role=['admin'])) 
async def check_llm(info: AiModelCreator, trans: Trans):
    async def generate():
        try:
            additional_params = {item.key: prepare_model_arg(item.val) for item in info.config_list if item.key and item.val}
            config = LLMConfig(
                model_type="openai" if info.protocol == 1 else "vllm",
                model_name=info.base_model,
                api_key=info.api_key,
                api_base_url=info.api_domain,
                additional_params=additional_params,
            )
            llm_instance = LLMFactory.create_llm(config)
            async for chunk in llm_instance.llm.astream("1+1=?"):
                SQLBotLogUtil.info(chunk)
                if chunk and isinstance(chunk, str):
                    yield json.dumps({"content": chunk}) + "\n"
                if chunk and isinstance(chunk, dict) and chunk.content:
                    yield json.dumps({"content": chunk.content}) + "\n"
        
        except Exception as e:
            SQLBotLogUtil.error(f"Error checking LLM: {e}")
            error_msg = trans('i18n_llm.validate_error', msg=str(e))
            yield json.dumps({"error": error_msg}) + "\n"
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")

@router.get("/default", include_in_schema=False)
async def check_default(session: SessionDep, trans: Trans):
    db_model = session.exec(
        select(AiModelDetail).where(AiModelDetail.default_model == True)
    ).first()
    if not db_model:
        raise Exception(trans('i18n_llm.miss_default'))
    
@router.put("/default/{id}", summary=f"{PLACEHOLDER_PREFIX}system_model_default", description=f"{PLACEHOLDER_PREFIX}system_model_default")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.AI_MODEL, resource_id_expr="id"))
async def set_default(session: SessionDep, id: int = Path(description="ID")):
    db_model = session.get(AiModelDetail, id)
    if not db_model:
        raise ValueError(f"AiModelDetail with id {id} not found")
    if db_model.default_model:
        return

    try:
        session.exec(
            update(AiModelDetail).values(default_model=False)
        )
        db_model.default_model = True
        session.add(db_model)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e

@router.get("", response_model=list[AiModelGridItem], summary=f"{PLACEHOLDER_PREFIX}system_model_grid", description=f"{PLACEHOLDER_PREFIX}system_model_grid")
@require_permissions(permission=SqlbotPermission(role=['admin'])) 
async def query(
        session: SessionDep,
        keyword: Union[str, None] = Query(default=None, max_length=255, description=f"{PLACEHOLDER_PREFIX}keyword")
):
    statement = select(AiModelDetail.id, 
                       AiModelDetail.name, 
                       AiModelDetail.model_type, 
                       AiModelDetail.base_model, 
                       AiModelDetail.supplier,
                       AiModelDetail.protocol, 
                       AiModelDetail.default_model)
    if keyword is not None:
        statement = statement.where(AiModelDetail.name.like(f"%{keyword}%"))
    statement = statement.order_by(AiModelDetail.default_model.desc(), AiModelDetail.name, AiModelDetail.create_time)
    items = session.exec(statement).all()
    return items


class AiModelExportRequest(BaseModel):
    """批量导出 AI 模型：请求体为要导出的模型 id 列表，空则导出全部"""
    ids: Optional[List[int]] = None


@router.post("/export", response_model=AiModelExportPayload, summary="批量导出 AI 模型配置",
             description="导出 AI 模型配置（含 api_domain/api_key 解密后导出，便于迁移或备份）。")
@require_permissions(permission=SqlbotPermission(role=['admin']))
async def export_aimodels(
    session: SessionDep,
    body: AiModelExportRequest = Body(default=None),
):
    ids = body.ids if body and body.ids else None
    if ids is not None and len(ids) == 0:
        items = []
    else:
        stmt = select(AiModelDetail).order_by(AiModelDetail.default_model.desc(), AiModelDetail.name)
        if ids:
            stmt = stmt.where(AiModelDetail.id.in_(ids))
        rows = session.exec(stmt).all()
        items = []
        for db_model in rows:
            config_list: List[AiModelConfigItem] = []
            if db_model.config:
                try:
                    raw = json.loads(db_model.config)
                    config_list = [AiModelConfigItem(**item) for item in raw]
                except Exception:
                    pass
            try:
                api_key = await sqlbot_decrypt(db_model.api_key) if db_model.api_key else ""
                api_domain = await sqlbot_decrypt(db_model.api_domain) if db_model.api_domain else ""
            except Exception:
                api_key = db_model.api_key or ""
                api_domain = db_model.api_domain or ""
            items.append(
                AiModelExportItem(
                    name=db_model.name,
                    model_type=db_model.model_type,
                    base_model=db_model.base_model,
                    supplier=db_model.supplier,
                    protocol=db_model.protocol,
                    default_model=db_model.default_model,
                    api_domain=api_domain,
                    api_key=api_key or "",
                    config_list=config_list,
                )
            )
    return AiModelExportPayload(version=1, models=items)


@router.post("/import", summary="批量导入 AI 模型配置",
             description="从导出的 JSON 批量导入，合并模式：同名称则更新，否则新建，不报错。")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.CREATE, module=OperationModules.AI_MODEL))
async def import_aimodels(
    session: SessionDep,
    body: AiModelExportPayload = Body(...),
):
    result = []
    for item in body.models or []:
        if not item.name:
            continue
        try:
            existing = session.exec(
                select(AiModelDetail).where(AiModelDetail.name == item.name)
            ).first()
            config_json = json.dumps([c.model_dump(exclude_unset=True) for c in (item.config_list or [])])
            if existing:
                existing.model_type = item.model_type
                existing.base_model = item.base_model
                existing.supplier = item.supplier
                existing.protocol = item.protocol
                existing.api_domain = item.api_domain or ""
                existing.api_key = item.api_key or ""
                existing.config = config_json
                session.add(existing)
                session.commit()
                session.refresh(existing)
                result.append(existing)
            else:
                data = {
                    "name": item.name,
                    "model_type": item.model_type,
                    "base_model": item.base_model,
                    "supplier": item.supplier,
                    "protocol": item.protocol,
                    "default_model": False,
                    "api_domain": item.api_domain or "",
                    "api_key": item.api_key or "",
                    "config": config_json,
                }
                detail = AiModelDetail.model_validate(data)
                detail.create_time = get_timestamp()
                count = session.exec(select(func.count(AiModelDetail.id))).one()
                if count == 0:
                    detail.default_model = True
                session.add(detail)
                session.commit()
                session.refresh(detail)
                result.append(detail)
        except Exception as e:
            SQLBotLogUtil.warning(f"import_aimodels skip {item.name}: {e}")
            continue
    return result


@router.get("/{id}", response_model=AiModelEditor, summary=f"{PLACEHOLDER_PREFIX}system_model_query", description=f"{PLACEHOLDER_PREFIX}system_model_query")
@require_permissions(permission=SqlbotPermission(role=['admin'])) 
async def get_model_by_id(
        session: SessionDep,
        id: int = Path(description="ID")
):
    db_model = session.get(AiModelDetail, id)
    if not db_model:
        raise ValueError(f"AiModelDetail with id {id} not found")

    config_list: List[AiModelConfigItem] = []
    if db_model.config:
        try:
            raw = json.loads(db_model.config)
            config_list = [AiModelConfigItem(**item) for item in raw]
        except Exception:
            pass
    try:
        if db_model.api_key:
            db_model.api_key = await sqlbot_decrypt(db_model.api_key)
        if db_model.api_domain:
            db_model.api_domain = await sqlbot_decrypt(db_model.api_domain)
    except Exception:
        pass
    data = AiModelDetail.model_validate(db_model).model_dump(exclude_unset=True)
    data.pop("config", None)
    data["config_list"] = config_list
    return AiModelEditor(**data)

@router.post("", summary=f"{PLACEHOLDER_PREFIX}system_model_create", description=f"{PLACEHOLDER_PREFIX}system_model_create")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.CREATE, module=OperationModules.AI_MODEL, result_id_expr="id"))
async def add_model(
        session: SessionDep,
        creator: AiModelCreator
):
    data = creator.model_dump(exclude_unset=True)
    data["config"] = json.dumps([item.model_dump(exclude_unset=True) for item in creator.config_list])
    data.pop("config_list", None)
    detail = AiModelDetail.model_validate(data)
    detail.create_time = get_timestamp()
    count = session.exec(select(func.count(AiModelDetail.id))).one()
    if count == 0:
        detail.default_model = True
    session.add(detail)
    session.commit()
    return detail

@router.put("", summary=f"{PLACEHOLDER_PREFIX}system_model_update", description=f"{PLACEHOLDER_PREFIX}system_model_update")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.AI_MODEL, resource_id_expr="editor.id"))
async def update_model(
        session: SessionDep,
        editor: AiModelEditor
):
    id = int(editor.id)
    data = editor.model_dump(exclude_unset=True)
    data["config"] = json.dumps([item.model_dump(exclude_unset=True) for item in editor.config_list])
    data.pop("config_list", None)
    db_model = session.get(AiModelDetail, id)
    #update_data = AiModelDetail.model_validate(data)
    db_model.sqlmodel_update(data)
    session.add(db_model)
    session.commit()

@router.delete("/{id}", summary=f"{PLACEHOLDER_PREFIX}system_model_del", description=f"{PLACEHOLDER_PREFIX}system_model_del")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.DELETE, module=OperationModules.AI_MODEL, resource_id_expr="id"))
async def delete_model(
        session: SessionDep,
        trans: Trans,
        id: int = Path(description="ID")
):
    item = session.get(AiModelDetail, id)
    if item.default_model:
        raise Exception(trans('i18n_llm.delete_default_error', key=item.name))
    session.delete(item)
    session.commit()
