#!/bin/bash
# 快速数据分析模板
# 使用方式: ./quick-analysis.sh <csv-file>

if [ -z "$1" ]; then
    echo "❌ 错误: 请提供CSV文件路径"
    echo "   使用方式: $0 <csv-file>"
    exit 1
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo "❌ 错误: 文件不存在 - $FILE"
    exit 1
fi

# 检查 XAN_PATH 是否设置
if [ -z "$XAN_PATH" ]; then
    # 尝试自动加载配置
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    CONFIG_FILE="$SCRIPT_DIR/xan-config.sh"
    
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
    else
        echo "❌ 错误: XAN_PATH 环境变量未设置"
        echo "   请先运行: source ../auto-setup.sh"
        exit 1
    fi
fi

echo "=========================================="
echo "📊 CSV 数据快速分析报告"
echo "=========================================="
echo "文件: $FILE"
echo ""

echo "1️⃣  数据规模"
echo "-------------------------------------------"
$XAN_PATH count "$FILE"
echo ""

echo "2️⃣  列结构"
echo "-------------------------------------------"
$XAN_PATH headers "$FILE"
echo ""

echo "3️⃣  数据预览（前10行）"
echo "-------------------------------------------"
$XAN_PATH view -l 10 "$FILE"
echo ""

echo "4️⃣  数值列统计"
echo "-------------------------------------------"
$XAN_PATH stats "$FILE"
echo ""

echo "✅ 分析完成！"
