---
name: csv-explorer
description: CSV 数据探查和分析技能。基于 xan 高性能命令行工具，用于处理大型 CSV 文件的数据探索、转换、聚合和可视化任务。当用户需要分析 CSV 文件、探查数据结构、执行数据筛选和聚合统计时使用此技能。
---

# CSV 数据探查技能

本技能基于 **xan** 高性能 CSV 处理工具，提供强大的数据探查、分析和处理能力。

## 场景触发规则

### 快速探查 CSV 文件

**触发关键词**：

- 查看CSV有多少行、统计CSV行数、CSV文件有多少记录
- 查看CSV有哪些列、CSV有哪些字段、查看CSV列名
- 预览CSV前几行、查看CSV数据样例、显示CSV前N行
- 分析CSV结构、探查CSV文件

→ 使用工具：**xan** (count, headers, view, head)

→ 参考文档：**`references/quick-start.md`**

### 数据筛选和查询

**触发关键词**：

- 筛选CSV数据、过滤CSV、查询符合条件的记录
- 大于多少、小于多少、等于某个值
- 搜索某个值、查找包含某字符串的记录
- 筛选数值列、筛选文本列

→ 使用工具：**xan** (filter, search)

→ 参考文档：**`references/filtering-guide.md`**

### 数据排序和比较

**触发关键词**：

- 按某列排序、CSV排序、升序、降序
- 最大的N个、最小的N个、Top N
- 数值排序、按金额排序、按时间排序

→ 使用工具：**xan** (sort)

→ 参考文档：**`references/sorting-guide.md`**

### 统计分析和聚合

**触发关键词**：

- 统计平均值、计算总和、最大值、最小值
- 分组统计、按某列分组、Group By
- 频率分析、统计各值的数量、分布情况
- 列统计、统计汇总、数据分析

→ 使用工具：**xan** (stats, frequency, groupby)

→ 参考文档：**`references/aggregation-guide.md`**

### 数据质量检查

**触发关键词**：

- 检查数据质量、CSV数据验证、发现数据问题
- 空值检查、重复数据检查、异常值检测
- 数据完整性、数据准确性

→ 使用工具：**templates/data-quality-check.sh**

→ 参考文档：**`references/data-quality.md`**

### 数据分析和报告

**触发关键词**：

- 生成数据报告、CSV分析报告、数据分析
- 销售数据分析、用户行为分析、业务数据分析
- 数据概览、快速分析

→ 使用工具：**templates/quick-analysis.sh** 或 **templates/sales-analysis.sh**

→ 参考文档：**`references/analysis-patterns.md`**

## 执行规范

### ⚠️ 从项目根目录执行

所有命令必须在项目根目录（包含 `.claude` 目录的目录）执行：

```bash
# 1. 确认在项目根目录
pwd
ls .claude/skills/csv-explorer/

# 2. 设置环境变量（每个命令都需要）
export XAN_PATH="/path/to/xan"  # 根据实际情况修改
```

### 方式一：直接使用 xan 命令

```bash
# 快速探查
export XAN_PATH="/path/to/xan" && $XAN_PATH count data.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH headers data.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH view -l 10 data.csv

# 数据筛选
export XAN_PATH="/path/to/xan" && $XAN_PATH filter 'salary > 5000' data.csv > filtered.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH search -s city 'Beijing' data.csv

# 数据排序
export XAN_PATH="/path/to/xan" && $XAN_PATH sort -s salary -N -R data.csv

# 统计分析
export XAN_PATH="/path/to/xan" && $XAN_PATH stats -s salary data.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH frequency -s department data.csv
export XAN_PATH="/path/to/xan" && $XAN_PATH groupby city 'mean(salary)' data.csv
```

### 方式二：使用便捷脚本

```bash
# 快速分析（推荐）
bash .claude/skills/csv-explorer/templates/quick-analysis.sh data.csv

# 数据质量检查
bash .claude/skills/csv-explorer/templates/data-quality-check.sh data.csv

# 销售数据分析
bash .claude/skills/csv-explorer/templates/sales-analysis.sh sales.csv
```

## 核心能力

- **高性能**: SIMD 解析器，支持并行计算，可处理 GB 级别文件
- **功能丰富**: 数据探索、转换、聚合、可视化等全方位操作
- **内存优化**: 最小化内存使用，支持流式处理
- **格式兼容**: 支持多种 CSV 格式和压缩文件

## 快速配置

### 首次使用

```bash
cd .claude/skills/csv-explorer
chmod +x auto-setup.sh
./auto-setup.sh
source xan-config.sh

# 验证安装
$XAN_PATH --version
```

### 重要：Bash 工具集成使用

**通过编程工具使用时，每个命令都是独立会话，必须在每个命令中设置环境变量：**

```bash
# ✅ 正确方式
export XAN_PATH="/path/to/xan" && $XAN_PATH count data.csv

# ❌ 错误方式（环境变量不会持久化）
export XAN_PATH="/path/to/xan"
$XAN_PATH count data.csv  # 失败：找不到 XAN_PATH
```

## 命令速查表

### 数据探索

| 命令             | 功能      | 示例                                      |
|----------------|---------|-----------------------------------------|
| `count`        | 统计行数    | `$XAN_PATH count data.csv`              |
| `headers`      | 显示列名    | `$XAN_PATH headers data.csv`            |
| `view -l N`    | 预览 N 行  | `$XAN_PATH view -l 10 data.csv`         |
| `head -l N`    | 显示前 N 行 | `$XAN_PATH head -l 5 data.csv`          |
| `stats -s col` | 列统计     | `$XAN_PATH stats -s col1,col2 data.csv` |

**⚠️ 注意**: `head` 使用 `-l` 参数（不是 `-n`）

### 数据筛选

| 命令                        | 功能    | 示例                                            |
|---------------------------|-------|-----------------------------------------------|
| `filter 'expr'`           | 数值筛选  | `$XAN_PATH filter 'age > 30' data.csv`        |
| `search -s col 'pattern'` | 字符串搜索 | `$XAN_PATH search -s city 'Beijing' data.csv` |

**⚠️ 重要**: 字符串比较必须使用 `search`，不要用 `filter`

### 数据排序

| 命令                  | 功能   | 示例                                        |
|---------------------|------|-------------------------------------------|
| `sort -s col -N`    | 数值升序 | `$XAN_PATH sort -s age -N data.csv`       |
| `sort -s col -N -R` | 数值降序 | `$XAN_PATH sort -s salary -N -R data.csv` |

**⚠️ 注意**:

- 数值排序必须加 `-N` 标志
- 降序使用 `-R`（大写）

### 数据聚合

| 命令                  | 功能   | 示例                                               |
|---------------------|------|--------------------------------------------------|
| `frequency -s col`  | 频率分析 | `$XAN_PATH frequency -s status data.csv`         |
| `groupby col 'agg'` | 分组聚合 | `$XAN_PATH groupby city 'mean(salary)' data.csv` |

**聚合函数**: `sum()`, `mean()`, `max()`, `min()`, `count()`, `stddev()`, `variance()`

## 重要限制

### 1. 管道操作限制

在某些 shell 环境（特别是 zsh）中，管道操作可能遇到权限问题。

**问题示例：**

```bash
# ❌ 可能失败
$XAN_PATH filter 'salary > 10000' data.csv | $XAN_PATH sort -s salary -N -R
```

**推荐解决方案：**

```bash
# ✅ 使用临时文件
$XAN_PATH filter 'salary > 10000' data.csv > temp1.csv
$XAN_PATH sort -s salary -N -R temp1.csv
rm temp1.csv
```

> 📖 详细技术分析：[PIPELINE_ISSUE_ANALYSIS.md](PIPELINE_ISSUE_ANALYSIS.md)

### 2. 字符串筛选限制

```bash
# ❌ filter 字符串比较会报错
$XAN_PATH filter 'city == "Beijing"' data.csv

# ✅ 使用 search 命令
$XAN_PATH search -s city 'Beijing' data.csv
```

## 便捷工具

技能提供以下辅助脚本：

- **quick-test.sh** - 验证技能配置和功能
- **auto-setup.sh** - 自动检测平台并生成配置
- **templates/quick-analysis.sh** - 一键生成数据概览报告
- **templates/sales-analysis.sh** - 销售数据分析
- **templates/data-quality-check.sh** - 数据质量检查

## 获取帮助

```bash
# 查看主帮助
$XAN_PATH -h

# 查看特定命令帮助
$XAN_PATH count -h
$XAN_PATH filter -h
$XAN_PATH sort -h

# 查看表达式语言速查表
$XAN_PATH help cheatsheet

# 查看聚合函数
$XAN_PATH help aggs
```

## 延伸阅读

- **[USAGE_TIPS.md](USAGE_TIPS.md)** - 实战指南：常见场景、性能优化、最佳模式
- **[PIPELINE_ISSUE_ANALYSIS.md](PIPELINE_ISSUE_ANALYSIS.md)** - 技术分析：管道问题深度分析
- **test-data/TEST_SUMMARY.md** - 测试报告和功能验证

## 最佳实践速记

1. **先探索后处理**: count → headers → view → stats
2. **数值排序加 -N**: 排序数值列时必须加 `-N` 标志
3. **字符串搜索用 search**: 避免使用 filter 的字符串比较
4. **尽早筛选数据**: 先筛选减少数据量，再进行聚合
5. **使用临时文件**: 在管道操作有问题的环境中使用临时文件替代
6. **测试复杂表达式**: 先用小数据集测试再处理大文件

## 适用场景

✅ 快速探查 CSV 文件结构和内容
✅ 数据清洗和质量检查
✅ 数据筛选和转换
✅ 统计分析和聚合计算
✅ 处理大型 CSV 文件（GB 级别）
✅ 数据预处理和格式转换

⚠️ 不适用于：

- 复杂的数据可视化（建议配合其他工具）
- 需要类型安全的高级数据处理
- 非 CSV 格式的数据处理