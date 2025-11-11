# SQLBot 开发环境 Docker 指南

这是一套完整的 SQLBot 开发环境 Docker 解决方案，专门为"外网编译，内网开发"的场景设计。

## 📋 文件说明

### 核心文件

| 文件 | 作用 | 使用环境 |
|------|------|----------|
| `Dockerfile` | 开发环境镜像定义（包含完整技术栈） | 外网编译 |
| `build.sh` | 镜像编译脚本 | 外网编译 |
| `run.sh` | 容器运行脚本 | 内网运行 |
| `start-container.sh` | 容器内启动脚本 | 容器内 |
| `Dockerfile.test` | 简化版测试镜像（仅用于快速验证） | 测试用 |
| `build-test.sh` | 快速测试构建脚本 | 测试用 |

## 🚀 快速开始

### 外网环境（编译镜像）

```bash
# 1. 编译开发镜像
./build.sh sqlbot-debug:latest 22

# 2. 导出镜像用于传输
docker save sqlbot-debug:latest > sqlbot-debug.tar
# 或压缩版本
docker save sqlbot-debug:latest | gzip > sqlbot-debug.tar.gz
```

### 内网环境（使用镜像）

```bash
# 1. 导入镜像
docker load < sqlbot-debug.tar
# 或压缩版本
gunzip -c sqlbot-debug.tar.gz | docker load

# 2. 运行容器
./run.sh 2222 false 5678
```

## 📖 详细使用说明

### 编译脚本 (build.sh)

```bash
./build.sh [image_name] [ssh_port]
```

**参数说明：**
- `image_name`: 镜像名称（默认: `sqlbot-debug:latest`）
- `ssh_port`: 容器内SSH端口（默认: `22`）

**示例：**
```bash
./build.sh my-sqlbot:dev 2222
```

**输出：**
- 编译完成的 Docker 镜像
- 导出镜像的命令提示
- 内网使用流程指导

### 运行脚本 (run.sh)

```bash
./run.sh [host_ssh_port] [debug_mode] [host_debug_port] [image_name] [mount_code]
```

**参数说明：**
- `host_ssh_port`: 宿主机SSH端口（默认: `2222`）
- `debug_mode`: 调试模式（`true/false`，默认: `false`）
- `host_debug_port`: 宿主机调试端口（默认: `5678`）
- `image_name`: 镜像名称（默认: `sqlbot-debug:latest`）
- `mount_code`: 是否挂载代码（`true/false`，默认: `false`）

**常用示例：**

```bash
# 正常运行
./run.sh 2222 false 5678

# 调试模式
./run.sh 2222 true 5678

# 自定义镜像
./run.sh 2222 false 5678 my-sqlbot:dev

# 代码挂载模式（开发时推荐）
./run.sh 2222 true 5678 sqlbot-debug:latest true
```

### 容器启动脚本 (start-container.sh)

容器内的启动脚本，根据环境变量决定启动模式：

- **正常模式**: 运行原始的 `start.sh`
- **调试模式**: 使用 debugpy 启动 Python 应用，等待调试器连接

## 🔧 镜像功能特性

### 技术栈
- **Python**: 完整的 Python 环境，包含 uv 包管理器
- **Node.js**: 前端构建环境
- **PostgreSQL**: 数据库服务
- **SSH**: 远程访问支持
- **debugpy**: Python 远程调试

### 用户账户
- **用户名**: `sqlbot`
- **密码**: `sqlbot`
- **权限**: sudo 免密码

### 端口映射
| 容器端口 | 宿主机端口 | 说明 |
|----------|------------|------|
| 22 | 自定义 | SSH 服务 |
| 3000 | 3000 | 前端服务 |
| 8000 | 8000 | 后端API |
| 5678 | 自定义 | Python 调试端口 |

## 🌐 网络访问

### SSH 访问
```bash
ssh sqlbot@127.0.0.1 -p 2222
# 密码: sqlbot
```

### 应用访问
- **前端**: http://localhost:3000
- **后端API**: http://localhost:8000
- **PostgreSQL**: localhost:5432

### 调试连接
- **调试端口**: 127.0.0.1:5678（debugpy）
- **IDE配置**: 使用 PyCharm 的 "Attach to Process" 功能

## 📁 目录结构

### 容器内主要目录
```
/opt/sqlbot/
├── app/              # Python 应用代码
├── frontend/         # 前端构建文件
├── g2-ssr/          # G2 SSR 服务
└── models/          # 模型文件
```

### 项目结构
```
SQLBot/
├── build/
│   └── dev/         # 开发环境文件
│       ├── Dockerfile
│       ├── build.sh
│       ├── run.sh
│       ├── start-container.sh
│       └── DEVELOPMENT_GUIDE.md
├── backend/         # 后端代码
├── frontend/        # 前端代码
├── g2-ssr/         # SSR 服务代码
└── start.sh        # 原始启动脚本
```

## 🔧 开发模式

### 代码挂载模式
使用 `mount_code=true` 参数可以将宿主机代码挂载到容器：

```bash
./run.sh 2222 true 5678 sqlbot-debug:latest true
```

**挂载映射：**
- `./backend` -> `/opt/sqlbot/app`
- `./frontend` -> `/tmp/frontend`
- `./g2-ssr` -> `/opt/sqlbot/g2-ssr`

**优势：**
- 在宿主机编辑代码
- 容器内实时同步
- 无需重新构建镜像

### 调试模式
使用 `debug_mode=true` 参数启用调试：

```bash
./run.sh 2222 true 5678
```

**调试流程：**
1. 容器启动后，debugpy 监听指定端口
2. 在 PyCharm 中配置 Remote Debugger
3. 连接到 127.0.0.1:5678
4. 设置断点开始调试

## 🚨 故障排除

### 镜像不存在
```bash
错误: 镜像 sqlbot-debug:latest 不存在!
```
**解决方案：**
```bash
docker load < sqlbot-debug.tar
```

### SSH 连接失败
- 检查端口映射是否正确
- 确认容器正在运行
- 使用 `docker ps` 查看容器状态

### 调试器连接失败
- 确认调试模式已启用（`debug_mode=true`）
- 检查端口映射
- 确认 IDE 配置正确

### 容器启动失败
```bash
docker logs sqlbot-debug
```
查看容器日志进行诊断。

## 📦 镜像管理

### 导出镜像
```bash
# 未压缩
docker save sqlbot-debug:latest > sqlbot-debug.tar

# 压缩
docker save sqlbot-debug:latest | gzip > sqlbot-debug.tar.gz
```

### 导入镜像
```bash
# 未压缩
docker load < sqlbot-debug.tar

# 压缩
gunzip -c sqlbot-debug.tar.gz | docker load
```

### 镜像大小优化
如果镜像过大，可以使用多阶段构建或清理不必要的层。

## 🔄 完整工作流程

### 外网 → 内网 流程

1. **外网编译**
   ```bash
   ./build.sh
   docker save sqlbot-debug:latest > sqlbot-debug.tar
   ```

2. **传输到内网**
   ```bash
   scp sqlbot-debug.tar user@internal-host:/path/
   ```

3. **内网运行**
   ```bash
   docker load < sqlbot-debug.tar
   ./run.sh 2222 true 5678 sqlbot-debug:latest true
   ```

4. **开始开发**
   - SSH 连接容器
   - IDE 连接调试器
   - 在宿主机编辑代码
   - 浏览器访问应用

## 💡 最佳实践

1. **开发时启用代码挂载**：避免频繁重建镜像
2. **调试时先启动容器**：等待服务完全启动再连接调试器
3. **定期保存镜像**：开发进度较大时重新构建和导出镜像
4. **内网环境优化**：根据实际网络情况调整超时参数

## 🆘 支持与反馈

如果遇到问题，请检查：
1. Docker 版本兼容性
2. 网络连接状态
3. 端口占用情况
4. 镜像完整性

---

**注意**: 此方案专为内网开发环境设计，确保在部署前测试所有功能正常。