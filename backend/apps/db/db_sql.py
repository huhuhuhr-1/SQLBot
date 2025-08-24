# Author: Junjun
# Date: 2025/8/20
from apps.datasource.models.datasource import CoreDatasource, DatasourceConf


def get_table_sql(ds: CoreDatasource, conf: DatasourceConf):
    if ds.type == "mysql" or ds.type == "doris":
        return f"""
                SELECT 
                    TABLE_NAME, 
                    TABLE_COMMENT
                FROM 
                    information_schema.TABLES
                WHERE 
                    TABLE_SCHEMA = '{conf.database}'
                """
    elif ds.type == "sqlServer":
        return f"""
                SELECT 
                    TABLE_NAME AS [TABLE_NAME],
                    ISNULL(ep.value, '') AS [TABLE_COMMENT]
                FROM 
                    INFORMATION_SCHEMA.TABLES t
                LEFT JOIN 
                    sys.extended_properties ep 
                    ON ep.major_id = OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME)
                    AND ep.minor_id = 0 
                    AND ep.name = 'MS_Description' 
                WHERE 
                    t.TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                    AND t.TABLE_SCHEMA = '{conf.dbSchema}'
                """
    elif ds.type == "pg" or ds.type == "excel":
        return f"""
              SELECT c.relname                                       AS TABLE_NAME,
                     COALESCE(d.description, obj_description(c.oid)) AS TABLE_COMMENT
              FROM pg_class c
                       LEFT JOIN
                   pg_namespace n ON n.oid = c.relnamespace
                       LEFT JOIN
                   pg_description d ON d.objoid = c.oid AND d.objsubid = 0
              WHERE n.nspname = '{conf.dbSchema}'
                AND c.relkind IN ('r', 'v', 'p', 'm')
                AND c.relname NOT LIKE 'pg_%'
                AND c.relname NOT LIKE 'sql_%'
              ORDER BY c.relname \
              """
    elif ds.type == "oracle":
        return f"""
                SELECT 
                    t.TABLE_NAME AS "TABLE_NAME",
                    NVL(c.COMMENTS, '') AS "TABLE_COMMENT"
                FROM (
                    SELECT TABLE_NAME, 'TABLE' AS OBJECT_TYPE
                    FROM DBA_TABLES
                    WHERE OWNER = '{conf.dbSchema}'  
                    UNION ALL
                    SELECT VIEW_NAME AS TABLE_NAME, 'VIEW' AS OBJECT_TYPE
                    FROM DBA_VIEWS
                    WHERE OWNER = '{conf.dbSchema}'  
                ) t
                LEFT JOIN DBA_TAB_COMMENTS c 
                    ON t.TABLE_NAME = c.TABLE_NAME 
                    AND c.TABLE_TYPE = t.OBJECT_TYPE
                    AND c.OWNER = '{conf.dbSchema}'   
                ORDER BY t.TABLE_NAME
                """
    elif ds.type == "ck":
        return f"""
                SELECT name, comment
                FROM system.tables
                WHERE database = '{conf.database}'
                  AND engine NOT IN ('Dictionary')
                ORDER BY name
                """
    elif ds.type == 'dm':
        return f"""
                select table_name, comments 
                from all_tab_comments 
                where owner='{conf.dbSchema}'
                AND (table_type = 'TABLE' or table_type = 'VIEW')
                """


def get_field_sql(ds: CoreDatasource, conf: DatasourceConf, table_name: str = None):
    if ds.type == "mysql" or ds.type == "doris":
        sql1 = f"""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    COLUMN_COMMENT
                FROM 
                    INFORMATION_SCHEMA.COLUMNS
                WHERE 
                    TABLE_SCHEMA = '{conf.database}'
                """
        sql2 = f" AND TABLE_NAME = '{table_name}'" if table_name is not None and table_name != "" else ""
        return sql1 + sql2
    elif ds.type == "sqlServer":
        sql1 = f"""
                SELECT 
                    COLUMN_NAME AS [COLUMN_NAME],
                    DATA_TYPE AS [DATA_TYPE],
                    ISNULL(EP.value, '') AS [COLUMN_COMMENT]
                FROM 
                    INFORMATION_SCHEMA.COLUMNS C
                LEFT JOIN 
                    sys.extended_properties EP 
                    ON EP.major_id = OBJECT_ID(C.TABLE_SCHEMA + '.' + C.TABLE_NAME)
                    AND EP.minor_id = C.ORDINAL_POSITION
                    AND EP.name = 'MS_Description'
                WHERE 
                    C.TABLE_SCHEMA = '{conf.dbSchema}'
                """
        sql2 = f" AND C.TABLE_NAME = '{table_name}'" if table_name is not None and table_name != "" else ""
        return sql1 + sql2
    elif ds.type == "pg" or ds.type == "excel":
        sql1 = f"""
               SELECT a.attname                                       AS COLUMN_NAME,
                      pg_catalog.format_type(a.atttypid, a.atttypmod) AS DATA_TYPE,
                      col_description(c.oid, a.attnum)                AS COLUMN_COMMENT
               FROM pg_catalog.pg_attribute a
                        JOIN
                    pg_catalog.pg_class c ON a.attrelid = c.oid
                        JOIN
                    pg_catalog.pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = '{conf.dbSchema}'
                 AND a.attnum > 0
                 AND NOT a.attisdropped \
               """
        sql2 = f" AND c.relname = '{table_name}'" if table_name is not None and table_name != "" else ""
        return sql1 + sql2
    elif ds.type == "oracle":
        sql1 = f"""
                SELECT 
                    col.COLUMN_NAME AS "COLUMN_NAME",
                    (CASE 
                        WHEN col.DATA_TYPE IN ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR') 
                            THEN col.DATA_TYPE || '(' || col.DATA_LENGTH || ')' 
                        WHEN col.DATA_TYPE = 'NUMBER' AND col.DATA_PRECISION IS NOT NULL 
                            THEN col.DATA_TYPE || '(' || col.DATA_PRECISION || 
                                 CASE WHEN col.DATA_SCALE > 0 THEN ',' || col.DATA_SCALE END || ')' 
                        ELSE col.DATA_TYPE 
                    END) AS "DATA_TYPE",
                    NVL(com.COMMENTS, '') AS "COLUMN_COMMENT"
                FROM 
                    DBA_TAB_COLUMNS col
                LEFT JOIN 
                    DBA_COL_COMMENTS com 
                    ON col.OWNER = com.OWNER 
                    AND col.TABLE_NAME = com.TABLE_NAME 
                    AND col.COLUMN_NAME = com.COLUMN_NAME
                WHERE 
                    col.OWNER = '{conf.dbSchema}'
                """
        sql2 = f" AND col.TABLE_NAME = '{table_name}'" if table_name is not None and table_name != "" else ""
        return sql1 + sql2
    elif ds.type == "ck":
        sql1 = f"""
                SELECT 
                    name AS COLUMN_NAME,
                    type AS DATA_TYPE,
                    comment AS COLUMN_COMMENT
                FROM system.columns
                WHERE database = '{conf.database}'
                """
        sql2 = f" AND table = '{table_name}'" if table_name is not None and table_name != "" else ""
        return sql1 + sql2
    elif ds.type == 'dm':
        sql1 = f"""
                SELECT 
                    c.COLUMN_NAME    AS "COLUMN_NAME",
                    c.DATA_TYPE      AS "DATA_TYPE",
                    COALESCE(com.COMMENTS, '') AS "COMMENTS"
                FROM 
                    ALL_TAB_COLS c
                LEFT JOIN 
                    ALL_COL_COMMENTS com 
                    ON c.OWNER = com.OWNER 
                   AND c.TABLE_NAME = com.TABLE_NAME 
                   AND c.COLUMN_NAME = com.COLUMN_NAME
                WHERE 
                    c.OWNER = '{conf.dbSchema}'
                """
        sql2 = f" AND c.TABLE_NAME = '{table_name}'" if table_name is not None and table_name != "" else ""
        return sql1 + sql2
