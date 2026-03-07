#!/bin/bash
# x86 平台快速构建脚本

VERSION="20251130"
BASE_IMAGE="sqlbot-dev-${VERSION}:latest"
FINAL_IMAGE="zf-sqlbot:latest"

echo "🔨 构建 x86 平台镜像..."
docker build -f build/Dockerfile.update.x86 -t ${FINAL_IMAGE} .
echo "✅ x86 镜像构建完成: ${FINAL_IMAGE}"
