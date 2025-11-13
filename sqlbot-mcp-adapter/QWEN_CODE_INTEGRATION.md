# Qwen Code 集成指南

本指南详细介绍如何将 SQLBot MCP Adapter 集成到 Qwen Code 中。

## 🎯 集成概述

SQLBot MCP Adapter 通过标准的 Model Context Protocol (MCP) 为 Qwen Code 提供了访问 SQLBot 数据源的能力。

## 📋 前置条件

1. **Qwen Code 已安装并运行**
2. **SQLBot 服务已部署并可访问**
3. **SQLBot MCP Adapter 已启动**

## 🔧 配置步骤

### 1. 启动 SQLBot MCP Adapter

```bash
# 进入适配器目录
cd sqlbot-mcp-adapter

# 配置环境变量
cp .env.example .env
nano .env

# 设置 SQLBot 连接信息
SQLBOT_BASE_URL=http://your-sqlbot-server:8000
SQLBOT_USERNAME=your_username
SQLBOT_PASSWORD=your_password

# 启动服务
./start.sh http
```

服务启动后，你应该看到：
```
[INFO] SQLBot MCP Adapter started in HTTP mode on 0.0.0.0:8080
[INFO] HTTP Server: http://0.0.0.0:8080
[INFO] MCP Endpoint: http://0.0.0.0:8080/mcp
[INFO] Health Check: http://0.0.0.0:8080/health
```

### 2. 配置 Qwen Code

找到 Qwen Code 的配置文件 `settings.json`（通常位于用户配置目录）：

#### Windows
```
%APPDATA%\QwenCode\settings.json
```

#### macOS
```
~/Library/Application Support/QwenCode/settings.json
```

#### Linux
```
~/.config/QwenCode/settings.json
```

在 `settings.json` 中添加 MCP 服务器配置：

```json
{
  "mcpServers": {
    "sqlbot-adapter": {
      "httpUrl": "http://localhost:8080/mcp",
      "headers": {
        "Content-Type": "application/json"
      },
      "timeout": 30000,
      "trust": false
    }
  },
  "mcpSettings": {
    "sqlbot-adapter": {
      "enabled": true
    }
  }
}
```

### 3. 重启 Qwen Code

配置完成后，重启 Qwen Code 以加载新的 MCP 服务器。

## ✅ 验证集成

### 1. 检查 MCP 连接

在 Qwen Code 中输入：

```
列出所有可用的 MCP 工具
```

你应该看到类似输出：
```
可用的 MCP 工具：
- sqlbot-adapter: get_token
- sqlbot-adapter: get_database_list
```

### 2. 测试获取令牌

```
请使用 sqlbot-adapter 的 get_token 工具获取访问令牌
```

成功响应示例：
```
获取到访问令牌：
- access_token: bearer eyJhbGciOiJIUzI1NiIs...
- token_type: bearer
- expire: 2025-11-21 11:45:44
- chat_id: null
```

### 3. 测试获取数据源列表

```
请使用 sqlbot-adapter 的 get_database_list 工具获取所有可用的数据源
```

成功响应示例：
```
找到 1 个数据源：
1. 人员台账 (Excel/CSV)
   - ID: 1
   - 描述: 人员台账
   - 状态: Success
   - 创建时间: 2025-11-13T20:03:06
```

## 🎨 使用场景示例

### 场景 1: 查看可用数据源

```
我想知道当前可以访问哪些数据源
```

Qwen Code 会自动调用 `get_database_list` 工具并展示结果。

### 场景 2: 数据探索对话

```
请帮我分析一下人员台账数据源的基本信息
```

Qwen Code 会先获取令牌，然后获取数据源列表，最后提供分析建议。

### 场景 3: 自动化数据查询

```
我需要定期获取人员台账的状态信息，请帮我设置一个自动化流程
```

## 🔧 高级配置

### 1. 自定义超时设置

```json
{
  "mcpServers": {
    "sqlbot-adapter": {
      "httpUrl": "http://localhost:8080/mcp",
      "timeout": 60000,
      "trust": false
    }
  }
}
```

### 2. 远程部署配置

如果 SQLBot MCP Adapter 部署在远程服务器：

```json
{
  "mcpServers": {
    "sqlbot-adapter": {
      "httpUrl": "http://your-server.com:8080/mcp",
      "headers": {
        "Content-Type": "application/json",
        "Authorization": "Bearer your-token-if-needed"
      },
      "timeout": 30000,
      "trust": true
    }
  }
}
```

### 3. 负载均衡配置

对于高可用场景，可以配置多个实例：

```json
{
  "mcpServers": {
    "sqlbot-adapter-1": {
      "httpUrl": "http://server1:8080/mcp"
    },
    "sqlbot-adapter-2": {
      "httpUrl": "http://server2:8080/mcp"
    }
  }
}
```

## 🐛 故障排除

### 常见问题

#### 1. MCP 服务器连接失败

**症状**: Qwen Code 中无法使用 SQLBot 工具

**解决方案**:
```bash
# 检查服务是否运行
curl http://localhost:8080/health

# 检查 MCP 端点
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'
```

#### 2. 令牌获取失败

**症状**: get_token 工具返回错误

**解决方案**:
- 检查 `.env` 文件中的用户名密码
- 验证 SQLBot 服务是否正常运行
- 确认账号权限是否正确

#### 3. 数据源列表为空

**症状**: get_database_list 返回空列表

**解决方案**:
- 检查用户是否有访问数据源的权限
- 确认 SQLBot 中是否已配置数据源

### 日志调试

启用详细日志：

```bash
# 停止当前服务
pkill -f sqlbot_mcp_adapter

# 重新启动并启用调试日志
LOG_LEVEL=DEBUG ./start.sh http
```

查看日志：
```bash
tail -f nohup.out
```

## 🚀 性能优化

### 1. 连接池配置

在 `.env` 文件中配置连接池：

```env
# HTTP 连接池大小
HTTP_POOL_SIZE=10

# 连接超时
HTTP_TIMEOUT=30
```

### 2. 令牌缓存优化

```env
# 令牌刷新阈值（秒）
TOKEN_REFRESH_THRESHOLD=300
```

### 3. 并发限制

```env
# 最大并发请求数
MAX_CONCURRENT_REQUESTS=5
```

## 📊 监控和维护

### 1. 健康检查

定期检查服务状态：

```bash
#!/bin/bash
# health_check.sh

HEALTH_URL="http://localhost:8080/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "SQLBot MCP Adapter: HEALTHY"
else
    echo "SQLBot MCP Adapter: UNHEALTHY (HTTP $RESPONSE)"
    # 发送告警
fi
```

### 2. 日志轮转

使用 logrotate 管理日志：

```bash
# /etc/logrotate.d/sqlbot-mcp-adapter
/path/to/sqlbot-mcp-adapter/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 user group
}
```

## 🔐 安全建议

### 1. 环境变量安全

- 使用强密码
- 定期轮换凭据
- 不要在代码中硬编码凭据

### 2. 网络安全

- 使用 HTTPS 连接（生产环境）
- 配置防火墙规则
- 启用访问日志

### 3. 权限控制

- 为 Qwen Code 创建专用 SQLBot 账号
- 限制账号权限范围
- 定期审计访问日志

## 📚 更多资源

- [SQLBot 官方文档](https://docs.sqlbot.com)
- [Qwen Code 用户指南](https://docs.qwencode.com)
- [MCP 协议规范](https://modelcontextprotocol.io)
- [GitHub Issues](https://github.com/sqlbot/sqlbot-mcp-adapter/issues)

---

🎉 现在你已经成功将 SQLBot 集成到 Qwen Code 中了！开始享受强大的数据查询和分析能力吧！