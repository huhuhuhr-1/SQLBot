#!/bin/bash
# ARM64 平台快速构建脚本

VERSION="20251130"
BASE_IMAGE="sqlbot-dev-${VERSION}:arm64"
FINAL_IMAGE="zf-sqlbot:arm64"

echo "🔨 构建 ARM64 平台镜像..."
docker build -f build/Dockerfile.update.arm64 -t ${FINAL_IMAGE} .
echo "✅ ARM64 镜像构建完成: ${FINAL_IMAGE}"
