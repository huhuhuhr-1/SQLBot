# SQL Executor - Usage Examples

This document provides practical examples of using the sql-executor skill.

## Basic Usage

### Example 1: Simple SELECT Query

```python
from scripts.execute_sql import execute_sql

result = execute_sql(
    db_type="mysql",
    host="localhost",
    port=3306,
    username="root",
    password="password",
    database="test_db",
    sql="SELECT * FROM users LIMIT 10",
    timeout=30,
    read_only=True
)

if result["success"]:
    print(f"Retrieved {result['row_count']} rows")
    for row in result["data"]:
        print(row)
else:
    print(f"Error: {result['error']}")
```

### Example 2: Query with JOIN

```python
result = execute_sql(
    db_type="pg",
    host="localhost",
    port=5432,
    username="postgres",
    password="password",
    database="ecommerce",
    sql="""
    SELECT
        o.order_id,
        c.customer_name,
        o.order_date,
        o.total_amount
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_date >= '2024-01-01'
    ORDER BY o.order_date DESC
    LIMIT 100
    """,
    timeout=60,
    read_only=True,
    max_rows=100
)

print(f"Fields: {result['fields']}")
print(f"Data: {result['data']}")
```

### Example 3: Validating SQL Before Execution

```python
from scripts.sql_validator import SQLValidator

validator = SQLValidator(read_only=True)
validation = validator.validate(sql="SELECT * FROM users")

if validation["valid"]:
    print("SQL is valid, safe to execute")
else:
    print("SQL validation failed:")
    for error in validation["errors"]:
        print(f"  - {error}")
```

## Using with SQLBot Datasource Configuration

### Example 4: Using SQLBot's DatasourceConf

```python
import json
from apps.datasource.models.datasource import DatasourceConf

# Assuming you have a SQLBot datasource configuration
config_json = '''
{
  "host": "localhost",
  "port": 3306,
  "username": "root",
  "password": "password",
  "database": "test_db",
  "timeout": 30
}
'''

config = DatasourceConf(**json.loads(config_json))

result = execute_sql(
    db_type="mysql",
    host=config.host,
    port=config.port,
    username=config.username,
    password=config.password,
    database=config.database,
    sql="SELECT COUNT(*) as total FROM users",
    timeout=config.timeout,
    read_only=True
)

print(f"Total users: {result['data'][0]['total']}")
```

## Command-Line Interface

### Example 5: Execute SQL via CLI

```bash
python scripts/execute_sql.py \
  --db-type mysql \
  --host localhost \
  --port 3306 \
  --username root \
  --password password \
  --database test_db \
  --sql "SELECT * FROM users LIMIT 10" \
  --read-only \
  --max-rows 10 \
  --output pretty
```

### Example 6: Validate SQL via CLI

```bash
python scripts/sql_validator.py \
  --sql "SELECT * FROM users WHERE id = 1" \
  --read-only \
  --suggest-timeout \
  --estimate-size \
  --table-rows 1000000
```

## Integration with sql-generator and echarts-renderer Skills

### Example 7: Complete Workflow

```python
# 1. Generate SQL using sql-generator skill
# (Assume sql-generator skill returns: "SELECT category, COUNT(*) as count FROM products GROUP BY category")

generated_sql = "SELECT category, COUNT(*) as count FROM products GROUP BY category"

# 2. Validate SQL
from scripts.sql_validator import SQLValidator
validator = SQLValidator(read_only=True)
validation = validator.validate(generated_sql)

if not validation["valid"]:
    print(f"Validation errors: {validation['errors']}")
    exit(1)

# 3. Execute SQL
from scripts.execute_sql import execute_sql
result = execute_sql(
    db_type="mysql",
    host="localhost",
    port=3306,
    username="root",
    password="password",
    database="ecommerce",
    sql=generated_sql,
    timeout=30,
    read_only=True
)

if not result["success"]:
    print(f"Execution error: {result['error']}")
    exit(1)

# 4. Process results for echarts-renderer
chart_data = {
    "fields": result["fields"],
    "data": result["data"]
}

# 5. Use echarts-renderer skill to create visualization
# (Pass chart_data to echarts-renderer)
```

## Advanced Usage

### Example 8: Query with Timeout Estimation

```python
from scripts.sql_validator import SQLValidator

sql = """
SELECT
    o.order_id,
    c.customer_name,
    p.product_name,
    od.quantity,
    od.unit_price
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_details od ON o.order_id = od.order_id
JOIN products p ON od.product_id = p.product_id
WHERE o.order_date BETWEEN '2024-01-01' AND '2024-12-31'
"""

validator = SQLValidator(read_only=True)
suggested_timeout = validator.suggest_timeout(sql)

print(f"Suggested timeout: {suggested_timeout} seconds")

result = execute_sql(
    db_type="pg",
    host="localhost",
    port=5432,
    username="postgres",
    password="password",
    database="ecommerce",
    sql=sql,
    timeout=suggested_timeout,
    read_only=True
)
```

### Example 9: Result Size Estimation

```python
sql = "SELECT * FROM orders WHERE status = 'completed'"

validator = SQLValidator(read_only=True)
size_estimate = validator.estimate_result_size(sql, table_rows=1000000)

print(f"Estimated rows: {size_estimate['estimated_rows']}")
print(f"Confidence: {size_estimate['confidence']}")

# Set max_rows based on estimation
max_rows = min(size_estimate['estimated_rows'], 10000)

result = execute_sql(
    db_type="mysql",
    host="localhost",
    port=3306,
    username="root",
    password="password",
    database="ecommerce",
    sql=sql,
    timeout=30,
    max_rows=max_rows,
    read_only=True
)
```

### Example 10: Batch Query Execution

```python
queries = [
    "SELECT COUNT(*) as total FROM users",
    "SELECT COUNT(*) as active FROM users WHERE status = 'active'",
    "SELECT COUNT(*) as new_users FROM users WHERE created_at >= '2024-01-01'"
]

results = []
for query in queries:
    result = execute_sql(
        db_type="pg",
        host="localhost",
        port=5432,
        username="postgres",
        password="password",
        database="analytics",
        sql=query,
        timeout=30,
        read_only=True
    )
    results.append(result)

# Process all results
for i, result in enumerate(results):
    if result["success"]:
        print(f"Query {i+1}: {result['data']}")
```

## Error Handling

### Example 11: Comprehensive Error Handling

```python
from scripts.execute_sql import execute_sql
from scripts.sql_validator import SQLValidator

def safe_execute_sql(db_type, host, port, username, password, database, sql, **kwargs):
    """Execute SQL with comprehensive error handling."""

    # Step 1: Validate SQL
    validator = SQLValidator(read_only=kwargs.get("read_only", True))
    validation = validator.validate(sql)

    if not validation["valid"]:
        return {
            "success": False,
            "stage": "validation",
            "errors": validation["errors"],
            "warnings": validation["warnings"]
        }

    print(f"Warnings: {validation['warnings']}")

    # Step 2: Suggest timeout if not provided
    if "timeout" not in kwargs:
        kwargs["timeout"] = validator.suggest_timeout(sql)
        print(f"Suggested timeout: {kwargs['timeout']} seconds")

    # Step 3: Execute SQL
    try:
        result = execute_sql(
            db_type=db_type,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            sql=sql,
            **kwargs
        )

        if result["success"]:
            print(f"Query executed successfully, retrieved {result['row_count']} rows")
        else:
            print(f"Execution failed: {result['error']}")

        return result

    except Exception as e:
        return {
            "success": False,
            "stage": "execution",
            "error": str(e),
            "type": type(e).__name__
        }

# Usage
result = safe_execute_sql(
    db_type="mysql",
    host="localhost",
    port=3306,
    username="root",
    password="password",
    database="test_db",
    sql="SELECT * FROM users LIMIT 10",
    read_only=True
)
```

## Performance Optimization

### Example 12: Optimizing Query Performance

```python
from scripts.sql_validator import SQLValidator

def optimize_query_execution(sql, db_config):
    """Optimize query execution with validation and tuning."""

    validator = SQLValidator(read_only=True)

    # Get validation results
    validation = validator.validate(sql)

    # Apply recommendations
    if validation["recommendations"]:
        print("Recommendations:")
        for rec in validation["recommendations"]:
            print(f"  - {rec}")

    # Suggest timeout
    timeout = validator.suggest_timeout(sql)
    print(f"Recommended timeout: {timeout} seconds")

    # Estimate result size
    size_estimate = validator.estimate_result_size(sql)
    print(f"Estimated rows: {size_estimate['estimated_rows']} (confidence: {size_estimate['confidence']})")

    # Set max_rows to prevent excessive results
    max_rows = min(size_estimate['estimated_rows'], 10000) if size_estimate['estimated_rows'] > 0 else 1000

    # Execute with optimized parameters
    result = execute_sql(
        db_type=db_config["type"],
        host=db_config["host"],
        port=db_config["port"],
        username=db_config["username"],
        password=db_config["password"],
        database=db_config["database"],
        sql=sql,
        timeout=timeout,
        max_rows=max_rows,
        read_only=True
    )

    return result

# Usage
db_config = {
    "type": "mysql",
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "password",
    "database": "analytics"
}

sql = """
SELECT
    date_trunc('day', order_date) as order_day,
    COUNT(*) as order_count,
    SUM(total_amount) as revenue
FROM orders
WHERE order_date >= '2024-01-01'
GROUP BY order_day
ORDER BY order_day
"""

result = optimize_query_execution(sql, db_config)
```

## Security Examples

### Example 13: Detecting SQL Injection Attempts

```python
from scripts.sql_validator import SQLValidator

validator = SQLValidator(read_only=True)

# Malicious SQL attempts
malicious_queries = [
    "SELECT * FROM users WHERE id = 1; DROP TABLE users--",
    "SELECT * FROM users WHERE id = 1 OR 1=1",
    "SELECT * FROM users WHERE name = 'admin'--",
    "SELECT * FROM users WHERE id = 1 UNION SELECT * FROM passwords"
]

for query in malicious_queries:
    validation = validator.validate(query)
    print(f"Query: {query}")
    print(f"Valid: {validation['valid']}")
    print(f"Errors: {validation['errors']}")
    print()
```

### Example 14: Enforcing Read-Only Mode

```python
from scripts.sql_validator import SQLValidator

validator = SQLValidator(read_only=True)

# Attempt to execute write operations
write_queries = [
    "DELETE FROM users WHERE id = 1",
    "UPDATE users SET status = 'inactive'",
    "INSERT INTO logs (message) VALUES ('test')",
    "DROP TABLE old_data"
]

for query in write_queries:
    validation = validator.validate(query)
    if not validation["valid"]:
        print(f"Blocked: {query}")
        print(f"Reason: {validation['errors']}")
        print()
```