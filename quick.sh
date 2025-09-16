#!/bin/bash

# Get the current date in the format YYYYMMDD
VERSION=$(date +%Y%m%d)

echo "🚀 快速构建 SQLBot..."

export DOCKER_BUILDKIT=1
docker build -t zf-sqlbot:v1.1.2.$VERSION .

echo "✅ 完成！"
