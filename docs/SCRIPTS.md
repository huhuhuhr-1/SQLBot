# SQLBot 脚本使用说明

## 📋 脚本概览

SQLBot 项目包含以下脚本文件：

| 脚本 | 描述 | 用途 |
|------|------|------|
| `quick_build.sh` | 主要构建脚本 | 构建所有组件和 Docker 镜像 |
| `start.sh` | 服务启动脚本 | 启动生产环境服务 |
| `Makefile` | 构建工具 | 提供便捷的 make 命令 |

## 🚀 快速开始

### 1. 构建项目

```bash
# 基本构建
./quick_build.sh

# 构建并创建 Docker 镜像
./quick_build.sh -d

# 清理后构建
./quick_build.sh -c
```

### 2. 使用 Makefile

```bash
# 查看所有命令
make help

# 构建项目
make build

# 启动开发环境
make dev

# 运行测试
make test

# 清理构建
make clean
```

### 3. 启动服务

```bash
# 启动生产环境
./start.sh

# 或使用 docker-compose
docker-compose up -d
```

## 📦 脚本详解

### quick_build.sh

主要的构建脚本，支持以下功能：

#### 命令行选项

| 选项 | 描述 | 示例 |
|------|------|------|
| `-d, --docker` | 自动构建 Docker 镜像 | `./quick_build.sh -d` |
| `-c, --clean` | 清理之前的构建 | `./quick_build.sh -c` |
| `-v, --verbose` | 详细输出 | `./quick_build.sh -v` |
| `-h, --help` | 显示帮助信息 | `./quick_build.sh -h` |

#### 构建流程

1. **检查环境**: 验证 Python、Node.js、npm 等工具
2. **构建后端**: 使用 uv 或 pip 构建 Python wheel 包
3. **构建前端**: 使用 npm 构建静态资源
4. **安装 g2-ssr**: 安装图表渲染服务依赖
5. **构建 Docker**: 可选，构建 Docker 镜像

#### 构建产物

- `backend/dist/` - Python wheel 包
- `frontend/dist/` - 静态资源文件
- `g2-ssr/` - 图表渲染服务

### Makefile

提供便捷的 make 命令：

#### 常用命令

| 命令 | 描述 | 用途 |
|------|------|------|
| `make help` | 显示帮助 | 查看所有可用命令 |
| `make build` | 构建项目 | 构建所有组件 |
| `make dev` | 启动开发环境 | 启动所有开发服务 |
| `make test` | 运行测试 | 执行后端测试 |
| `make clean` | 清理构建 | 删除构建产物 |
| `make install` | 安装依赖 | 安装所有依赖 |
| `make start` | 启动服务 | 启动生产服务 |
| `make stop` | 停止服务 | 停止所有服务 |
| `make status` | 查看状态 | 显示服务运行状态 |
| `make logs` | 查看日志 | 显示 Docker 日志 |

#### 开发环境

```bash
# 启动完整的开发环境
make dev

# 这会启动：
# 1. PostgreSQL 数据库 (Docker)
# 2. 后端服务 (uvicorn)
# 3. 前端服务 (Vite)
# 4. g2-ssr 服务 (Node.js)
```

### start.sh

生产环境启动脚本，支持多种环境：

```bash
#!/bin/bash

# SQLBot Production Startup Script
# 支持生产环境、本地包构建和开发环境

# 自动检测环境并设置路径
if [[ -d "/opt/sqlbot" ]]; then
    # 生产环境
    BASE_DIR="/opt/sqlbot"
    SSR_PATH="$BASE_DIR/g2-ssr"
    APP_PATH="$BASE_DIR/app"
elif [[ -d "package/opt/sqlbot" ]]; then
    # 本地包构建
    BASE_DIR="package/opt/sqlbot"
    SSR_PATH="$BASE_DIR/g2-ssr"
    APP_PATH="$BASE_DIR/app"
else
    # 开发环境
    BASE_DIR="."
    SSR_PATH="g2-ssr"
    APP_PATH="backend"
fi

# 启动所有服务
# 1. g2-ssr 图表渲染服务 (端口 3000)
# 2. MCP 服务 (端口 8001)
# 3. 主应用服务 (端口 8000)
```

## 🔧 高级用法

### 自定义构建

```bash
# 只构建后端
make backend

# 只构建前端
make frontend

# 只安装 g2-ssr
make g2-ssr
```

### 开发工作流

```bash
# 1. 安装依赖
make install

# 2. 启动开发环境
make dev

# 3. 运行测试
make test

# 4. 构建项目
make build

# 5. 清理
make clean
```

### 生产部署工作流

```bash
# 1. 构建项目
make build

# 2. 部署到生产环境
make deploy

# 3. 复制到服务器
sudo cp -r package/opt/sqlbot /opt/

# 4. 启动服务
cd /opt/sqlbot && ./start.sh
```

### 服务管理

```bash
# 查看服务状态
make status

# 查看日志
make logs

# 停止所有服务
make stop
```

## 🚨 常见问题

### 权限问题

```bash
# 给脚本添加执行权限
chmod +x quick_build.sh
chmod +x start.sh
```

### 依赖问题

```bash
# 安装 uv (推荐)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 端口冲突

```bash
# 检查端口占用
lsof -i :8000  # 后端
lsof -i :5173  # 前端
lsof -i :3000  # g2-ssr

# 停止服务
make stop
```

## 📚 相关文档

- [构建指南](BUILD_GUIDE.md) - 详细的构建说明
- [调试指南](DEBUG_GUIDE.md) - 开发调试指南
- [README.md](../README.md) - 项目概述

---

如有问题，请查看相应文档或联系项目维护者。
