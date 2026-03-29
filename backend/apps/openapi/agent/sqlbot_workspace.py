"""Data Agent 本地工作区：可配置 SQLBOT_HOME、与 skills/run.sh 相同的落盘布局。"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from sqlmodel import Session

from apps.datasource.crud.datasource import (
    get_datasource_list_for_openapi,
    get_table_obj_by_ds,
    get_table_schema,
)
from apps.datasource.models.datasource import CoreDatasource
from apps.db.db import exec_sql
from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id
from apps.openapi.models.openapiModels import DataSourceRequest
from apps.openapi.service.openapi_service import is_safe_sql
from apps.terminology.curd.terminology import get_terminology_template
from common.core.config import settings
from common.core.deps import CurrentUser
from common.error import ParseSQLResultError

_AGENT_FILE = Path(__file__).resolve()


def repo_root_path() -> Path:
    """SQLBot 仓库根目录（含 .claude/skills 的上一级）。"""
    # backend/apps/openapi/agent/sqlbot_workspace.py -> parents[4] == repo root
    return _AGENT_FILE.parents[4]


def sqlbot_root_path() -> Path:
    raw = (getattr(settings, "SQLBOT_HOME", None) or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".sqlbot").resolve()


def skills_container_dir() -> Path:
    """DeepAgents `skills=` 目录：内含多个技能子目录（各含 SKILL.md）。"""
    raw = (getattr(settings, "DATA_AGENT_SKILL_ROOT", None) or "").strip()
    if raw:
        root = Path(raw).expanduser().resolve()
        if (root / "SKILL.md").is_file():
            return root.parent
        return root
    return (repo_root_path() / ".claude" / "skills").resolve()


def data_explorer_skill_dir() -> Path:
    """LocalShellBackend root_dir：默认同 Claude Code，使用 <skills>/data-explorer。"""
    container = skills_container_dir()
    dex = container / "data-explorer"
    if dex.is_dir():
        return dex
    return container


def skills_middleware_dir() -> Path:
    """与 skills_container_dir 相同：始终指向技能集合根目录。"""
    return skills_container_dir()


def workspace_uid(user: CurrentUser) -> str:
    acc = (getattr(user, "account", None) or "").strip()
    if not acc:
        return str(user.id)
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", acc)
    safe = safe.strip("._-") or str(user.id)
    return safe[:120]


def user_dir(uid: str) -> Path:
    return sqlbot_root_path() / uid


def ensure_user_workspace(uid: str) -> Path:
    d = user_dir(uid)
    (d / "exports").mkdir(parents=True, exist_ok=True)
    (d / "permissions").mkdir(parents=True, exist_ok=True)
    return d


def write_agent_config(uid: str, api_base: str, token: str) -> None:
    """供 CLI run.sh 与 Agent 共用：写入 config.json（不含密码；token 与 getToken 一致带 bearer 前缀）。"""
    d = ensure_user_workspace(uid)
    host = api_base.rstrip("/")
    tok = token.strip()
    if not tok.lower().startswith("bearer "):
        tok = f"bearer {tok}"
    cfg = {"host": host, "token": tok}
    with open(d / "config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def write_permissions(
    session: Session, user: CurrentUser, uid: str
) -> list[dict[str, Any]]:
    rows = get_datasource_list_for_openapi(session=session, user=user)
    payload = [
        {
            "id": str(r.id),
            "name": r.name,
            "type": r.type,
            "type_name": r.type_name,
            "description": r.description or "",
        }
        for r in rows
    ]
    d = ensure_user_workspace(uid)
    with open(d / "permissions" / "datasources.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def _ds_index(ds: CoreDatasource) -> dict[str, Any]:
    return {
        "id": ds.id,
        "name": ds.name,
        "type": ds.type,
        "type_name": ds.type_name,
        "description": ds.description or "",
        "status": ds.status,
    }


def sync_datasource_to_disk(
    session: Session, user: CurrentUser, uid: str, db_id: int
) -> dict[str, Any]:
    """L1/L2 schema + 术语 + 关系落盘（对齐原 run.sh pull-index / pull-semantic / pull-relations）。"""
    ds = get_datasource_by_name_or_id(
        session=session, user=user, query=DataSourceRequest(id=int(db_id))
    )
    if ds is None:
        return {"ok": False, "error": f"数据源 {db_id} 未找到或无权访问"}

    base = ensure_user_workspace(uid)
    sid = str(db_id)
    schema_dir = base / "schema" / sid
    sem_dir = base / "semantic" / sid
    rel_dir = base / "relations" / sid
    schema_dir.mkdir(parents=True, exist_ok=True)
    sem_dir.mkdir(parents=True, exist_ok=True)
    rel_dir.mkdir(parents=True, exist_ok=True)

    schema_str = get_table_schema(
        session=session, current_user=user, ds=ds, question="", embedding=False
    )
    table_objs = get_table_obj_by_ds(session=session, current_user=user, ds=ds)
    summary = [
        {"id": obj.table.id, "table": obj.table.table_name} for obj in table_objs
    ]

    with open(schema_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump(_ds_index(ds), f, ensure_ascii=False, indent=2)
    with open(schema_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(schema_dir / "full_table_schema.txt", "w", encoding="utf-8") as f:
        f.write(schema_str or "")

    terms_str, terms_list = get_terminology_template(
        session=session,
        question="",
        oid=user.oid if user.oid is not None else 1,
        datasource=int(ds.id),
    )
    with open(sem_dir / "terminologies.txt", "w", encoding="utf-8") as f:
        f.write(terms_str or "")

    def _term_dump(t: Any) -> Any:
        if isinstance(t, dict):
            return t
        md = getattr(t, "model_dump", None)
        if callable(md):
            return md()
        return str(t)

    with open(sem_dir / "terminologies.json", "w", encoding="utf-8") as f:
        json.dump([_term_dump(t) for t in terms_list], f, ensure_ascii=False, indent=2)

    rel = ds.table_relation if getattr(ds, "table_relation", None) else []
    with open(rel_dir / "table_relations.json", "w", encoding="utf-8") as f:
        json.dump(rel or [], f, ensure_ascii=False, indent=2)

    return {
        "ok": True,
        "datasource_id": db_id,
        "name": ds.name,
        "tables": len(summary),
        "schema_dir": str(schema_dir),
    }


def safe_export_filename(name: str) -> str:
    name = (name or "result").strip()
    if not name.lower().endswith(".csv"):
        name += ".csv"
    base = Path(name).name
    if not base or ".." in name or "/" in name or "\\" in name:
        raise ValueError("非法的文件名")
    if not re.match(r"^[a-zA-Z0-9._-]+\.csv$", base):
        raise ValueError("文件名仅允许字母数字、._- 且须为 .csv")
    return base


def sql_result_to_csv_bytes(fields: list[str], rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=fields, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fields})
    return buf.getvalue().encode("utf-8-sig")


def execute_sql_to_csv(
    session: Session,
    user: CurrentUser,
    uid: str,
    db_id: int,
    sql: str,
    output_filename: str,
    max_preview_rows: int = 8,
) -> dict[str, Any]:
    if not sql or not sql.strip():
        return {"ok": False, "error": "SQL 为空"}
    sql = sql.strip()
    if not is_safe_sql(sql):
        return {"ok": False, "error": "SQL 未通过安全校验（仅允许只读查询）"}

    ds = get_datasource_by_name_or_id(
        session=session, user=user, query=DataSourceRequest(id=int(db_id))
    )
    if ds is None:
        return {"ok": False, "error": f"数据源 {db_id} 未找到或无权访问"}

    try:
        result = exec_sql(ds=ds, sql=sql, origin_column=False)
    except (ParseSQLResultError, ValueError, Exception) as e:
        return {"ok": False, "error": str(e)}

    fields = list(result.get("fields") or [])
    data = result.get("data") or []
    fname = safe_export_filename(output_filename)
    export_dir = ensure_user_workspace(uid) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / fname
    path.write_bytes(sql_result_to_csv_bytes(fields, data))

    preview = data[:max_preview_rows]
    return {
        "ok": True,
        "path": str(path),
        "row_count": len(data),
        "columns": fields,
        "preview_rows": preview,
    }
