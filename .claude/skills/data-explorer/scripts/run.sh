#!/bin/bash
# 数据探查技能 - 统一执行入口

# 1. 探测有效的 Python 命令
if command -v python3 &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
else
    echo "❌ 错误：未找到 Python 环境，请先安装 Python 3.x"
    exit 1
fi

# 2. 检查脚本路径
REAL_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "$REAL_PATH")

# 统一核心脚本路径
UTILS_PY="$SCRIPT_DIR/sqlbot_utils.py"

if [ ! -f "$UTILS_PY" ]; then
    echo "❌ 错误：未找到 sqlbot_utils.py 核心脚本 (查找路径: $UTILS_PY)"
    exit 1
fi

ACTION=$1

# 帮助信息函数
show_help() {
    echo "数据探查工具 (Data Explorer Tool)"
    echo ""
    echo "用法: bash scripts/run.sh [action] [options]"
    echo ""
    echo "可用操作 (Actions):"
    echo "  init        初始化配置 (输入 IP, 端口, 用户名, 密码)"
    echo "  list        获取所有可用数据源列表"
    echo "  sync        同步特定数据源的元数据"
    echo "  exec        执行探查指令并导出为 CSV"
    echo "  -h, --help  显示此帮助信息"
    echo ""
    echo "示例 (Examples):"
    echo "  bash scripts/run.sh init 127.0.0.1 8000 admin SQLBot@123456"
    echo "  bash scripts/run.sh list"
    echo "  bash scripts/run.sh sync 1"
    echo "  bash scripts/run.sh exec 1 \"SELECT ...\" result.csv"
}

# 如果没有参数或请求帮助
if [[ -z "$ACTION" || "$ACTION" == "-h" || "$ACTION" == "--help" ]]; then
    show_help
    exit 0
fi

shift # 移除第一个参数 (action)

case $ACTION in
    init|list|sync|exec)
        $PY "$UTILS_PY" "$ACTION" "$@"
        ;;
    *)
        echo "❌ 错误: 未知操作 '$ACTION'"
        echo ""
        show_help
        exit 1
        ;;
esac
