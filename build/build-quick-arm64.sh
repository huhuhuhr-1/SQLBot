#!/bin/bash
# ARM64 平台快速构建（由 Dockerfile.update 替换 FROM 生成）

VERSION="20251130"
FINAL_IMAGE="zf-sqlbot:arm64"

cd "$(dirname "$0")/.." || exit 1
echo "🔨 构建 ARM64 平台镜像..."
sed 's/FROM sqlbot-dev-20251130:latest/FROM sqlbot-dev-20251130:arm64/' build/Dockerfile.update | docker build -f - -t ${FINAL_IMAGE} .
echo "✅ ARM64 镜像构建完成: ${FINAL_IMAGE}"
