#!/bin/bash
set -e

SSR_PATH=/opt/sqlbot/g2-ssr
APP_PATH=/opt/sqlbot/app
PM2_CMD_PATH=$SSR_PATH/node_modules/pm2/bin/pm2

echo "Starting SQLBot in development mode..."

# Start PM2 for SSR (Server-Side Rendering)
echo "Starting PM2 for G2-SSR service..."
nohup $PM2_CMD_PATH start $SSR_PATH/app.js &
sleep 2

# Start MCP app
echo "Starting MCP app on port 8001..."
nohup uvicorn main:mcp_app --host 0.0.0.0 --port 8001 &
sleep 2

# Start main app
echo "Starting main app on port 8000..."
cd $APP_PATH
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers