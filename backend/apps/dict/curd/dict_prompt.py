from collections import defaultdict
from typing import Dict, List, Tuple

from sqlalchemy import and_
from sqlmodel import select

from apps.dict.models.dict_model import BizDict, BizDictBinding, BizDictItem
from common.core.deps import SessionDep

MAX_ENUM_ITEMS_DEFAULT = 20


def _safe_enum_token(s: str) -> str:
    if not s:
        return ""
    return (
        str(s)
        .replace("|", "·")
        .replace("\n", " ")
        .strip()
    )


def format_field_line_with_enums(
    field_name: str,
    field_type: str,
    field_comment: str,
    enums: List[Tuple[str, str]],
    max_items: int = MAX_ENUM_ITEMS_DEFAULT,
) -> str:
    """Build one M-Schema field line; append enums:code=label|... when enums non-empty."""
    ft = (field_type or "").strip() or "unknown"
    fc = (field_comment or "").strip()
    if not enums:
        if fc == "":
            return f"({field_name}:{ft})"
        return f"({field_name}:{ft}, {fc})"
    slice_ = enums[:max_items]
    parts = []
    for code, label in slice_:
        c = _safe_enum_token(code)
        n = _safe_enum_token(label)
        if c == "":
            continue
        parts.append(f"{c}={n}" if n else c)
    if not parts:
        if fc == "":
            return f"({field_name}:{ft})"
        return f"({field_name}:{ft}, {fc})"
    enum_str = "|".join(parts)
    truncated = len(enums) > max_items
    if truncated:
        enum_str += "|...(truncated)"
    if fc == "":
        return f"({field_name}:{ft}, enums:{enum_str})"
    return f"({field_name}:{ft}, {fc}, enums:{enum_str})"


def load_enum_map(session: SessionDep, oid: int, datasource_id: int) -> Dict[Tuple[str, str], List[Tuple[str, str]]]:
    """
    Map (table_name, column_name) -> [(item_code, item_name), ...] for prompt injection.
    Exact match on table/column names as stored in bindings.
    """
    stmt = (
        select(
            BizDictBinding.table_name,
            BizDictBinding.column_name,
            BizDictItem.item_code,
            BizDictItem.item_name,
            BizDictItem.sort,
        )
        .select_from(BizDictBinding)
        .join(BizDict, BizDict.id == BizDictBinding.dict_id)
        .join(BizDictItem, BizDictItem.dict_id == BizDict.id)
        .where(
            and_(
                BizDict.oid == oid,
                BizDict.enabled.is_(True),
                BizDictBinding.datasource_id == datasource_id,
                BizDictBinding.enabled.is_(True),
                BizDictItem.enabled.is_(True),
            )
        )
        .order_by(
            BizDictBinding.table_name,
            BizDictBinding.column_name,
            BizDictItem.sort,
            BizDictItem.item_code,
        )
    )
    rows = session.exec(stmt).all()
    acc: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for table_name, column_name, item_code, item_name, _sort in rows:
        key = (table_name or "", column_name or "")
        if key[0] and key[1]:
            acc[key].append((item_code or "", item_name or ""))
    return dict(acc)
