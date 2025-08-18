# Backend Code Guide

本文档帮助你快速了解 SQLBot 后端的核心结构与运行流程。

## 启动阶段

1. `main.py` 通过 `run_migrations` 执行数据库迁移，确保结构最新。
2. 初始化缓存 `init_sqlbot_cache` 与动态 CORS 设置 `init_dynamic_cors`。
3. 挂载 MCP 静态资源并创建 `FastApiMCP` 以提供插件能力。
4. 注册路由与中间件，启动后即对外提供 API。

## 运行阶段：聊天主流程

1. 前端调用 `apps/chat/api/chat.py` 中的 `/chat/question`。
2. `LLMService` 保存提问记录、生成 SQL、执行查询并生成图表。
3. 结果以 `StreamingResponse` 逐步返回给前端，形成实时对话。

## 数据源操作

相关接口位于 `apps/datasource/api/datasource.py`，主要包含：

- 列出、添加、更新、删除数据源。
- 校验数据源连接、同步表和字段。
- 上传 Excel/CSV 并导入为临时数据表供分析使用。

## 其他模块

- `apps/api.py` 聚合各业务模块路由。
- `apps/system/middleware/auth.py` 解析请求头中的令牌并校验权限。
- `apps/mcp` 提供给外部系统的轻量接口。
