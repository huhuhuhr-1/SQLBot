#!/usr/bin/env python3
"""
SQL Executor Script
Executes SQL queries on various database types and returns results in JSON format.

Supported databases:
- MySQL
- PostgreSQL
- SQL Server
- Oracle
- ClickHouse
- Doris
- StarRocks
- Redshift
- DM (达梦)
- KingBase
- Elasticsearch
"""

import argparse
import json
import sys
from decimal import Decimal
from typing import Dict, List, Any, Optional


def execute_sql(
    db_type: str,
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
    sql: str,
    timeout: int = 30,
    db_schema: Optional[str] = None,
    extra_jdbc: Optional[str] = None,
    max_rows: Optional[int] = None,
    read_only: bool = True
) -> Dict[str, Any]:
    """
    Execute SQL query on the specified database.

    Args:
        db_type: Database type (mysql, pg, sqlServer, oracle, ck, doris, starrocks, redshift, dm, kingbase, es)
        host: Database host
        port: Database port
        username: Database username
        password: Database password
        database: Database name
        sql: SQL query to execute
        timeout: Query timeout in seconds (default: 30)
        db_schema: Database schema (for PostgreSQL)
        extra_jdbc: Extra JDBC connection parameters
        max_rows: Maximum number of rows to return
        read_only: If True, only allow SELECT queries

    Returns:
        Dictionary with keys:
        - fields: List of column names
        - data: List of row dictionaries
        - sql: Base64 encoded SQL query
        - row_count: Number of rows returned
    """
    # Import database drivers based on type
    try:
        if db_type.lower() in ["mysql", "doris", "starrocks"]:
            import pymysql
        elif db_type.lower() in ["pg", "kingbase"]:
            import psycopg2
        elif db_type.lower() == "sqlserver":
            import pymssql
        elif db_type.lower() == "oracle":
            import oracledb
        elif db_type.lower() == "ck":
            import clickhouse_connect
        elif db_type.lower() == "redshift":
            import redshift_connector
        elif db_type.lower() == "dm":
            import dmPython
        elif db_type.lower() == "es":
            # Elasticsearch uses HTTP client
            pass
        else:
            return {
                "success": False,
                "error": f"Unsupported database type: {db_type}",
                "supported_types": ["mysql", "pg", "sqlserver", "oracle", "ck", "doris", "starrocks", "redshift", "dm", "kingbase", "es"]
            }
    except ImportError as e:
        return {
            "success": False,
            "error": f"Database driver not installed: {str(e)}",
            "message": "Please install the required database driver"
        }

    # Validate SQL if read-only mode is enabled
    if read_only:
        validation = validate_sql_read_only(sql)
        if not validation["valid"]:
            return {
                "success": False,
                "error": "SQL validation failed",
                "details": validation["errors"]
            }

    # Execute query based on database type
    try:
        if db_type.lower() == "mysql":
            return _execute_mysql(host, port, username, password, database, sql, timeout, extra_jdbc, max_rows)
        elif db_type.lower() == "pg":
            return _execute_postgresql(host, port, username, password, database, sql, timeout, db_schema, extra_jdbc, max_rows)
        elif db_type.lower() == "sqlserver":
            return _execute_sqlserver(host, port, username, password, database, sql, timeout, extra_jdbc, max_rows)
        elif db_type.lower() in ["doris", "starrocks"]:
            return _execute_doris_starrocks(host, port, username, password, database, sql, timeout, extra_jdbc, max_rows)
        elif db_type.lower() == "ck":
            return _execute_clickhouse(host, port, username, password, database, sql, timeout, max_rows)
        elif db_type.lower() == "redshift":
            return _execute_redshift(host, port, username, password, database, sql, timeout, extra_jdbc, max_rows)
        elif db_type.lower() == "dm":
            return _execute_dm(host, port, username, password, database, sql, timeout, extra_jdbc, max_rows)
        elif db_type.lower() == "kingbase":
            return _execute_kingbase(host, port, username, password, database, sql, timeout, db_schema, extra_jdbc, max_rows)
        else:
            return {
                "success": False,
                "error": f"Database type {db_type} not yet implemented in standalone mode"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        }


def _execute_mysql(host, port, username, password, database, sql, timeout, extra_jdbc, max_rows):
    import pymysql
    conn = pymysql.connect(
        host=host,
        port=port,
        user=username,
        password=password,
        database=database,
        connect_timeout=timeout,
        read_timeout=timeout
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            if max_rows:
                rows = cursor.fetchmany(max_rows)
            else:
                rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            result = [_format_row(columns, row) for row in rows]
            return {
                "success": True,
                "fields": columns,
                "data": result,
                "row_count": len(result)
            }
    finally:
        conn.close()


def _execute_postgresql(host, port, username, password, database, sql, timeout, db_schema, extra_jdbc, max_rows):
    import psycopg2
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=username,
        password=password,
        database=database,
        connect_timeout=timeout,
        options=f"-c statement_timeout={timeout * 1000}"
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            if max_rows:
                cursor.fetchmany(max_rows)
            else:
                rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            result = [_format_row(columns, row) for row in rows]
            return {
                "success": True,
                "fields": columns,
                "data": result,
                "row_count": len(result)
            }
    finally:
        conn.close()


def _execute_sqlserver(host, port, username, password, database, sql, timeout, extra_jdbc, max_rows):
    import pymssql
    conn = pymssql.connect(
        server=host,
        port=port,
        user=username,
        password=password,
        database=database,
        timeout=timeout
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            if max_rows:
                rows = cursor.fetchmany(max_rows)
            else:
                rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            result = [_format_row(columns, row) for row in rows]
            return {
                "success": True,
                "fields": columns,
                "data": result,
                "row_count": len(result)
            }
    finally:
        conn.close()


def _execute_doris_starrocks(host, port, username, password, database, sql, timeout, extra_jdbc, max_rows):
    import pymysql
    conn = pymysql.connect(
        host=host,
        port=port,
        user=username,
        password=password,
        database=database,
        connect_timeout=timeout,
        read_timeout=timeout
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            if max_rows:
                rows = cursor.fetchmany(max_rows)
            else:
                rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            result = [_format_row(columns, row) for row in rows]
            return {
                "success": True,
                "fields": columns,
                "data": result,
                "row_count": len(result)
            }
    finally:
        conn.close()


def _execute_clickhouse(host, port, username, password, database, sql, timeout, max_rows):
    import clickhouse_connect
    client = clickhouse_connect.get_client(
        host=host,
        port=port,
        username=username,
        password=password,
        database=database
    )
    result = client.query(sql, query_timeout=timeout)
    if max_rows:
        rows = result.result_rows[:max_rows]
    else:
        rows = result.result_rows
    columns = result.column_names
    data = [_format_row(columns, row) for row in rows]
    return {
        "success": True,
        "fields": columns,
        "data": data,
        "row_count": len(data)
    }


def _execute_redshift(host, port, username, password, database, sql, timeout, extra_jdbc, max_rows):
    import redshift_connector
    conn = redshift_connector.connect(
        host=host,
        port=port,
        database=database,
        user=username,
        password=password,
        timeout=timeout
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            if max_rows:
                rows = cursor.fetchmany(max_rows)
            else:
                rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            result = [_format_row(columns, row) for row in rows]
            return {
                "success": True,
                "fields": columns,
                "data": result,
                "row_count": len(result)
            }
    finally:
        conn.close()


def _execute_dm(host, port, username, password, database, sql, timeout, extra_jdbc, max_rows):
    import dmPython
    conn = dmPython.connect(
        user=username,
        password=password,
        server=host,
        port=port
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, timeout=timeout)
            if max_rows:
                rows = cursor.fetchmany(max_rows)
            else:
                rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            result = [_format_row(columns, row) for row in rows]
            return {
                "success": True,
                "fields": columns,
                "data": result,
                "row_count": len(result)
            }
    finally:
        conn.close()


def _execute_kingbase(host, port, username, password, database, sql, timeout, db_schema, extra_jdbc, max_rows):
    import psycopg2
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=username,
        password=password,
        database=database,
        connect_timeout=timeout,
        options=f"-c statement_timeout={timeout * 1000}"
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            if max_rows:
                rows = cursor.fetchmany(max_rows)
            else:
                rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            result = [_format_row(columns, row) for row in rows]
            return {
                "success": True,
                "fields": columns,
                "data": result,
                "row_count": len(result)
            }
    finally:
        conn.close()


def _format_row(columns: List[str], row: tuple) -> Dict[str, Any]:
    """Format a row tuple into a dictionary, handling Decimal types."""
    return {
        str(col): float(val) if isinstance(val, Decimal) else val
        for col, val in zip(columns, row)
    }


def validate_sql_read_only(sql: str) -> Dict[str, Any]:
    """
    Validate SQL to ensure it's read-only (SELECT only).

    Args:
        sql: SQL query to validate

    Returns:
        Dictionary with keys:
        - valid: Boolean indicating if SQL is valid
        - errors: List of error messages if invalid
    """
    sql_clean = sql.strip().upper()

    # Check for SQL injection patterns
    injection_patterns = [
        (";", "Semicolon detected - multiple statements not allowed"),
        ("--", "SQL comment detected"),
        ("/*", "Multi-line comment detected"),
        ("xp_", "Extended stored procedure detected"),
        ("sp_executesql", "Dynamic SQL execution detected"),
        ("EXEC(", "EXEC command detected"),
        ("EXECUTE(", "EXECUTE command detected"),
    ]

    errors = []
    for pattern, message in injection_patterns:
        if pattern.upper() in sql_clean:
            errors.append(message)

    # Check for non-SELECT statements
    dangerous_keywords = [
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
        "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
    ]

    for keyword in dangerous_keywords:
        if keyword in sql_clean and sql_clean.startswith("SELECT") is False:
            errors.append(f"Dangerous keyword detected: {keyword}")

    # Check if query starts with SELECT or WITH (CTE)
    if not (sql_clean.startswith("SELECT") or sql_clean.startswith("WITH") or sql_clean.startswith("SHOW") or sql_clean.startswith("DESCRIBE") or sql_clean.startswith("EXPLAIN")):
        errors.append("Query must start with SELECT, WITH, SHOW, DESCRIBE, or EXPLAIN")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def main():
    """CLI interface for SQL executor."""
    parser = argparse.ArgumentParser(description="Execute SQL queries on various databases")
    parser.add_argument("--db-type", required=True, help="Database type")
    parser.add_argument("--host", required=True, help="Database host")
    parser.add_argument("--port", type=int, required=True, help="Database port")
    parser.add_argument("--username", required=True, help="Database username")
    parser.add_argument("--password", required=True, help="Database password")
    parser.add_argument("--database", required=True, help="Database name")
    parser.add_argument("--sql", required=True, help="SQL query to execute")
    parser.add_argument("--timeout", type=int, default=30, help="Query timeout in seconds")
    parser.add_argument("--schema", help="Database schema (for PostgreSQL)")
    parser.add_argument("--max-rows", type=int, help="Maximum number of rows to return")
    parser.add_argument("--read-only", action="store_true", default=True, help="Only allow SELECT queries")
    parser.add_argument("--output", choices=["json", "pretty"], default="json", help="Output format")

    args = parser.parse_args()

    result = execute_sql(
        db_type=args.db_type,
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        database=args.database,
        sql=args.sql,
        timeout=args.timeout,
        db_schema=args.schema,
        max_rows=args.max_rows,
        read_only=args.read_only
    )

    if args.output == "pretty":
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()