# 折线图（Line）图表类型

## 数据结构特性

### 必需特征
- **X 轴（时间维度）**：时间字段，必须按时间排序
- **Y 轴（指标）**：数值型字段，通常是聚合结果
- **连续性**：数据点之间有连续性关系
- **趋势展示**：重点展示数据随时间的变化趋势

### 适用场景

#### ✅ 推荐使用折线图的情况：

1. **时间趋势分析**
   - 销售额月度趋势
   - 用户增长曲线
   - 订单量变化
   - 访问量统计

2. **连续变化**
   - 数据随时间连续变化
   - 强调数据点的连续性
   - 展示上升/下降趋势

3. **多系列对比**
   - 多个产品的时间趋势对比
   - 不同地区的业绩趋势
   - 同比/环比分析

4. **波动分析**
   - 数据波动情况
   - 峰值和谷值识别
   - 周期性模式

#### ❌ 不推荐使用折线图的情况：

1. **无时间顺序** - 应使用柱状图
2. **占比分析** - 应使用饼图
3. **离散分类** - 应使用柱状图
4. **单一时间点** - 应使用表格或柱状图

## SQL 查询模式

### 典型模式 1：月度趋势
```sql
SELECT
  DATE_FORMAT(order_date, '%Y-%m') AS month,
  SUM(amount) AS total_sales,
  COUNT(*) AS order_count
FROM orders
WHERE order_date >= '2024-01-01'
GROUP BY month
ORDER BY month
LIMIT 1000
```

**特征**：
- GROUP BY 时间函数（DATE_FORMAT）
- 按时间排序（ORDER BY month）
- 聚合指标（SUM/COUNT）
- 有时间范围过滤（WHERE）

### 典型模式 2：日度趋势
```sql
SELECT
  DATE(create_time) AS date,
  COUNT(*) AS daily_users
FROM user_logs
WHERE create_time >= NOW() - INTERVAL 30 DAY
GROUP BY date
ORDER BY date
LIMIT 1000
```

**特征**：
- GROUP BY 日期
- 最近 N 天的过滤
- 按日期排序

### 典型模式 3：多系列趋势
```sql
SELECT
  DATE_FORMAT(order_date, '%Y-%m') AS month,
  category,
  SUM(amount) AS category_sales
FROM orders
WHERE order_date >= '2024-01-01'
GROUP BY month, category
ORDER BY month, category
LIMIT 1000
```

**特征**：
- GROUP BY 时间 + 类别
- 两个维度：一个作为 X 轴，一个作为 Series

## 数据要求

### 字段类型
- **X 轴字段（时间）**：
  - DATE 类型
  - DATETIME/TIMESTAMP 类型
  - 时间格式化后的字符串（YYYY-MM, YYYY-MM-DD）
  - 必须可排序

- **Y 轴字段（指标）**：
  - 数值类型（INT, BIGINT, DECIMAL, FLOAT）
  - 聚合结果（SUM, COUNT, AVG）
  - 连续变化的数值

### 数据量建议
- **最少**：2 个时间点（至少 2 个点连成线）
- **推荐**：7-30 个时间点
- **上限**：365 个时间点（过多会密集，考虑按周/月聚合）

### 时间粒度
- **年度**：5-10 年数据
- **月度**：12-36 个月数据
- **周度**：26-52 周数据
- **日度**：7-90 天数据
- **小时**：24-48 小时数据

## 配置生成规则

### 自动检测条件
满足以下条件时，推荐使用折线图：

1. **用户关键词**：问题包含"折线图"、"趋势图"、"趋势"、"变化"
2. **数据特征**：
   - X 轴是时间字段
   - 有 GROUP BY 时间函数
   - 有 ORDER BY 时间字段
   - 需要展示时间序列变化

3. **图表类型**：chart_type 参数为 "line"

### 配置生成逻辑
```python
# 伪代码
time_dimensions = get_time_dimension_fields()  # 时间字段
metrics = get_metric_fields()                   # 聚合字段

if len(time_dimensions) >= 1 and len(metrics) >= 1:
    config = {
        "type": "line",
        "title": generate_title(),
        "axis": {
            "x": {
                "name": time_dimensions[0].display_name,
                "value": time_dimensions[0].safe_name
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
   - 时间字段（DATE/DATETIME）
   - 时间函数结果（YEAR, MONTH, DATE_FORMAT）
   - 包含时间关键词的字段（date, time, year, month）

2. **Y 轴选择优先级**：
   - 聚合函数字段（SUM/COUNT/AVG）
   - 数值类型字段
   - 连续变化的指标

3. **Series 选择**：
   - 非时间的第二个维度
   - 用于分组显示多条趋势线

## 输出格式

### 无 Series（单条线）
```json
{
  "type": "line",
  "title": "月度销售趋势",
  "axis": {
    "x": {"name": "月份", "value": "month"},
    "y": {"name": "销售额", "value": "total_sales"}
  }
}
```

### 有 Series（多条线）
```json
{
  "type": "line",
  "title": "各地区销售趋势",
  "axis": {
    "x": {"name": "月份", "value": "month"},
    "y": {"name": "销售额", "value": "total_sales"},
    "series": {"name": "地区", "value": "region"}
  }
}
```

## 用户问题示例

### 触发折线图的典型问题：

- "用折线图展示销售额趋势"
- "显示最近30天的用户增长"
- "月度收入变化趋势"
- "各季度的订单量趋势"
- "比较不同产品的时间趋势"

### 对应的 SQL：

```sql
-- 月度销售趋势
SELECT
  DATE_FORMAT(order_date, '%Y-%m') AS month,
  SUM(amount) AS total_sales
FROM orders
WHERE order_date >= '2024-01-01'
GROUP BY month
ORDER BY month
LIMIT 1000;

-- 最近30天用户增长
SELECT
  DATE(created_at) AS date,
  COUNT(*) AS new_users
FROM users
WHERE created_at >= CURDATE() - INTERVAL 30 DAY
GROUP BY date
ORDER BY date
LIMIT 1000;

-- 各地区销售趋势
SELECT
  DATE_FORMAT(order_date, '%Y-%m') AS month,
  region,
  SUM(amount) AS regional_sales
FROM orders
WHERE order_date >= '2024-01-01'
GROUP BY month, region
ORDER BY month, region
LIMIT 1000;
```

## 最佳实践

1. **时间排序至关重要**：
   - 始终使用 ORDER BY time_field ASC
   - 确保时间连续性（无缺失时间点）
   - 考虑填充缺失的时间点（值为0或NULL）

2. **时间粒度选择**：
   - 数据跨度大 → 使用粗粒度（年、月）
   - 数据跨度小 → 使用细粒度（日、小时）
   - 避免过多数据点（> 365 个）

3. **时间范围过滤**：
   - 使用 WHERE 限制时间范围
   - 避免全表扫描
   - 考虑使用索引

4. **Y 轴指标选择**：
   - 使用有意义的聚合函数
   - 同比/环比分析时使用增长率
   - 考虑移动平均平滑数据

5. **标签和格式**：
   - X 轴时间格式要统一
   - Y 轴包含单位说明
   - 标题包含时间范围

## 时间处理函数参考

### PostgreSQL
```sql
-- 按月
TO_CHAR(order_date, 'YYYY-MM')

-- 按日
TO_CHAR(order_date, 'YYYY-MM-DD')

-- 按年
TO_CHAR(order_date, 'YYYY')

-- 按周
TO_CHAR(order_date, 'IYYY-IW')
```

### MySQL
```sql
-- 按月
DATE_FORMAT(order_date, '%Y-%m')

-- 按日
DATE_FORMAT(order_date, '%Y-%m-%d')

-- 按年
DATE_FORMAT(order_date, '%Y')

-- 按周
DATE_FORMAT(order_date, '%Y-%u')
```

### Oracle
```sql
-- 按月
TO_CHAR(order_date, 'YYYY-MM')

-- 按日
TO_CHAR(order_date, 'YYYY-MM-DD')

-- 按年
TO_CHAR(order_date, 'YYYY')
```

## 常见问题

### Q1: 数据点过多怎么办？
**A**: 考虑以下优化：
- 使用更粗的时间粒度（从日改为周/月）
- 添加时间范围过滤（WHERE）
- 使用数据采样

### Q2: 时间点不连续怎么办？
**A**:
- 使用 generate_series 生成完整时间序列（PostgreSQL）
- LEFT JOIN 时间表
- 前端处理缺失点

### Q3: 多条线如何区分？
**A**:
- 使用不同颜色
- 使用图例
- 支持系列点击切换
- 避免超过 5 条线

## 与柱状图的区别

| 特性 | 折线图（Line） | 柱状图（Column） |
|------|---------------|----------------|
| X 轴 | 必须是时间 | 任意分类 |
| 重点 | 连续性、趋势 | 对比数值大小 |
| 排序 | 必须按时间排序 | 可任意排序 |
| 数据点 | 建议 ≥ 7 个 | 建议 ≤ 15 个 |
| 用途 | 趋势、变化 | 对比、排名 |

## 注意事项

1. **时间连续性**：
   - 确保时间序列完整
   - 处理缺失时间点
   - 避免时间间隔不均匀

2. **数据量控制**：
   - 避免过多数据点
   - 选择合适的时间粒度
   - 考虑数据聚合

3. **Y 轴范围**：
   - 不一定从 0 开始
   - 根据数据波动调整
   - 突出变化趋势

4. **交互设计**：
   - 鼠标悬停显示具体数值
   - 支持缩放（Zoom）
   - 数据点点击显示详情
   - 图例切换显示系列
