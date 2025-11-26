# SQLBot MCP Adapter

一个轻量级但功能完善的 MCP (Model Context Protocol) 适配器，用于将 SQLBot 服务与支持 MCP 的 AI 助手（如 Claude Desktop、Qwen Code 等）集成。

## ✨ 特性

- 🚀 **开箱即用** - 简单配置即可启动服务
- 🔐 **安全认证** - 支持 SQLBot 用户认证和令牌管理
- 📡 **双协议支持** - 同时支持 HTTP 和 Stdio 模式
- 🛠️ **FastAPI 驱动** - 基于 FastAPI 构建，性能优异
- 📊 **数据源管理** - 获取和管理 SQLBot 数据源
- 📝 **详细日志** - 完整的请求日志和错误追踪
- 🐳 **部署友好** - 支持 Docker 部署和环境变量配置

## 📦 系统要求

- Python 3.11+
- SQLBot 服务实例
- uv (推荐) 或 pip

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/sqlbot/sqlbot-mcp-adapter.git
cd sqlbot-mcp-adapter
```

### 2. 配置环境

复制并编辑配置文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置你的 SQLBot 服务信息：

```env
# SQLBot API 配置
SQLBOT_BASE_URL=http://your-sqlbot-server:8000
SQLBOT_USERNAME=your_username
SQLBOT_PASSWORD=your_password

# 服务器配置
HOST=0.0.0.0
PORT=8080
LOG_LEVEL=INFO
```

### 3. 安装依赖

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -e .
```

### 4. 启动服务

#### 方式一：使用启动脚本

```bash
chmod +x start.sh
./start.sh
```

#### 方式二：直接运行

```bash
uv run python main.py
```

服务将在 `http://localhost:8080` 启动。

## 🛠️ MCP 工具

该适配器提供以下 MCP 工具：

### get_token
获取 SQLBot 访问令牌，用于后续 API 调用。

**参数：**
- `create_chat` (boolean): 是否创建聊天会话，默认为 `true`

**返回：**
```json
{
  "access_token": "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expire": "2025-11-21 11:45:44",
  "chat_id": "chat_12345"
}
```

### get_database_list
获取 SQLBot 中的所有数据源列表。

**参数：** 无

**返回：**
```json
{
  "databases": [
    {
      "id": 1,
      "name": "销售数据",
      "description": "2024年销售数据台账",
      "type": "mysql",
      "type_name": "MySQL数据库",
      "create_time": "2025-11-13T20:03:06.233119",
      "status": "Success",
      "num": "1/3"
    }
  ],
  "count": 1
}
```

## 🔌 集成配置

### Claude Desktop

在 Claude Desktop 的 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "sqlbot-adapter": {
      "command": "uv",
      "args": ["run", "python", "/path/to/sqlbot-mcp-adapter/main.py"],
      "env": {
        "SQLBOT_BASE_URL": "http://your-sqlbot-server:8000",
        "SQLBOT_USERNAME": "your_username",
        "SQLBOT_PASSWORD": "your_password"
      }
    }
  }
}
```

### Qwen Code

在 Qwen Code 的设置中添加 MCP 服务器：

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
  }
}
```

### 其他 MCP 客户端

对于支持 MCP 的其他客户端，你可以：

1. **HTTP 模式**：访问 `http://localhost:8080/mcp`
2. **Stdio 模式**：直接运行 `uv run python main.py --mode stdio`

## 📋 API 端点

除了 MCP 协议，服务还提供以下 HTTP 端点：

### GET /health
健康检查端点。

**响应：**
```json
{
  "status": "healthy",
  "service": "SQLBot MCP Adapter",
  "version": "1.0.0"
}
```

### GET /get_database_list
直接获取数据源列表（通过 HTTP API）。

### MCP 协议端点
- `GET /mcp` - MCP 服务器信息
- `POST /mcp/call/{tool_name}` - 调用 MCP 工具

## 🐳 Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 复制项目文件
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["uv", "run", "python", "main.py"]
```

构建和运行：

```bash
docker build -t sqlbot-mcp-adapter .
docker run -p 8080:8080 --env-file .env sqlbot-mcp-adapter
```

## ⚙️ 配置选项

### 环境变量

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `SQLBOT_BASE_URL` | SQLBot API 基础URL | `http://localhost:8000` | ✅ |
| `SQLBOT_USERNAME` | SQLBot 用户名 | - | ✅ |
| `SQLBOT_PASSWORD` | SQLBot 密码 | - | ✅ |
| `HOST` | HTTP服务器主机地址 | `0.0.0.0` | ❌ |
| `PORT` | HTTP服务器端口 | `8080` | ❌ |
| `LOG_LEVEL` | 日志级别 (DEBUG/INFO/WARNING/ERROR) | `INFO` | ❌ |

### 命令行参数

```bash
python main.py --help
```

## 📊 使用示例

### 对话示例

**用户：** "请使用 sqlbot-adapter 获取可用的数据源列表"

**AI 响应流程：**
1. 调用 `get_token` 工具获取访问令牌
2. 使用令牌调用 `get_database_list` 工具
3. 展示数据源列表

**示例响应：**
```
我已经获取到了可用的数据源：

1. 销售数据 (MySQL数据库)
   - 描述：2024年销售数据台账
   - 状态：正常
   - ID: 1

2. 客户信息 (Excel文件)
   - 描述：客户基本信息台账
   - 状态：正常
   - ID: 2

你想对哪个数据源进行操作？
```

## 🔧 开发指南

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/sqlbot/sqlbot-mcp-adapter.git
cd sqlbot-mcp-adapter

# 设置开发环境
uv sync --dev

# 运行测试
pytest

# 代码格式化
ruff format .
ruff check .

# 启动开发服务器
uv run python main.py
```

### 添加新工具

1. 在 `main.py` 中添加新的 FastAPI 路由
2. 使用 `@app.get()` 或 `@app.post()` 装饰器
3. 确保函数有适当的参数和返回类型
4. 调用 `mcp.setup_server()` 重新注册工具

示例：
```python
@app.get("/my_new_tool", operation_id="my_new_tool")
async def my_new_tool(param1: str, param2: int = 10):
    """
    我的自定义工具
    """
    # 实现逻辑
    return {"result": "success"}
```

## 🔍 故障排除

### 常见问题

1. **连接 SQLBot 失败**
   ```
   错误：Request error: Connection refused
   ```
   - 检查 `SQLBOT_BASE_URL` 是否正确
   - 确认 SQLBot 服务正在运行
   - 检查网络连接

2. **认证失败**
   ```
   错误：Token request failed: Invalid credentials
   ```
   - 验证 `SQLBOT_USERNAME` 和 `SQLBOT_PASSWORD`
   - 检查用户是否有 API 访问权限

3. **端口占用**
   ```
   错误：Address already in use
   ```
   - 修改 `PORT` 环境变量
   - 或停止占用端口的其他服务

### 调试模式

启用详细日志：

```bash
LOG_LEVEL=DEBUG uv run python main.py
```

### 健康检查

```bash
curl http://localhost:8080/health
```

## 📈 性能优化

1. **异步处理**：使用 `httpx.AsyncClient` 进行异步 HTTP 请求
2. **连接池**：HTTP 客户端自动管理连接池
3. **缓存**：令牌在内存中缓存，避免重复认证
4. **日志优化**：合理设置日志级别，避免过多日志影响性能

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🔗 相关链接

- [SQLBot 官网](https://sqlbot.com)
- [Model Context Protocol 规范](https://modelcontextprotocol.io/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [问题反馈](https://github.com/sqlbot/sqlbot-mcp-adapter/issues)

## 🆘 支持

如果遇到问题：

1. 查看 [故障排除](#故障排除) 部分
2. 搜索现有的 [Issues](https://github.com/sqlbot/sqlbot-mcp-adapter/issues)
3. 创建新的 Issue 并提供详细信息

---

🚀 现在你可以将 SQLBot 的强大数据查询能力集成到任何支持 MCP 的 AI 助手中了！