# SQLBot 开发环境

此目录包含用于在开发模式下构建和运行 SQLBot 的文件。

## 快速开始

### 1. 构建开发镜像
```bash
./build.sh [镜像名] [SSH端口]
```

### 2. 配置开发环境
复制示例配置文件并按需修改：
```bash
cp .env.example .env
# 编辑 .env 文件以匹配您的环境配置
```

### 3. 启动开发环境
```bash
./run.sh [.env文件路径，默认为.env]
```

## 配置说明

`.env` 文件包含以下配置项：

- `SSH_PORT`: 容器内 SSH 端口 (默认 22)
- `HOST_SSH_PORT`: 宿主机 SSH 端口映射 (默认 2222)
- `HOST_BACKEND_PORT`: 后端 API 端口映射 (默认 8000)
- `HOST_FRONTEND_PORT`: 前端端口映射 (默认 3000)
- `HOST_MCP_PORT`: MCP 服务端口映射 (默认 8001)
- `DEBUG_MODE`: 是否启用调试模式 (true/false, 默认 false)
- `PY_DEBUG_PORT`: Python 调试端口 (默认 5678)
- `HOST_DEBUG_PORT`: 宿主机调试端口映射 (默认 5678)
- `POSTGRES_SERVER`: 数据库服务器地址
- `POSTGRES_PORT`: 数据库端口 (默认 5432)
- `POSTGRES_USER`: 数据库用户名
- `POSTGRES_PASSWORD`: 数据库密码
- `POSTGRES_DB`: 数据库名称
- `MOUNT_CODE`: 是否挂载本地代码 (true/false, 默认 false)

## 调试模式

启用调试模式后，您可以：

1. 通过 SSH 连接到容器进行开发
2. 使用 debugpy 进行远程 Python 调试
3. 在不重启容器的情况下替换后端进程

### SSH 连接
```bash
ssh sqlbot@localhost -p [HOST_SSH_PORT]  # 密码: sqlbot
```

### Python 调试
在您的 IDE (如 PyCharm 或 VSCode) 中配置远程调试，连接到:
- 主机: localhost
- 端口: [HOST_DEBUG_PORT]