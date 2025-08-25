# SQLBot 部署指南

## 📋 部署方式概览

SQLBot 支持多种部署方式：

| 部署方式 | 适用场景 | 复杂度 | 推荐度 |
|----------|----------|--------|--------|
| Docker | 快速部署、容器化环境 | 低 | ⭐⭐⭐⭐⭐ |
| 本地构建 | 开发测试、自定义部署 | 中 | ⭐⭐⭐⭐ |
| 生产部署 | 生产环境、服务器部署 | 高 | ⭐⭐⭐ |

## 🐳 Docker 部署（推荐）

### 快速部署

```bash
# 拉取官方镜像
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

### 使用 docker-compose

```bash
# 启动完整环境（包含数据库）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

## 🔨 本地构建部署

### 1. 构建项目

```bash
# 快速构建
./quick_build.sh

# 或使用 Makefile
make build
```

### 2. 部署到生产环境

```bash
# 方法一：使用 Makefile
make deploy

# 方法二：手动部署
sudo cp -r package/opt/sqlbot /opt/
cd /opt/sqlbot
./start.sh
```

## 🚀 生产环境部署

### 环境要求

- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+)
- **Python**: 3.11+
- **Node.js**: 18+
- **PostgreSQL**: 12+
- **内存**: 至少 4GB
- **磁盘**: 至少 10GB 可用空间

### 部署步骤

#### 1. 准备环境

```bash
# 安装依赖
sudo apt update
sudo apt install -y python3.11 python3.11-venv nodejs npm postgresql

# 或 CentOS/RHEL
sudo yum install -y python3.11 nodejs npm postgresql
```

#### 2. 构建项目

```bash
# 克隆项目
git clone https://github.com/dataease/SQLBot.git
cd SQLBot

# 构建项目
./quick_build.sh
```

#### 3. 部署到服务器

```bash
# 创建部署目录
sudo mkdir -p /opt/sqlbot

# 复制构建产物
sudo cp -r package/opt/sqlbot/* /opt/sqlbot/

# 设置权限
sudo chown -R $USER:$USER /opt/sqlbot
chmod +x /opt/sqlbot/start.sh
```

#### 4. 配置数据库

```bash
# 创建数据库
sudo -u postgres createdb sqlbot

# 创建用户
sudo -u postgres createuser sqlbot

# 设置密码
sudo -u postgres psql -c "ALTER USER sqlbot PASSWORD 'sqlbot';"

# 授权
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sqlbot TO sqlbot;"
```

#### 5. 配置环境变量

```bash
# 编辑配置文件
vim /opt/sqlbot/app/.env

# 配置内容
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=sqlbot
POSTGRES_PASSWORD=sqlbot
POSTGRES_DB=sqlbot
FRONTEND_HOST=http://your-domain.com
BACKEND_CORS_ORIGINS=http://your-domain.com
LOG_LEVEL=INFO
SQL_DEBUG=false
```

#### 6. 启动服务

```bash
# 进入部署目录
cd /opt/sqlbot

# 启动服务
./start.sh
```

### 服务管理

#### 使用 systemd（推荐）

创建服务文件：

```bash
sudo vim /etc/systemd/system/sqlbot.service
```

服务配置：

```ini
[Unit]
Description=SQLBot Application
After=network.target postgresql.service

[Service]
Type=simple
User=sqlbot
WorkingDirectory=/opt/sqlbot
ExecStart=/opt/sqlbot/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable sqlbot

# 启动服务
sudo systemctl start sqlbot

# 查看状态
sudo systemctl status sqlbot

# 查看日志
sudo journalctl -u sqlbot -f
```

#### 手动管理

```bash
# 启动服务
cd /opt/sqlbot && ./start.sh

# 停止服务
pkill -f "uvicorn main:app"
pkill -f "node app.js"

# 查看进程
ps aux | grep -E "(uvicorn|node)" | grep -v grep
```

## 🔧 配置说明

### 环境变量配置

#### 后端配置 (`/opt/sqlbot/app/.env`)

```bash
# 数据库配置
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=sqlbot
POSTGRES_PASSWORD=your-password
POSTGRES_DB=sqlbot

# 应用配置
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 前端配置
FRONTEND_HOST=http://your-domain.com
BACKEND_CORS_ORIGINS=http://your-domain.com,http://localhost:3000

# 日志配置
LOG_LEVEL=INFO
SQL_DEBUG=false

# 文件路径
UPLOAD_DIR=/opt/sqlbot/data/uploads
MCP_IMAGE_PATH=/opt/sqlbot/data/mcp
EXCEL_PATH=/opt/sqlbot/data/excel
```

### 目录结构

```
/opt/sqlbot/
├── app/                    # 后端应用
│   ├── main.py            # 主应用入口
│   ├── .env               # 环境配置
│   ├── static/            # 前端静态文件
│   └── ...
├── g2-ssr/                # 图表渲染服务
│   ├── app.js             # 服务入口
│   ├── package.json       # 依赖配置
│   └── ...
├── data/                  # 数据目录
│   ├── uploads/           # 上传文件
│   ├── mcp/               # MCP 文件
│   └── excel/             # Excel 文件
├── logs/                  # 日志目录
├── start.sh               # 启动脚本
└── docker-compose.yaml    # Docker 配置
```

## 🔍 监控和日志

### 日志文件

- **后端日志**: `/opt/sqlbot/app/logs/`
- **g2-ssr 日志**: `/opt/sqlbot/g2-ssr/g2-ssr.log`
- **MCP 日志**: `/opt/sqlbot/app/mcp.log`
- **系统日志**: `sudo journalctl -u sqlbot`

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查端口占用
netstat -tlnp | grep -E "(8000|8001|3000)"

# 检查进程
ps aux | grep -E "(uvicorn|node)" | grep -v grep
```

### 性能监控

```bash
# 查看内存使用
free -h

# 查看磁盘使用
df -h

# 查看 CPU 使用
top -p $(pgrep -f "uvicorn|node")
```

## 🚨 故障排除

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

#### 2. 数据库连接失败

```bash
# 检查 PostgreSQL 服务
sudo systemctl status postgresql

# 检查数据库连接
psql -h localhost -U sqlbot -d sqlbot

# 检查防火墙
sudo ufw status
```

#### 3. 权限问题

```bash
# 修复权限
sudo chown -R $USER:$USER /opt/sqlbot
chmod +x /opt/sqlbot/start.sh
```

#### 4. 依赖问题

```bash
# 重新安装后端依赖
cd /opt/sqlbot/app
uv sync

# 重新安装前端依赖
cd /opt/sqlbot/g2-ssr
npm install
```

### 日志分析

```bash
# 查看错误日志
tail -f /opt/sqlbot/app/logs/error.log

# 查看访问日志
tail -f /opt/sqlbot/app/logs/access.log

# 查看系统日志
sudo journalctl -u sqlbot -f
```

## 📚 相关文档

- [构建指南](./BUILD_GUIDE.md) - 详细的构建说明
- [调试指南](./DEBUG_GUIDE.md) - 开发调试指南
- [G2-SSR 指南](./G2_SSR_GUIDE.md) - 图表服务说明

---

如有问题，请查看相应文档或联系项目维护者。
