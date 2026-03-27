from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, func, or_
from sqlmodel import select

from apps.dict.models.dict_model import (
    BizDict,
    BizDictBinding,
    BizDictItem,
    BizDictBindingRow,
    BizDictBindingSave,
    BizDictDetail,
    BizDictItemInfo,
    BizDictListRow,
    BizDictSave,
)
from apps.datasource.models.datasource import CoreDatasource
from common.core.deps import SessionDep, Trans


def _get_ds_or_404(session: SessionDep, ds_id: int, oid: int) -> CoreDatasource:
    ds = session.get(CoreDatasource, ds_id)
    if not ds or ds.oid != oid:
        raise HTTPException(status_code=404, detail="Datasource not found")
    return ds


def page_dict(
    session: SessionDep,
    current_page: int,
    page_size: int,
    keyword: Optional[str],
    oid: int,
) -> Tuple[int, int, int, int, List[BizDictListRow]]:
    page_size = max(10, page_size)
    base = select(BizDict).where(BizDict.oid == oid)
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        base = base.where(
            or_(BizDict.name.ilike(kw), BizDict.code.ilike(kw), BizDict.description.ilike(kw))
        )
    count_stmt = select(func.count()).select_from(base.subquery())
    total_count = session.execute(count_stmt).scalar() or 0
    total_pages = (total_count + page_size - 1) // page_size if total_count else 0
    current_page = max(1, min(current_page, total_pages)) if total_pages else 1

    stmt = (
        base.order_by(BizDict.create_time.desc())
        .offset((current_page - 1) * page_size)
        .limit(page_size)
    )
    rows = session.exec(stmt).all()
    out: List[BizDictListRow] = []
    for d in rows:
        cnt = session.execute(
            select(func.count()).select_from(BizDictItem).where(BizDictItem.dict_id == d.id)
        ).scalar() or 0
        out.append(
            BizDictListRow(
                id=d.id,
                name=d.name,
                code=d.code,
                description=d.description,
                enabled=d.enabled,
                create_time=d.create_time,
                item_count=int(cnt),
            )
        )
    return current_page, page_size, int(total_count), total_pages, out


def get_dict_detail(session: SessionDep, dict_id: int, oid: int) -> BizDictDetail:
    d = session.get(BizDict, dict_id)
    if not d or d.oid != oid:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    items = session.exec(
        select(BizDictItem)
        .where(BizDictItem.dict_id == dict_id)
        .order_by(BizDictItem.sort, BizDictItem.item_code)
    ).all()
    return BizDictDetail(
        id=d.id,
        name=d.name,
        code=d.code,
        description=d.description,
        enabled=d.enabled,
        create_time=d.create_time,
        items=[
            BizDictItemInfo(
                id=i.id,
                item_code=i.item_code,
                item_name=i.item_name,
                sort=i.sort,
                enabled=i.enabled,
            )
            for i in items
        ],
    )


def save_dict(session: SessionDep, info: BizDictSave, oid: int, trans: Trans) -> int:
    code = (info.code or "").strip()
    name = (info.name or "").strip()
    if not code or not name:
        raise HTTPException(status_code=400, detail=trans("i18n_dict.code_name_required"))

    dup_stmt = select(BizDict).where(BizDict.oid == oid, BizDict.code == code)
    if info.id:
        dup_stmt = dup_stmt.where(BizDict.id != info.id)
    if session.exec(dup_stmt).first():
        raise HTTPException(status_code=400, detail=trans("i18n_dict.code_exists"))

    now = datetime.utcnow()
    if info.id:
        d = session.get(BizDict, info.id)
        if not d or d.oid != oid:
            raise HTTPException(status_code=404, detail="Dictionary not found")
        d.name = name
        d.code = code
        d.description = info.description
        d.enabled = info.enabled
        session.add(d)
        for row in session.exec(select(BizDictItem).where(BizDictItem.dict_id == d.id)).all():
            session.delete(row)
        session.flush()
        dict_id = d.id
    else:
        d = BizDict(
            oid=oid,
            name=name,
            code=code,
            description=info.description,
            enabled=info.enabled,
            create_time=now,
        )
        session.add(d)
        session.flush()
        session.refresh(d)
        dict_id = d.id

    for idx, it in enumerate(info.items or []):
        ic = (it.item_code or "").strip()
        if not ic:
            continue
        session.add(
            BizDictItem(
                dict_id=dict_id,
                item_code=ic,
                item_name=(it.item_name or "").strip() or ic,
                sort=it.sort if it.sort is not None else idx,
                enabled=it.enabled,
            )
        )
    session.commit()
    return dict_id


def delete_dict(session: SessionDep, id_list: List[int], oid: int):
    if not id_list:
        return
    for i in id_list:
        d = session.get(BizDict, i)
        if d and d.oid == oid:
            session.delete(d)
    session.commit()


def enable_dict(session: SessionDep, dict_id: int, enabled: bool, oid: int, trans: Trans):
    d = session.get(BizDict, dict_id)
    if not d or d.oid != oid:
        raise HTTPException(status_code=404, detail=trans("i18n_dict.not_found"))
    d.enabled = enabled
    session.add(d)
    session.commit()


def page_binding(
    session: SessionDep,
    current_page: int,
    page_size: int,
    oid: int,
    datasource_id: Optional[int] = None,
    dict_id: Optional[int] = None,
) -> Tuple[int, int, int, int, List[BizDictBindingRow]]:
    page_size = max(10, page_size)
    count_q = (
        select(func.count(BizDictBinding.id))
        .select_from(BizDictBinding)
        .join(BizDict, BizDict.id == BizDictBinding.dict_id)
        .join(CoreDatasource, CoreDatasource.id == BizDictBinding.datasource_id)
        .where(and_(BizDict.oid == oid, CoreDatasource.oid == oid))
    )
    if datasource_id is not None:
        count_q = count_q.where(BizDictBinding.datasource_id == datasource_id)
    if dict_id is not None:
        count_q = count_q.where(BizDictBinding.dict_id == dict_id)
    total_count = session.execute(count_q).scalar() or 0

    base = (
        select(BizDictBinding, BizDict, CoreDatasource.name)
        .join(BizDict, BizDict.id == BizDictBinding.dict_id)
        .join(CoreDatasource, CoreDatasource.id == BizDictBinding.datasource_id)
        .where(and_(BizDict.oid == oid, CoreDatasource.oid == oid))
    )
    if datasource_id is not None:
        base = base.where(BizDictBinding.datasource_id == datasource_id)
    if dict_id is not None:
        base = base.where(BizDictBinding.dict_id == dict_id)
    total_pages = (total_count + page_size - 1) // page_size if total_count else 0
    current_page = max(1, min(current_page, total_pages)) if total_pages else 1

    stmt = (
        base.order_by(BizDictBinding.id.desc())
        .offset((current_page - 1) * page_size)
        .limit(page_size)
    )
    raw = session.exec(stmt).all()
    out: List[BizDictBindingRow] = []
    for b, d, ds_name in raw:
        out.append(
            BizDictBindingRow(
                id=b.id,
                dict_id=b.dict_id,
                dict_name=d.name,
                dict_code=d.code,
                datasource_id=b.datasource_id,
                datasource_name=ds_name,
                table_name=b.table_name,
                column_name=b.column_name,
                enabled=b.enabled,
            )
        )
    return current_page, page_size, int(total_count), total_pages, out


def save_binding(session: SessionDep, info: BizDictBindingSave, oid: int, trans: Trans) -> int:
    _get_ds_or_404(session, info.datasource_id, oid)
    d = session.get(BizDict, info.dict_id)
    if not d or d.oid != oid:
        raise HTTPException(status_code=404, detail=trans("i18n_dict.not_found"))

    tn = (info.table_name or "").strip()
    cn = (info.column_name or "").strip()
    if not tn or not cn:
        raise HTTPException(status_code=400, detail=trans("i18n_dict.table_column_required"))

    if info.id:
        b = session.get(BizDictBinding, info.id)
        if not b:
            raise HTTPException(status_code=404, detail="Binding not found")
        bd = session.get(BizDict, b.dict_id)
        if not bd or bd.oid != oid:
            raise HTTPException(status_code=403, detail="Forbidden")
        dup = session.exec(
            select(BizDictBinding).where(
                BizDictBinding.datasource_id == info.datasource_id,
                BizDictBinding.table_name == tn,
                BizDictBinding.column_name == cn,
                BizDictBinding.id != info.id,
            )
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=trans("i18n_dict.binding_exists"))
        b.dict_id = info.dict_id
        b.datasource_id = info.datasource_id
        b.table_name = tn
        b.column_name = cn
        b.enabled = info.enabled
        session.add(b)
        session.commit()
        return b.id

    dup = session.exec(
        select(BizDictBinding).where(
            BizDictBinding.datasource_id == info.datasource_id,
            BizDictBinding.table_name == tn,
            BizDictBinding.column_name == cn,
        )
    ).first()
    if dup:
        raise HTTPException(status_code=400, detail=trans("i18n_dict.binding_exists"))

    b = BizDictBinding(
        dict_id=info.dict_id,
        datasource_id=info.datasource_id,
        table_name=tn,
        column_name=cn,
        enabled=info.enabled,
    )
    session.add(b)
    session.commit()
    session.refresh(b)
    return b.id


def delete_binding(session: SessionDep, id_list: List[int], oid: int):
    if not id_list:
        return
    for bid in id_list:
        b = session.get(BizDictBinding, bid)
        if not b:
            continue
        d = session.get(BizDict, b.dict_id)
        if d and d.oid == oid:
            session.delete(b)
    session.commit()


def list_dict_options(session: SessionDep, oid: int) -> List[dict]:
    rows = session.exec(
        select(BizDict.id, BizDict.name, BizDict.code)
        .where(BizDict.oid == oid, BizDict.enabled.is_(True))
        .order_by(BizDict.name)
    ).all()
    return [{"id": r[0], "name": r[1], "code": r[2]} for r in rows]
