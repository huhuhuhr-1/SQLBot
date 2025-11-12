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

# Check if we should start services based on START_SERVICES environment variable
START_SERVICES=${START_SERVICES:-true}

if [ "${DEBUG_MODE:-false}" = "true" ]; then
  # Debug mode: start services with debugpy
  PY_DEBUG_PORT=${PY_DEBUG_PORT:-5678}
  echo "DEBUG_MODE is true - starting app under debugpy. Listening on 0.0.0.0:${PY_DEBUG_PORT}"

  # Start G2-SSR service (server-side rendering) - always start this
  PM2_CMD_PATH=/opt/sqlbot/g2-ssr/node_modules/pm2/bin/pm2
  echo "Starting PM2 for G2-SSR service..."
  nohup $PM2_CMD_PATH start /opt/sqlbot/g2-ssr/app.js &
  sleep 2

  # Start MCP app with debugpy
  echo "Starting MCP app with debugpy on port ${PY_DEBUG_PORT}..."
  nohup ${PYTHON} -m debugpy --listen 0.0.0.0:${PY_DEBUG_PORT} --wait-for-client -m uvicorn main:mcp_app --host 0.0.0.0 --port 8001 &
  sleep 2

  # Start main app with debugpy if START_SERVICES is true
  if [ "$START_SERVICES" = "true" ]; then
    echo "Starting main app with debugpy on port 8000..."
    cd $APP_HOME
    exec ${PYTHON} -m debugpy --listen 0.0.0.0:${PY_DEBUG_PORT} --wait-for-client -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
  else
    echo "START_SERVICES is false, main app not started automatically. You can start it manually."
    # Keep the container running
    tail -f /dev/null
  fi
else
  # Normal mode: start all services normally
  if [ "$START_SERVICES" = "true" ]; then
    echo "Starting app normally via start.sh"
    exec sh "${APP_HOME}/start.sh"
  else
    echo "START_SERVICES is false, services not started automatically. You can start them manually."
    # Keep the container running
    tail -f /dev/null
  fi
fi