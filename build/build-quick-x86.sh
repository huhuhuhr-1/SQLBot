#!/bin/bash
# x86 平台快速构建（与 Dockerfile.update 的 FROM 一致，直接使用）

VERSION="20251130"
FINAL_IMAGE="zf-sqlbot:latest"

cd "$(dirname "$0")/.." || exit 1
echo "🔨 构建 x86 平台镜像..."
docker build -f build/Dockerfile.update -t ${FINAL_IMAGE} .
echo "✅ x86 镜像构建完成: ${FINAL_IMAGE}"
