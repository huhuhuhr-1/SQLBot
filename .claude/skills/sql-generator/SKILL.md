---
name: sql-generator
description: 将自然语言问题转换为 SQL 查询，支持多种数据库类型（PostgreSQL、MySQL、Oracle、SQL Server、ClickHouse、Doris、StarRocks）。自动应用数据库特定的语法规则，智能推荐图表类型，生成查询元数据。支持 M-Schema 格式的数据库结构输入。
---

# SQL 生成器

## 概述

将自然语言问题转换为生产级 SQL 查询。本 SKILL 理解数据库结构，应用数据库特定的语法规则，并提供智能的图表可视化建议。

## 快速开始

**基本用法：**
```
输入：用户问题 + 数据库结构（M-Schema 格式）+ 数据库类型
输出：SQL 查询 + 元数据（使用的表、图表类型推荐、标题）
```

**示例：**
```yaml
问题："查询各个国家每年的GDP"
数据库：PostgreSQL
结构： 【DB_ID】 test_db, 测试数据库
        【Schema】
        # Table: test_country_gdp, 各国GDP数据
        [
        (country: varchar, 国家),
        (year: varchar, 年份),
        (gdp: bigint, GDP(美元)),
        ]

输出：{
  "success": true,
  "sql": "SELECT \"country\" AS \"country_name\", \"year\" AS \"year\", \"gdp\" AS \"gdp\" FROM \"test\".\"test_country_gdp\" ORDER BY \"country\", \"year\" LIMIT 1000",
  "tables": ["test_country_gdp"],
  "chart-type": "line",
  "brief": "各国年度GDP查询"
}
```

## 核心工作流程

### 步骤 1：解析输入参数

从用户请求中提取以下参数：

1. **question**（必需）：自然语言问题
2. **db_schema**（必需）：M-Schema 格式的数据库结构
3. **db_type**（必需）：数据库类型（PostgreSQL、MySQL、Oracle、SQL Server、ClickHouse 等）
4. **terminologies**（可选）：业务术语词典
5. **enable_query_limit**（可选）：是否启用数据量限制（默认：true）
6. **custom_prompt**（可选）：额外的提示词指令

### 步骤 2：加载数据库特定规则

根据 `db_type` 从 `references/database-rules/` 加载相应的数据库规则文件：

- **PostgreSQL**：`references/database-rules/postgresql.md`
- **MySQL**：`references/database-rules/mysql.md`
- **Oracle**：`references/database-rules/oracle.md`
- **SQL Server**：`references/database-rules/sqlserver.md`
- **ClickHouse**：`references/database-rules/clickhouse.md`
- **Doris**：`references/database-rules/doris.md`
- **StarRocks**：`references/database-rules/starrocks.md`

每个规则文件包含：
- 引号字符要求
- LIMIT 语法
- 函数特定规则
- SQL 示例模式

### 步骤 3：构建系统提示词

使用以下组件构建系统提示词：

**基础指令：**
```
你是"SQLBOT"，智能问数小助手，可以根据用户提问，专业生成SQL与可视化图表。
你当前的任务是根据给定的表结构和用户问题生成SQL语句、对话标题、可能适合展示的图表类型以及该SQL中所用到的表名。
```

**核心规则：**
1. 只生成 SELECT 查询（不允许 INSERT/UPDATE/DELETE）
2. 默认 LIMIT 1000（除非 `enable_query_limit=false`）
3. 应用从规则加载的数据库特定语法
4. 不要编造 schema 中不存在的表
5. 返回 JSON 格式，包含必需字段

**JSON 输出格式：**
```json
{
  "success": true/false,
  "sql": "生成的 SQL 语句",
  "tables": ["table1", "table2"],
  "chart-type": "table/column/bar/line/pie",
  "brief": "对话标题（≤20字符）",
  "message": "success=false 时的错误信息"
}
```

### 步骤 4：应用时间格式化规则

当 SQL 包含时间字段时：

- **未指定时间排序**：默认升序排序
- **时间格式映射**：
  - 提问="时间" → 格式化为 `yyyy-MM-dd HH:mm:ss`
  - 提问="日期" → 格式化为 `yyyy-MM-dd`
  - 提问="年月" → 格式化为 `yyyy-MM`
  - 提问="年" → 格式化为 `yyyy`

应用数据库特定的时间格式化函数。

### 步骤 5：确定图表类型

遵循图表选择原则：

- **时间趋势** → `line`（例如：每月销售额）
- **分类对比** → `column` 或 `bar`（例如：各地区销售额）
- **占比** → `pie`（例如：市场份额）
- **原始数据** → `table`（例如：用户列表）

**图表特定的 SQL 要求：**
- `column`、`bar`、`line`：必须有维度字段（已排序）+ 指标字段
- `pie`：必须有分类字段 + 数值字段
- 支持可选的 series（分类）字段

### 步骤 6：处理多表关联

当关联多个表时：

1. 优先使用标记为 "Primary key"/"ID"/"主键" 的字段
2. 生成表别名（不加 AS 关键字）
3. 对所有标识符应用正确的引号字符
4. 使用适合数据库类型的 JOIN 语法

### 步骤 7：生成最终 SQL

按顺序应用所有规则：
1. 基础查询结构
2. 数据库特定的引号字符
3. 表别名
4. 字段格式化（时间、百分比等）
5. LIMIT 子句
6. ORDER BY 子句

## 输入结构格式（M-Schema）

**必需格式：**
```yaml
【DB_ID】 database_name, description
【Schema】
# Table: schema.table_name, table_comment
[
  (column_name: data_type, column_comment, examples:['example1','example2']),
  (column2: data_type, comment),
  ...
]
# Table: schema.table2, ...
```

**示例：**
```yaml
【DB_ID】 sales_db, 销售数据库
【Schema】
# Table: sales.orders, 订单表
[
  (id: bigint, Primary key, ID),
  (user_id: bigint, 用户ID),
  (amount: decimal, 订单金额),
  (create_time: timestamp, 创建时间),
]
# Table: sales.users, 用户表
[
  (id: bigint, Primary key, ID),
  (name: varchar, 用户名),
  (email: varchar, 邮箱),
]
```

## 数据库特定规则

从 `references/database-rules/{database}.md` 加载数据库特定规则。每个文件包含：

### PostgreSQL 规则
- 引号：双引号（`"`）
- 限制：`LIMIT n`
- 时间函数：`TO_TIMESTAMP()`、`TO_CHAR()`
- 拼接：`||`
- 百分比：`ROUND(x * 100, 2) || '%'`

### MySQL 规则
- 引号：反引号（`` ` ``）
- 限制：`LIMIT n`
- 时间函数：`DATE_FORMAT()`、`STR_TO_DATE()`
- 拼接：`CONCAT()`
- 百分比：`CONCAT(ROUND(x * 100, 2), '%')`

### SQL Server 规则
- 引号：方括号（`[`）
- 限制：`TOP n` 或 `OFFSET-FETCH`
- 时间函数：`CONVERT()`、`DATE_FORMAT()`
- 拼接：`+`
- 百分比：`CONVERT(VARCHAR, ROUND(x * 100, 2)) + '%'`

### Oracle 规则
- 引号：双引号（`"`）
- 限制：`FETCH FIRST n ROWS ONLY`
- 时间函数：`TO_DATE()`、`TO_CHAR()`
- 拼接：`||`
- 百分比：`ROUND(x * 100, 2) || '%'`

完整规则请参见 `references/database-rules/`。

## 常见模式

### 模式 1：简单查询
```
输入："查询所有用户"
结构：users(id, name, email, create_time)
输出：SELECT "id", "name", "email", "create_time" FROM "users" LIMIT 1000
```

### 模式 2：聚合与分组
```
输入："统计各个部门的员工数量"
结构：employees(id, name, department_id), departments(id, name)
输出：SELECT "d"."name" AS "dept_name", COUNT("e"."id") AS "emp_count"
        FROM "departments" "d" JOIN "employees" "e" ON "d"."id" = "e"."department_id"
        GROUP BY "d"."name" ORDER BY "emp_count" DESC LIMIT 1000
```

### 模式 3：时间序列与图表
```
输入："使用折线图展示每月销售额趋势"
结构：orders(id, amount, create_time)
输出：{
  "sql": "SELECT DATE_FORMAT(\"create_time\", '%Y-%m') AS \"month\", SUM(\"amount\") AS \"total_sales\" FROM \"orders\" GROUP BY \"month\" ORDER BY \"month\" LIMIT 1000",
  "chart-type": "line"
}
```

### 模式 4：条件过滤
```
输入："查询活跃用户（status=1）的数量"
结构：users(id, name, status)
输出：SELECT COUNT("id") AS "active_count" FROM "users" WHERE "status" = 1 LIMIT 1000
```

## 错误处理

**无法生成 SQL 时：**
```json
{
  "success": false,
  "message": "无法生成 SQL：[具体原因]"
}
```

**常见失败原因：**
- Schema 不包含所需的表/字段
- 问题需要非 SELECT 操作
- 问题过于模糊
- 数据库不支持请求的操作

**务必在 message 字段中包含具体原因。**

## 最佳实践

1. **字段选择**：用户未指定字段时，列出 schema 中所有非敏感字段
2. **字段顺序**：保持 schema 定义的字段顺序
3. **别名策略**：
   - 普通字段：不需要别名
   - 函数字段：必须有别名（例如：`COUNT("id") AS "total"`）
   - 中文字段：添加英文别名
4. **避免歧义**：永不输出重复或冗余内容
5. **Schema 遵循**：仅使用 schema 中明确定义的表/字段

## 资源

### references/database-rules/
数据库特定的语法和规则文件。仅加载与用户 `db_type` 参数匹配的文件。

- `postgresql.md` - PostgreSQL 语法规则
- `mysql.md` - MySQL 语法规则
- `oracle.md` - Oracle 语法规则
- `sqlserver.md` - SQL Server 语法规则
- `clickhouse.md` - ClickHouse 语法规则
- `doris.md` - Apache Doris 语法规则
- `starrocks.md` - StarRocks 语法规则
