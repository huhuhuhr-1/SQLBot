#!/bin/bash
#
# 会话管理辅助脚本
# 帮助创建和管理会话
#

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 创建新会话
create_session() {
    local skill_name="$1"
    local session_description="$2"
    local action_type="${3:-general}"  # 操作类型，默认为 general

    if [ -z "$skill_name" ]; then
        echo "用法: $0 create <技能名> [会话描述] [操作类型]"
        echo "示例: $0 create meta-discovery \"探查 sqlbot 数据库\" discovery-full"
        echo ""
        echo "常用操作类型:"
        echo "  metadata-import: import-source, import-schema, import-table, import-batch"
        echo "  meta-discovery: test-conn, schemas, tables, describe, discovery-full"
        echo "  auto-tester: env-check, test-one, test-all, test-integration"
        echo "  data-quality: check-null, check-duplicate, check-range, generate-report"
        echo "  data-security: scan-sensitive, apply-masking, security-report"
        echo "  data-integration: sync-full, sync-incremental, job-config, job-execute"
        echo "  ops-console: backup, restore, deploy, monitor"
        return 1
    fi

    # 生成会话 ID（格式: {action-type}_{timestamp}）
    local session_id="${action_type}_$(date +%Y%m%d_%H%M%S)"
    local session_dir="$PROJECT_ROOT/tmp/$skill_name/$session_id"

    # 创建会话目录
    mkdir -p "$session_dir"/{reports,logs}

    # 创建 README
    cat > "$session_dir/README.md" << EOF
# ${skill_name^} 会话 - $(date '+%Y-%m-%d %H:%M:%S')

## 会话 ID
\`\`\`
$session_id
\`\`\`

## 目标
$session_description

## 执行命令
<!-- 在这里记录执行的命令 -->

## 结果
<!-- 在这里记录执行结果 -->

## 保留状态
<!-- 用户选择: 保留 / 删除 -->
EOF

    # 更新 .latest
    echo "$session_id" > "$PROJECT_ROOT/tmp/$skill_name/.latest"

    echo -e "${GREEN}✓ 会话创建成功${NC}"
    echo "  技能: $skill_name"
    echo "  操作类型: $action_type"
    echo "  会话 ID: $session_id"
    echo "  目录: $session_dir"
    echo ""
    echo "使用方法:"
    echo "  export SESSION_DIR=\"$session_dir\""
    echo "  命令 --output \"\$SESSION_DIR/reports/result.md\""
}

# 列出会话
list_sessions() {
    local skill_name="$1"
    local skill_dir="$PROJECT_ROOT/tmp/$skill_name"

    if [ -z "$skill_name" ]; then
        echo "用法: $0 list <技能名>"
        return 1
    fi

    if [ ! -d "$skill_dir" ]; then
        echo "错误: 技能目录不存在: $skill_dir"
        return 1
    fi

    echo "=== $skill_name 会话列表 ==="
    echo ""

    # 按时间倒序列出会话（兼容新旧格式）
    # 新格式: {action}_{timestamp}，旧格式: s_{timestamp}
    local sessions=$(ls -td "$skill_dir"/*_*_* 2>/dev/null || true)
    # 如果没有新格式，尝试旧格式
    if [ -z "$sessions" ]; then
        sessions=$(ls -td "$skill_dir"/s_* 2>/dev/null || true)
    fi

    if [ -z "$sessions" ]; then
        echo "无会话"
        return 0
    fi

    local index=1
    while IFS= read -r session_dir; do
        local session_name=$(basename "$session_dir")
        # 兼容新旧格式的时间戳提取
        # 旧格式: s_YYYYMMDD_HHMMSS，新格式: {action}_YYYYMMDD_HHMMSS
        local timestamp=$(echo "$session_name" | sed 's/^[^_]*_//' | sed 's/_/\n/g' | head -2 | tr '\n' ' ')
        local formatted_date=$(echo "$timestamp" | sed 's/\([0-9]\{8\}\)\([0-9]\{6\}\).*/\1 \2/' | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\) \([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')

        # 检查是否有 README
        local readme_file="$session_dir/README.md"
        local description=""
        if [ -f "$readme_file" ]; then
            description=$(grep "^## 目标" "$readme_file" -A 1 | tail -1 | xargs || echo "")
        fi

        # 标记最新会话
        local latest_marker=""
        local latest_id=$(cat "$skill_dir/.latest" 2>/dev/null || echo "")
        if [ "$session_name" == "$latest_id" ]; then
            latest_marker=" ${GREEN}[最新]${NC}"
        fi

        echo -e "${index}. ${BLUE}$session_name${NC}$latest_marker"
        echo "   时间: $formatted_date"
        [ -n "$description" ] && echo "   目标: $description"
        echo ""

        ((index++))
    done <<< "$sessions"
}

# 切换到会话
switch_session() {
    local skill_name="$1"
    local session_id="$2"
    local skill_dir="$PROJECT_ROOT/tmp/$skill_name"

    if [ -z "$skill_name" ] || [ -z "$session_id" ]; then
        echo "用法: $0 switch <技能名> <会话ID>"
        echo "示例: $0 switch meta-discovery s_20250110_143022"
        return 1
    fi

    local session_dir="$skill_dir/$session_id"

    if [ ! -d "$session_dir" ]; then
        echo "错误: 会话不存在: $session_dir"
        return 1
    fi

    echo "export SESSION_DIR=\"$session_dir\""
    echo ""
    echo "已设置会话环境变量，使用方法:"
    echo "  命令 --output \"\$SESSION_DIR/reports/result.md\""
}

# 删除会话
delete_session() {
    local skill_name="$1"
    local session_id="$2"
    local skill_dir="$PROJECT_ROOT/tmp/$skill_name"

    if [ -z "$skill_name" ] || [ -z "$session_id" ]; then
        echo "用法: $0 delete <技能名> <会话ID>"
        echo "示例: $0 delete meta-discovery s_20250110_143022"
        return 1
    fi

    local session_dir="$skill_dir/$session_id"

    if [ ! -d "$session_dir" ]; then
        echo "错误: 会话不存在: $session_dir"
        return 1
    fi

    echo "确认删除会话: $session_dir"
    read -p "确认？[y/N]: " confirm

    if [[ $confirm == "y" || $confirm == "Y" ]]; then
        rm -rf "$session_dir"
        echo -e "${GREEN}✓ 会话已删除${NC}"
    else
        echo "已取消"
    fi
}

# 显示会话详情
show_session() {
    local skill_name="$1"
    local session_id="$2"
    local skill_dir="$PROJECT_ROOT/tmp/$skill_name"
    local session_dir="$skill_dir/$session_id"

    if [ -z "$skill_name" ] || [ -z "$session_id" ]; then
        echo "用法: $0 show <技能名> <会话ID>"
        return 1
    fi

    if [ ! -d "$session_dir" ]; then
        echo "错误: 会话不存在: $session_dir"
        return 1
    fi

    echo "=== 会话详情 ==="
    echo ""
    echo "会话 ID: $session_id"
    echo "目录: $session_dir"
    echo ""

    # 显示 README 内容
    if [ -f "$session_dir/README.md" ]; then
        echo "--- README.md ---"
        cat "$session_dir/README.md"
    fi

    echo ""
    echo "--- 文件列表 ---"
    ls -lh "$session_dir"/
}

# 主函数
main() {
    local command="$1"
    shift

    case "$command" in
        "create")
            create_session "$@"
            ;;
        "list")
            list_sessions "$@"
            ;;
        "switch")
            switch_session "$@"
            ;;
        "delete")
            delete_session "$@"
            ;;
        "show")
            show_session "$@"
            ;;
        *)
            echo "会话管理辅助脚本"
            echo ""
            echo "用法: $0 <命令> [参数...]"
            echo ""
            echo "命令:"
            echo "  create <技能名> [描述]   创建新会话"
            echo "  list <技能名>            列出所有会话"
            echo "  switch <技能名> <会话ID>  切换到会话（输出环境变量）"
            echo "  delete <技能名> <会话ID>  删除会话"
            echo "  show <技能名> <会话ID>    显示会话详情"
            echo ""
            echo "示例:"
            echo "  $0 create meta-discovery \"探查数据库\""
            echo "  $0 list meta-discovery"
            echo "  $0 switch meta-discovery s_20250110_143022"
            echo "  $0 delete meta-discovery s_20250110_143022"
            exit 1
            ;;
    esac
}

main "$@"
