#!/bin/bash
# 数据质量检查模板
# 使用方式: ./data-quality-check.sh <csv-file>

if [ -z "$1" ]; then
    echo "❌ 错误: 请提供CSV文件路径"
    echo "   使用方式: $0 <csv-file>"
    exit 1
fi

FILE="$1"

# 检查 XAN_PATH
if [ -z "$XAN_PATH" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    CONFIG_FILE="$SCRIPT_DIR/xan-config.sh"
    
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
    else
        echo "❌ 错误: XAN_PATH 环境变量未设置"
        exit 1
    fi
fi

echo "=========================================="
echo "🔍 数据质量检查报告"
echo "=========================================="
echo "文件: $FILE"
echo ""

echo "1️⃣  基础信息"
echo "-------------------------------------------"
TOTAL_ROWS=$($XAN_PATH count "$FILE")
echo "总行数: $TOTAL_ROWS"
$XAN_PATH headers "$FILE"
echo ""

echo "2️⃣  空值检查（查找空字符串）"
echo "-------------------------------------------"
echo "提示: 检查每个列是否有空值..."
# 注意：xan search 对空值的支持有限，这里只是示例
echo "（需要根据具体列名定制检查）"
echo ""

echo "3️⃣  重复值检查"
echo "-------------------------------------------"
echo "第一列的重复值检查:"
$XAN_PATH frequency "$FILE" | head -20
echo ""

echo "4️⃣  数值列异常值检测"
echo "-------------------------------------------"
$XAN_PATH stats "$FILE"
echo ""
echo "💡 建议: 查看上述统计，检查 min/max 是否合理"
echo ""

echo "✅ 检查完成！"
echo ""
echo "📝 自定义检查建议:"
echo "   1. 使用 filter 查找异常值: $XAN_PATH filter 'column > threshold' $FILE"
echo "   2. 使用 search 查找特定值: $XAN_PATH search -s column 'value' $FILE"
echo "   3. 使用 groupby 检查分布: $XAN_PATH groupby column 'count(*)' $FILE"
