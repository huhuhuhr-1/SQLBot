#!/usr/bin/env bash
set -e

# 快速测试构建脚本
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
IMAGE_NAME=sqlbot-test:latest

echo "快速构建测试镜像: ${IMAGE_NAME}"
cd "$PROJECT_ROOT"
docker build -f build/dev/Dockerfile.test -t ${IMAGE_NAME} .

echo "测试镜像构建完成!"
echo "现在可以运行: ./run.sh 2222 true 5678 ${IMAGE_NAME}"