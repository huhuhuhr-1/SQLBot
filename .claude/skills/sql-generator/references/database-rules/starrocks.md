# StarRocks SQL Generation Rules

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

**Approximate aggregation:**
```sql
NDV(`column`)         -- Approximate distinct count
PERCENTILE(`column`, 0.5)  -- Approximate percentile
HLL_HASH_AGG(`column`)      -- HyperLogLog aggregation
```

## JOIN Syntax

```sql
FROM `table1` `t1`
INNER JOIN `table2` `t2` ON `t1`.`id` = `t2`.`t1_id`
LEFT JOIN `table3` `t3` ON `t1`.`id` = `t3`.`t1_id`
```

**Note:** StarRocks supports various JOIN types including:
- INNER JOIN
- LEFT OUTER JOIN
- RIGHT OUTER JOIN
- FULL OUTER JOIN
- CROSS JOIN
- SEMI JOIN / ANTI JOIN

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

**GROUPING SETS:**
```sql
SELECT
  `product`,
  `region`,
  SUM(`sales`) AS `total_sales`
FROM `sales_data`
GROUP BY GROUPING SETS ((`product`), (`region`), ())
```

## Window Functions

```sql
ROW_NUMBER() OVER (PARTITION BY `department` ORDER BY `salary` DESC) AS `row_num`
RANK() OVER (PARTITION BY `department` ORDER BY `salary` DESC) AS `rank`
DENSE_RANK() OVER (PARTITION BY `department` ORDER BY `salary` DESC) AS `dense_rank`
LAG(`column`, 1) OVER (PARTITION BY `id` ORDER BY `time`) AS `prev_value`
LEAD(`column`, 1) OVER (PARTITION BY `id` ORDER BY `time`) AS `next_value`
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

## Performance Considerations

1. **Partition pruning:** Filter on partition columns
2. **Bucketing:** Join on bucket keys for optimal performance
3. **Materialized views:** Use for pre-aggregated data
4. **Primary Key tables:** Faster point queries and updates
5. **Aggregate tables:** Pre-aggregate for faster analytics

## StarRocks-Specific Features

**Primary Key table:**
```sql
-- Better for real-time updates and point queries
CREATE TABLE ... PRIMARY KEY (id) DISTRIBUTED BY HASH (id)
```

**Aggregate table:**
```sql
-- Pre-aggregate data for faster queries
CREATE TABLE ... AGGREGATE KEY (dim1, dim2)
  (
    `metric1` SUM,
    `metric2` MAX,
    `metric3` MIN
  )
```

**Duplicate table:**
```sql
-- No aggregation, store all data
CREATE TABLE ... DUPLICATE KEY (dim1, dim2)
```
