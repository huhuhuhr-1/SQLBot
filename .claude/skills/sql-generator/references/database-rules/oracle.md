# Oracle SQL Generation Rules

## Quote Rules

**Must use double quotes (`"`) for:**
- All identifiers (recommended practice)
- Case-sensitive names
- Keywords used as identifiers
- Names with special characters

**Dot notation format:**
```sql
"schema"."table"          -- Correct
"schema"."table"."column" -- Correct
```

**Note:** Oracle defaults to uppercase for unquoted identifiers.

## LIMIT Syntax

**Modern Oracle (12c+):**
```sql
SELECT ... FROM ... FETCH FIRST 1000 ROWS ONLY
```

**With offset:**
```sql
SELECT ... FROM ... OFFSET 10 ROWS FETCH NEXT 1000 ROWS ONLY
```

**Legacy Oracle (11g and earlier):**
```sql
SELECT * FROM (
  SELECT a.*, ROWNUM as rn FROM (
    /* original query */
  ) a WHERE ROWNUM <= 1010
) WHERE rn > 10
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
SYSDATE              -- Current date and time
CURRENT_DATE         -- Current date
SYSTIMESTAMP         -- Current timestamp with timezone
```

**Formatting:**
```sql
TO_CHAR("date_column", 'YYYY-MM-DD')             -- Date
TO_CHAR("timestamp_column", 'YYYY-MM-DD HH24:MI:SS')  -- Timestamp
TO_CHAR("date_column", 'YYYY-MM')                -- Year-month
TO_CHAR("date_column", 'YYYY')                   -- Year
```

**Date manipulation:**
```sql
TRUNC("date_column", 'DD')    -- Truncate to day
TRUNC("date_column", 'MM')    -- Truncate to month
TRUNC("date_column", 'YYYY')  -- Truncate to year
```

**Date arithmetic:**
```sql
SYSDATE + 1           -- Add 1 day
SYSDATE - 7           -- Subtract 7 days
ADD_MONTHS(SYSDATE, 3) -- Add 3 months
```

## String Operations

**Concatenation:**
```sql
"first_name" || ' ' || "last_name" AS "full_name"
```

**String matching:**
```sql
"column_name" LIKE '%pattern%'
REGEXP_LIKE("column_name", 'pattern')
```

## Aggregation Functions

```sql
COUNT("column")  -- Count rows
COUNT(*)         -- Count all rows
SUM("column")    -- Sum values
AVG("column")    -- Average values
MIN("column")    -- Minimum value
MAX("column")    -- Maximum value
```

## JOIN Syntax

```sql
FROM "table1" "t1"
INNER JOIN "table2" "t2" ON "t1"."id" = "t2"."t1_id"
LEFT JOIN "table3" "t3" ON "t1"."id" = "t3"."t1_id"
```

## Conditional Logic

**CASE statement:**
```sql
CASE
  WHEN "amount" > 1000 THEN 'high'
  WHEN "amount" > 500 THEN 'medium'
  ELSE 'low'
END AS "amount_category"
```

**NVL for NULL handling:**
```sql
NVL("column", 'default_value')  -- Return default if NULL
```

## Common Patterns

**Simple query:**
```sql
SELECT "id", "name", "email"
FROM "users"
FETCH FIRST 1000 ROWS ONLY
```

**Aggregation with GROUP BY:**
```sql
SELECT
  "department",
  COUNT("id") AS "emp_count"
FROM "employees"
GROUP BY "department"
ORDER BY "emp_count" DESC
FETCH FIRST 1000 ROWS ONLY
```

**Time series:**
```sql
SELECT
  TO_CHAR("create_time", 'YYYY-MM') AS "month",
  SUM("amount") AS "total_amount"
FROM "orders"
GROUP BY TO_CHAR("create_time", 'YYYY-MM')
ORDER BY "month"
FETCH FIRST 1000 ROWS ONLY
```

**Multi-table join:**
```sql
SELECT
  "u"."name" AS "user_name",
  "o"."amount" AS "order_amount"
FROM "users" "u"
INNER JOIN "orders" "o" ON "u"."id" = "o"."user_id"
FETCH FIRST 1000 ROWS ONLY
```

## Error Prevention

**Handle NULL values:**
```sql
NVL("column", 'default_value')     -- Return default if NULL
NVL2("column", val1, val2)         -- val1 if not NULL, val2 if NULL
COALESCE("col1", "col2", 'default') -- First non-NULL value
```

**String to number conversion:**
```sql
TO_NUMBER("string_column", '999999')  -- Convert to number
```

**Date conversion:**
```sql
TO_DATE('2025-01-15', 'YYYY-MM-DD')  -- String to date
```

## Performance Considerations

**Use ROWNUM for pagination (legacy):**
```sql
SELECT * FROM (
  SELECT a.*, ROWNUM rn FROM (
    SELECT * FROM "table" ORDER BY "id"
  ) a WHERE ROWNUM <= 1000
) WHERE rn > 0
```

**Index hints (if needed):**
```sql
SELECT /*+ INDEX("table" "index_name") */ ...
FROM "table"
```
