# CSV Explorer 技能 - 实战指南

本文档提供实战场景、最佳实践和性能优化技巧。

> 📖 **基础配置**：请先阅读 [SKILL.md](SKILL.md) 的快速配置部分

## 实战场景

### 场景 1: 快速了解新数据集

**目标**：快速掌握 CSV 文件的基本信息

```bash
# Step 1: 数据规模和结构
export XAN_PATH="/path/to/xan" && $XAN_PATH count data.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH headers data.csv

# Step 2: 预览数据样本
export XAN_PATH="/path/to/xan" && $XAN_PATH view -l 20 data.csv

# Step 3: 关键字段统计
export XAN_PATH="/path/to/xan" && $XAN_PATH stats -s important_column data.csv

# 或使用一键分析脚本
./templates/quick-analysis.sh data.csv
```

**输出解读要点**：
- `count`: 总行数（评估数据量）
- `headers`: 列名（了解字段语义）
- `view`: 数据类型、格式、示例值
- `stats`: 数值范围、分布特征

### 场景 2: 数据质量检查

**目标**：识别数据质量问题（空值、重复值、异常值）

```bash
# 1. 检查空值
export XAN_PATH="/path/to/xan" && $XAN_PATH search -s name '^$' data.csv

# 2. 检查重复值
export XAN_PATH="/path/to/xan" && $XAN_PATH frequency -s id data.csv > freq.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH filter 'count > 1' freq.csv
rm freq.csv

# 3. 检查数值异常
export XAN_PATH="/path/to/xan" && $XAN_PATH stats -s numeric_column data.csv
# 关注 min/max 是否合理，mean/stddev 是否符合预期

# 或使用数据质量检查脚本
./templates/data-quality-check.sh data.csv
```

**常见问题模式**：
- 空字符串 `^$` vs 真正的空值
- 重复 ID 导致统计偏差
- 异常值影响聚合结果

### 场景 3: 复杂筛选和多步分析

**目标**：组合多个条件筛选数据，并进行后续分析

```bash
# 案例：找出北京地区且薪资 > 10000 的工程师

# Step 1: 按城市筛选
export XAN_PATH="/path/to/xan" && $XAN_PATH search -s city 'Beijing' employees.csv > temp1.csv

# Step 2: 按薪资筛选
export XAN_PATH="/path/to/xan" && $XAN_PATH filter 'salary > 10000' temp1.csv > temp2.csv

# Step 3: 按部门筛选
export XAN_PATH="/path/to/xan" && $XAN_PATH search -s department 'Engineering' temp2.csv > result.csv

# Step 4: 统计分析
export XAN_PATH="/path/to/xan" && $XAN_PATH stats -s salary result.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH view -l 10 result.csv

# 清理临时文件
rm temp1.csv temp2.csv result.csv
```

**多步骤技巧**：
- 每步查看中间结果，确保筛选正确
- 使用清晰的临时文件命名（temp1, temp2）
- 及时清理临时文件

### 场景 4: 销售数据分析

**目标**：从多个维度分析销售数据

```bash
# 1. 订单状态分布
export XAN_PATH="/path/to/xan" && $XAN_PATH frequency -s status sales_data.csv

# 2. 各品类销售额
export XAN_PATH="/path/to/xan" && $XAN_PATH groupby category 'sum(quantity*price) as total' sales_data.csv

# 3. 畅销产品排行
export XAN_PATH="/path/to/xan" && $XAN_PATH groupby product 'sum(quantity) as total_qty' sales_data.csv > product_qty.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH sort -s total_qty -N -R product_qty.csv > product_sorted.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH view -l 10 product_sorted.csv
rm product_qty.csv product_sorted.csv

# 或使用销售分析脚本
./templates/sales-analysis.sh sales_data.csv
```

**聚合表达式技巧**：
- 计算字段：`quantity*price`
- 别名：`as total`（用于后续排序）
- 多聚合：`sum(amount), count(*), avg(price)`

### 场景 5: 时间序列数据分析

**目标**：按时间维度聚合分析

```bash
# 假设有 date 列（格式：YYYY-MM-DD）

# 1. 按日期统计订单数
export XAN_PATH="/path/to/xan" && $XAN_PATH frequency -s date sales.csv

# 2. 按月份统计（需要日期格式支持）
export XAN_PATH="/path/to/xan" && $XAN_PATH groupby date_month 'sum(amount)' sales.csv

# 3. 找出高峰日期
export XAN_PATH="/path/to/xan" && $XAN_PATH groupby date 'count(*) as orders' sales.csv > daily.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH sort -s orders -N -R daily.csv
rm daily.csv
```

## 性能优化

### 1. 大文件处理策略

**问题**：GB 级别文件处理缓慢或内存溢出

**解决方案**：

```bash
# ❌ 不好：一次性加载全部数据
$XAN_PATH view huge_file.csv  # 可能卡死

# ✅ 好：限制预览行数
$XAN_PATH view -l 100 huge_file.csv

# ✅ 好：尽早筛选减少数据量
$XAN_PATH filter 'status == "active"' huge_file.csv > active.csv
$XAN_PATH groupby category 'sum(value)' active.csv
```

**优化原则**：
- 限制预览行数（`-l` 参数）
- 先筛选后聚合（减少处理数据量）
- 分批处理大文件（按日期、类别等拆分）

### 2. 内存优化

**策略**：最小化内存占用

```bash
# 流式处理（不保存中间结果）
$XAN_PATH filter 'condition' data.csv | \
  $XAN_PATH groupby category 'sum(value)' > result.csv

# vs 保存中间结果（需要更多内存）
$XAN_PATH filter 'condition' data.csv > temp.csv
$XAN_PATH groupby category 'sum(value)' temp.csv > result.csv
```

**选择建议**：
- 小文件（< 100MB）：保存中间结果，便于调试
- 大文件（> 100MB）：流式处理（注意管道限制）
- 超大文件（> 1GB）：分批处理

### 3. 批处理脚本

**场景**：需要处理多个 CSV 文件

```bash
#!/bin/bash
source /path/to/xan-config.sh

for file in *.csv; do
    echo "=== 处理: $file ==="
    $XAN_PATH count "$file"
    $XAN_PATH headers "$file"
    echo ""
done
```

**进阶**：并行处理

```bash
#!/bin/bash
source /path/to/xan-config.sh

# 使用 GNU parallel 并行处理
ls *.csv | parallel -j 4 \
  '$XAN_PATH count {} > {.}_count.txt'
```

## 常见陷阱和解决方案

### 陷阱 1: 字符串筛选失败

**错误现象**：
```bash
$XAN_PATH filter 'city == "Beijing"' data.csv
# Error: type error
```

**原因**：`filter` 的字符串比较存在类型转换问题

**解决方案**：
```bash
# 使用 search 命令
$XAN_PATH search -s city 'Beijing' data.csv

# 支持正则表达式
$XAN_PATH search -s city '^Beijing' data.csv
$XAN_PATH search -s email '.*@gmail\.com' data.csv
```

### 陷阱 2: 数值排序结果错误

**错误现象**：
```bash
$XAN_PATH sort -s price data.csv
# 输出：10, 100, 20, 200, 30（字符串排序）
```

**原因**：未指定数值排序标志

**解决方案**：
```bash
# 添加 -N 标志（Numeric）
$XAN_PATH sort -s price -N data.csv
# 输出：10, 20, 30, 100, 200（数值排序）
```

### 陷阱 3: 降序排序不生效

**错误现象**：
```bash
$XAN_PATH sort -s salary -N -r data.csv  # 小写 r
# 仍然是升序
```

**原因**：降序标志是 `-R`（大写）

**解决方案**：
```bash
$XAN_PATH sort -s salary -N -R data.csv  # 大写 R
```

### 陷阱 4: 管道操作权限错误

**错误现象**：
```bash
$XAN_PATH filter 'salary > 10000' data.csv | $XAN_PATH sort -s salary -N
# (eval):1: 权限不够:
```

**原因**：某些 shell 环境（zsh）的管道权限限制

**解决方案**：
```bash
# 使用临时文件（推荐）
$XAN_PATH filter 'salary > 10000' data.csv > temp1.csv
$XAN_PATH sort -s salary -N temp1.csv
rm temp1.csv
```

> 📖 详细技术分析：[PIPELINE_ISSUE_ANALYSIS.md](PIPELINE_ISSUE_ANALYSIS.md)

### 陷阱 5: 环境变量不持久

**错误现象**：
```bash
export XAN_PATH="/path/to/xan"
$XAN_PATH count data.csv  # 错误：command not found
```

**原因**：编程工具的 Bash 每次调用都是独立会话

**解决方案**：
```bash
# 每个命令都设置环境变量
export XAN_PATH="/path/to/xan" && $XAN_PATH count data.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH headers data.csv
```

## 最佳实践模式

### 模式 1: 探索性数据分析工作流

```bash
# 1. 基础信息
count → headers → view → stats

# 2. 单列分析
frequency → filter/groupby → view

# 3. 多维分析
groupby (多个维度) → sort → view
```

### 模式 2: 数据清洗工作流

```bash
# 1. 质量检查
search (空值) → frequency (重复) → stats (异常)

# 2. 数据筛选
filter/search → view (验证)

# 3. 数据转换
groupby (聚合) → sort (排序) → 保存结果
```

### 模式 3: 报表生成工作流

```bash
# 1. 数据准备
filter (时间范围) → filter (业务条件)

# 2. 数据聚合
groupby (维度) → 聚合函数 → sort (排行)

# 3. 结果输出
view (预览) → 保存到文件
```

## 测试数据

技能提供了测试数据，位于 `test-data/` 目录：

- `basic_data.csv` - 基础员工数据（15 行）
- `sales_data.csv` - 销售订单数据（20 行）
- `employee_performance.csv` - 员工绩效数据（15 行）

**快速测试**：
```bash
cd test-data

# 验证基础功能
export XAN_PATH="/path/to/xan" && \
  $XAN_PATH count basic_data.csv && \
  $XAN_PATH headers basic_data.csv && \
  $XAN_PATH view -l 5 basic_data.csv

# 测试筛选和聚合
export XAN_PATH="/path/to/xan" && \
  $XAN_PATH filter 'salary > 10000' basic_data.csv && \
  $XAN_PATH frequency -s city basic_data.csv && \
  $XAN_PATH groupby department 'mean(salary)' basic_data.csv
```

## 进阶技巧

### 1. 组合使用搜索和筛选

```bash
# 先搜索字符串，再筛选数值
$XAN_PATH search -s city 'Beijing' data.csv > temp.csv
$XAN_PATH filter 'salary > 10000' temp.csv
rm temp.csv
```

### 2. 使用正则表达式精确匹配

```bash
# 匹配邮箱
$XAN_PATH search -s email '.*@gmail\.com' data.csv

# 匹配日期格式
$XAN_PATH search -s date '2024-[01]-\d{2}' data.csv
```

### 3. 复杂聚合表达式

```bash
# 多个聚合
$XAN_PATH groupby category 'sum(amount), count(*), avg(price)' sales.csv

# 条件聚合
$XAN_PATH groupby category 'sum(if(status=="completed", amount, 0))' sales.csv

# 计算比例
$XAN_PATH groupby category 'sum(amount) / sum(amount) over () as percent' sales.csv
```

### 4. 排序后筛选 Top N

```bash
# 找出销售额前 10 的产品
$XAN_PATH groupby product 'sum(amount) as total' sales.csv > temp.csv
$XAN_PATH sort -s total -N -R temp.csv | head -n 10
rm temp.csv
```

## 获取帮助

```bash
# 查看主帮助
$XAN_PATH -h

# 查看特定命令帮助
$XAN_PATH filter -h
$XAN_PATH sort -h
$XAN_PATH groupby -h

# 查看表达式语言速查表
$XAN_PATH help cheatsheet

# 查看聚合函数
$XAN_PATH help aggs
```

## 延伸阅读

- **[SKILL.md](SKILL.md)** - 核心参考：命令速查表、配置指南
- **[PIPELINE_ISSUE_ANALYSIS.md](PIPELINE_ISSUE_ANALYSIS.md)** - 技术分析：管道问题深度分析