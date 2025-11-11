#!/usr/bin/env bash
set -e

# Usage: ./run.sh <host_ssh_port> <debug_mode(true|false)> <host_debug_port>
HOST_SSH_PORT=${1:-2222}
DEBUG_MODE=${2:-false}
HOST_DEBUG_PORT=${3:-5678}
IMAGE_NAME=sqlbot-debug:latest
CONTAINER_NAME=sqlbot-debug

echo "Building image (docker build) with container internal SSH port default 22..."
docker build --progress=plain -t ${IMAGE_NAME} .

# remove old container if exists
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
  docker rm -f ${CONTAINER_NAME} || true
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
  ${IMAGE_NAME}

echo "Done."
echo "SSH -> ssh sqlbot@127.0.0.1 -p ${HOST_SSH_PORT} (password: sqlbot)"
if [ "${DEBUG_MODE}" = "true" ]; then
  echo "Debug listening at 127.0.0.1:${HOST_DEBUG_PORT} (debugpy) — remember to 'Attach' from PyCharm"
fi
