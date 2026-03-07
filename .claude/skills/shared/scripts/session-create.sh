#!/bin/bash
#
# Claude 会话创建脚本
# 自动创建会话目录和模板文件
#

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSIONS_DIR="$PROJECT_ROOT/tmp/sessions"
TEMPLATE_DIR="$SESSIONS_DIR/.template"

# 生成会话ID
SESSION_ID="session-$(date +%Y%m%d_%H%M%S)"
SESSION_DIR="$SESSIONS_DIR/$SESSION_ID"

# 创建会话目录
mkdir -p "$SESSION_DIR"

echo -e "${BLUE}创建 Claude 会话${NC}"
echo "会话 ID: $SESSION_ID"
echo "会话目录: $SESSION_DIR"
echo ""

# 复制模板文件
cp "$TEMPLATE_DIR/context.md" "$SESSION_DIR/"
cp "$TEMPLATE_DIR/process.md" "$SESSION_DIR/"
cp "$TEMPLATE_DIR/result.md" "$SESSION_DIR/"
cp "$TEMPLATE_DIR/decision.md" "$SESSION_DIR/"

# 生成 metadata.json
cat > "$SESSION_DIR/metadata.json" << EOF
{
  "session_id": "$SESSION_ID",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "preserve": false,
  "upgraded_to_docs": [],
  "tags": []
}
EOF

# 初始化 context.md
sed -i "s/{{TIMESTAMP}}/$(date '+%Y-%m-%d %H:%M:%S')/" "$SESSION_DIR/context.md"
sed -i "s|{{USER_REQUIREMENT}}||" "$SESSION_DIR/context.md"

# 更新 .latest
echo "$SESSION_ID" > "$SESSIONS_DIR/.latest"

echo -e "${GREEN}✓ 会话创建成功${NC}"
echo ""
echo "下一步："
echo "  1. 编辑会话文件："
echo "     - context.md  (需求)"
echo "     - process.md  (过程)"
echo "     - result.md   (结果)"
echo "     - decision.md (决策)"
echo ""
echo "  2. 设置环境变量："
echo "     export SESSION_DIR=\"$SESSION_DIR\""
echo ""
echo "  3. 完成后询问是否升级到 docs/"
