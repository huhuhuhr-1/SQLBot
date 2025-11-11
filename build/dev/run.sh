#!/usr/bin/env bash
set -e

# Usage: ./run.sh <host_ssh_port> <debug_mode(true|false)> <host_debug_port> [image_name] [mount_code]
HOST_SSH_PORT=${1:-2222}
DEBUG_MODE=${2:-false}
HOST_DEBUG_PORT=${3:-5678}
IMAGE_NAME=${4:-sqlbot-debug:latest}
MOUNT_CODE=${5:-false}
CONTAINER_NAME=sqlbot-debug

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Check if image exists, if not提示导入
if ! docker image inspect ${IMAGE_NAME} >/dev/null 2>&1; then
    echo "错误: 镜像 ${IMAGE_NAME} 不存在!"
    echo ""
    echo "请先导入预编译的镜像:"
    echo "  docker load < sqlbot-debug.tar"
    echo ""
    echo "或者使用 ./build.sh 编译镜像"
    exit 1
fi

echo "使用现有镜像: ${IMAGE_NAME}"

# remove old container if exists
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
  docker rm -f ${CONTAINER_NAME} || true
fi

# Prepare volume mounts
VOLUME_MOUNTS=""
if [ "${MOUNT_CODE}" = "true" ]; then
    VOLUME_MOUNTS="-v ${PROJECT_ROOT}/backend:/opt/sqlbot/app -v ${PROJECT_ROOT}/frontend:/tmp/frontend -v ${PROJECT_ROOT}/g2-ssr:/opt/sqlbot/g2-ssr"
    echo "代码挂载模式已启用: 修改宿主机代码会同步到容器"
fi

echo "Running container: mapping host ${HOST_SSH_PORT}->container 22, host ${HOST_DEBUG_PORT}->container ${HOST_DEBUG_PORT}"
docker run -d \
  --name ${CONTAINER_NAME} \
  -p ${HOST_SSH_PORT}:22 \
  -p 8000:8000 \
  -p 3000:3000 \
  -p ${HOST_DEBUG_PORT}:${HOST_DEBUG_PORT} \
  -e DEBUG_MODE=${DEBUG_MODE} \
  -e PY_DEBUG_PORT=${HOST_DEBUG_PORT} \
  ${VOLUME_MOUNTS} \
  ${IMAGE_NAME}

echo "Done."
echo "SSH -> ssh sqlbot@127.0.0.1 -p ${HOST_SSH_PORT} (password: sqlbot)"
echo "前端访问: http://localhost:3000"
echo "后端API: http://localhost:8000"
if [ "${DEBUG_MODE}" = "true" ]; then
  echo "Debug listening at 127.0.0.1:${HOST_DEBUG_PORT} (debugpy) — remember to 'Attach' from PyCharm"
fi
if [ "${MOUNT_CODE}" = "true" ]; then
  echo "代码挂载: 宿主机 ${PROJECT_ROOT}/ -> 容器 /opt/sqlbot/"
fi
