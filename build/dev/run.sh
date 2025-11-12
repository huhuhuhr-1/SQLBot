#!/usr/bin/env bash
set -e

# 加载配置文件
ENV_FILE="${1:-.env}"
if [ -f "$ENV_FILE" ]; then
    echo "使用配置文件: $ENV_FILE"
    # 加载 .env 文件内容
    export $(cat "$ENV_FILE" | sed 's/#.*//g' | xargs)
else
    echo "警告: 配置文件 $ENV_FILE 不存在，将使用默认值。"
    echo "建议复制 .env.example 为 .env 并根据需要修改配置。"
fi

# 设置默认值（如果环境变量未设置）
HOST_SSH_PORT=${HOST_SSH_PORT:-2222}
IMAGE_NAME=${IMAGE_NAME:-sqlbot-debug:latest}
DEBUG_MODE=${DEBUG_MODE:-false}
HOST_DEBUG_PORT=${HOST_DEBUG_PORT:-5678}
HOST_BACKEND_PORT=${HOST_BACKEND_PORT:-8000}
HOST_FRONTEND_PORT=${HOST_FRONTEND_PORT:-3000}
HOST_MCP_PORT=${HOST_MCP_PORT:-8001}
MOUNT_CODE=${MOUNT_CODE:-false}
CONTAINER_NAME=sqlbot-debug

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Check if image exists
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

echo "运行容器: 映射主机 ${HOST_SSH_PORT}->容器 ${SSH_PORT}, 主机 ${HOST_DEBUG_PORT}->容器 ${PY_DEBUG_PORT}, 主机 ${HOST_BACKEND_PORT}->容器 8000, 主机 ${HOST_FRONTEND_PORT}->容器 3000, 主机 ${HOST_MCP_PORT}->容器 8001"
docker run -d \
  --name ${CONTAINER_NAME} \
  -p ${HOST_SSH_PORT}:${SSH_PORT} \
  -p ${HOST_BACKEND_PORT}:8000 \
  -p ${HOST_FRONTEND_PORT}:3000 \
  -p ${HOST_MCP_PORT}:8001 \
  -p ${HOST_DEBUG_PORT}:${PY_DEBUG_PORT} \
  -e DEBUG_MODE=${DEBUG_MODE} \
  -e PY_DEBUG_PORT=${PY_DEBUG_PORT} \
  -e POSTGRES_SERVER=${POSTGRES_SERVER} \
  -e POSTGRES_PORT=${POSTGRES_PORT} \
  -e POSTGRES_USER=${POSTGRES_USER} \
  -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
  -e POSTGRES_DB=${POSTGRES_DB} \
  ${VOLUME_MOUNTS} \
  ${IMAGE_NAME}

echo "完成."
echo "SSH -> ssh sqlbot@127.0.0.1 -p ${HOST_SSH_PORT} (密码: sqlbot)"
echo "前端访问: http://localhost:${HOST_FRONTEND_PORT}"
echo "后端API: http://localhost:${HOST_BACKEND_PORT}"
echo "MCP服务: http://localhost:${HOST_MCP_PORT}"
echo "数据库连接: ${POSTGRES_SERVER}:${POSTGRES_PORT} (db: ${POSTGRES_DB}, user: ${POSTGRES_USER})"
if [ "${DEBUG_MODE}" = "true" ]; then
  echo "调试监听在 127.0.0.1:${HOST_DEBUG_PORT} (debugpy) — 记得在 PyCharm 中 'Attach'"
fi
if [ "${MOUNT_CODE}" = "true" ]; then
  echo "代码挂载: 宿主机 ${PROJECT_ROOT}/ -> 容器 /opt/sqlbot/"
fi
