# SQLBot 开发环境调试模式

本文档介绍如何在开发环境中使用不同的调试模式，确保前端进程保持运行而后端进程可以替换，避免 PyCharm 与容器内服务之间的端口冲突。

## 配置说明

以下环境变量控制开发模式行为：

- `START_SERVICES`: 是否自动启动后端服务 (true/false, 默认 true)
- `DEBUG_MODE`: 是否启用调试模式 (true/false, 默认 false)
- `PY_DEBUG_PORT`: Python 调试端口 (默认 5678)

## 开发模式

### 模式1：自动启动服务（适用于非调试场景）
在 `.env` 中设置：
```bash
START_SERVICES=true
DEBUG_MODE=false
```
容器启动时会自动运行所有服务。

### 模式2：PyCharm 远程调试模式（推荐）
在 `.env` 中设置：
```bash
START_SERVICES=false
DEBUG_MODE=true
PY_DEBUG_PORT=5678
```
此模式下容器不会自动启动后端服务，PyCharm 可以完全控制服务启动，避免端口冲突。

### 模式3：手动控制模式
在 `.env` 中设置：
```bash
START_SERVICES=false
DEBUG_MODE=false
```
容器只启动 SSH 服务和 G2-SSR 服务，后端服务需要手动启动。

## PyCharm 调试配置

### 步骤1: 配置环境
1. 复制 `.env.example` 为 `.env`
2. 设置以下参数：
   ```
   START_SERVICES=false
   DEBUG_MODE=true
   PY_DEBUG_PORT=5678
   ```

### 步骤2: 启动容器
```bash
./run.sh .env
```

### 步骤3: 在 PyCharm 中配置远程解释器
1. `File` → `Settings` → `Project` → `Python Interpreter`
2. 点击齿轮图标 → `Add...`
3. 选择 `SSH Interpreter`
4. 配置 SSH 连接：
   - Host: localhost
   - Username: sqlbot
   - Password: sqlbot
   - Interpreter Path: `/opt/sqlbot/app/.venv/bin/python`

### 步骤4: 配置运行/调试配置
1. `Run` → `Edit Configurations`
2. 添加 `Python` 配置：
   - Script path: `/opt/sqlbot/app/main.py`
   - Parameters: `-m uvicorn main:app --host 0.0.0.0 --port 8000`
   - Python interpreter: 选择刚配置的 SSH 解释器
   - Working directory: `/opt/sqlbot/app`

### 步骤5: 使用 debugpy 调试
在 PyCharm 中：
1. 在代码中设置断点
2. 运行或调试配置
3. PyCharm 会启动服务并连接到调试器

## 处理端口冲突

当遇到 PyCharm 与容器内服务端口冲突时：

### 方法1：使用 START_SERVICES=false（推荐）
将 `START_SERVICES` 设置为 `false`，让 PyCharm 完全控制服务启动。

### 方法2：手动停止再启动
1. SSH 到容器：
   ```bash
   ssh sqlbot@localhost -p [SSH_PORT]  # 密码: sqlbot
   ```

2. 停止运行中的服务：
   ```bash
   pkill -f "uvicorn.*main:app"
   ```

3. 手动启动调试服务：
   ```bash
   cd /opt/sqlbot/app
   python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## 保持前端服务稳定

在所有开发模式中，以下服务都会保持稳定运行：

- **G2-SSR 服务**：通过 PM2 管理，提供图表渲染服务
- **SSH 服务**：支持远程连接
- **前端资源**：通过后端服务提供（需要后端服务运行）

## 故障排除

### 1. 端口冲突错误
- 确认 `START_SERVICES=false` 以避免自动启动冲突
- 检查是否有其他进程占用 8000 端口

### 2. PyCharm 无法连接调试
- 检查 `DEBUG_MODE=true` 和 `PY_DEBUG_PORT` 设置
- 确认端口映射正确

### 3. 数据库连接失败
- 确认 `.env` 中的数据库连接参数是否正确
- 检查数据库服务是否运行且可访问

### 4. 前端页面加载失败
- 确认后端服务（处理 8000 端口请求的 uvicorn）正在运行
- 检查容器日志确认后端服务状态