#!/bin/bash

# Get the current date in the format YYYYMMDD
VERSION=$(date +%Y%m%d)

echo "🚀 快速构建 SQLBot..."

# 启用 BuildKit 支持 --platform 参数
export DOCKER_BUILDKIT=1
echo "🔨 使用 BuildKit 构建引擎..."

# 优先使用标准 Docker 构建（自动使用本地镜像缓存）
# buildx 的 docker-container 构建器不会自动使用本地缓存
if docker buildx version >/dev/null 2>&1; then
    echo "🚀 使用 Docker 构建（启用本地缓存）..."
    docker build -t zf-sqlbot:latest .
else
    echo "🏗️  使用标准 Docker 构建..."
    docker build -t zf-sqlbot:latest .
fi

echo "✅ 完成！"
