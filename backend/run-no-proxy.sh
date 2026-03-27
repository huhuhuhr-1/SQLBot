#!/usr/bin/env bash
# 本地启动后端时使用：临时取消代理，避免 LangChain 报 SOCKS 代理错误；不影响本机 Clash
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
