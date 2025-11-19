#!/bin/bash

# 启动脚本
echo "Starting NiFi MCP Server..."

# 检查环境变量
if [ -z "$NIFI_BASE_URL" ]; then
    echo "Warning: NIFI_BASE_URL not set, using default: http://localhost:8080"
    export NIFI_BASE_URL="http://localhost:8080"
fi

# 启动服务
python main.py