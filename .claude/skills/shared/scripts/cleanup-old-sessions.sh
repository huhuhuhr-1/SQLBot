#!/bin/bash
#
# 会话清理脚本
# 清理 tmp/ 目录下的旧会话
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$PROJECT_ROOT/tmp"

# 统计函数
count_sessions() {
    local skill_dir="$1"
    find "$skill_dir" -maxdepth 1 -type d -name "s_*" 2>/dev/null | wc -l
}

# 清理函数
cleanup_old_sessions() {
    local skill_dir="$1"
    local days="$2"
    local count=0

    echo -e "${YELLOW}清理 $skill_dir 中 ${days} 天前的会话...${NC}"

    while IFS= read -r session_dir; do
        echo "  删除: $session_dir"
        rm -rf "$session_dir"
        ((count++))
    done < <(find "$skill_dir" -maxdepth 1 -type d -name "s_*" -mtime +$days 2>/dev/null)

    echo -e "${GREEN}✓ 已清理 $count 个旧会话${NC}"
}

# 保留最近 N 个会话
keep_recent_sessions() {
    local skill_dir="$1"
    local keep_count="$2"
    local total=$(count_sessions "$skill_dir")
    local to_delete=$((total - keep_count))
    local count=0

    if [ $to_delete -le 0 ]; then
        echo -e "${GREEN}✓ 会话数 ($total) 未超过保留数量 ($keep_count)${NC}"
        return
    fi

    echo -e "${YELLOW}保留最近 $keep_count 个会话，删除其余 $to_delete 个...${NC}"

    while IFS= read -r session_dir; do
        echo "  删除: $session_dir"
        rm -rf "$session_dir"
        ((count++))
    done < <(find "$skill_dir" -maxdepth 1 -type d -name "s_*" 2>/dev/null | sort -r | tail -n +$((keep_count + 1)))

    echo -e "${GREEN}✓ 已清理 $count 个旧会话${NC}"
}

# 显示会话统计
show_stats() {
    echo ""
    echo "=== 会话统计 ==="
    echo ""

    local total_sessions=0
    local total_size=0

    for skill_dir in "$TMP_DIR"/*/; do
        if [ -d "$skill_dir" ]; then
            local skill_name=$(basename "$skill_dir")
            local session_count=$(count_sessions "$skill_dir")
            local session_size=$(du -sh "$skill_dir" 2>/dev/null | cut -f1)

            echo "📁 $skill_name"
            echo "   会话数: $session_count"
            echo "   大小: $session_size"
            echo ""

            total_sessions=$((total_sessions + session_count))
        fi
    done

    echo "总计: $total_sessions 个会话"
    echo ""
}

# 清理空目录
cleanup_empty_dirs() {
    echo -e "${YELLOW}清理空目录...${NC}"

    local count=0
    while IFS= read -r dir; do
        if [ -d "$dir" ]; then
            rmdir "$dir" 2>/dev/null && ((count++))
        fi
    done < <(find "$TMP_DIR" -type d -empty 2>/dev/null)

    echo -e "${GREEN}✓ 已清理 $count 个空目录${NC}"
}

# 主函数
main() {
    echo "====================================="
    echo "  会话清理脚本"
    echo "  项目: $PROJECT_ROOT"
    echo "====================================="
    echo ""

    # 检查 tmp 目录是否存在
    if [ ! -d "$TMP_DIR" ]; then
        echo -e "${YELLOW}⚠ tmp/ 目录不存在，无需清理${NC}"
        return 0
    fi

    # 显示清理前的统计
    show_stats

    # 解析命令行参数
    CLEANUP_MODE="${1:-all}"
    DAYS="${2:-7}"
    KEEP_COUNT="${2:-5}"

    case "$CLEANUP_MODE" in
        "old")
            # 清理 N 天前的会话
            echo "清理模式: 按时间 ($DAYS 天前)"
            echo ""

            for skill_dir in "$TMP_DIR"/*/; do
                if [ -d "$skill_dir" ]; then
                    cleanup_old_sessions "$skill_dir" "$DAYS"
                fi
            done
            ;;

        "recent")
            # 保留最近 N 个会话
            echo "清理模式: 按数量 (保留最近 $KEEP_COUNT 个)"
            echo ""

            for skill_dir in "$TMP_DIR"/*/; do
                if [ -d "$skill_dir" ]; then
                    keep_recent_sessions "$skill_dir" "$KEEP_COUNT"
                fi
            done
            ;;

        "all")
            # 清理所有会话
            echo -e "${RED}清理模式: 全部清理${NC}"
            echo ""
            read -p "确认清理所有会话？[y/N]: " confirm

            if [[ $confirm == "y" || $confirm == "Y" ]]; then
                for skill_dir in "$TMP_DIR"/*/; do
                    if [ -d "$skill_dir" ]; then
                        local count=$(count_sessions "$skill_dir")
                        if [ $count -gt 0 ]; then
                            echo "清理 $skill_dir ($count 个会话)"
                            rm -rf "$skill_dir"/s_*
                        fi
                    fi
                done
                echo -e "${GREEN}✓ 已清理所有会话${NC}"
            else
                echo -e "${YELLOW}已取消${NC}"
                return 0
            fi
            ;;

        *)
            echo "用法: $0 [all|old|recent] [天数|保留数量]"
            echo ""
            echo "示例:"
            echo "  $0 old 7        # 清理 7 天前的会话"
            echo "  $0 recent 5     # 保留最近 5 个会话"
            echo "  $0 all          # 清理所有会话（需确认）"
            echo ""
            echo "默认: $0 old 7"
            return 1
            ;;
    esac

    # 清理空目录
    cleanup_empty_dirs

    # 显示清理后的统计
    echo ""
    show_stats

    echo -e "${GREEN}✓ 清理完成${NC}"
}

# 执行主函数
main "$@"
