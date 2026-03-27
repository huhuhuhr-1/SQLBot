# Debug entrypoint: same as start.sh but main app runs under debugpy for IDE attach on 5678
SSR_PATH=/opt/sqlbot/g2-ssr
APP_PATH=/opt/sqlbot/app
PM2_CMD_PATH=$SSR_PATH/node_modules/pm2/bin/pm2

# 取消代理环境变量，避免 Python/LangChain 使用 SOCKS 代理导致启动报错；不影响本机 Clash 及其他程序
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy

/usr/local/bin/docker-entrypoint.sh postgres &
sleep 5
wait-for-it 127.0.0.1:5432 --timeout=120 --strict -- echo -e "\033[1;32mPostgreSQL started.\033[0m"

nohup $PM2_CMD_PATH start $SSR_PATH/app.js &

nohup uvicorn main:mcp_app --host 0.0.0.0 --port 8001 &

cd $APP_PATH
# Listen on 0.0.0.0:5678 for IDE "Remote Attach" (e.g. VS Code / PyCharm)
exec python -m debugpy --listen 0.0.0.0:5678 -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
