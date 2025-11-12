#!/usr/bin/env bash
set -e

# Usage: ./build.sh [image_name] [ssh_port]
IMAGE_NAME=${1:-sqlbot-debug:latest}
SSH_PORT=${2:-22}

# 获取脚本所在目录的父目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "开始编译 SQLBot 开发镜像..."
echo "项目根目录: ${PROJECT_ROOT}"
echo "镜像名称: ${IMAGE_NAME}"
echo "容器内SSH端口: ${SSH_PORT}"
echo ""

# 切换到项目根目录并构建镜像
cd "$PROJECT_ROOT"
docker build \
  --build-arg SSH_PORT=${SSH_PORT} \
  --progress=plain \
  -f build/dev/Dockerfile \
  -t ${IMAGE_NAME} \
  .

echo ""
echo "编译完成!"
echo ""
echo "导出镜像用于内网部署:"
echo "  docker save ${IMAGE_NAME} | gzip > sqlbot-debug.tar.gz"
echo "  # 或者"
echo "  docker save ${IMAGE_NAME} > sqlbot-debug.tar"
echo ""
echo "运行容器 (连接到本地数据库):"
echo "  ./run.sh 2222 false 5678 ${IMAGE_NAME} false 8000 3000 8001 localhost 5432 root Password123@pg sqlbot"
echo ""
echo "内网使用流程:"
echo "  1. 在外网: ./build.sh && docker save sqlbot-debug:latest > sqlbot-debug.tar"
echo "  2. 传输到内网: scp sqlbot-debug.tar user@internal-host:/path/"
echo "  3. 在内网: docker load < sqlbot-debug.tar && ./run.sh"