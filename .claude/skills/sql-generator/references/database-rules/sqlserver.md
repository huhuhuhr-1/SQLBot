# SQL Server SQL Generation Rules

## Quote Rules

**Must use square brackets (`[`) for:**
- All identifiers (best practice)
- Keywords used as identifiers
- Names with spaces or special characters

**Dot notation format:**
```sql
[schema].[table]          -- Correct
[schema].[table].[column] -- Correct
```

## LIMIT Syntax

**SQL Server 2012+: Using OFFSET-FETCH:**
```sql
SELECT ... FROM ... ORDER BY [column] OFFSET 0 ROWS FETCH NEXT 1000 ROWS ONLY
```

**Legacy SQL Server (2008 R2 and earlier): Using TOP:**
```sql
SELECT TOP 1000 ... FROM ...
```

**With pagination (2012+):**
```sql
SELECT ... FROM ...
ORDER BY [column]
OFFSET 10 ROWS FETCH NEXT 1000 ROWS ONLY
```

## Table Aliases

**Required for all tables, no AS keyword:**
```sql
FROM [schema].[table_name] [t1]     -- Correct
FROM [schema].[table_name] AS [t1]  -- WRONG - don't use AS
```

## Field Aliases

**Function fields MUST have aliases:**
```sql
COUNT([id]) AS [total_count]           -- Correct
COUNT([id])                           -- WRONG - missing alias
SUM([amount]) AS [total_amount]       -- Correct
```

## Percentage Formatting

**Pattern:**
```sql
CONVERT(VARCHAR, ROUND([column] * 100, 2)) + '%' AS [percent]
```

**Example:**
```sql
SELECT
  [product_name],
  CONVERT(VARCHAR, ROUND([sales_ratio] * 100, 2)) + '%' AS [sales_percent]
FROM [products]
```

## Time Functions

**Current date/time:**
```sql
GETDATE()               -- Current datetime
CURRENT_TIMESTAMP       -- Current datetime
SYSDATETIME()           -- Current datetime with more precision
GETUTCDATE()            -- Current UTC datetime
```

**Formatting:**
```sql
FORMAT([date_column], 'yyyy-MM-dd')               -- Date
FORMAT([timestamp_column], 'yyyy-MM-dd HH:mm:ss') -- Timestamp
FORMAT([date_column], 'yyyy-MM')                  -- Year-month
FORMAT([date_column], 'yyyy')                     -- Year
```

**Date extraction:**
```sql
DATEPART(YEAR, [date_column])      -- Extract year
DATEPART(MONTH, [date_column])     -- Extract month
DATEPART(DAY, [date_column])       -- Extract day
```

**Date manipulation:**
```sql
DATEADD(DAY, 1, GETDATE())     -- Add 1 day
DATEADD(MONTH, -3, GETDATE())  -- Subtract 3 months
DATEDIFF(DAY, [date1], [date2]) -- Days between dates
```

## String Operations

**Concatenation:**
```sql
[first_name] + ' ' + [last_name] AS [full_name]
-- Or with CONCAT (SQL Server 2012+):
CONCAT([first_name], ' ', [last_name]) AS [full_name]
```

**String matching:**
```sql
[column_name] LIKE '%pattern%'
```

## Aggregation Functions

```sql
COUNT([column])  -- Count rows
COUNT(*)         -- Count all rows
SUM([column])    -- Sum values
AVG([column])    -- Average values
MIN([column])    -- Minimum value
MAX([column])    -- Maximum value
```

## JOIN Syntax

```sql
FROM [table1] [t1]
INNER JOIN [table2] [t2] ON [t1].[id] = [t2].[t1_id]
LEFT JOIN [table3] [t3] ON [t1].[id] = [t3].[t1_id]
```

## Conditional Logic

**CASE statement:**
```sql
CASE
  WHEN [amount] > 1000 THEN 'high'
  WHEN [amount] > 500 THEN 'medium'
  ELSE 'low'
END AS [amount_category]
```

**ISNULL for NULL handling:**
```sql
ISNULL([column], 'default_value')  -- Return default if NULL
```

## Common Patterns

**Simple query:**
```sql
SELECT [id], [name], [email]
FROM [users]
ORDER BY [id]
OFFSET 0 ROWS FETCH NEXT 1000 ROWS ONLY
```

**Aggregation with GROUP BY:**
```sql
SELECT
  [department],
  COUNT([id]) AS [emp_count]
FROM [employees]
GROUP BY [department]
ORDER BY [emp_count] DESC
OFFSET 0 ROWS FETCH NEXT 1000 ROWS ONLY
```

**Time series:**
```sql
SELECT
  FORMAT([create_time], 'yyyy-MM') AS [month],
  SUM([amount]) AS [total_amount]
FROM [orders]
GROUP BY FORMAT([create_time], 'yyyy-MM')
ORDER BY [month]
OFFSET 0 ROWS FETCH NEXT 1000 ROWS ONLY
```

**Multi-table join:**
```sql
SELECT
  [u].[name] AS [user_name],
  [o].[amount] AS [order_amount]
FROM [users] [u]
INNER JOIN [orders] [o] ON [u].[id] = [o].[user_id]
OFFSET 0 ROWS FETCH NEXT 1000 ROWS ONLY
```

**Conditional aggregation:**
```sql
SELECT
  [department],
  SUM(CASE WHEN [status] = 'active' THEN 1 ELSE 0 END) AS [active_count],
  SUM(CASE WHEN [status] = 'inactive' THEN 1 ELSE 0 END) AS [inactive_count]
FROM [employees]
GROUP BY [department]
```

## Error Prevention

**Handle NULL values:**
```sql
ISNULL([column], 'default_value')        -- Return default if NULL
COALESCE([col1], [col2], 'default')      -- First non-NULL value
```

**String to number conversion:**
```sql
CAST([string_column] AS INT)      -- To integer
CAST([string_column] AS DECIMAL) -- To decimal
-- Or:
CONVERT(INT, [string_column])
```

**Date conversion:**
```sql
CAST('2025-01-15' AS DATE)
CONVERT(DATE, '2025-01-15')
```

## Data Type Casting

**CAST syntax:**
```sql
CAST([column] AS data_type)
```

**CONVERT syntax (more options):**
```sql
CONVERT(data_type, [column], style)
```

**Common conversions:**
```sql
CAST([column] AS VARCHAR(50))
CAST([column] AS INT)
CAST([column] AS DECIMAL(10,2))
CONVERT(VARCHAR, [column])
```

## Window Functions (Advanced)

**ROW_NUMBER:**
```sql
SELECT
  [column],
  ROW_NUMBER() OVER (ORDER BY [column]) AS [row_num]
FROM [table]
```

**RANK:**
```sql
SELECT
  [department],
  [salary],
  RANK() OVER (PARTITION BY [department] ORDER BY [salary] DESC) AS [rank_in_dept]
FROM [employees]
```
