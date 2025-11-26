# SQLBot MCP Server Docker 部署指南

本文档提供 SQLBot MCP Server 的 Docker 部署完整指南。

## 📋 部署概述

SQLBot MCP Server 是一个轻量级的 Model Context Protocol (MCP) 适配器，用于将 SQLBot 服务与支持 MCP 的 AI 助手集成。

## 🏗️ 架构

```
┌─────────────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Assistant (Claude) │───▶│ SQLBot MCP Server│───▶│   SQLBot API   │
│   (MCP Client)         │    │  (This Service) │    │                 │
└─────────────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 快速部署

### 1. 构建镜像

```bash
# 克隆项目
git clone <repository-url>
cd sqlbot-mcp-adapter

# 构建 Docker 镜像
docker build -t sqlbot-mcp-server:latest .
```

### 2. 运行容器

```bash
# 基本运行
docker run -d \
  --name sqlbot-mcp-server \
  -p 8080:8080 \
  -e SQLBOT_BASE_URL=http://your-sqlbot-host:8000/api/v1 \
  -e SQLBOT_USERNAME=your_username \
  -e SQLBOT_PASSWORD=your_password \
  sqlbot-mcp-server:latest
```

### 3. 使用 Docker Compose（推荐）

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f sqlbot-mcp-server

# 停止服务
docker-compose down
```

## ⚙️ 环境变量配置

### 必需配置

| 变量名 | 描述 | 示例值 | 必需 |
|--------|------|--------|------|
| `SQLBOT_BASE_URL` | SQLBot API 基础 URL | `http://sqlbot:8000/api/v1` | ✅ |
| `SQLBOT_USERNAME` | SQLBot 用户名 | `admin` | ✅ |
| `SQLBOT_PASSWORD` | SQLBot 密码 | `password123` | ✅ |

### 可选配置

| 变量名 | 描述 | 默认值 | 说明 |
|--------|------|--------|------|
| `HOST` | 服务器监听地址 | `0.0.0.0` | 通常不需要修改 |
| `PORT` | 服务器端口 | `8080` | 可根据需要修改 |
| `LOG_LEVEL` | 日志级别 | `INFO` | DEBUG/INFO/WARNING/ERROR |
| `DB_NAME` | 默认数据库名称 | `人员台账` | 用于 /question 端点 |

## 🔌 API 端点

服务启动后，提供以下 API 端点：

### HTTP API

- `GET /health` - 健康检查
- `GET /get_token?create_chat=true` - 获取访问令牌
- `GET /get_database_list` - 获取数据源列表
- `POST /get_data_source_by_name` - 通过名称获取数据源详情
- `POST /question?question=xxx&chat_id=xxx` - 智能问答（流式输出）

### MCP 协议

- `GET /mcp` - MCP 服务器信息
- `POST /mcp/call/{tool_name}` - 调用 MCP 工具

## 🐳 Docker Compose 配置

### 基本配置

```yaml
version: '3.8'

services:
  sqlbot-mcp-server:
    image: sqlbot-mcp-server:latest
    container_name: sqlbot-mcp-server
    ports:
      - "8080:8080"
    environment:
      - SQLBOT_BASE_URL=http://sqlbot:8000/api/v1
      - SQLBOT_USERNAME=admin
      - SQLBOT_PASSWORD=SQLBot@123456
      - LOG_LEVEL=INFO
      - DB_NAME=人员台账
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 完整配置（包含 SQLBot 服务）

```yaml
version: '3.8'

services:
  sqlbot-mcp-server:
    build:
      context: .
      dockerfile: Dockerfile
    image: sqlbot-mcp-server:latest
    container_name: sqlbot-mcp-server
    ports:
      - "8080:8080"
    environment:
      - SQLBOT_BASE_URL=http://sqlbot:8000/api/v1
      - SQLBOT_USERNAME=admin
      - SQLBOT_PASSWORD=SQLBot@123456
      - LOG_LEVEL=INFO
      - DB_NAME=人员台账
    restart: unless-stopped
    depends_on:
      sqlbot:
        condition: service_healthy
    networks:
      - sqlbot-network

  sqlbot:
    image: registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-python-pg:latest
    container_name: sqlbot
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_DB=sqlbot
      - POSTGRES_USER=root
      - POSTGRES_PASSWORD=Password123@pg
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - sqlbot-network

networks:
  sqlbot-network:
    driver: bridge
```

## 🔍 验证部署

### 1. 健康检查

```bash
# 检查服务状态
curl http://localhost:8080/health

# 预期响应：
# {
#   "status": "healthy",
#   "service": "SQLBot MCP Adapter",
#   "version": "1.0.0",
#   "sqlbot_url": "http://sqlbot:8000/api/v1",
#   "timestamp": ""
# }
```

### 2. 获取令牌

```bash
# 获取访问令牌
curl "http://localhost:8080/get_token?create_chat=true"

# 预期响应包含 access_token 等字段
```

### 3. 获取数据源列表

```bash
# 获取数据源列表
curl http://localhost:8080/get_database_list

# 预期响应包含数据源列表
```

## 🔧 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   # 查看容器日志
   docker logs sqlbot-mcp-server
   ```

2. **无法连接 SQLBot**
   - 检查 `SQLBOT_BASE_URL` 配置
   - 确认 SQLBot 服务正常运行
   - 检查网络连接

3. **健康检查失败**
   ```bash
   # 进入容器调试
   docker exec -it sqlbot-mcp-server bash

   # 手动测试
   curl http://localhost:8080/health
   ```

### 日志查看

```bash
# 查看实时日志
docker-compose logs -f sqlbot-mcp-server

# 查看最近的日志
docker-compose logs --tail=100 sqlbot-mcp-server
```

## 📊 监控和维护

### 资源监控

```bash
# 查看容器资源使用情况
docker stats sqlbot-mcp-server

# 查看容器详细信息
docker inspect sqlbot-mcp-server
```

### 定期维护

```bash
# 清理未使用的镜像
docker image prune -f

# 清理未使用的容器
docker container prune -f

# 更新镜像
docker pull sqlbot-mcp-server:latest
docker-compose up -d
```

## 🚀 生产环境建议

### 1. 安全配置

- 使用强密码
- 配置 HTTPS
- 限制网络访问
- 定期更新镜像

### 2. 高可用

- 配置健康检查
- 设置自动重启
- 使用负载均衡器
- 配置日志收集

### 3. 性能优化

- 配置资源限制
- 使用适当的基础镜像
- 优化日志输出
- 监控性能指标

## 📞 支持

如果遇到问题：

1. 查看本文档的故障排除部分
2. 检查容器日志
3. 确认环境变量配置
4. 验证网络连接

---

🎉 现在你可以将 SQLBot MCP Server 部署到任何支持 Docker 的环境中！