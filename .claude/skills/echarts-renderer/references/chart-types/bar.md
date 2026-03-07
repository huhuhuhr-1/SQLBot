# 条形图（Bar）图表类型

## 数据结构特性

### 必需特征
- **X 轴（维度）**：分类字段，通常是字符串
- **Y 轴（指标）**：数值型字段，通常是聚合结果
- **横向柱子**：柱子从左到右延伸
- **对比展示**：适合比较不同类别的数值大小

### 适用场景

#### ✅ 推荐使用条形图的情况：

1. **长标签名称**
   - 产品全称（较长）
   - 地区完整名称
   - 包含空格或特殊字符的类别名
   - 柱状图标签会重叠的情况

2. **类别数量较多**
   - 15-30 个类别
   - 柱状图会过于拥挤
   - 条形图横向排列更易阅读

3. **水平对比**
   - 从左到右的自然阅读顺序
   - 排名展示（水平条形图）
   - 进度条样式

4. **空间有限**
   - 垂直空间有限
   - 需要较长的标签
   - 移动端展示

#### ❌ 不推荐使用条形图的情况：

1. **时间序列** - 应使用折线图
2. **占比分析** - 应使用饼图
3. **标签很短** - 柱状图更直观
4. **连续趋势** - 应使用折线图

## SQL 查询模式

### 典型模式 1：长标签分类
```sql
SELECT
  product_full_name,
  SUM(sales_quantity) AS total_quantity
FROM sales
GROUP BY product_full_name
ORDER BY total_quantity DESC
LIMIT 20
```

**特征**：
- GROUP BY 长字符串字段
- 按指标降序排列
- LIMIT 控制类别数量

### 典型模式 2：地区排名
```sql
SELECT
  region_name,
  COUNT(*) AS customer_count
FROM customers
GROUP BY region_name
ORDER BY customer_count DESC
LIMIT 30
```

**特征**：
- 按地区分组
- 地区名称可能较长
- 排名展示

### 典型模式 3：多维度（带 series）
```sql
SELECT
  product_category,
  region,
  SUM(revenue) AS total_revenue
FROM sales
GROUP BY product_category, region
ORDER BY total_revenue DESC
LIMIT 1000
```

## 数据要求

### 字段类型
- **X 轴字段**：
  - 字符串（类别名称，可能较长）
  - 支持长标签、换行
  - 低基数到中等基数（< 30 个唯一值）

- **Y 轴字段**：
  - 数值类型（INT, BIGINT, DECIMAL, FLOAT）
  - 通常是聚合结果（COUNT, SUM, AVG）

### 数据量建议
- **最少**：2 个类别
- **推荐**：5-20 个类别
- **上限**：30 个类别（过多难以阅读）

## 配置生成规则

### 自动检测条件
满足以下条件时，推荐使用条形图：

1. **用户关键词**：问题包含"条形图"、"横向"
2. **数据特征**：
   - 分类标签较长（> 10 字符）
   - 类别数量较多（> 12 个）
   - 用户明确要求横向展示

3. **图表类型**：chart_type 参数为 "bar"

### 配置生成逻辑
```python
# 伪代码
dimensions = get_dimension_fields()
metrics = get_metric_fields()

# 判断是否应该用条形图
should_use_bar = (
    chart_type == "bar" or
    any(len(dim.display_name) > 10 for dim in dimensions) or
    len(dimensions) > 12
)

if should_use_bar and len(dimensions) >= 1 and len(metrics) >= 1:
    config = {
        "type": "bar",
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
```

### 字段映射规则
与柱状图相同，但方向不同：
- **X 轴**：仍然是维度字段（注意：条形图的 X 轴是横向，但字段映射逻辑相同）
- **Y 轴**：仍然是指标字段
- **区别**：视觉方向从纵向变为横向

## 输出格式

### 无 Series（单系列）
```json
{
  "type": "bar",
  "title": "产品销量排名",
  "axis": {
    "x": {"name": "产品名称", "value": "product_full_name"},
    "y": {"name": "销量", "value": "total_quantity"}
  }
}
```

### 有 Series（多系列）
```json
{
  "type": "bar",
  "title": "各地区产品销售额",
  "axis": {
    "x": {"name": "产品", "value": "product_category"},
    "y": {"name": "销售额", "value": "total_revenue"},
    "series": {"name": "地区", "value": "region"}
  }
}
```

## 用户问题示例

### 触发条形图的典型问题：

- "用条形图展示产品销量排名"
- "各地区客户数量对比（条形图）"
- "TOP 20 供应商采购金额"
- "部门员工数量横向对比"

### 对应的 SQL：

```sql
-- 产品销量排名
SELECT product_name, SUM(quantity) AS total_qty
FROM order_items
GROUP BY product_name
ORDER BY total_qty DESC
LIMIT 20;

-- 各地区客户数量
SELECT region_name, COUNT(*) AS customer_count
FROM customers
GROUP BY region_name
ORDER BY customer_count DESC
LIMIT 30;
```

## 最佳实践

1. **排序很重要**：
   - 使用 ORDER BY 让条子按有意义的顺序排列
   - 通常是按 Y 轴指标降序（DESC）
   - 排名场景从上到下递减

2. **限制类别数量**：
   - 使用 LIMIT 控制（建议 20-30）
   - 过滤小数据类别
   - TOP N 查询

3. **标签处理**：
   - 长标签自动换行
   - 考虑标签截断（显示前 N 个字符）
   - 鼠标悬停显示完整标签

4. **空间利用**：
   - 设置合适的图表高度
   - 确保所有标签可见
   - 考虑分页或滚动

## 与柱状图的对比

| 特性 | 条形图（Bar） | 柱状图（Column） |
|------|--------------|----------------|
| 方向 | 横向 | 纵向 |
| X 轴 | 维度（分类） | 维度（分类/时间） |
| Y 轴 | 指标（数值） | 指标（数值） |
| 标签 | 支持长标签 | 标签应短 |
| 类别数 | 适合较多（15-30） | 适合较少（5-15） |
| 排名 | 自然从上到下 | 需要确认方向 |
| 移动端 | 更友好 | 可能拥挤 |

### 选择决策树

```
需要对比不同类别的数值
    │
    ├─ 有时间维度且强调趋势？
    │   └─ YES → 折线图
    │
    ├─ 类别标签长度 > 10 字符？
    │   └─ YES → 条形图
    │
    ├─ 类别数量 > 15 个？
    │   └─ YES → 条形图
    │
    ├─ 排名展示（从高到低）？
    │   └─ YES → 条形图
    │
    └─ 其他情况 → 柱状图
```

## 注意事项

1. **标签长度管理**：
   - 过长标签考虑缩写
   - 支持标签换行
   - 鼠标悬停显示完整信息

2. **Y 轴范围**：
   - 从 0 开始（除非特殊需求）
   - 确保所有数据点可见
   - 考虑数值格式化

3. **颜色使用**：
   - 多系列时使用不同颜色
   - 支持图例切换
   - 保持颜色一致性

4. **性能考虑**：
   - 类别过多时考虑分页
   - 使用 LIMIT 限制数据量
   - 避免过长的查询时间

## 常见应用场景

### 1. 产品排名
```sql
SELECT product_name, SUM(sales) AS total_sales
FROM sales_data
GROUP BY product_name
ORDER BY total_sales DESC
LIMIT 20;
```
→ 条形图，产品名横向，销量纵向

### 2. 地区对比
```sql
SELECT region_full_name, COUNT(*) AS user_count
FROM users
GROUP BY region_full_name
ORDER BY user_count DESC;
```
→ 条形图，地区名横向，用户数纵向

### 3. 部门绩效
```sql
SELECT department_name, AVG(performance_score) AS avg_score
FROM employees
GROUP BY department_name
ORDER BY avg_score DESC;
```
→ 条形图，部门名横向，平均分纵向

## 可视化增强

1. **数据标签**：
   - 在条形末端显示具体数值
   - 添加百分比（如果是占比）
   - 格式化数值（千分位、单位）

2. **颜色编码**：
   - 按数值范围着色
   - 高亮 TOP N
   - 阈值标记

3. **交互功能**：
   - 点击条形钻取详情
   - 悬停显示完整信息
   - 排序切换
