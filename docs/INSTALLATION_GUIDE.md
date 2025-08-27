# SQLBot 安装指南

## 📋 目录

- [系统要求](#系统要求)
- [快速安装](#快速安装)
- [Docker 安装](#docker-安装)
- [源码安装](#源码安装)
- [配置说明](#配置说明)
- [验证安装](#验证安装)

## 🖥️ 系统要求

### 最低配置
- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+), macOS 10.15+, Windows 10+
- **CPU**: 2 核心
- **内存**: 4GB RAM
- **磁盘**: 10GB 可用空间
- **网络**: 支持 HTTP/HTTPS 访问

### 推荐配置
- **操作系统**: Linux (Ubuntu 22.04+, CentOS 8+)
- **CPU**: 4+ 核心
- **内存**: 8GB+ RAM
- **磁盘**: 50GB+ SSD
- **网络**: 稳定的网络连接

### 依赖软件
- **Python**: 3.11+
- **Node.js**: 18+
- **PostgreSQL**: 12+
- **Docker**: 20.10+ (可选)

## 🚀 快速安装

### 方式一：Docker 安装（推荐）

```bash
# 拉取官方镜像
docker pull dataease/sqlbot:v1.0.1

# 运行容器
docker run -d \
  --name sqlbot \
  -p 8000:8000 \
  -p 8001:8001 \
  -p 3000:3000 \
  -e POSTGRES_SERVER=your-db-host \
  -e POSTGRES_PASSWORD=your-password \
  dataease/sqlbot:v1.0.1
```

### 方式二：一键安装脚本

```bash
# 下载安装脚本
curl -fsSL https://raw.githubusercontent.com/dataease/SQLBot/main/installer/install.sh | bash

# 或使用 wget
wget -O - https://raw.githubusercontent.com/dataease/SQLBot/main/installer/install.sh | bash
```

## 🐳 Docker 安装

### 使用 docker-compose（推荐）

```bash
# 1. 下载 docker-compose 文件
wget https://raw.githubusercontent.com/dataease/SQLBot/main/docker-compose.yaml

# 2. 启动服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f
```

### 自定义配置

```yaml
# docker-compose.yaml
version: '3.8'
services:
  sqlbot:
    image: dataease/sqlbot:v1.0.1
    ports:
      - "8000:8000"  # 后端 API
      - "8001:8001"  # MCP 服务
      - "3000:3000"  # 图表服务
    environment:
      - POSTGRES_SERVER=postgres
      - POSTGRES_PASSWORD=your-password
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/opt/sqlbot/data
      - ./logs:/opt/sqlbot/logs
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: pgvector/pgvector:pg17
    environment:
      - POSTGRES_DB=sqlbot
      - POSTGRES_USER=sqlbot
      - POSTGRES_PASSWORD=your-password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

## 🔨 源码安装

### 1. 克隆项目

```bash
git clone https://github.com/dataease/SQLBot.git
cd SQLBot
```

### 2. 快速构建安装

```bash
# 使用快速构建脚本
chmod +x quick_build.sh
./quick_build.sh

# 启动服务
./start.sh
```

### 3. 手动安装

```bash
# 安装后端
cd backend
uv venv && uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# 安装前端
cd frontend
npm install && npm run build

# 安装图表服务
cd g2-ssr
npm install && npm start
```

## ⚙️ 配置说明

### 环境变量配置

#### 后端配置 (`backend/.env`)

```bash
# 数据库配置
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=sqlbot
POSTGRES_PASSWORD=your-password
POSTGRES_DB=sqlbot

# 应用配置
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 前端配置
FRONTEND_HOST=http://localhost:8000
BACKEND_CORS_ORIGINS=http://localhost:8000,http://localhost:3000

# 日志配置
LOG_LEVEL=INFO
SQL_DEBUG=false

# 文件路径
UPLOAD_DIR=/opt/sqlbot/data/uploads
MCP_IMAGE_PATH=/opt/sqlbot/data/mcp
EXCEL_PATH=/opt/sqlbot/data/excel
```

#### 前端配置 (`frontend/.env.production`)

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=SQLBot
VITE_DEBUG=false
```

### 数据库配置

```bash
# 创建数据库
sudo -u postgres createdb sqlbot

# 创建用户
sudo -u postgres createuser sqlbot

# 设置密码
sudo -u postgres psql -c "ALTER USER sqlbot PASSWORD 'your-password';"

# 授权
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sqlbot TO sqlbot;"
```

## ✅ 验证安装

### 1. 检查服务状态

```bash
# 检查后端服务
curl http://localhost:8000/health

# 检查 MCP 服务
curl http://localhost:8001/health

# 检查图表服务
curl http://localhost:3000/health
```

### 2. 访问 Web 界面

- **前端界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **默认账号**: admin
- **默认密码**: SQLBot@123456

### 3. 功能测试

```bash
# 测试数据库连接
curl -X POST http://localhost:8000/api/v1/datasource/test \
  -H "Content-Type: application/json" \
  -d '{"type": "postgresql", "host": "localhost", "port": 5432}'

# 测试 AI 模型
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello SQLBot!"}'
```

## 🚨 安装问题排查

### 常见问题

#### 1. 端口冲突
```bash
# 检查端口占用
lsof -i :8000
lsof -i :8001
lsof -i :3000

# 杀死占用进程
sudo kill -9 <PID>
```

#### 2. 权限问题
```bash
# 修复权限
sudo chown -R $USER:$USER /opt/sqlbot
chmod +x /opt/sqlbot/start.sh
```

#### 3. 依赖问题
```bash
# 重新安装后端依赖
cd backend && uv sync

# 重新安装前端依赖
cd frontend && npm install
```

### 获取帮助

- **GitHub Issues**: [提交问题](https://github.com/dataease/SQLBot/issues)
- **技术交流群**: 扫描二维码加入
- **文档中心**: [在线文档](https://docs.sqlbot.com)

---

安装完成后，请参考 [用户指南](./USER_GUIDE.md) 开始使用 SQLBot。
