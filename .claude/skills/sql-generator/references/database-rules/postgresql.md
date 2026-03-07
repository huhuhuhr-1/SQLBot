# PostgreSQL SQL Generation Rules

## Quote Rules

**Must use double quotes (`"`) for all identifiers:**
- Database names: `"database_name"`
- Schema names: `"schema_name"`
- Table names: `"table_name"`
- Column names: `"column_name"`
- Aliases: `"alias_name"`

**Dot notation format:**
```sql
"schema"."table"          -- Correct
"schema"."table"."column" -- Correct
"schema.table"            -- WRONG - dots outside quotes
```

**All identifiers require quotes**, even if not keywords or special characters.

## LIMIT Syntax

**Standard LIMIT:**
```sql
SELECT ... FROM ... LIMIT 1000
```

**With OFFSET:**
```sql
SELECT ... FROM ... LIMIT 1000 OFFSET 10
```

## Table Aliases

**Required for all tables, no AS keyword:**
```sql
FROM "schema"."table_name" "t1"     -- Correct
FROM "schema"."table_name" AS "t1"  -- WRONG - don't use AS
```

## Field Aliases

**Function fields MUST have aliases:**
```sql
COUNT("id") AS "total_count"           -- Correct
COUNT("id")                           -- WRONG - missing alias
SUM("amount") AS "total_amount"       -- Correct
```

**Regular fields:** Aliases optional
```sql
"column_name" AS "alias"  -- Optional but recommended for clarity
"column_name"             -- Also acceptable
```

**Chinese/special character fields:** Add English alias
```sql
"订单ID" AS "order_id"    -- Correct
"订单ID"                  -- WRONG - needs English alias
```

## Percentage Formatting

**Pattern:**
```sql
ROUND("column" * 100, 2) || '%' AS "percent"
```

**Example:**
```sql
SELECT
  "product_name",
  ROUND("sales_ratio" * 100, 2) || '%' AS "sales_percent"
FROM "products"
```

## Time Functions

**Current date/time:**
```sql
NOW()               -- Current timestamp
CURRENT_DATE        -- Current date
CURRENT_TIMESTAMP   -- Current timestamp
```

**Formatting:**
```sql
TO_CHAR("date_column", 'YYYY-MM-DD')           -- Date
TO_CHAR("timestamp_column", 'YYYY-MM-DD HH24:MI:SS')  -- Timestamp
TO_CHAR("date_column", 'YYYY-MM')              -- Year-month
TO_CHAR("date_column", 'YYYY')                 -- Year
```

**Date truncation:**
```sql
DATE_TRUNC('day', "timestamp_column")   -- Truncate to day
DATE_TRUNC('month', "timestamp_column")  -- Truncate to month
DATE_TRUNC('year', "timestamp_column")   -- Truncate to year
```

## String Operations

**Concatenation:**
```sql
"first_name" || ' ' || "last_name" AS "full_name"
```

**String matching:**
```sql
"column_name" LIKE '%pattern%'
"column_name" ~ 'regex_pattern'  -- Regex match
```

## Aggregation Functions

```sql
COUNT("column")     -- Count rows
COUNT(*)            -- Count all rows
SUM("column")       -- Sum values
AVG("column")       -- Average values
MIN("column")       -- Minimum value
MAX("column")       -- Maximum value
```

## JOIN Syntax

```sql
FROM "table1" "t1"
INNER JOIN "table2" "t2" ON "t1"."id" = "t2"."t1_id"
LEFT JOIN "table3" "t3" ON "t1"."id" = "t3"."t1_id"
```

## Common Patterns

**Simple query:**
```sql
SELECT "id", "name", "email" FROM "users" LIMIT 1000
```

**Aggregation with GROUP BY:**
```sql
SELECT
  "department",
  COUNT("id") AS "emp_count"
FROM "employees"
GROUP BY "department"
ORDER BY "emp_count" DESC
LIMIT 1000
```

**Time series:**
```sql
SELECT
  TO_CHAR("create_time", 'YYYY-MM') AS "month",
  SUM("amount") AS "total_amount"
FROM "orders"
GROUP BY "month"
ORDER BY "month"
LIMIT 1000
```

**Multi-table join:**
```sql
SELECT
  "u"."name" AS "user_name",
  "o"."amount" AS "order_amount"
FROM "users" "u"
INNER JOIN "orders" "o" ON "u"."id" = "o"."user_id"
LIMIT 1000
```

## Error Prevention

**Avoid keyword conflicts:**
```sql
SELECT "user", "order", "group", "select" FROM "table"  -- All quoted
```

**Handle NULL values:**
```sql
COALESCE("column", 'default_value')  -- Return default if NULL
```
