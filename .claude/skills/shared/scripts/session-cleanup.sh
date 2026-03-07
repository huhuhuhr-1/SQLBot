#!/bin/bash
#
# tmp/ 目录清理脚本
# 自动清理过期的会话和临时文件
#

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$PROJECT_ROOT/tmp"

echo -e "${YELLOW}tmp/ 目录清理${NC}"
echo ""

# 统计信息
SESSIONS_COUNT=$(find "$TMP_DIR/sessions" -type d -name "session-*" 2>/dev/null | wc -l)
EXPERIMENTS_COUNT=$(find "$TMP_DIR/experiments" -type d 2>/dev/null | wc -l)
DRAFTS_COUNT=$(find "$TMP_DIR/drafts" -type d 2>/dev/null | wc -l)

echo "清理前统计："
echo "  会话数: $SESSIONS_COUNT"
echo "  实验数: $EXPERIMENTS_COUNT"
echo "  草稿数: $DRAFTS_COUNT"
echo ""

# 清理函数
cleanup_sessions() {
    echo -e "${YELLOW}清理会话（7天前，未标记保留）...${NC}"

    local count=0
    while IFS= read -r session_dir; do
        if [ -d "$session_dir" ]; then
            local metadata="$session_dir/metadata.json"
            if [ -f "$metadata" ]; then
                # 检查 preserve 标记
                if grep -q '"preserve": true' "$metadata"; then
                    continue
                fi
            fi
            rm -rf "$session_dir"
            ((count++))
        fi
    done < <(find "$TMP_DIR/sessions" -type d -name "session-*" -mtime +7 2>/dev/null)

    echo -e "${GREEN}✓ 已清理 $count 个会话${NC}"
}

cleanup_experiments() {
    echo -e "${YELLOW}清理实验（30天前）...${NC}"

    local count=$(find "$TMP_DIR/experiments" -type d -mtime +30 2>/dev/null | wc -l)
    find "$TMP_DIR/experiments" -type d -mtime +30 2>/dev/null | xargs rm -rf

    echo -e "${GREEN}✓ 已清理 $count 个实验${NC}"
}

cleanup_drafts() {
    echo -e "${YELLOW}清理草稿（14天前）...${NC}"

    local count=$(find "$TMP_DIR/drafts" -type d -mtime +14 2>/dev/null | wc -l)
    find "$TMP_DIR/drafts" -type d -mtime +14 2>/dev/null | xargs rm -rf

    echo -e "${GREEN}✓ 已清理 $count 个草稿${NC}"
}

# 执行清理
cleanup_sessions
cleanup_experiments
cleanup_drafts

echo ""

# 清理后统计
SESSIONS_COUNT=$(find "$TMP_DIR/sessions" -type d -name "session-*" 2>/dev/null | wc -l)
EXPERIMENTS_COUNT=$(find "$TMP_DIR/experiments" -type d 2>/dev/null | wc -l)
DRAFTS_COUNT=$(find "$TMP_DIR/drafts" -type d 2>/dev/null | wc -l)

echo "清理后统计："
echo "  会话数: $SESSIONS_COUNT"
echo "  实验数: $EXPERIMENTS_COUNT"
echo "  草稿数: $DRAFTS_COUNT"
echo ""

echo -e "${GREEN}✓ 清理完成${NC}"
