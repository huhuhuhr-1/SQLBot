#!/bin/bash

# 简单的 SQLBot MCP 启动脚本

echo "启动 SQLBot MCP 服务..."
echo "确保已配置 .env 文件中的 SQLBOT 凭据"

# 检查 uv 是否可用
if command -v uv &> /dev/null; then
    echo "使用 uv 运行服务..."
    uv run python main.py
else
    echo "uv 未找到，尝试直接运行..."
    python main.py
fi