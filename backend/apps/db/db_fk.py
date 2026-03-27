# Foreign key discovery for smart relation inference
from typing import List, Tuple, Optional

from sqlalchemy import text

from apps.datasource.models.datasource import CoreDatasource, DatasourceConf
from apps.db.db import get_session
from common.utils.utils import equals_ignore_case


def get_fk_sql(ds: CoreDatasource, conf: DatasourceConf) -> Optional[Tuple[str, str]]:
    """Return (sql, param) for FK query, or None if DB type does not support."""
    if equals_ignore_case(ds.type, "mysql", "doris", "starrocks"):
        sql = """
            SELECT
                kcu.TABLE_NAME AS table_name,
                kcu.COLUMN_NAME AS column_name,
                kcu.REFERENCED_TABLE_NAME AS ref_table_name,
                kcu.REFERENCED_COLUMN_NAME AS ref_column_name
            FROM information_schema.KEY_COLUMN_USAGE kcu
            WHERE kcu.TABLE_SCHEMA = :param
              AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        """
        return sql, conf.database or ""
    if equals_ignore_case(ds.type, "pg", "kingbase"):
        sql = """
            SELECT
                kcu.table_name AS table_name,
                kcu.column_name AS column_name,
                ccu.table_name AS ref_table_name,
                ccu.column_name AS ref_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = :param
        """
        return sql, conf.dbSchema or "public"
    return None


def get_fk_relations(ds: CoreDatasource) -> List[Tuple[str, str, str, str]]:
    """
    Query DB for foreign keys. Returns list of (table_name, column_name, ref_table_name, ref_column_name).
    Returns empty list on unsupported type or on error.
    """
    from apps.datasource.utils.utils import aes_decrypt
    import json
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if ds.type != "excel" else None
    if not conf or equals_ignore_case(ds.type, "excel"):
        return []
    sql_param = get_fk_sql(ds, conf)
    if not sql_param:
        return []
    sql, param = sql_param
    try:
        with get_session(ds) as session:
            with session.execute(text(sql), {"param": param}) as result:
                rows = result.fetchall()
                return [(str(r[0]), str(r[1]), str(r[2]), str(r[3])) for r in rows]
    except Exception:
        return []
