#!/bin/bash
set -e

# 设置时区（仅在有权限时执行）
if [ -w /etc/localtime ]; then
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime 2>/dev/null || true
    echo "Asia/Shanghai" > /etc/timezone 2>/dev/null || true
    echo "Timezone set to Asia/Shanghai"
else
    echo "Skipping timezone setup (no permission)"
fi

echo "Starting SQLBot MCP Adapter..."
echo "=================================="
echo "Configuration:"
echo "  SQLBOT_BASE_URL: ${SQLBOT_BASE_URL:-http://localhost:8000/api/v1}"
echo "  SQLBOT_USERNAME: ${SQLBOT_USERNAME:-admin}"
echo "  HOST: ${HOST:-0.0.0.0}"
echo "  PORT: ${PORT:-8080}"
echo "  LOG_LEVEL: ${LOG_LEVEL:-INFO}"
echo "  DB_NAME: ${DB_NAME:-研发质量数据}"
echo "=================================="

# 验证必要的环境变量
if [ -z "$SQLBOT_USERNAME" ] || [ -z "$SQLBOT_PASSWORD" ]; then
    echo "ERROR: SQLBOT_USERNAME and SQLBOT_PASSWORD must be set"
    exit 1
fi

# 等待 SQLBot 服务启动（如果配置了的话）
if [ ! -z "$SQLBOT_BASE_URL" ]; then
    echo "Waiting for SQLBot service to be available at $SQLBOT_BASE_URL..."
    timeout=60
    count=0

    # 尝试多个可能的健康检查端点
    HEALTH_URLS=(
        "$SQLBOT_BASE_URL/../health"
        "$SQLBOT_BASE_URL/../"
        "${SQLBOT_BASE_URL%/api/v1}/health"ze
        "${SQLBOT_BASE_URL%/api/v1}/"
    )

    HEALTH_CHECK_PASSED=false
    while [ "$HEALTH_CHECK_PASSED" = false ]; do
        for health_url in "${HEALTH_URLS[@]}"; do
            echo "Trying health check at: $health_url"
            if curl -f "$health_url" >/dev/null 2>&1; then
                echo "SQLBot service is available at $health_url!"
                HEALTH_CHECK_PASSED=true
                break 2
            fi
        done

        if [ $count -ge $timeout ]; then
            echo "ERROR: SQLBot service is not available after ${timeout}s"
            echo "Tried the following endpoints:"
            for health_url in "${HEALTH_URLS[@]}"; do
                echo "  - $health_url"
            done
            exit 1
        fi
        echo "Waiting for SQLBot service... ($count/$timeout)"
        sleep 2
        count=$((count + 2))
    done
fi

echo "Starting SQLBot MCP Server..."

# 启动应用
exec python main.py