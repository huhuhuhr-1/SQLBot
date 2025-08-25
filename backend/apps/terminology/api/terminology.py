from typing import Optional

from fastapi import APIRouter, Query

from apps.terminology.curd.terminology import page_terminology, create_terminology, update_terminology, \
    delete_terminology
from apps.terminology.models.terminology_model import TerminologyInfo
from common.core.deps import SessionDep

router = APIRouter(tags=["Terminology"], prefix="/system/terminology")


@router.get("/page/{current_page}/{page_size}")
async def pager(session: SessionDep, current_page: int, page_size: int,
                word: Optional[str] = Query(None, description="搜索术语(可选)")):
    current_page, page_size, total_count, total_pages, _list = page_terminology(session, current_page, page_size, word)

    return {
        "current_page": current_page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "data": _list
    }


@router.put("")
async def create_or_update(session: SessionDep, info: TerminologyInfo):
    if info.id:
        return update_terminology(session, info)
    else:
        return create_terminology(session, info)


@router.delete("")
async def delete(session: SessionDep, id_list: list[int]):
    delete_terminology(session, id_list)
