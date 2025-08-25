import datetime
from typing import List, Optional

from sqlalchemy import and_, or_, select, func, delete, update
from sqlalchemy.orm import aliased

from apps.terminology.models.terminology_model import Terminology, TerminologyInfo
from common.core.deps import SessionDep


def page_terminology(session: SessionDep, current_page: int = 1, page_size: int = 10, name: Optional[str] = None):
    _list: List[TerminologyInfo] = []

    child = aliased(Terminology)

    current_page = max(1, current_page)
    page_size = max(10, page_size)

    total_count = 0
    total_pages = 0

    if name and name.strip() != "":
        keyword_pattern = f"%{name.strip()}%"
        # 步骤1：先找到所有匹配的节点ID（无论是父节点还是子节点）
        matched_ids_subquery = (
            select(Terminology.id)
            .where(Terminology.word.like(keyword_pattern))  # LIKE查询条件
            .subquery()
        )

        # 步骤2：找到这些匹配节点的所有父节点（包括自身如果是父节点）
        parent_ids_subquery = (
            select(Terminology.id)
            .where(
                (Terminology.id.in_(matched_ids_subquery)) |
                (Terminology.id.in_(
                    select(Terminology.pid)
                    .where(Terminology.id.in_(matched_ids_subquery))
                    .where(Terminology.pid.isnot(None))
                ))
            )
            .where(Terminology.pid.is_(None))  # 只取父节点
        )

        count_stmt = select(func.count()).select_from(parent_ids_subquery.subquery())
        total_count = session.execute(count_stmt).scalar()
        total_pages = (total_count + page_size - 1) // page_size

        # 步骤3：获取分页后的父节点ID
        paginated_parent_ids = (
            parent_ids_subquery
            .order_by(Terminology.create_time.desc())
            .offset((current_page - 1) * page_size)
            .limit(page_size)
            .subquery()
        )

        # 步骤4：获取这些父节点的childrenNames
        children_subquery = (
            select(
                child.pid,
                func.jsonb_agg(child.word).filter(child.word.isnot(None)).label('other_words')
            )
            .where(child.pid.isnot(None))
            .group_by(child.pid)
            .subquery()
        )

        # 主查询
        stmt = (
            select(
                Terminology.id,
                Terminology.word,
                Terminology.create_time,
                Terminology.description,
                children_subquery.c.other_words
            )
            .outerjoin(
                children_subquery,
                Terminology.id == children_subquery.c.pid
            )
            .where(Terminology.id.in_(paginated_parent_ids))
            .order_by(Terminology.create_time.desc())
        )
        print(str(stmt))
    else:
        parent_ids_subquery = (
            select(Terminology.id)
            .where(Terminology.pid.is_(None))  # 只取父节点
        )
        count_stmt = select(func.count()).select_from(parent_ids_subquery.subquery())
        total_count = session.execute(count_stmt).scalar()
        total_pages = (total_count + page_size - 1) // page_size

        paginated_parent_ids = (
            parent_ids_subquery
            .order_by(Terminology.create_time.desc())
            .offset((current_page - 1) * page_size)
            .limit(page_size)
            .subquery()
        )

        stmt = (
            select(
                Terminology.id,
                Terminology.word,
                Terminology.create_time,
                Terminology.description,
                func.jsonb_agg(child.word).filter(child.word.isnot(None)).label('other_words')
            )
            .outerjoin(child, and_(Terminology.id == child.pid))
            .where(Terminology.id.in_(paginated_parent_ids))
            .group_by(Terminology.id, Terminology.word)
            .order_by(Terminology.create_time.desc())
        )
        print(str(stmt))

    result = session.execute(stmt)

    for row in result:
        _list.append(TerminologyInfo(
            id=row.id,
            word=row.word,
            create_time=row.create_time,
            description=row.description,
            other_words=row.other_words if row.other_words else [],
        ))

    return current_page, page_size, total_count, total_pages, _list


def create_terminology(session: SessionDep, info: TerminologyInfo):
    create_time = datetime.datetime.now()
    parent = Terminology(word=info.word, create_time=create_time, description=info.description)

    result = Terminology(**parent.model_dump())

    session.add(parent)
    session.flush()
    session.refresh(parent)

    result.id = parent.id
    session.commit()

    _list: List[Terminology] = []
    if info.other_words:
        for other_word in info.other_words:
            _list.append(
                Terminology(pid=result.id, word=other_word, create_time=create_time))
    session.bulk_save_objects(_list)
    session.flush()
    session.commit()

    # todo embedding

    return result.id


def update_terminology(session: SessionDep, info: TerminologyInfo):
    stmt = update(Terminology).where(and_(Terminology.id == info.id)).values(
        word=info.word,
        description=info.description,
    )
    session.execute(stmt)
    session.commit()

    stmt = delete(Terminology).where(and_(Terminology.pid == info.id))
    session.execute(stmt)
    session.commit()

    create_time = datetime.datetime.now()
    _list: List[Terminology] = []
    if info.other_words:
        for other_word in info.other_words:
            _list.append(
                Terminology(pid=info.id, word=other_word, create_time=create_time))
    session.bulk_save_objects(_list)
    session.flush()
    session.commit()

    # todo embedding

    return info.id


def delete_terminology(session: SessionDep, ids: list[int]):
    stmt = delete(Terminology).where(or_(Terminology.id.in_(ids), Terminology.pid.in_(ids)))
    session.execute(stmt)
    session.commit()
