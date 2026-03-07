# MySQL SQL Generation Rules

## Quote Rules

**Must use backticks (`` ` ``) for identifiers that are:**
- Keywords (`order`, `group`, `desc`, `table`, etc.)
- Contain special characters
- Need case preservation
- **Good practice: Use backticks for all identifiers**

**Dot notation format:**
```sql
`schema`.`table`          -- Correct
`schema`.`table`.`column` -- Correct
```

## LIMIT Syntax

**Standard LIMIT:**
```sql
SELECT ... FROM ... LIMIT 1000
```

**With OFFSET:**
```sql
SELECT ... FROM ... LIMIT 1000 OFFSET 10
-- Alternative syntax:
SELECT ... FROM ... LIMIT 10, 1000
```

## Table Aliases

**Required for all tables, no AS keyword:**
```sql
FROM `schema`.`table_name` `t1`     -- Correct
FROM `schema`.`table_name` AS `t1`  -- WRONG - don't use AS
```

## Field Aliases

**Function fields MUST have aliases:**
```sql
COUNT(`id`) AS `total_count`           -- Correct
COUNT(`id`)                           -- WRONG - missing alias
SUM(`amount`) AS `total_amount`       -- Correct
```

**Regular fields:** Aliases optional
```sql
`column_name` AS `alias`  -- Optional but recommended
`column_name`             -- Also acceptable
```

**Chinese/special character fields:** Add English alias
```sql
`订单ID` AS `order_id`    -- Correct
`订单ID`                  -- WRONG - needs English alias
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
```

## String Operations

**Concatenation:**
```sql
CONCAT(`first_name`, ' ', `last_name`) AS `full_name`
```

**String matching:**
```sql
`column_name` LIKE '%pattern%'
`column_name` REGEXP 'regex_pattern'
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

## JOIN Syntax

```sql
FROM `table1` `t1`
INNER JOIN `table2` `t2` ON `t1`.`id` = `t2`.`t1_id`
LEFT JOIN `table3` `t3` ON `t1`.`id` = `t3`.`t1_id`
```

## Conditional Logic

**IF statement:**
```sql
IF(`status` = 1, 'active', 'inactive') AS `status_text`
```

**CASE statement:**
```sql
CASE
  WHEN `amount` > 1000 THEN 'high'
  WHEN `amount` > 500 THEN 'medium'
  ELSE 'low'
END AS `amount_category`
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

## Error Prevention

**Avoid keyword conflicts:**
```sql
SELECT `user`, `order`, `group`, `select` FROM `table`  -- All quoted
```

**Handle NULL values:**
```sql
IFNULL(`column`, 'default_value')   -- Return default if NULL
COALESCE(`column`, 'default_value') -- Return first non-NULL
```

**String to number conversion:**
```sql
CAST(`string_column` AS SIGNED)     -- To integer
CAST(`string_column` AS DECIMAL)    -- To decimal
```
