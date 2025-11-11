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
  # Use -m debugpy to listen and then run your app module. Adjust -m app.main if your project entry differs.
  exec "${PYTHON}" -m debugpy --listen 0.0.0.0:${PY_DEBUG_PORT} --wait-for-client -m app.main
else
  echo "Starting app normally via start.sh"
  # run the original start script (keeps same behavior as original Dockerfile)
  exec sh "${APP_HOME}/start.sh"
fi
