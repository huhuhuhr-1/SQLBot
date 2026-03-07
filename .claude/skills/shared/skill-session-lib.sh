#!/bin/bash
################################################################################
# Skill Session Library
# 统一的技能会话管理函数库
#
# 功能：
# - 初始化会话目录（自动设置 SESSION_DIR）
# - 持久化会话状态（跨 shell 进程）
# - 自动恢复会话（支持 Claude Code 多次 Bash 调用）
# - 完成会话并询问是否保留
# - 提供调试支持
#
# 使用方法：
#   source scripts/skill-session-lib.sh
#   skill_session_init <skill_name> <action_type> <description>
#
# 特性：
# - 会话状态持久化到 tmp/.skill-session
# - 支持多次 Bash 调用（Claude Code 场景）
# - 自动清理过期会话文件
################################################################################

set -euo pipefail

# 颜色定义
readonly COLOR_RED='\033[0;31m'
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_YELLOW='\033[1;33m'
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_RESET='\033[0m'

# 会话状态文件（持久化会话信息，跨 shell 进程）
readonly SESSION_STATE_FILE="tmp/.skill-session"

################################################################################
# 初始化会话
#
# 参数：
#   $1 - skill_name: 技能名称（如 meta-discovery）
#   $2 - action_type: 操作类型（如 test-all, import-source）
#   $3 - description: 操作描述（可选）
#
# 输出：
#   设置环境变量 SESSION_DIR
#   创建会话目录结构
#   输出调试信息
################################################################################
skill_session_init() {
    local skill_name="$1"
    local action_type="$2"
    local description="${3:-}"

    # 验证参数
    if [[ -z "$skill_name" ]]; then
        echo -e "${COLOR_RED}ERROR: skill_name 不能为空${COLOR_RESET}" >&2
        return 1
    fi

    if [[ -z "$action_type" ]]; then
        echo -e "${COLOR_RED}ERROR: action_type 不能为空${COLOR_RESET}" >&2
        return 1
    fi

    # 确认在项目根目录
    if [[ ! -d ".claude/skills" ]]; then
        echo -e "${COLOR_RED}ERROR: 不在项目根目录（找不到 .claude/skills）${COLOR_RESET}" >&2
        echo -e "${COLOR_YELLOW}建议: cd 到项目根目录后执行${COLOR_RESET}" >&2
        return 1
    fi

    # 生成会话 ID
    local session_id="${action_type}_$(date +%Y%m%d_%H%M%S)"
    local session_dir="tmp/${skill_name}/${session_id}"

    # 创建会话目录
    mkdir -p "$session_dir"/{reports,logs}

    # 设置环境变量（使用 export，确保子进程可以访问）
    export SESSION_DIR="$session_dir"

    # 创建 README.md
    cat > "$SESSION_DIR/README.md" <<EOF
# 技能会话 - ${session_id}

## 技能

${skill_name}

## 操作类型

${action_type}

## 描述

${description}

## 开始时间

$(date '+%Y-%m-%d %H:%M:%S')

## 目录结构

- \`reports/\` - 输出报告
- \`logs/\` - 执行日志
- \`README.md\` - 本文件
EOF

    # 更新最新会话标记
    mkdir -p "tmp/${skill_name}"
    echo "$session_id" > "tmp/${skill_name}/.latest"

    # 持久化会话状态（写入状态文件）
    cat > "$SESSION_STATE_FILE" <<EOF
SESSION_ID=${session_id}
SESSION_DIR=${session_dir}
SKILL_NAME=${skill_name}
ACTION_TYPE=${action_type}
CREATED_AT=$(date +%s)
EOF

    # 导出所有会话变量到当前 shell（使其在外部可访问）
    export SESSION_ID="$session_id"
    export SESSION_DIR="$session_dir"
    export SKILL_NAME="$skill_name"
    export ACTION_TYPE="$action_type"

    # 输出调试信息
    echo -e "${COLOR_GREEN}✓ 会话已初始化${COLOR_RESET}" >&2
    echo -e "${COLOR_BLUE}  技能: ${skill_name}${COLOR_RESET}" >&2
    echo -e "${COLOR_BLUE}  操作: ${action_type}${COLOR_RESET}" >&2
    echo -e "${COLOR_BLUE}  会话: ${SESSION_ID}${COLOR_RESET}" >&2
    echo -e "${COLOR_BLUE}  目录: ${SESSION_DIR}${COLOR_RESET}" >&2
    echo -e "${COLOR_BLUE}  状态: ${SESSION_STATE_FILE}${COLOR_RESET}" >&2

    return 0
}

################################################################################
# 从持久化文件恢复会话状态
#
# 说明：
# - 如果 SESSION_DIR 未设置，尝试从 SESSION_STATE_FILE 读取
# - 支持跨 shell 进程恢复会话（Claude Code 多次 Bash 调用场景）
#
# 返回：
#   0 - 恢复成功或已存在 SESSION_DIR
#   1 - 恢复失败（状态文件不存在或无效）
################################################################################
skill_session_restore() {
    # 如果 SESSION_DIR 已设置，直接返回
    if [[ -n "${SESSION_DIR:-}" ]]; then
        return 0
    fi

    # 检查状态文件是否存在
    if [[ ! -f "$SESSION_STATE_FILE" ]]; then
        return 1
    fi

    # 读取状态文件
    source "$SESSION_STATE_FILE"

    # 验证恢复的 SESSION_DIR 是否有效
    if [[ ! -d "$SESSION_DIR" ]]; then
        echo -e "${COLOR_YELLOW}WARNING: 会话目录不存在: ${SESSION_DIR}${COLOR_RESET}" >&2
        return 1
    fi

    # 导出 SESSION_DIR（使其在当前 shell 中可用）
    export SESSION_DIR
    export SESSION_ID

    echo -e "${COLOR_GREEN}✓ 会话已恢复${COLOR_RESET}" >&2
    echo -e "${COLOR_BLUE}  会话: ${SESSION_ID}${COLOR_RESET}" >&2
    echo -e "${COLOR_BLUE}  目录: ${SESSION_DIR}${COLOR_RESET}" >&2

    return 0
}

################################################################################
# 清理会话状态文件
#
# 说明：
# - 删除 SESSION_STATE_FILE
# - 通常在会话完成时调用
################################################################################
skill_session_cleanup_state() {
    if [[ -f "$SESSION_STATE_FILE" ]]; then
        rm -f "$SESSION_STATE_FILE"
    fi
    return 0
}

################################################################################
# 验证会话环境（支持自动恢复）
#
# 检查：
# - SESSION_DIR 是否已设置（自动尝试从状态文件恢复）
# - SESSION_DIR 目录是否存在
# - 路径是否安全（不在系统根目录）
#
# 返回：
#   0 - 验证通过
#   1 - 验证失败
################################################################################
skill_session_validate() {
    local errors=0

    # 如果 SESSION_DIR 未设置，尝试自动恢复
    if [[ -z "${SESSION_DIR:-}" ]]; then
        if skill_session_restore 2>/dev/null; then
            # 恢复成功，继续验证
            :
        else
            echo -e "${COLOR_RED}ERROR: SESSION_DIR 未设置${COLOR_RESET}" >&2
            echo -e "${COLOR_YELLOW}建议: 先调用 skill_session_init${COLOR_RESET}" >&2
            ((errors++))
            return $errors
        fi
    fi

    # 检查目录是否存在
    if [[ ! -d "${SESSION_DIR:-}" ]]; then
        echo -e "${COLOR_RED}ERROR: SESSION_DIR 目录不存在: ${SESSION_DIR:-}${COLOR_RESET}" >&2
        ((errors++))
    fi

    # 检查路径安全性（防止写入系统根目录）
    if [[ -n "${SESSION_DIR:-}" ]]; then
        # 如果是绝对路径，检查是否在项目 tmp/ 目录下
        if [[ "$SESSION_DIR" = /* ]]; then
            local project_root
            project_root="$(pwd)"
            if [[ ! "$SESSION_DIR" = "${project_root}/tmp"* ]]; then
                echo -e "${COLOR_YELLOW}WARNING: 路径不在项目 tmp/ 目录下: ${SESSION_DIR}${COLOR_RESET}" >&2
            fi
        fi

        # 检查是否在系统根目录
        if [[ "$SESSION_DIR" = /^[^/]*$ ]]; then
            echo -e "${COLOR_RED}ERROR: 路径在系统根目录，可能导致权限问题: ${SESSION_DIR}${COLOR_RESET}" >&2
            ((errors++))
        fi
    fi

    return $errors
}

################################################################################
# 完成会话
#
# 参数：
#   $1 - message: 完成消息（可选）
#
# 操作：
# - 记录完成时间到 README.md
# - 询问用户是否保留会话
# - 如果不保留，删除会话目录
# - 清理会话状态文件
################################################################################
skill_session_finish() {
    local message="${1:-会话已完成}"

    # 验证会话环境
    if ! skill_session_validate; then
        echo -e "${COLOR_RED}ERROR: 会话环境验证失败，无法完成${COLOR_RESET}" >&2
        return 1
    fi

    # 更新 README.md
    cat >> "$SESSION_DIR/README.md" <<EOF

## 完成时间

$(date '+%Y-%m-%d %H:%M:%S')

## 结果

${message}

## 保留状态

待用户确认
EOF

    # 输出完成信息
    echo -e "${COLOR_GREEN}✓ ${message}${COLOR_RESET}" >&2
    echo -e "${COLOR_BLUE}  会话目录: ${SESSION_DIR}${COLOR_RESET}" >&2

    # 询问是否保留（仅在交互模式下）
    if [[ -t 0 ]]; then
        echo -ne "${COLOR_YELLOW}保留此会话？[Y/n]: ${COLOR_RESET}" >&2
        read -r choice

        if [[ "$choice" =~ ^[Nn]$ ]]; then
            rm -rf "$SESSION_DIR"
            echo -e "${COLOR_GREEN}✓ 会话已清理${COLOR_RESET}" >&2
        else
            # 更新保留状态
            echo "保留: 是" >> "$SESSION_DIR/README.md"
            echo -e "${COLOR_GREEN}✓ 会话已保留${COLOR_RESET}" >&2
        fi
    else
        echo -e "${COLOR_YELLOW}提示: 会话已保留（非交互模式）${COLOR_RESET}" >&2
    fi

    # 清理会话状态文件
    skill_session_cleanup_state

    return 0
}

################################################################################
# 调试输出
#
# 参数：
#   $@ - 要输出的内容
#
# 说明：
#   输出调试信息到 stderr（不影响 stdout）
################################################################################
skill_session_debug() {
    echo -e "${COLOR_BLUE}DEBUG: $*${COLOR_RESET}" >&2
}

################################################################################
# 错误输出
#
# 参数：
#   $@ - 要输出的错误信息
#
# 说明：
#   输出错误信息到 stderr
################################################################################
skill_session_error() {
    echo -e "${COLOR_RED}ERROR: $*${COLOR_RESET}" >&2
}

################################################################################
# 警告输出
#
# 参数：
#   $@ - 要输出的警告信息
#
# 说明：
#   输出警告信息到 stderr
################################################################################
skill_session_warning() {
    echo -e "${COLOR_YELLOW}WARNING: $*${COLOR_RESET}" >&2
}

################################################################################
# 获取会话目录（用于命令替换）
#
# 返回：
#   输出 SESSION_DIR 的值
#
# 使用：
#   DIR=$(skill_session_get_dir)
################################################################################
skill_session_get_dir() {
    echo "${SESSION_DIR:-}"
}

################################################################################
# 检查会话目录是否存在
#
# 返回：
#   0 - 存在
#   1 - 不存在
################################################################################
skill_session_exists() {
    [[ -d "${SESSION_DIR:-}" ]]
}

################################################################################
# 创建子目录（在会话目录下）
#
# 参数：
#   $@ - 子目录名称（可以是多个）
#
# 示例：
#   skill_session_mkdir jobs configs
################################################################################
skill_session_mkdir() {
    if ! skill_session_validate; then
        return 1
    fi

    local subdir
    for subdir in "$@"; do
        mkdir -p "$SESSION_DIR/$subdir"
        echo -e "${COLOR_GREEN}✓ 创建目录: ${SESSION_DIR}/${subdir}${COLOR_RESET}" >&2
    done

    return 0
}

################################################################################
# 生成日志文件路径
#
# 参数：
#   $1 - log_name: 日志文件名（可选，默认为 session.log）
#
# 返回：
#   输出日志文件的完整路径
#
# 示例：
#   LOG_FILE=$(skill_session_log_path test.log)
#   command > "$LOG_FILE" 2>&1
################################################################################
skill_session_log_path() {
    local log_name="${1:-session.log}"

    if ! skill_session_validate; then
        return 1
    fi

    echo "$SESSION_DIR/logs/$log_name"
}

################################################################################
# 生成报告文件路径
#
# 参数：
#   $1 - report_name: 报告文件名（可选，默认为 report.md）
#
# 返回：
#   输出报告文件的完整路径
#
# 示例：
#   REPORT_FILE=$(skill_session_report_path tables.md)
#   command --output "$REPORT_FILE"
################################################################################
skill_session_report_path() {
    local report_name="${1:-report.md}"

    if ! skill_session_validate; then
        return 1
    fi

    echo "$SESSION_DIR/reports/$report_name"
}

################################################################################
# 导出函数（用于 source <(command) 模式）
################################################################################
# 检查脚本是被 source 还是直接执行
_SOURCED=0
if [[ "${BASH_SOURCE[0]:-}" != "${0}" ]] && [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    _SOURCED=1
fi

if [[ $_SOURCED -eq 1 ]]; then
    # 脚本被 source 时执行
    :
else
    # 脚本直接执行时显示帮助
    cat <<EOF
Skill Session Library v1.0.0

统一的技能会话管理函数库

使用方法：
  source .claude/skills/shared/skill-session-lib.sh

主要函数：
  skill_session_init <skill_name> <action_type> [description]
    初始化会话（必须首先调用）

  skill_session_validate
    验证会话环境

  skill_session_finish [message]
    完成会话并询问是否保留

  skill_session_log_path [log_name]
    生成日志文件路径

  skill_session_report_path [report_name]
    生成报告文件路径

示例：
  # 初始化会话
  source .claude/skills/shared/skill-session-lib.sh
  skill_session_init meta-discovery test-all "测试所有技能"

  # 执行命令（使用双引号）
  LOG_FILE=\$(skill_session_log_path test.log)
  REPORT_FILE=\$(skill_session_report_path tables.md)

  java -jar tool.jar --output "\$REPORT_FILE" 2>&1 | tee "\$LOG_FILE"

  # 完成会话
  skill_session_finish "测试完成"

更多信息，请参考: docs/decisions/004-20260111-skill-session-path-error-analysis.md
EOF
fi
