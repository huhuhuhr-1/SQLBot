# Backend Code Guide

本文档帮助你快速了解 SQLBot 后端的核心结构。

## main.py
负责创建 FastAPI 应用并在启动时执行数据库迁移、缓存初始化以及 MCP 服务器的挂载。

## apps/api.py
聚合各业务模块的路由，将登录、用户、工作空间、聊天等接口统一暴露给前端。

## apps/mcp
包含 MCP 相关接口：
- `mcp.py` 提供外部系统使用的登录与提问能力
- `__init__.py` 标记此包并提供简要说明

## apps/system/middleware/auth.py
全局请求中间件，从请求头解析并校验用户或助手的访问令牌，确保接口安全。

