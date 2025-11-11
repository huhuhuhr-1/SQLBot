#!/bin/bash
set -e

# paths
SQLBOT_HOME=${SQLBOT_HOME:-/opt/sqlbot}
APP_HOME=${SQLBOT_HOME}/app
VENV=${APP_HOME}/.venv
PYTHON=${VENV}/bin/python

# ensure ssh service can be started by sudo (sudo no-password for sqlbot)
echo "Starting SSH service..."
sudo service ssh start || { echo "failed to start ssh, trying /usr/sbin/sshd"; sudo /usr/sbin/sshd; }

# If venv Python missing, fallback to system python
if [ ! -x "$PYTHON" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON=$(command -v python3)
  else
    echo "No python found"; exit 1
  fi
fi

# If DEBUG_MODE=true then start under debugpy and wait for attach
if [ "${DEBUG_MODE:-false}" = "true" ]; then
  PY_DEBUG_PORT=${PY_DEBUG_PORT:-5678}
  echo "DEBUG_MODE is true - starting app under debugpy. Listening on 0.0.0.0:${PY_DEBUG_PORT}"

  # 启动必要的服务 (PostgreSQL + G2-SSR)
  /usr/local/bin/docker-entrypoint.sh postgres &
  sleep 5
  wait-for-it 127.0.0.1:5432 --timeout=120 --strict -- echo "PostgreSQL started."

  PM2_CMD_PATH=/opt/sqlbot/g2-ssr/node_modules/pm2/bin/pm2
  nohup $PM2_CMD_PATH start /opt/sqlbot/g2-ssr/app.js &

  # 启动主应用 (需要找到实际的主入口点)
  echo "Starting main Python app with debugpy..."
  # 假设主应用是通过某个脚本启动的，这里需要根据实际情况调整
  if [ -f "${APP_HOME}/main.py" ]; then
    exec "${PYTHON}" -m debugpy --listen 0.0.0.0:${PY_DEBUG_PORT} --wait-for-client main.py
  else
    echo "警告: 找不到 main.py，请检查实际的应用入口点"
    echo "当前目录内容:"
    ls -la ${APP_HOME}
    exec "${PYTHON}" -m debugpy --listen 0.0.0.0:${PY_DEBUG_PORT} --wait-for-client -c "
import os
import sys
sys.path.insert(0, '${APP_HOME}')
# 这里需要根据实际应用结构调整
exec(open('app.py').read())"
  fi
else
  echo "Starting app normally via start.sh"
  # run the original start script (keeps same behavior as original Dockerfile)
  exec sh "${APP_HOME}/start.sh"
fi
