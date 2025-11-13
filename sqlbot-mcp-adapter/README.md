# SQLBot MCP Adapter

轻量级的 SQLBot MCP 适配器，将 SQLBot 服务与 Claude 的 Model Context Protocol (MCP) 集成。

## 快速开始

### 先决条件

- Python 3.11+
- uv (推荐)

### 配置

1. 复制环境变量文件:
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置 SQLBot 凭据
   ```

### 运行

```bash
# 启动服务
uv run python main.py
```

## 核心功能

### 工具列表

#### get_token
- **描述**: 获取 SQLBot 访问令牌
- **参数**: `create_chat` (boolean, 是否创建聊天会话)
- **返回**: 令牌信息对象

#### get_database_list  
- **描述**: 获取数据源列表
- **参数**: 无 (通过 X-Sqlbot-Token 头传递认证)
- **返回**: 数据源列表

## 配置

### 环境变量

| 变量 | 描述 | 默认 |
|------|------|------|
| `SQLBOT_BASE_URL` | SQLBot API 基础 URL | `http://localhost:8000` |
| `SQLBOT_USERNAME` | SQLBot 用户名 | - |
| `SQLBOT_PASSWORD` | SQLBot 密码 | - |

### 示例 .env

```env
# SQLBot API 配置
SQLBOT_BASE_URL=http://localhost:8000
SQLBOT_USERNAME=your_username
SQLBOT_PASSWORD=your_password
```

## 🚀 快速开始

### 1. 环境配置

```bash
# 进入项目目录
cd sqlbot-mcp-adapter

# 复制环境变量模板
cp .env.example .env

# 编辑配置（设置你的 SQLBot 信息）
nano .env
```

在 `.env` 文件中设置：

```env
SQLBOT_BASE_URL=http://your-sqlbot-server:8000
SQLBOT_USERNAME=your_username
SQLBOT_PASSWORD=your_password
```

### 2. 启动服务

#### 使用一键启动脚本（推荐）

```bash
# 安装依赖并启动 HTTP 模式
./start.sh

# 或者分步执行
./start.sh install  # 安装依赖
./start.sh check    # 检查配置
./start.sh http     # 启动HTTP模式
```

#### 手动启动

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动 HTTP 模式
python -m sqlbot_mcp_adapter.main --mode http --host 0.0.0.0 --port 8080

# 或启动 Stdio 模式
python -m sqlbot_mcp_adapter.main --mode stdio
```

### 3. Qwen Code 集成配置

在 Qwen Code 的 `settings.json` 中添加：

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

## 💡 使用示例

集成到 Qwen Code 后，你可以这样使用：

```
请使用 sqlbot-adapter 的 get_token 工具获取访问令牌，设置 create_chat 为 true

请使用 sqlbot-adapter 的 get_database_list 工具获取所有可用的数据源
```

## 📋 API 详细说明

### 1. 获取访问令牌

**工具名称**: `get_token`

**参数**:
- `create_chat` (boolean, 可选): 是否创建chatId，默认为 true

**响应示例**:
```json
{
  "access_token": "bearer eyJhbGciOiJIUzI1NiIsInR5cCXE-sr0",
  "token_type": "bearer",
  "expire": "2025-11-21 11:45:44",
  "chat_id": null
}
```

### 2. 获取数据源列表

**工具名称**: `get_database_list`

**参数**: 无

**响应示例**:
```json
{
  "databases": [
    {
      "id": 1,
      "name": "人员台账",
      "description": "人员台账",
      "type": "excel",
      "type_name": "Excel/CSV",
      "create_time": "2025-11-13T20:03:06.233119",
      "create_by": 1,
      "status": "Success",
      "num": "1/3",
      "oid": 1
    }
  ],
  "count": 1
}
```

## 🔧 技术特性

### 📦 依赖管理

- **FastAPI** - HTTP 服务器框架
- **httpx** - 异步 HTTP 客户端
- **Pydantic** - 数据验证和序列化
- **python-dotenv** - 环境变量管理
- **mcp** - MCP SDK

### 🛡️ 安全特性

- ✅ 敏感信息环境变量化
- ✅ 令牌安全存储和自动刷新
- ✅ 输入验证和错误处理
- ✅ 详细的日志记录

### 📊 监控和调试

- ✅ 健康检查端点 `/health`
- ✅ 可配置日志级别
- ✅ 详细的错误信息
- ✅ HTTP 模式便于调试

## 🎯 适用场景

1. **企业数据查询** - 将 SQLBot 数据源能力集成到 AI 助手
2. **自动化报表** - 通过 AI 自动生成数据分析报告
3. **数据科学工作流** - 结合 AI 进行数据探索和分析
4. **开发工具集成** - 在 IDE 中直接访问企业数据库

## 🔧 开发指南

### 本地开发

```bash
# 安装开发依赖
pip install -r requirements.txt
pip install -e .

# 运行测试
pytest

# 代码格式化
black src/

# 类型检查
mypy src/
```

### Docker 部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY .env.example .env

EXPOSE 8080

CMD ["python", "-m", "sqlbot_mcp_adapter.main", "--mode", "http"]
```

## 📝 环境变量

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `SQLBOT_BASE_URL` | SQLBot API 基础URL | `http://localhost:8000` | ✅ |
| `SQLBOT_USERNAME` | SQLBot 用户名 | - | ✅ |
| `SQLBOT_PASSWORD` | SQLBot 密码 | - | ✅ |
| `HOST` | HTTP服务器主机 | `0.0.0.0` | ❌ |
| `PORT` | HTTP服务器端口 | `8080` | ❌ |
| `LOG_LEVEL` | 日志级别 | `INFO` | ❌ |

## 🐛 故障排除

### 常见问题

1. **连接失败**
   - 检查 `SQLBOT_BASE_URL` 是否正确
   - 确认 SQLBot 服务正在运行

2. **认证失败**
   - 验证 `SQLBOT_USERNAME` 和 `SQLBOT_PASSWORD`
   - 检查账号是否有相应权限

3. **令牌过期**
   - 适配器会自动刷新令牌
   - 如果持续失败，检查 SQLBot 服务状态

### 日志查看

```bash
# 查看详细日志
LOG_LEVEL=DEBUG python -m sqlbot_mcp_adapter.main --mode http
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🆘 支持

如有问题，请：
1. 查看 [故障排除](#故障排除) 部分
2. 搜索现有的 [Issues](https://github.com/sqlbot/sqlbot-mcp-adapter/issues)
3. 创建新的 Issue

---

🚀 现在你可以将 SQLBot 的强大功能集成到任何支持 MCP 的 AI 助手中了！