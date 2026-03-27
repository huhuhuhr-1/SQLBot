#!/bin/bash
# SQLBot Data Explorer - V2.0 渐进式同步脚本

if command -v python3 &>/dev/null; then
    PY="python3"
else
    PY="python"
fi

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
UTILS_PY="$SCRIPT_DIR/sqlbot_utils.py"

ACTION=$1
# 注意：这里不需要 shift，直接透传所有参数给 python 脚本处理
# 或者在 python 脚本里按顺序读取

show_help() {
    echo "V2.0 数据探查工具 (Data Explorer Tool)"
    echo "用法: bash scripts/run.sh <action> <user_id> [args]"
    echo ""
    echo "指令集:"
    echo "  login <user_id> <username> <password>  登录并获取 Token (自动保存到 config.json)"
    echo "  init <user_id> <url> <token>      初始化用户物理空间"
    echo "  check <user_id> <db_id>           检查元数据是否过期"
    echo "  pull-permissions <user_id>       同步该用户可见数据源清单"
    echo "  pull-index <user_id> <db_id>      同步库索引与表概要 (L1/L2)"
    echo "  pull-semantic <user_id> <db_id>   同步术语与指标 (L2)"
    echo "  pull-relations <user_id> <db_id> 同步表关系图（可用于多表 JOIN）"
    echo "  pull-table <user_id> <db_id> <t>  同步特定表详情 (L3)"
    echo "  pull-tables <user_id> <db_id>     同步该库所有表详情 (L3)"
    echo "  pull-knowledge-common <user_id>   同步 engines/sql样例/基础规则到 ~/.sqlbot/_common"
    echo "  pull-terminologies-all <user_id>  拉取所有数据源全量术语到 semantic 下"
    echo "  exec <user_id> <db_id> <sql> <f>  执行查询并导出结果"
    echo ""
}

if [[ -z "$ACTION" || "$ACTION" == "-h" ]]; then
    show_help
    exit 0
fi

case $ACTION in
    login|init|check|pull-permissions|pull-index|pull-semantic|pull-relations|pull-table|pull-tables|pull-knowledge-common|pull-terminologies-all|exec)
        $PY "$UTILS_PY" "$@"
        ;;
    *)
        echo "❌ 未知操作 '$ACTION'"
        show_help
        exit 1
        ;;
esac
