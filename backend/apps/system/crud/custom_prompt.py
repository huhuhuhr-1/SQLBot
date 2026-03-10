"""
自定义提示词 CRUD，使用表 custom_prompt，不依赖 xpack。
"""
from datetime import datetime
from typing import List, Optional, Tuple

from sqlmodel import Session, select, func
from sqlalchemy import and_

from apps.system.models.custom_prompt_model import CustomPrompt


def page_list(
    session: Session,
    oid: int,
    type_: str,
    page_num: int,
    page_size: int,
    name: Optional[str] = None,
) -> Tuple[List[CustomPrompt], int]:
    """分页查询，返回 (data, total_count)。"""
    base = select(CustomPrompt).where(
        and_(CustomPrompt.oid == oid, CustomPrompt.type == type_)
    )
    if name and name.strip():
        base = base.where(CustomPrompt.name.ilike(f"%{name.strip()}%"))

    count_stmt = select(func.count(CustomPrompt.id)).where(
        and_(CustomPrompt.oid == oid, CustomPrompt.type == type_)
    )
    if name and name.strip():
        count_stmt = count_stmt.where(CustomPrompt.name.ilike(f"%{name.strip()}%"))
    total = session.exec(count_stmt).one() or 0

    offset_val = max(0, (page_num - 1) * page_size) if page_num >= 1 else 0
    stmt = base.order_by(CustomPrompt.create_time.desc()).offset(offset_val).limit(page_size)
    rows = list(session.exec(stmt).all())
    return rows, total


def get_one(session: Session, id_: int, oid: int) -> Optional[CustomPrompt]:
    """按 id 和 oid 取一条。"""
    stmt = select(CustomPrompt).where(and_(CustomPrompt.id == id_, CustomPrompt.oid == oid))
    return session.exec(stmt).first()


def create_or_update(session: Session, oid: int, data: dict) -> CustomPrompt:
    """创建或更新一条，返回当前记录。"""
    id_ = data.get("id")
    if id_:
        row = get_one(session, int(id_), oid)
        if row:
            row.name = data.get("name") or row.name
            row.prompt = data.get("prompt") if data.get("prompt") is not None else row.prompt
            row.specific_ds = data.get("specific_ds") if data.get("specific_ds") is not None else row.specific_ds
            row.datasource_ids = data.get("datasource_ids") if data.get("datasource_ids") is not None else row.datasource_ids
            row.type = data.get("type") or row.type
            if "is_full_template" in data:
                row.is_full_template = data.get("is_full_template", False)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row
    row = CustomPrompt(
        oid=oid,
        type=data.get("type"),
        name=data.get("name"),
        prompt=data.get("prompt"),
        specific_ds=data.get("specific_ds", False),
        datasource_ids=data.get("datasource_ids") or [],
        is_full_template=data.get("is_full_template", False),
        create_time=datetime.utcnow(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_by_ids(session: Session, oid: int, ids: List[int]) -> None:
    """按 id 列表删除，仅允许删除本 oid 下的记录。"""
    stmt = select(CustomPrompt).where(
        and_(CustomPrompt.oid == oid, CustomPrompt.id.in_(ids))
    )
    for row in session.exec(stmt).all():
        session.delete(row)
    session.commit()


def list_for_export(session: Session, oid: int, type_: str, name: Optional[str] = None) -> List[CustomPrompt]:
    """导出用：按 type、可选 name 筛选。"""
    stmt = select(CustomPrompt).where(
        and_(CustomPrompt.oid == oid, CustomPrompt.type == type_)
    )
    if name and name.strip():
        stmt = stmt.where(CustomPrompt.name.ilike(f"%{name.strip()}%"))
    stmt = stmt.order_by(CustomPrompt.create_time.desc())
    return list(session.exec(stmt).all())


def build_rule_snippets(
    session: Session,
    oid: int,
    type_: str,
    ds_id: Optional[int] = None,
) -> Tuple[str, List[CustomPrompt]]:
    """
    根据 oid / type / ds_id 汇总适用的自定义提示词，并拼接为 <rule> 片段字符串。
    - specific_ds = False: 对工作空间下所有数据源生效
    - specific_ds = True: 仅当 ds_id 在 datasource_ids 中时生效
    返回 (规则字符串, 参与拼接的记录列表)
    """
    stmt = (
        select(CustomPrompt)
        .where(
            and_(
                CustomPrompt.oid == oid,
                CustomPrompt.type == type_,
            )
        )
        .order_by(CustomPrompt.create_time.desc())
    )
    rows: List[CustomPrompt] = []
    for row in session.exec(stmt).all():
        # 过滤掉完整模板类型：在新逻辑中不再使用
        if getattr(row, "is_full_template", False):
            continue
        # 没有限定数据源，或者当前数据源命中列表时生效
        if not row.specific_ds:
            rows.append(row)
        elif ds_id is not None and row.datasource_ids and ds_id in row.datasource_ids:
            rows.append(row)

    if not rows:
        return "", []

    rule_parts: List[str] = []
    for r in rows:
        if not r.prompt:
            continue
        # 将每条提示词包裹成一个 <rule> 块，避免破坏主模板结构
        rule_parts.append(f"<rule>{r.prompt}</rule>")

    rules_str = "\n".join(rule_parts) + "\n" if rule_parts else ""
    return rules_str, rows
