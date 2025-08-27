#!/bin/bash

# Get the current date in the format YYYYMMDD
VERSION=$(date +%Y%m%d)

echo "🚀 快速构建 SQLBot..."

export DOCKER_BUILDKIT=1

# 检查是否在 build 目录下
if [[ "$PWD" == *"/build" ]]; then
    echo "📍 在 build 目录下，切换到项目根目录构建..."
    echo "📁 当前目录: $(pwd)"
    echo "📁 切换到上级目录..."
    cd ..
    echo "📁 当前目录: $(pwd)"
    echo "📁 检查 build 目录内容:"
    ls -la build/
    echo "📁 检查 backend 目录内容:"
    ls -la backend/ | head -5
    echo "🚀 开始构建..."
    docker build -f build/Dockerfile -t my-sqlbot:v1.0.0.$VERSION .
    echo "📁 构建完成，回到 build 目录..."
    cd build
    echo "📁 当前目录: $(pwd)"
else
    echo "📍 在项目根目录下，直接构建..."
    echo "📁 当前目录: $(pwd)"
    echo "📁 检查 build 目录内容:"
    ls -la build/
    echo "📁 检查 backend 目录内容:"
    ls -la backend/ | head -5
    echo "🚀 开始构建..."
    docker build -f build/Dockerfile -t my-sqlbot:v1.0.0.$VERSION .
fi

echo "✅ 完成！"
