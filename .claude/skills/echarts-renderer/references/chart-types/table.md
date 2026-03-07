# 表格（Table）图表类型

## 数据结构特性

### 必需特征
- **多列展示**：适合展示 3 个及以上字段的原始数据
- **无聚合要求**：可以是明细数据，不需要 GROUP BY
- **高基数维度**：可以展示大量不同的值
- **灵活排序**：支持多列排序

### 适用场景

#### ✅ 推荐使用表格的情况：

1. **数据探索**
   - 用户想要查看原始数据
   - 需要看到所有字段详细信息
   - 数据量适中（100-1000 行）

2. **多字段展示**
   - 查询返回 5 个以上字段
   - 每个字段都包含重要信息
   - 不需要可视化聚合

3. **精确数值查看**
   - 需要查看具体数值
   - 需要复制数据到其他地方
   - 数据审核或校验

4. **列表展示**
   - 用户清单
   - 订单列表
   - 产品目录

#### ❌ 不推荐使用表格的情况：

1. **数据量过大**（> 1000 行）- 应使用分页或聚合
2. **单一指标展示** - 应使用图表更直观
3. **趋势分析** - 应使用折线图
4. **占比分析** - 应使用饼图

## SQL 查询模式

### 典型模式 1：原始数据查询
```sql
SELECT
  id,
  name,
  email,
  department,
  create_time
FROM users
LIMIT 1000
```

**特征**：
- 无 GROUP BY
- 无聚合函数
- 多个 SELECT 字段
- 有 LIMIT

### 典型模式 2：简单过滤
```sql
SELECT
  order_id,
  customer_name,
  amount,
  status,
  order_date
FROM orders
WHERE status = 'completed'
  AND order_date >= '2024-01-01'
LIMIT 1000
```

**特征**：
- 有 WHERE 过滤
- 无聚合
- 返回符合条件的明细

## 数据要求

### 字段类型
- **无特殊要求**：可以包含任何类型的字段
- **字段数量**：建议 ≥ 3 个字段
- **数据类型**：字符串、数值、时间日期都可以

### 数据量建议
- **最少**：1 行
- **推荐**：10-500 行
- **上限**：1000 行（超过建议分页）

## 配置生成规则

### 自动检测条件
满足以下任一条件时，推荐使用表格：

1. **字段数量**：SELECT 字段数 ≥ 5
2. **无聚合**：没有 GROUP BY 且没有聚合函数
3. **用户关键词**：问题包含"列表"、"详情"、"所有"、"全部"
4. **数据探索**：查询目的是查看数据明细

### 配置生成逻辑
```python
# 伪代码
if select_columns_count >= 5 or has_no_aggregation():
    return {
        "type": "table",
        "title": generate_title(),
        "columns": [
            {"name": field.display_name, "value": field.safe_name}
            for field in all_fields
        ]
    }
```

### 字段映射
- **所有字段**：包含所有 SELECT 字段
- **保持顺序**：保持 SQL 中字段定义的顺序
- **使用别名**：优先使用 AS 别名
- **去除引号**：value 中去掉所有引号

## 输出格式

```json
{
  "type": "table",
  "title": "用户列表",
  "columns": [
    {"name": "ID", "value": "id"},
    {"name": "姓名", "value": "name"},
    {"name": "邮箱", "value": "email"},
    {"name": "部门", "value": "department"},
    {"name": "创建时间", "value": "create_time"}
  ]
}
```

## 用户问题示例

### 触发表图的典型问题：

- "查询所有用户信息"
- "显示订单列表"
- "查看产品详情"
- "列出最近的交易记录"
- "展示所有部门的员工"

### 对应的 SQL：

```sql
-- 查询所有用户信息
SELECT id, name, email, department, status, create_time
FROM users
LIMIT 1000;

-- 显示订单列表
SELECT order_id, customer_name, amount, status, order_date
FROM orders
ORDER BY order_date DESC
LIMIT 1000;
```

## 最佳实践

1. **限制行数**：始终使用 LIMIT 避免返回过多数据
2. **选择必要字段**：避免 SELECT *
3. **合理排序**：使用 ORDER BY 提供有用的默认排序
4. **字段别名**：为复杂表达式添加有意义的别名
5. **时间范围**：添加时间过滤避免全表扫描

## 注意事项

1. **性能考虑**：
   - 大表查询添加 WHERE 条件
   - 创建适当的索引
   - 使用 LIMIT 限制返回行数

2. **用户体验**：
   - 字段名要有意义
   - 使用别名改善可读性
   - 考虑数据类型格式化（时间、数值）

3. **安全性**：
   - 避免暴露敏感字段
   - 对权限字段进行过滤
