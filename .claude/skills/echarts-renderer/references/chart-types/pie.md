# 饼图（Pie）图表类型

## 数据结构特性

### 必需特征
- **数值轴（Y）**：数值型字段，表示每个部分的大小
- **分类轴（Series）**：分类字段，表示不同的部分
- **部分与整体关系**：所有数值相加代表整体
- **占比展示**：重点展示各部分占整体的比例

### 适用场景

#### ✅ 推荐使用饼图的情况：

1. **占比分析**
   - 市场份额
   - 销售额占比
   - 用户分布
   - 预算分配

2. **分类较少**
   - 类别数量 2-8 个最佳
   - 最多不超过 10 个
   - 清晰展示各部分占比

3. **突出重点**
   - 强调某个部分的占比
   - 展示主要部分和次要部分
   - 对比几个主要类别

4. **百分比意义**
   - 百分比比绝对值更有意义
   - 相对大小关系重要
   - 各部分加起来等于 100%

#### ❌ 不推荐使用饼图的情况：

1. **类别过多**（> 10 个） - 应使用柱状图
2. **时间序列** - 应使用折线图
3. **绝对值对比** - 应使用柱状图
4. **相似占比** - 各部分大小相近，难以区分

## SQL 查询模式

### 典型模式 1：简单占比
```sql
SELECT
  category,
  SUM(amount) AS total_amount
FROM sales
GROUP BY category
ORDER BY total_amount DESC
LIMIT 10
```

**特征**：
- GROUP BY 单个分类字段
- 聚合求和（SUM）
- 通常按数值降序排列
- LIMIT 限制类别数量

### 典型模式 2：市场份额
```sql
SELECT
  company_name,
  SUM(revenue) AS market_share
FROM market_data
WHERE year = 2024
GROUP BY company_name
ORDER BY market_share DESC
LIMIT 8
```

**特征**：
- 按公司/产品分组
- 计算总额（代表市场总量）
- LIMIT 控制显示数量

### 典型模式 3：地区分布
```sql
SELECT
  region,
  COUNT(*) AS customer_count
FROM customers
GROUP BY region
ORDER BY customer_count DESC
LIMIT 10
```

**特征**：
- 按地区分组
- COUNT 计数
- 排序后取前几名

## 数据要求

### 字段类型
- **数值轴（Y）**：
  - 必须是数值类型（INT, BIGINT, DECIMAL, FLOAT）
  - 必须是聚合结果（SUM, COUNT）
  - 所有值的总和代表整体（100%）

- **分类轴（Series）**：
  - 字符串类型（类别名称）
  - 日期字符串（年、月等）
  - 低基数（2-10 个唯一值最佳）

### 数据量建议
- **最少**：2 个类别（至少 2 个部分）
- **推荐**：3-7 个类别
- **上限**：10 个类别（过多难以阅读）

### 数值要求
- 所有数值必须 ≥ 0
- 不能有负值
- 建议有明显的差异（不要太接近）

## 配置生成规则

### 自动检测条件
满足以下条件时，推荐使用饼图：

1. **用户关键词**：问题包含"饼图"、"占比"、"百分比"、"分布"、"份额"
2. **数据特征**：
   - 有 GROUP BY 和聚合函数
   - 类别数量适中（2-10 个）
   - 关注部分与整体的关系
   - 强调占比而非绝对值

3. **图表类型**：chart_type 参数为 "pie"

### 配置生成逻辑
```python
# 伪代码
dimensions = get_dimension_fields()
metrics = get_metric_fields()

if len(dimensions) >= 1 and len(metrics) >= 1:
    # 检查是否适合饼图
    if is_suitable_for_pie(dimensions, metrics):
        config = {
            "type": "pie",
            "title": generate_title(),
            "axis": {
                "y": {
                    "name": metrics[0].display_name,
                    "value": metrics[0].safe_name
                },
                "series": {
                    "name": dimensions[0].display_name,
                    "value": dimensions[0].safe_name
                }
            }
        }

def is_suitable_for_pie(dimensions, metrics):
    """判断是否适合饼图"""
    # 1. 只有一个维度
    if len(dimensions) > 1:
        return False

    # 2. 有聚合指标
    if not metrics:
        return False

    # 3. 类别数量适中（需要检查实际数据）
    # 这一步需要在有数据后验证

    return True
```

### 字段映射规则
1. **数值轴（Y）选择优先级**：
   - SUM 聚合字段（最常见）
   - COUNT 聚合字段
   - 第一个数值型聚合字段

2. **分类轴（Series）选择**：
   - 唯一的 GROUP BY 字段
   - 字符串类型字段
   - 类别名称字段

## 输出格式

```json
{
  "type": "pie",
  "title": "产品类别销售额占比",
  "axis": {
    "y": {"name": "销售额", "value": "total_amount"},
    "series": {"name": "产品类别", "value": "category"}
  }
}
```

**说明**：
- `y.value` 中的字段提供数值（扇区大小）
- `series.value` 中的字段提供分类标签（扇区名称）

## 用户问题示例

### 触发饼图的典型问题：

- "用饼图展示各产品类别销售额占比"
- "显示各地区市场份额分布"
- "部门人数占比情况"
- "不同支付方式的使用比例"

### 对应的 SQL：

```sql
-- 产品类别销售额占比
SELECT
  category,
  SUM(amount) AS total_amount
FROM sales
GROUP BY category
ORDER BY total_amount DESC
LIMIT 10;

-- 市场份额分布
SELECT
  company,
  SUM(revenue) AS market_share
FROM market_data
WHERE year = 2024
GROUP BY company
ORDER BY market_share DESC
LIMIT 8;

-- 部门人数占比
SELECT
  department,
  COUNT(*) AS emp_count
FROM employees
GROUP BY department
ORDER BY emp_count DESC;
```

## 最佳实践

1. **限制类别数量**：
   - 使用 LIMIT 或 WHERE 过滤
   - 最多显示 8-10 个类别
   - 考虑将小类别合并为"其他"

2. **排序策略**：
   - 通常按数值降序排列（DESC）
   - 最大部分从 12 点方向开始
   - 顺时针方向展示

3. **数据聚合**：
   - 必须使用聚合函数（SUM/COUNT）
   - 确保数据完整性（覆盖 100%）
   - 考虑添加"其他"类别

4. **标签处理**：
   - 标签要简洁
   - 显示百分比和数值
   - 鼠标悬停显示详细信息

5. **颜色选择**：
   - 使用对比明显的颜色
   - 避免过于相近的颜色
   - 保持颜色一致性

## 高级功能

### 1. 其他类别处理
```sql
-- 将小类别合并为"其他"
SELECT
  CASE
    WHEN total_amount < 1000 THEN '其他'
    ELSE category
  END AS category_group,
  SUM(total_amount) AS amount
FROM (
  SELECT category, SUM(amount) AS total_amount
  FROM sales
  GROUP BY category
) subquery
GROUP BY category_group
ORDER BY amount DESC;
```

### 2. 环形图（Donut Chart）
- 饼图的变体
- 中心空白区域显示总数或标签
- 配置基本相同，只是样式差异

### 3. 多级饼图
- 外圈：大类
- 内圈：小类
- 需要两个 GROUP BY 字段
- 实际上更推荐使用旭日图

## 常见问题

### Q1: 类别太多怎么办？
**A**: 使用以下策略：
1. 只显示 TOP N（LIMIT）
2. 将小类别合并为"其他"
3. 改用柱状图展示

### Q2: 如何显示百分比？
**A**:
- 前端计算：数值 / 总和 × 100
- 后端计算：SQL 中添加百分比计算
- 工具提示：悬停时显示

### Q3: 饼图 vs 柱状图如何选择？
**A**:
```
关注占比 → 饼图
关注对比 → 柱状图
类别 > 10 → 柱状图
类别少（2-8） → 饼图
```

### Q4: 数值差异太小怎么办？
**A**:
1. 考虑使用柱状图（更容易看出差异）
2. 放大显示差异部分
3. 使用表格显示精确数值

## 与其他图表的对比

| 图表类型 | 适用场景 | 类别数 | 重点 |
|---------|---------|--------|------|
| 饼图 | 占比分析 | 2-8 个 | 百分比、部分与整体 |
| 柱状图 | 数值对比 | 5-15 个 | 绝对值、排名 |
| 条形图 | 标签较长 | 5-30 个 | 排名、长标签 |
| 折线图 | 时间趋势 | 7+ 个 | 变化趋势、连续性 |
| 表格 | 详细数据 | 不限 | 精确数值、多字段 |

## 注意事项

1. **避免使用场景**：
   - 不适合展示随时间变化的趋势
   - 不适合类别过多的情况
   - 不需要强调差异的场景

2. **数据完整性**：
   - 确保所有类别加起来等于 100%
   - 考虑是否需要"其他"类别
   - 注意缺失数据

3. **视觉设计**：
   - 使用对比明显的颜色
   - 避免过多扇区（< 8 个最佳）
   - 标签清晰易读

4. **交互功能**：
   - 悬停显示详细信息和百分比
   - 点击扇区钻取或筛选
   - 支持图例切换显示

5. **可访问性**：
   - 提供文本替代
   - 确保颜色对比度足够
   - 考虑色盲友好配色
