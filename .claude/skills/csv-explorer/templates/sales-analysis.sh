#!/bin/bash
# 销售数据分析模板
# 使用方式: ./sales-analysis.sh <sales-csv-file>

if [ -z "$1" ]; then
    echo "❌ 错误: 请提供销售数据CSV文件"
    echo "   使用方式: $0 <sales-csv-file>"
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
echo "💰 销售数据分析报告"
echo "=========================================="
echo "文件: $FILE"
echo ""

echo "1️⃣  订单概览"
echo "-------------------------------------------"
$XAN_PATH count "$FILE"
echo ""

echo "2️⃣  订单状态分布"
echo "-------------------------------------------"
$XAN_PATH frequency -s status "$FILE"
echo ""

echo "3️⃣  品类销售总额（降序）"
echo "-------------------------------------------"
$XAN_PATH groupby category 'sum(quantity*price) as total_sales' "$FILE" | \
$XAN_PATH sort -s total_sales -N -R | \
$XAN_PATH view
echo ""

echo "4️⃣  最畅销产品TOP 5"
echo "-------------------------------------------"
$XAN_PATH groupby product 'sum(quantity) as total_qty' "$FILE" | \
$XAN_PATH sort -s total_qty -N -R | \
$XAN_PATH view -l 5
echo ""

echo "✅ 分析完成！"
