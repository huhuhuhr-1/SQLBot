# Apache Doris SQL Generation Rules

## Quote Rules

**Must use backticks (`` ` ``) for:**
- All identifiers (best practice)
- Keywords used as identifiers
- Names with special characters

**Dot notation format:**
```sql
`database`.`table`          -- Correct
`database`.`table`.`column` -- Correct
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
FROM `database`.`table_name` `t1`     -- Correct
FROM `database`.`table_name` AS `t1`  -- WRONG - don't use AS
```

## Field Aliases

**Function fields MUST have aliases:**
```sql
COUNT(`id`) AS `total_count`           -- Correct
COUNT(`id`)                           -- WRONG - missing alias
SUM(`amount`) AS `total_amount`       -- Correct
```

## Percentage Formatting

**Pattern:**
```sql
CONCAT(ROUND(`column` * 100, 2), '%') AS `percent`
```

**Example:**
```sql
SELECT
  `product_name`,
  CONCAT(ROUND(`sales_ratio` * 100, 2), '%') AS `sales_percent`
FROM `products`
```

## Time Functions

**Current date/time:**
```sql
NOW()               -- Current datetime
CURRENT_DATE        -- Current date
CURRENT_TIMESTAMP   -- Current timestamp
CURDATE()           -- Current date
CURTIME()           -- Current time
```

**Formatting:**
```sql
DATE_FORMAT(`date_column`, '%Y-%m-%d')              -- Date
DATE_FORMAT(`timestamp_column`, '%Y-%m-%d %H:%i:%s') -- Timestamp
DATE_FORMAT(`date_column`, '%Y-%m')                 -- Year-month
DATE_FORMAT(`date_column`, '%Y')                    -- Year
```

**Date extraction:**
```sql
DATE(`timestamp_column`)      -- Extract date
YEAR(`date_column`)           -- Extract year
MONTH(`date_column`)          -- Extract month
DAY(`date_column`)            -- Extract day
QUARTER(`date_column`)        -- Extract quarter
```

**Date truncation:**
```sql
DATE_TRUNC(`date_column`, 'DAY')    -- Truncate to day
DATE_TRUNC(`date_column`, 'MONTH')  -- Truncate to month
DATE_TRUNC(`date_column`, 'YEAR')   -- Truncate to year
```

## String Operations

**Concatenation:**
```sql
CONCAT(`first_name`, ' ', `last_name`) AS `full_name`
```

**String matching:**
```sql
`column_name` LIKE '%pattern%'
```

## Aggregation Functions

```sql
COUNT(`column`)  -- Count rows
COUNT(*)         -- Count all rows
SUM(`column`)    -- Sum values
AVG(`column`)    -- Average values
MIN(`column`)    -- Minimum value
MAX(`column`)    -- Maximum value
```

**Multi-dimensional aggregation:**
```sql
SUM(`column`) GROUPING SETS ((`dim1`), (`dim2`), ())
```

## JOIN Syntax

```sql
FROM `table1` `t1`
INNER JOIN `table2` `t2` ON `t1`.`id` = `t2`.`t1_id`
LEFT JOIN `table3` `t3` ON `t1`.`id` = `t3`.`t1_id`
```

**Note:** Doris supports various JOIN strategies including:
- Broadcast JOIN (small table to large)
- Shuffle JOIN (large table to large)
- Colocate JOIN (same bucket)

## Conditional Logic

**CASE statement:**
```sql
CASE
  WHEN `amount` > 1000 THEN 'high'
  WHEN `amount` > 500 THEN 'medium'
  ELSE 'low'
END AS `amount_category`
```

**IF function:**
```sql
IF(`status` = 1, 'active', 'inactive') AS `status_text`
```

## Common Patterns

**Simple query:**
```sql
SELECT `id`, `name`, `email` FROM `users` LIMIT 1000
```

**Aggregation with GROUP BY:**
```sql
SELECT
  `department`,
  COUNT(`id`) AS `emp_count`
FROM `employees`
GROUP BY `department`
ORDER BY `emp_count` DESC
LIMIT 1000
```

**Time series:**
```sql
SELECT
  DATE_FORMAT(`create_time`, '%Y-%m') AS `month`,
  SUM(`amount`) AS `total_amount`
FROM `orders`
GROUP BY `month`
ORDER BY `month`
LIMIT 1000
```

**Multi-table join:**
```sql
SELECT
  `u`.`name` AS `user_name`,
  `o`.`amount` AS `order_amount`
FROM `users` `u`
INNER JOIN `orders` `o` ON `u`.`id` = `o`.`user_id`
LIMIT 1000
```

**Conditional aggregation:**
```sql
SELECT
  `department`,
  SUM(CASE WHEN `status` = 'active' THEN 1 ELSE 0 END) AS `active_count`,
  SUM(CASE WHEN `status` = 'inactive' THEN 1 ELSE 0 END) AS `inactive_count`
FROM `employees`
GROUP BY `department`
```

## Rollup and Cube

**ROLLUP:**
```sql
SELECT
  `year`,
  `month`,
  `day`,
  SUM(`sales`) AS `total_sales`
FROM `sales_data`
GROUP BY ROLLUP(`year`, `month`, `day`)
```

**CUBE:**
```sql
SELECT
  `product`,
  `region`,
  SUM(`sales`) AS `total_sales`
FROM `sales_data`
GROUP BY CUBE(`product`, `region`)
```

## Error Prevention

**Handle NULL values:**
```sql
IFNULL(`column`, 'default_value')   -- Return default if NULL
COALESCE(`column`, 'default_value') -- Return first non-NULL
```

**String to number conversion:**
```sql
CAST(`string_column` AS INT)      -- To integer
CAST(`string_column` AS DECIMAL) -- To decimal
```

## Window Functions

```sql
ROW_NUMBER() OVER (PARTITION BY `department` ORDER BY `salary` DESC) AS `rank`
RANK() OVER (PARTITION BY `department` ORDER BY `salary` DESC) AS `rank`
DENSE_RANK() OVER (PARTITION BY `department` ORDER BY `salary` DESC) AS `rank`
```

## Performance Considerations

1. **Partition pruning:** Design queries to filter on partition columns
2. **Bucketing:** Join on bucket keys when possible
3. **Materialized views:** Use for frequently aggregated data
4. **Rollup:** Use for pre-aggregated summaries
