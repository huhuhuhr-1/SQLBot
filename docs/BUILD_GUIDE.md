# SQLBot 构建指南

## 📋 目录

- [快速开始](#快速开始)
- [构建脚本](#构建脚本)
- [构建选项](#构建选项)
- [构建产物](#构建产物)
- [部署方式](#部署方式)
- [常见问题](#常见问题)

## 🚀 快速开始

### 环境准备

#### 必需工具
- **Python 3.11+**
- **Node.js 18+**
- **npm**
- **Git** (用于版本检测)

#### 可选工具
- **uv** (推荐，现代 Python 包管理器)
- **Docker** (容器化)
- **fpm** (RPM 包创建)

### 快速构建

```bash
# 使用快速构建脚本
chmod +x quick_build.sh
./quick_build.sh

# 使用 Makefile
make build
```

### 构建选项

```bash
# 基本构建
./quick_build.sh

# 自动构建 Docker 镜像
./quick_build.sh -d

# 清理后构建
./quick_build.sh -c

# 显示帮助
./quick_build.sh -h
```

## 🔧 构建脚本

### 主要构建脚本

#### `quick_build.sh` (Linux/macOS)
主要的构建脚本，支持快速构建和 Docker 镜像构建。

#### `Makefile`
提供便捷的 make 命令支持，包含开发、测试、部署等常用操作。

### Makefile 支持

```bash
# 查看所有可用命令
make help

# 构建所有组件
make build

# 构建特定组件
make backend
make frontend
make docker

# 清理构建
make clean

# 运行测试
make test
```

## ⚙️ 构建选项

### 命令行选项

| 选项 | 描述 | 示例 |
|------|------|------|
| `-d, --docker` | 自动构建 Docker 镜像 | `-d` |
| `-c, --clean` | 清理之前的构建 | `-c` |
| `-v, --verbose` | 详细输出 | `-v` |
| `-h, --help` | 显示帮助信息 | `-h` |

### 构建类型

- **`all`** (默认): 构建所有组件 (backend, frontend, g2-ssr)
- **`docker`**: 构建 Docker 镜像

### 环境变量

```bash
# 设置日志级别
export BUILD_LOG_LEVEL=DEBUG

# 跳过特定构建步骤
export SKIP_BUILD_STEPS=backend,frontend

# 设置并行任务数
export PARALLEL_JOBS=4
```

## 📁 构建产物

### 构建目录结构

```
SQLBot/
├── backend/
│   └── dist/
│       └── *.whl          # Python wheel 包
├── frontend/
│   └── dist/              # 构建的前端资源
├── g2-ssr/                # 图表渲染服务
├── package/               # 打包暂存目录
│   └── opt/
│       └── sqlbot/
├── *.rpm                  # RPM 包 (如果 fpm 可用)
└── build.log              # 构建日志文件
```

### 构建产物说明

#### 后端产物
- **位置**: `backend/dist/*.whl`
- **内容**: Python wheel 包，包含所有后端代码和依赖
- **用途**: 用于部署或进一步打包

#### 前端产物
- **位置**: `frontend/dist/`
- **内容**: 静态资源文件 (HTML, CSS, JS)
- **用途**: 部署到 Web 服务器

#### g2-ssr 产物
- **位置**: `g2-ssr/`
- **内容**: Node.js 服务源码和依赖
- **用途**: 图表渲染服务

## 🚀 部署方式

### 1. Docker 部署

#### 构建 Docker 镜像
```bash
# 使用构建脚本
./quick_build.sh -d

# 或手动构建
docker build -t sqlbot:latest .

# 构建多架构镜像
docker buildx build --platform linux/amd64,linux/arm64 -t sqlbot:latest .
```

#### 运行 Docker 容器
```bash
# 基本运行
docker run -p 8000:8000 sqlbot:latest

# 使用 docker-compose
docker-compose up -d

# 自定义配置
docker run -p 8000:8000 \
  -e POSTGRES_SERVER=your-db-host \
  -e POSTGRES_PASSWORD=your-password \
  sqlbot:latest
```

### 2. RPM 包部署

#### 构建 RPM 包
```bash
# 使用构建脚本
./quick_build.sh

# 或手动构建
fpm -s dir -t rpm -n sqlbot -v 1.0.1 -C package opt/sqlbot
```

#### 安装 RPM 包
```bash
# 安装 RPM 包
sudo rpm -i sqlbot-*.rpm

# 启动服务
cd /opt/sqlbot
./start.sh
```

### 3. 直接运行

#### 从源码运行
```bash
# 启动所有服务
./start.sh

# 或分别启动
cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev
cd g2-ssr && npm start
```

#### 从构建产物运行
```bash
# 安装后端
cd backend && uv sync && uv run uvicorn main:app

# 部署前端
cp -r frontend/dist/* /var/www/html/

# 启动 g2-ssr
cd g2-ssr && npm start
```

## 🔧 自定义构建

### 配置文件

编辑 `build.config` 来自定义构建设置：

```toml
[build]
type = "all"
clean = true
skip_tests = false
verbose = true

[backend]
build_tool = "uv"
include_dev_deps = false

[frontend]
package_manager = "npm"
optimization = "production"

[packaging]
name = "sqlbot"
description = "SQLBot - AI-powered SQL assistant"
vendor = "SQLBot Team"
license = "MIT"
dependencies = ["python3.11", "nodejs", "npm"]

[docker]
base_image = "python:3.11-slim"
registry = "your-registry.com"
```

### 使用 Makefile

使用 Makefile 进行便捷操作：

```bash
# 查看所有可用命令
make help

# 构建所有组件
make build

# 启动开发环境
make dev

# 运行测试
make test

# 清理构建
make clean
```

### CI/CD 集成

#### GitHub Actions 示例
```yaml
name: Build SQLBot

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
          
             - name: Build
         run: |
           chmod +x quick_build.sh
           ./quick_build.sh
           
       - name: Build Docker
         run: ./quick_build.sh -d
```

## 🚨 常见问题

### 构建失败

#### 1. 权限问题
```bash
# 解决权限问题
chmod +x quick_build.sh
```

#### 2. 依赖工具缺失
```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### 3. 构建错误
- 确保所有依赖工具已正确安装
- 尝试使用 `-c` 标志清理之前的构建
- 检查控制台输出获取详细错误信息

### 部署问题

#### 1. Docker 构建失败
- 检查 Dockerfile 语法
- 确保 Docker 服务正在运行
- 检查网络连接

#### 2. RPM 包创建失败
- 确保已安装 fpm: `gem install fpm`
- 检查打包目录结构
- 验证依赖关系

#### 3. 服务启动失败
- 检查端口占用: `lsof -i :8000`
- 验证环境变量配置
- 检查日志文件

### 性能优化

#### 1. 构建速度优化
- 使用并行构建: `-p` 选项
- 使用 uv 替代 pip
- 启用构建缓存

#### 2. 镜像大小优化
- 使用多阶段构建
- 清理不必要的文件
- 使用 Alpine Linux 基础镜像

## 📚 相关文档

- [调试指南](./DEBUG_GUIDE.md) - 开发调试指南
- [README.md](../README.md) - 项目概述和快速开始
- [Dockerfile](../Dockerfile) - Docker 镜像构建文件
- [docker-compose.yaml](../docker-compose.yaml) - Docker 编排配置

---

如有问题，请查看构建日志或联系项目维护者。
