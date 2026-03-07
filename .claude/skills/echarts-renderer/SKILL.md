---
name: echarts-renderer
description: 从 SQL 查询结果和用户问题生成 ECharts 和 G2 图表配置。用于创建可视化规范，包括表格、柱状图、条形图、折线图、饼图，支持自动轴检测、字段映射和图表类型推荐。基于查询结构和内容分析进行数据驱动的智能图表选择。
---

# ECharts 渲染器

## 概述

从 SQL 查询结果生成 ECharts 和 G2 可视化库的生产级图表配置。本 SKILL 分析查询结构、检测字段、将数据映射到图表轴，并创建优化的可视化方案。

## 快速开始

**基本用法：**
```
输入：SQL 查询 + 查询结果数据 + 用户问题 + 推荐的图表类型
输出：图表配置 JSON（ECharts/G2 格式）
```

**示例：**
```yaml
SQL: SELECT country, gdp FROM countries WHERE year = 2024 ORDER BY gdp DESC
数据: [{"country": "China", "gdp": 12345}, {"country": "USA", "gdp": 9876}]
图表类型: pie
问题: "饼图展示各国GDP占比"

输出: {
  "type": "pie",
  "title": "各国GDP占比",
  "axis": {
    "y": {"name": "GDP", "value": "gdp"},
    "series": {"name": "国家", "value": "country"}
  }
}
```

## 核心工作流程

### 步骤 1：分析查询结构

从 SQL 查询中提取信息：

1. **列出所有 SELECT 列**（包括别名）
2. **识别聚合函数**（COUNT、SUM、AVG 等）
3. **检测 GROUP BY 列**（维度）
4. **检查 ORDER BY 子句**（排序）

**分析示例：**
```sql
SELECT
  department,
  COUNT(id) AS emp_count
FROM employees
GROUP BY department
ORDER BY emp_count DESC
```

分析结果：
- 列：`department`（维度）、`emp_count`（指标）
- 聚合：`COUNT(id)`
- 分组：`department`
- 排序：`emp_count DESC`

### 步骤 2：检测字段类型

分析数据以确定字段类型：

**维度字段**（分类）：
- 字符串值（国家、名称、部门等）
- 日期/时间值（年、月、日等）
- 低基数（< 50 个唯一值）

**指标字段**（数值）：
- 数值（计数、金额、GDP 等）
- 聚合结果
- 连续值

**自动检测示例：**
```javascript
// 数据分析示例
[
  {"country": "China", "gdp": 12345, "year": "2024"},
  {"country": "USA", "gdp": 9876, "year": "2024"}
]

// 检测到的类型：
- country: 维度（字符串，分类）
- gdp: 指标（数值）
- year: 维度（基于时间）
```

### 步骤 3：将字段映射到图表轴

根据图表类型，将字段映射到适当的轴：

**对于 `table`（表格）：**
```json
{
  "type": "table",
  "title": "数据表格",
  "columns": [
    {"name": "字段中文名", "value": "column_name"},
    {"name": "字段中文名2", "value": "column2"}
  ]
}
```

**对于 `column`（柱状图 - 纵向）：**
```json
{
  "type": "column",
  "title": "图表标题",
  "axis": {
    "x": {"name": "X轴名称", "value": "x_field"},
    "y": {"name": "Y轴名称", "value": "y_field"},
    "series": {"name": "系列名称", "value": "series_field"}
  }
}
```

**对于 `bar`（条形图 - 横向）：**
```json
{
  "type": "bar",
  "title": "图表标题",
  "axis": {
    "x": {"name": "X轴名称", "value": "x_field"},
    "y": {"name": "Y轴名称", "value": "y_field"},
    "series": {"name": "系列名称", "value": "series_field"}
  }
}
```

**对于 `line`（折线图）：**
```json
{
  "type": "line",
  "title": "图表标题",
  "axis": {
    "x": {"name": "X轴名称", "value": "x_field"},
    "y": {"name": "Y轴名称", "value": "y_field"},
    "series": {"name": "系列名称", "value": "series_field"}
  }
}
```

**对于 `pie`（饼图）：**
```json
{
  "type": "pie",
  "title": "图表标题",
  "axis": {
    "y": {"name": "数值名称", "value": "value_field"},
    "series": {"name": "分类名称", "value": "category_field"}
  }
}
```

### 步骤 4：生成图表标题

基于以下因素创建简洁、描述性的标题：
- 用户问题的意图
- 可视化的数据
- 图表类型

**标题生成原则：**
- 保持简短（首选 ≤ 20 字符）
- 使用中文（如果用户问题是中文）
- 描述图表显示的内容
- 包含关键指标或维度

**示例：**
```
"各国GDP统计"         // 各国 GDP
"部门人数统计"        // 按部门统计员工数
"月度销售趋势"        // 每月销售趋势
"产品类别占比"        // 产品类别比例
```

### 步骤 5：处理特殊情况

**多个指标字段：**
当 SQL 有多个数值字段时，根据以下因素选择最相关的一个：
- 用户问题提及
- 聚合优先级（COUNT > SUM > AVG）
- 字段名语义相关性

**无合适的图表类型：**
```json
{
  "type": "error",
  "reason": "无法生成图表：[具体原因]"
}
```

## 图表类型选择规则

### 表格（Table）
**使用场景：**
- 用户要求"列表"、"详情"
- 查询返回多列（> 5 列）
- 数据是原始/未聚合的
- 没有明确的可视化模式

### 柱状图（Column - 纵向柱子）
**使用场景：**
- 用户要求"柱状图"
- 比较分类（时间段、分组等）
- X 轴有分类/时间数据
- Y 轴有数值指标

### 条形图（Bar - 横向柱子）
**使用场景：**
- 用户要求"条形图"
- 与柱状图相同但横向排列
- 长分类标签（更好的可读性）

### 折线图（Line）
**使用场景：**
- 用户要求"折线图"、"趋势图"
- 显示时间趋势
- X 轴基于时间（年、月、日期等）

### 饼图（Pie）
**使用场景：**
- 用户要求"饼图"、"占比"
- 显示整体的部分
- 计算百分比/比率
- 有限类别（推荐 < 10 个）

## 输入参数

**必需：**
- `sql`：SQL 查询字符串
- `question`：用户的自然语言问题
- `chart_type`：推荐的图表类型（table/column/bar/line/pie）
- `data`：查询结果数据（对象 JSON 数组）

**可选：**
- `lang`：输出语言（默认："简体中文"）
- `custom_title`：自定义图表标题

## 字段映射算法

**字段选择的优先级顺序：**

1. **明确用户提及** - 如果问题提及特定字段名
2. **聚合结果** - 优先使用 COUNT/SUM/AVG 结果
3. **GROUP BY 字段** - 用作维度
4. **ORDER BY 字段** - 用作排序轴
5. **语义分析** - 将字段名匹配到问题关键词

## 常见模式

### 模式 1：简单聚合
```sql
SELECT category, COUNT(*) AS count
FROM items
GROUP BY category
```
→ 柱状图或饼图

### 模式 2：时间序列
```sql
SELECT DATE_FORMAT(date, '%Y-%m') AS month, SUM(amount) AS total
FROM sales
GROUP BY month
ORDER BY month
```
→ 折线图（时间趋势）

### 模式 3：多维度
```sql
SELECT region, product, SUM(revenue) AS total
FROM sales
GROUP BY region, product
```
→ 带系列的柱状图/折线图（地区或产品）

### 模式 4：原始数据
```sql
SELECT id, name, email, created_at
FROM users
LIMIT 1000
```
→ 表格（多列，无聚合）

## 错误处理

**返回错误 JSON 当：**
```json
{
  "type": "error",
  "reason": "无法生成图表配置：[具体原因]"
}
```

## 最佳实践

1. **始终验证**映射的字段存在于数据中
2. **优先使用聚合字段**作为 Y 轴（指标）
3. **优先使用分组字段**作为 X 轴（维度）
4. **包含系列**当存在多个分类时
5. **生成描述性标题**以解释可视化
6. **使用中文名称**当用户问题是中文时
7. **处理别名** - 存在时使用 `AS` 别名
8. **移除引号**从 `value` 字段中的字段名

## 资源

### scripts/
可执行的 Python 脚本，用于数据处理和转换。

- `data_converter.py` - 数据转换工具
  - 解析 SQL 查询结构
  - 检测字段类型（维度/指标）
  - 根据图表类型生成配置
  - 支持命令行使用：`python scripts/data_converter.py "SELECT..." "chart_type"`

**使用示例**：
```bash
# 从 SQL 查询结果生成图表配置
python scripts/data_converter.py \
  "SELECT department, COUNT(*) AS emp_count FROM employees GROUP BY department" \
  "column"
```

### references/chart-types/
详细的图表类型配置模式和使用指南。当需要特定图表类型指导时加载这些文件。

- `table.md` - 表格图表详细说明
  - 数据结构特性
  - 适用场景
  - SQL 查询模式
  - 配置生成规则

- `column.md` - 柱状图详细说明
  - 数据结构特性
  - 适用场景（对比、排名）
  - SQL 查询模式
  - 与条形图的区别

- `bar.md` - 条形图详细说明
  - 数据结构特性
  - 适用场景（长标签、多类别）
  - SQL 查询模式
  - 与柱状图的区别

- `line.md` - 折线图详细说明
  - 数据结构特性（时间序列）
  - 适用场景（趋势分析）
  - 时间处理函数参考
  - 与柱状图的区别

- `pie.md` - 饼图详细说明
  - 数据结构特性（占比分析）
  - 适用场景（市场份额、分布）
  - 配置生成规则
  - 与其他图表的对比

**何时使用参考文档**：
- 不确定图表类型选择时 → 查阅对应图表类型的"适用场景"
- 需要编写特定查询时 → 查阅"SQL 查询模式"
- 遇到配置问题时 → 查阅"配置生成规则"
- 了解最佳实践时 → 查阅"最佳实践"和"注意事项"
