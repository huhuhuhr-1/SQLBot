"""
自定义提示词 CRUD API：分页、增删改查、导出。
与前端 /system/custom_prompt/* 约定一致，不依赖 xpack。
"""
from typing import Optional, List
import io

from fastapi import APIRouter, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from apps.system.schemas.permission import SqlbotPermission, require_permissions
from apps.system.crud import custom_prompt as crud
from common.core.deps import SessionDep, CurrentUser

router = APIRouter(tags=["System"], prefix="/system/custom_prompt")


class CustomPromptBody(BaseModel):
    id: Optional[int] = None
    type: Optional[str] = None
    name: Optional[str] = None
    prompt: Optional[str] = None
    specific_ds: Optional[bool] = False
    datasource_ids: Optional[List[int]] = Field(default_factory=list)
    is_full_template: Optional[bool] = False


def _row_to_dict(row) -> dict:
    return {
        "id": row.id,
        "oid": row.oid,
        "type": row.type,
        "create_time": row.create_time.isoformat() if row.create_time else None,
        "name": row.name,
        "prompt": row.prompt,
        "specific_ds": row.specific_ds,
        "datasource_ids": row.datasource_ids or [],
        "is_full_template": getattr(row, "is_full_template", False) or False,
    }


@router.get("/{type}/page/{page_num}/{page_size}", summary="分页查询自定义提示词")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def page(
    session: SessionDep,
    current_user: CurrentUser,
    type: str,
    page_num: int,
    page_size: int,
    name: Optional[str] = Query(None, description="名称筛选"),
):
    data, total_count = crud.page_list(
        session, current_user.oid, type, page_num, page_size, name=name
    )
    return {"data": [_row_to_dict(d) for d in data], "total_count": total_count}


@router.get("/{id}", summary="获取单条自定义提示词")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def get_one(session: SessionDep, current_user: CurrentUser, id: int):
    row = crud.get_one(session, id, current_user.oid)
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")
    return _row_to_dict(row)


@router.put("", summary="创建或更新自定义提示词")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def create_or_update(session: SessionDep, current_user: CurrentUser, body: CustomPromptBody):
    data = body.model_dump()
    row = crud.create_or_update(session, current_user.oid, data)
    return _row_to_dict(row)


@router.delete("", summary="批量删除自定义提示词")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def delete_ids(session: SessionDep, current_user: CurrentUser, id_list: List[int] = Body(..., embed=False)):
    crud.delete_by_ids(session, current_user.oid, id_list)


@router.get("/{type}/export", summary="导出自定义提示词")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def export_excel(
    session: SessionDep,
    current_user: CurrentUser,
    type: str,
    name: Optional[str] = Query(None),
):
    rows = crud.list_for_export(session, current_user.oid, type, name=name)
    try:
        import pandas as pd
        data_list = [
            {"name": r.name, "prompt": r.prompt or "", "specific_ds": r.specific_ds, "datasource_ids": r.datasource_ids or []}
            for r in rows
        ]
        df = pd.DataFrame(data_list)
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=custom_prompt_{type}.xlsx"},
        )
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"detail": "Export failed"}, status_code=500)
