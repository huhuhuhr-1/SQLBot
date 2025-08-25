# SQLBot

<div align="center">

![SQLBot Logo](https://github.com/dataease/SQLBot/assets/2594ff29-5426-4457-b051-279855610030)

**基于大模型与 RAG 的智能问数系统**

[![GitHub stars](https://img.shields.io/github/stars/dataease/sqlbot)](https://github.com/dataease/sqlbot/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/dataease/sqlbot)](https://github.com/dataease/sqlbot/network)
[![GitHub issues](https://img.shields.io/github/issues/dataease/sqlbot)](https://github.com/dataease/sqlbot/issues)
[![GitHub license](https://img.shields.io/github/license/dataease/sqlbot)](https://github.com/dataease/sqlbot/blob/main/LICENSE)

[English](./README.md) | 简体中文

</div>

## ✨ 特性

- **🤖 智能问答**: 基于大语言模型的自然语言查询，支持复杂业务场景
- **📊 图表生成**: 自动生成多种类型的可视化图表（柱状图、折线图、饼图等）
- **🔍 数据探索**: 支持多数据源连接，提供灵活的数据查询能力
- **🎨 美观界面**: 现代化的 Web 界面，提供良好的用户体验
- **🔒 安全可控**: 基于工作空间的资源隔离机制，实现细粒度的数据权限控制

## 📋 目录

- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [构建部署](#构建部署)
- [调试指南](#调试指南)
- [常见问题](#常见问题)

## 🚀 快速开始

### Docker 部署（推荐）

```bash
# 拉取镜像
docker pull dataease/sqlbot:v1.0.0

# 运行容器
docker run -d \
  --name sqlbot \
  -p 8000:8000 \
  -p 8001:8001 \
  -p 3000:3000 \
  -e POSTGRES_SERVER=your-db-host \
  -e POSTGRES_PASSWORD=your-password \
  dataease/sqlbot:v1.0.0
```

### 本地构建

```bash
# 克隆项目
git clone https://github.com/dataease/SQLBot.git
cd SQLBot

# 快速构建
chmod +x quick_build.sh
./quick_build.sh

# 启动服务
./start.sh
```

### 访问系统

- **前端界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **默认账号**: admin
- **默认密码**: SQLBot@123456

## 🏗️ 项目结构

SQLBot 是一个基于大模型与 RAG 的问数系统，采用微服务架构：

```
SQLBot/
├── backend/           # FastAPI 后端服务 (Python)
├── frontend/          # Vue 3 + Vite 前端界面
├── g2-ssr/           # 图表渲染服务 (Node.js)
├── installer/        # 安装脚本及模板
├── quick_build.sh    # 快速构建脚本
├── Makefile          # 构建工具
├── docker-compose.yaml   # Docker 编排文件
└── Dockerfile        # Docker 镜像构建文件
```

### 技术栈

- **后端**: FastAPI + SQLModel + Alembic + PostgreSQL
- **前端**: Vue 3 + TypeScript + Vite + Element Plus
- **图表**: @antv/g2 + @antv/g2-ssr (服务端渲染)
- **包管理**: uv (Python) + npm (Node.js)
- **容器化**: Docker + Docker Compose

### 服务说明

- **Backend (8000)**: 主要的 API 服务，处理业务逻辑和数据查询
- **MCP (8001)**: Model Context Protocol 服务，用于 AI 模型集成
- **g2-ssr (3000)**: 图表服务端渲染服务，将数据转换为图片格式

### 服务说明

- **Backend (8000)**: 主要的 API 服务，处理业务逻辑和数据查询
- **MCP (8001)**: Model Context Protocol 服务，用于 AI 模型集成
- **g2-ssr (3000)**: 图表服务端渲染服务，将数据转换为图片格式

## 💻 开发指南

### 环境准备

- **Python 3.11+** + **Node.js 18+** + **PostgreSQL**
- **推荐工具**: uv, PyCharm, WebStorm, Docker

### 本地开发启动

```bash
# 1. 启动数据库
docker-compose up -d sqlbot-db

# 2. 启动后端服务
cd backend
uv venv && uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. 启动前端服务
cd frontend
npm install && npm run dev

# 4. 启动图表服务 (可选)
cd g2-ssr
npm install && npm start
```

### 环境配置

#### 后端 (`backend/.env`)
```bash
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=sqlbot
POSTGRES_PASSWORD=sqlbot
POSTGRES_DB=sqlbot
FRONTEND_HOST=http://localhost:5173
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=DEBUG
SQL_DEBUG=true
```

#### 前端 (`frontend/.env.development`)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=SQLBot Dev
VITE_DEBUG=true
```

## 🔨 构建部署

### 快速构建

```bash
# 使用快速构建脚本
chmod +x quick_build.sh
./quick_build.sh

# 使用 Makefile
make build
```

### 构建选项

| 选项 | 描述 | 示例 |
|------|------|------|
| `-d, --docker` | 自动构建 Docker 镜像 | `./quick_build.sh -d` |
| `-c, --clean` | 清理后构建 | `./quick_build.sh -c` |
| `-h, --help` | 显示帮助信息 | `./quick_build.sh -h` |

### 部署方式

```bash
# Docker 部署
docker build -t sqlbot:latest .
docker run -p 8000:8000 sqlbot:latest

# 本地构建部署
./quick_build.sh
sudo cp -r package/opt/sqlbot /opt/
cd /opt/sqlbot && ./start.sh

# 开发环境运行
./start.sh
```

## 🐛 调试指南

### IDE 调试配置

#### 后端调试 (PyCharm)
```json
{
  "name": "SQLBot Backend Debug",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": ["main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
  "cwd": "${workspaceFolder}/backend",
  "python": "${workspaceFolder}/backend/.venv/bin/python"
}
```

#### 前端调试 (WebStorm)
```json
{
  "name": "Frontend Chrome Debug",
  "type": "chrome",
  "request": "launch",
  "url": "http://localhost:5173",
  "webRoot": "${workspaceFolder}/frontend/src"
}
```

### 调试工具

- **PyCharm**: 后端 Python 代码调试
- **WebStorm**: 前端 JavaScript/TypeScript 调试
- **Chrome DevTools**: 浏览器调试
- **Vue DevTools**: Vue 组件调试

详细调试指南请参考：[调试指南](./docs/DEBUG_GUIDE.md)

## ❓ 常见问题

### 构建问题

**Q: 构建失败怎么办？**
A: 检查控制台输出，确保所有依赖工具已安装：
- Python 3.11+ + Node.js 18+ + uv (推荐)

**Q: 端口冲突怎么办？**
A: 检查端口占用并杀死进程：
```bash
lsof -i :8000  # 后端端口
lsof -i :5173  # 前端端口
kill -9 <PID>
```

### 运行问题

**Q: 数据库连接失败？**
A: 确保 PostgreSQL 服务正在运行：
```bash
docker-compose up -d sqlbot-db
```

**Q: 前端无法访问后端 API？**
A: 检查 CORS 配置和环境变量：
- 确保 `VITE_API_BASE_URL` 正确设置
- 检查 `BACKEND_CORS_ORIGINS` 包含前端地址

### 开发问题

**Q: 如何添加新的依赖？**
A: 
- 后端: `uv add <package>`
- 前端: `npm install <package>`

**Q: 如何运行测试？**
A: 
- 后端: `uv run pytest`
- 前端: `npm run test`

## 📞 联系我们

如你有更多问题，可以加入我们的技术交流群与我们交流。

<img width="180" height="180" alt="contact_me_qr" src="https://github.com/user-attachments/assets/2594ff29-5426-4457-b051-279855610030" />

## 🖼️ UI 展示

<img alt="q&a" src="https://github.com/user-attachments/assets/55526514-52f3-4cfe-98ec-08a986259280" />

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dataease/sqlbot&type=Date)](https://www.star-history.com/#dataease/sqlbot&Date)

## 🌟 飞致云旗下的其他明星项目

- [DataEase](https://github.com/dataease/dataease/) - 人人可用的开源 BI 工具
- [MeterSphere](https://github.com/metersphere/metersphere/) - 新一代的开源持续测试工具

## 📄 License

本仓库遵循 [FIT2CLOUD Open Source License](LICENSE) 开源协议，该许可证本质上是 GPLv3，但有一些额外的限制。
