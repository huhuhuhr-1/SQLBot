#!/usr/bin/env sh
# 一键启动小助手嵌入示例服务（Linux / macOS）
cd "$(dirname "$0")"
if ! command -v node >/dev/null 2>&1; then
  echo "未检测到 Node.js，请先安装: https://nodejs.org/"
  exit 1
fi
export PORT="${PORT:-3000}"
echo ""
echo "  启动示例服务 (端口: $PORT)"
echo "  启动后请将 SQLBot 小助手跨域设置包含: http://localhost:$PORT"
echo ""
exec node server.js
