# ClickHouse SQL Generation Rules

## Quote Rules

**Must use double quotes (`"`) for:**
- All identifiers (recommended)
- Keywords used as identifiers
- Names with special characters

**Dot notation format:**
```sql
"database"."table"          -- Correct
"database"."table"."column" -- Correct
```

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
FROM "database"."table_name" "t1"     -- Correct
FROM "database"."table_name" AS "t1"  -- WRONG - don't use AS
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
now()                -- Current timestamp
today()              -- Current date
yesterday()          -- Yesterday's date
```

**Formatting:**
```sql
formatDateTime("timestamp_column", '%Y-%m-%d')               -- Date
formatDateTime("timestamp_column", '%Y-%m-%d %H:%M:%S')      -- Timestamp
formatDateTime("timestamp_column", '%Y-%m')                  -- Year-month
toYear("timestamp_column")                                   -- Year
toYYYYMM("timestamp_column")                                 -- Year-month as number
```

**Date manipulation:**
```sql
toDate("timestamp_column")          -- Extract date
toStartOfMonth("timestamp_column")  -- Truncate to month
toStartOfYear("timestamp_column")   -- Truncate to year
```

**Date arithmetic:**
```sql
addDays("date_column", 7)     -- Add 7 days
subtractDays("date_column", 7) -- Subtract 7 days
addMonths("date_column", 3)    -- Add 3 months
```

## Array Functions

**Array creation:**
```sql
["value1", "value2", "value3"]
```

**Array access:**
```sql
"array_column"[1]  -- First element (1-indexed)
```

**Array functions:**
```sql
length("array_column")           -- Array length
arrayJoin("array_column")        -- Flatten array
has("array_column", "value")     -- Check if value exists
```

## Aggregation Functions

```sql
COUNT("column")  -- Count rows
COUNT(*)         -- Count all rows
SUM("column")    -- Sum values
AVG("column")    -- Average values
MIN("column")    -- Minimum value
MAX("column")    -- Maximum value
uniq("column")   -- Approximate unique count
uniqExact("column") -- Exact unique count
```

## JOIN Syntax

**Note:** ClickHouse JOINs require careful handling due to its columnar nature.

```sql
FROM "table1" "t1"
INNER JOIN "table2" "t2" ON "t1"."id" = "t2"."t1_id"
LEFT JOIN "table3" "t3" ON "t1"."id" = "t3"."t1_id"
```

**ALL or ANY keywords:**
```sql
INNER JOIN ANY -- Return any matching row (default)
INNER JOIN ALL -- Return all matching rows
```

## Conditional Logic

**if function:**
```sql
if("amount" > 1000, 'high', 'low') AS "amount_category"
```

**multiIf:**
```sql
multiIf(
  "amount" > 1000, 'high',
  "amount" > 500, 'medium',
  'low'
) AS "amount_category"
```

**CASE statement:**
```sql
CASE
  WHEN "amount" > 1000 THEN 'high'
  WHEN "amount" > 500 THEN 'medium'
  ELSE 'low'
END AS "amount_category"
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
  toYYYYMM("create_time") AS "month",
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

## ClickHouse-Specific Features

**MergeTree table engine considerations:**
- ORDER BY is crucial for performance
- Queries optimized for ORDER BY keys run faster

**Sampling:**
```sql
SELECT ... FROM "table" SAMPLE 0.1  -- 10% sample
```

**Final result:**
```sql
SELECT ... FROM "table" FINAL  -- Apply mutations
```

## String Operations

**Concatenation:**
```sql
"first_name" || ' ' || "last_name" AS "full_name"
concat("first_name", ' ', "last_name") AS "full_name"
```

**String matching:**
```sql
"column_name" LIKE '%pattern%'
has("column_name", 'pattern')  -- Contains substring
```

## Error Prevention

**Handle NULL values:**
```sql
coalesce("column", 'default_value')  -- Return default if NULL
ifNull("column", 'default_value')   -- Same as coalesce
```

**Type conversion:**
```sql
toString("column")     -- To string
toInt("column")        -- To integer
toFloat("column")      -- To float
toDateTime("column")   -- To datetime
```

## Performance Tips

1. **Use appropriate sample rates** for large datasets
2. **Prefer GROUP BY on ORDER BY keys** for better performance
3. **Use PREWHERE** for filtering early in query pipeline
4. **Limit result sets** with LIMIT clause
