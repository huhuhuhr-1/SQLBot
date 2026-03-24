#!/bin/bash
#
# csv-explorer 统一执行入口
# 功能: CSV 数据探查和分析
# 特点: 自动检测并配置 xan 工具路径
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# 自动检测 xan 路径
detect_xan() {
    local platforms=("x86_64-linux-gnu" "aarch64-linux-gnu" "x86_64-linux-musl" "aarch64-apple-darwin" "x86_64-apple-darwin" "x86_64-pc-windows-msvc")

    for platform in "${platforms[@]}"; do
        local xan_path="$SKILL_DIR/$platform/xan"
        if [ -f "$xan_path" ] && [ -x "$xan_path" ]; then
            echo "$xan_path"
            return 0
        fi
    done

    return 1
}

show_help() {
    cat << EOF
CSV 数据探查工具集 - 基于 xan 高性能工具

使用方法:
    ./scripts/explorer <csv_file>           # 快速探查文件
    ./scripts/analyze <csv_file>            # 生成分析报告
    ./scripts/quality <csv_file>            # 数据质量检查
    ./scripts/check                         # 验证工具配置
    ./scripts/help                          # 显示此帮助信息

可用功能:
    count       - 统计行数
    headers     - 显示列名
    view        - 预览数据
    filter      - 数据筛选
    sort        - 数据排序
    stats       - 统计分析
    frequency   - 频率分析
    groupby     - 分组聚合

示例:
    # 快速探查 CSV 文件
    ./scripts/explore data.csv

    # 生成数据分析报告
    ./scripts/analyze sales.csv

    # 数据质量检查
    ./scripts/quality data.csv

    # 验证工具配置
    ./scripts/check

环境变量（可选）:
    XAN_PATH     - 手动指定 xan 工具路径

EOF
}

check_config() {
    echo "=== csv-explorer 配置检查 ==="

    local xan_path
    if [ -n "$XAN_PATH" ] && [ -x "$XAN_PATH" ]; then
        xan_path="$XAN_PATH"
        echo "✓ 使用环境变量 XAN_PATH: $xan_path"
    elif xan_path=$(detect_xan); then
        echo "✓ 自动检测到 xan: $xan_path"
    else
        echo "✗ 未找到可执行的 xan 工具"
        echo ""
        echo "请执行以下命令进行初始化:"
        echo "  cd $SKILL_DIR"
        echo "  chmod +x auto-setup.sh"
        echo "  ./auto-setup.sh"
        return 1
    fi

    # 验证 xan 可用
    if "$xan_path" --version > /dev/null 2>&1; then
        echo "✓ xan 工具验证通过"
        "$xan_path" --version
    else
        echo "✗ xan 工具验证失败"
        return 1
    fi

    return 0
}

explore_file() {
    local csv_file="$1"
    if [ -z "$csv_file" ]; then
        echo "错误: 请指定 CSV 文件"
        echo "用法: ./scripts/explore <csv_file>"
        return 1
    fi

    if [ ! -f "$csv_file" ]; then
        echo "错误: 文件不存在: $csv_file"
        return 1
    fi

    local xan_path
    if [ -n "$XAN_PATH" ]; then
        xan_path="$XAN_PATH"
    elif ! xan_path=$(detect_xan); then
        echo "错误: 未找到 xan 工具"
        return 1
    fi

    echo "=== CSV 文件探查: $csv_file ==="
    echo ""
    echo "行数统计:"
    "$xan_path" count "$csv_file"
    echo ""
    echo "列名:"
    "$xan_path" headers "$csv_file"
    echo ""
    echo "数据预览 (前10行):"
    "$xan_path" view -l 10 "$csv_file"
}

analyze_file() {
    local csv_file="$1"
    if [ -z "$csv_file" ]; then
        echo "错误: 请指定 CSV 文件"
        echo "用法: ./scripts/analyze <csv_file>"
        return 1
    fi

    if [ ! -f "$csv_file" ]; then
        echo "错误: 文件不存在: $csv_file"
        return 1
    fi

    bash "$SKILL_DIR/templates/quick-analysis.sh" "$csv_file"
}

quality_check() {
    local csv_file="$1"
    if [ -z "$csv_file" ]; then
        echo "错误: 请指定 CSV 文件"
        echo "用法: ./scripts/quality <csv_file>"
        return 1
    fi

    if [ ! -f "$csv_file" ]; then
        echo "错误: 文件不存在: $csv_file"
        return 1
    fi

    bash "$SKILL_DIR/templates/data-quality-check.sh" "$csv_file"
}

case "$1" in
    check)
        check_config
        ;;
    explore)
        explore_file "$2"
        ;;
    analyze)
        analyze_file "$2"
        ;;
    quality)
        quality_check "$2"
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo "未知命令: $1"
        echo "使用 ./scripts/help 查看可用命令"
        exit 1
        ;;
esac
