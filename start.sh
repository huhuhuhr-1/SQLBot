SSR_PATH=/opt/sqlbot/g2-ssr
APP_PATH=/opt/sqlbot/app
docker-entrypoint.sh postgres
nohup node $SSR_PATH/app.js &

nohup uvicorn main:mcp_app --host 0.0.0.0 --port 8001 &

cd $APP_PATH
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
