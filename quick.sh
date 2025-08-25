#!/bin/bash

echo "🚀 快速构建 SQLBot..."

export DOCKER_BUILDKIT=1
docker build -t zf-sqlbot:v1.0.0.20250825 .

echo "✅ 完成！"