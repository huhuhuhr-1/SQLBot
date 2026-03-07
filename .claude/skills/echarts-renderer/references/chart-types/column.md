# 柱状图（Column）图表类型

## 数据结构特性

### 必需特征
- **X 轴（维度）**：分类字段或时间字段，必须参与排序
- **Y 轴（指标）**：数值型字段，通常是聚合结果
- **纵向柱子**：柱子从下到上延伸
- **对比展示**：适合比较不同类别的数值大小

### 适用场景

#### ✅ 推荐使用柱状图的情况：

1. **分类对比**
   - 比较不同部门的销售额
   - 各地区用户数量对比
   - 产品销量排名
   - 月度/季度业绩对比

2. **排名展示**
   - TOP N 排行榜
   - 按数值排序的分类数据
   - 业绩排名

3. **时间对比**
   - 月度数据对比
   - 季度数据对比
   - 年度数据对比
   - 但不强调连续趋势

#### ❌ 不推荐使用柱状图的情况：

1. **连续趋势展示** - 应使用折线图
2. **占比分析** - 应使用饼图
3. **分类过多**（> 15 个）- 应考虑条形图或数据过滤
4. **长标签** - 应使用条形图

## SQL 查询模式

### 典型模式 1：单维度聚合
```sql
SELECT
  department,
  COUNT(*) AS emp_count
FROM employees
GROUP BY department
ORDER BY emp_count DESC
LIMIT 1000
```

**特征**：
- 有 GROUP BY（单字段）
- 有聚合函数（COUNT/SUM/AVG）
- 有 ORDER BY（通常按指标排序）
- 有 LIMIT

### 典型模式 2：时间维度聚合
```sql
SELECT
  DATE_FORMAT(order_date, '%Y-%m') AS month,
  SUM(amount) AS total_sales
FROM orders
GROUP BY month
ORDER BY month
LIMIT 1000
```

**特征**：
- GROUP BY 时间函数
- 聚合指标
- 按时间排序

### 典型模式 3：多维度（带 series）
```sql
SELECT
  region,
  product_category,
  SUM(revenue) AS total
FROM sales
GROUP BY region, product_category
ORDER BY total DESC
LIMIT 1000
```

**特征**：
- GROUP BY 多个字段
- 可选：一个作为 X 轴，一个作为 Series

## 数据要求

### 字段类型
- **X 轴字段**：
  - 字符串（类别名称）
  - 时间（年、月、日期）
  - 低基数（< 20 个唯一值最佳）

- **Y 轴字段**：
  - 数值类型（INT, BIGINT, DECIMAL, FLOAT）
  - 通常是聚合结果（COUNT, SUM, AVG）
  - 必须是可比较大小的数值

### 数据量建议
- **最少**：2 个类别（至少 2 根柱子）
- **推荐**：3-12 个类别
- **上限**：20 个类别（过多会拥挤）

## 配置生成规则

### 自动检测条件
满足以下条件时，推荐使用柱状图：

1. **用户关键词**：问题包含"柱状图"、"比较"、"排名"、"TOP"
2. **数据特征**：
   - 有 GROUP BY 和聚合函数
   - X 轴是分类字段（非连续时间）
   - 需要对比不同类别的数值

3. **图表类型**：chart_type 参数为 "column"

### 配置生成逻辑
```python
# 伪代码
dimensions = get_dimension_fields()  # GROUP BY 字段
metrics = get_metric_fields()        # 聚合字段

if len(dimensions) >= 1 and len(metrics) >= 1:
    config = {
        "type": "column",
        "title": generate_title(),
        "axis": {
            "x": {
                "name": dimensions[0].display_name,
                "value": dimensions[0].safe_name
            },
            "y": {
                "name": metrics[0].display_name,
                "value": metrics[0].safe_name
            }
        }
    }

    # 如果有第二个维度，添加 series
    if len(dimensions) > 1:
        config["axis"]["series"] = {
            "name": dimensions[1].display_name,
            "value": dimensions[1].safe_name
        }
```

### 字段映射规则
1. **X 轴选择优先级**：
   - 第一个 GROUP BY 字段
   - 时间字段（如果有）
   - 字符串类型字段

2. **Y 轴选择优先级**：
   - 聚合函数字段（COUNT/SUM/AVG）
   - 数值类型字段
   - 第一个数值字段

3. **Series 选择**：
   - 第二个 GROUP BY 字段（如果有）
   - 可选：用于分组显示多个系列

## 输出格式

### 无 Series（单系列）
```json
{
  "type": "column",
  "title": "部门人数统计",
  "axis": {
    "x": {"name": "部门", "value": "department"},
    "y": {"name": "人数", "value": "emp_count"}
  }
}
```

### 有 Series（多系列）
```json
{
  "type": "column",
  "title": "各地区产品销售额",
  "axis": {
    "x": {"name": "产品", "value": "product"},
    "y": {"name": "销售额", "value": "revenue"},
    "series": {"name": "地区", "value": "region"}
  }
}
```

## 用户问题示例

### 触发柱状图的典型问题：

- "用柱状图展示各部门人数"
- "比较各地区的销售额"
- "TOP 10 产品销量排名"
- "月度收入对比"
- "各部门平均工资对比"

### 对应的 SQL：

```sql
-- 各部门人数
SELECT department, COUNT(*) AS emp_count
FROM employees
GROUP BY department
ORDER BY emp_count DESC
LIMIT 1000;

-- 各地区销售额
SELECT region, SUM(amount) AS total_sales
FROM orders
GROUP BY region
ORDER BY total_sales DESC
LIMIT 1000;

-- TOP 10 产品
SELECT product_name, SUM(quantity) AS total_qty
FROM order_items
GROUP BY product_name
ORDER BY total_qty DESC
LIMIT 10;
```

## 最佳实践

1. **排序很重要**：
   - 使用 ORDER BY 让柱子按有意义的顺序排列
   - 通常是按 Y 轴指标降序（DESC）
   - 时间数据按时间升序（ASC）

2. **限制类别数量**：
   - 使用 LIMIT 或 WHERE 过滤
   - TOP N 查询（N ≤ 15）
   - 过滤小数据类别

3. **Y 轴聚合**：
   - 必须使用聚合函数（COUNT/SUM/AVG）
   - 使用有意义的别名
   - 考虑单位（千、万、亿）

4. **标签清晰**：
   - X 轴标签不要太长
   - Y 轴包含单位说明
   - 标题简洁明确

## 与条形图（Bar）的区别

| 特性 | 柱状图（Column） | 条形图（Bar） |
|------|-----------------|--------------|
| 方向 | 纵向（垂直） | 横向（水平） |
| X 轴 | 分类 | 数值 |
| Y 轴 | 数值 | 分类 |
| 适用 | 类别名称较短 | 类别名称较长 |
| 示例 | 月度数据、部门对比 | 长名称产品、地区全称 |

## 注意事项

1. **数据量控制**：
   - 避免过多类别导致拥挤
   - 考虑数据采样或聚合

2. **数值范围**：
   - Y 轴从 0 开始（除非有特殊原因）
   - 考虑数值格式化（千分位、单位）

3. **颜色区分**：
   - 多系列时使用不同颜色
   - 保持颜色一致性
   - 避免过多颜色

4. **交互设计**：
   - 鼠标悬停显示详细信息
   - 点击柱子可钻取
   - 支持图例切换系列
