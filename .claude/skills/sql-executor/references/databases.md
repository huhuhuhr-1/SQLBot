# Supported Databases and Configuration

This document describes all supported database types and their configuration parameters for the sql-executor skill.

## Configuration Parameters

All database types support these common parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host` | string | Yes | Database server hostname or IP address |
| `port` | integer | Yes | Database server port |
| `username` | string | Yes | Database username |
| `password` | string | Yes | Database password |
| `database` | string | Yes | Database name |
| `timeout` | integer | No | Query timeout in seconds (default: 30) |
| `db_schema` | string | No | Database schema (PostgreSQL specific) |
| `extra_jdbc` | string | No | Extra JDBC connection parameters |
| `max_rows` | integer | No | Maximum number of rows to return |
| `read_only` | boolean | No | Only allow SELECT queries (default: True) |

## Database Types

### MySQL

**Type identifier:** `mysql`

**Default port:** 3306

**Python driver:** `pymysql`

**Connection string format:**
```
mysql+pymysql://{username}:{password}@{host}:{port}/{database}?{extra_jdbc}
```

**Example configuration:**
```json
{
  "type": "mysql",
  "host": "localhost",
  "port": 3306,
  "username": "root",
  "password": "password",
  "database": "test_db",
  "timeout": 30,
  "read_only": true
}
```

**Extra JDBC parameters (optional):**
- `charset`: Connection charset (e.g., `utf8mb4`)
- `autocommit`: Autocommit mode (e.g., `true`)

---

### PostgreSQL

**Type identifier:** `pg`

**Default port:** 5432

**Python driver:** `psycopg2`

**Connection string format:**
```
postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}?{extra_jdbc}
```

**Example configuration:**
```json
{
  "type": "pg",
  "host": "localhost",
  "port": 5432,
  "username": "postgres",
  "password": "password",
  "database": "test_db",
  "db_schema": "public",
  "timeout": 30,
  "read_only": true
}
```

**Schema support:** Use `db_schema` parameter to specify the schema (e.g., `public`, `my_schema`).

---

### SQL Server

**Type identifier:** `sqlServer`

**Default port:** 1433

**Python driver:** `pymssql`

**Connection string format:**
```
mssql+pymssql://{username}:{password}@{host}:{port}/{database}?{extra_jdbc}
```

**Example configuration:**
```json
{
  "type": "sqlServer",
  "host": "localhost",
  "port": 1433,
  "username": "sa",
  "password": "password",
  "database": "test_db",
  "timeout": 30,
  "read_only": true
}
```

---

### Oracle

**Type identifier:** `oracle`

**Default port:** 1521

**Python driver:** `oracledb`

**Connection string format:**
```
oracle+oracledb://{username}:{password}@{host}:{port}/?service_name={database}&{extra_jdbc}
```

**Example configuration:**
```json
{
  "type": "oracle",
  "host": "localhost",
  "port": 1521,
  "username": "system",
  "password": "password",
  "database": "ORCL",
  "timeout": 30,
  "read_only": true
}
```

**Connection modes:**
- `service_name`: Use service name (default)
- `sid`: Use System ID

---

### ClickHouse

**Type identifier:** `ck`

**Default port:** 8123

**Python driver:** `clickhouse-connect`

**Connection string format:**
```
clickhouse+http://{username}:{password}@{host}:{port}/{database}?{extra_jdbc}
```

**Example configuration:**
```json
{
  "type": "ck",
  "host": "localhost",
  "port": 8123,
  "username": "default",
  "password": "",
  "database": "default",
  "timeout": 30,
  "read_only": true
}
```

---

### Doris

**Type identifier:** `doris`

**Default port:** 9030

**Python driver:** `pymysql`

**Connection string format:**
```
mysql+pymysql://{username}:{password}@{host}:{port}/{database}?{extra_jdbc}
```

**Example configuration:**
```json
{
  "type": "doris",
  "host": "localhost",
  "port": 9030,
  "username": "root",
  "password": "password",
  "database": "test_db",
  "timeout": 30,
  "read_only": true
}
```

---

### StarRocks

**Type identifier:** `starrocks`

**Default port:** 9030

**Python driver:** `pymysql`

**Connection string format:**
```
mysql+pymysql://{username}:{password}@{host}:{port}/{database}?{extra_jdbc}
```

**Example configuration:**
```json
{
  "type": "starrocks",
  "host": "localhost",
  "port": 9030,
  "username": "root",
  "password": "password",
  "database": "test_db",
  "timeout": 30,
  "read_only": true
}
```

---

### Redshift

**Type identifier:** `redshift`

**Default port:** 5439

**Python driver:** `redshift_connector`

**Connection string format:**
```
redshift+connector://{username}:{password}@{host}:{port}/{database}?{extra_jdbc}
```

**Example configuration:**
```json
{
  "type": "redshift",
  "host": "redshift.amazonaws.com",
  "port": 5439,
  "username": "awsuser",
  "password": "password",
  "database": "dev",
  "timeout": 30,
  "read_only": true
}
```

---

### DM (达梦)

**Type identifier:** `dm`

**Default port:** 5236

**Python driver:** `dmPython`

**Example configuration:**
```json
{
  "type": "dm",
  "host": "localhost",
  "port": 5236,
  "username": "SYSDBA",
  "password": "password",
  "database": "test_db",
  "timeout": 30,
  "read_only": true
}
```

---

### KingBase

**Type identifier:** `kingbase`

**Default port:** 54321

**Python driver:** `psycopg2`

**Example configuration:**
```json
{
  "type": "kingbase",
  "host": "localhost",
  "port": 54321,
  "username": "SYSTEM",
  "password": "password",
  "database": "test_db",
  "db_schema": "public",
  "timeout": 30,
  "read_only": true
}
```

---

### Elasticsearch

**Type identifier:** `es`

**Default port:** 9200

**Python driver:** HTTP client

**Example configuration:**
```json
{
  "type": "es",
  "host": "localhost",
  "port": 9200,
  "username": "elastic",
  "password": "password",
  "database": "index_name",
  "timeout": 30,
  "read_only": true
}
```

**Note:** Elasticsearch uses SQL-like queries through the `_sql` endpoint.

## Security Best Practices

### 1. Read-Only Mode
Always enable `read_only: true` for production environments to prevent accidental data modification.

### 2. Query Timeout
Set appropriate `timeout` values based on query complexity:
- Simple queries: 10-30 seconds
- Complex queries with JOINs: 30-60 seconds
- Analytical queries: 60-300 seconds

### 3. Result Size Limits
Use `max_rows` to prevent returning excessive data:
- For web displays: 100-1000 rows
- For data exports: 10000-100000 rows

### 4. Connection Validation
Always validate database connections before executing queries to avoid hanging on invalid credentials.

### 5. SQL Injection Prevention
The skill includes built-in SQL injection detection:
- Blocks multiple statements (semicolons)
- Detects common injection patterns
- Enforces read-only mode when enabled

## Error Handling

### Common Error Codes

| Error | Description | Solution |
|-------|-------------|----------|
| `Unsupported database type` | Database type not supported | Check database type identifier |
| `Database driver not installed` | Python driver missing | Install required driver package |
| `SQL validation failed` | SQL query blocked | Check error details for specific issues |
| `Connection timeout` | Cannot connect to database | Verify host, port, credentials |
| `Query timeout` | Query execution too long | Increase timeout parameter |

## Performance Tips

1. **Use indexes**: Ensure query columns are indexed
2. **Avoid SELECT ***: Specify only needed columns
3. **Add LIMIT**: Always limit result set size
4. **Optimize JOINs**: Use appropriate join types and conditions
5. **Use WHERE clauses**: Filter data early to reduce processing
6. **Avoid subqueries**: Consider JOINs instead of nested subqueries

## Troubleshooting

### Connection Issues
- Verify network connectivity to database host
- Check firewall rules for database port
- Confirm username and password are correct
- Ensure database is running and accessible

### Query Performance Issues
- Run EXPLAIN/EXPLAIN ANALYZE to understand query plan
- Check if indexes exist on filtered columns
- Simplify complex queries with multiple JOINs
- Consider breaking large queries into smaller ones

### Driver Installation
```bash
# MySQL
pip install pymysql

# PostgreSQL
pip install psycopg2-binary

# SQL Server
pip install pymssql

# Oracle
pip install oracledb

# ClickHouse
pip install clickhouse-connect

# Redshift
pip install redshift_connector

# DM (达梦)
pip install dmPython

# KingBase
pip install psycopg2-binary
```