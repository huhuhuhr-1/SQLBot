# SQLBot 开发指南

## 📋 目录

- [开发环境准备](#开发环境准备)
- [项目结构](#项目结构)
- [本地开发](#本地开发)
- [调试指南](#调试指南)
- [代码规范](#代码规范)
- [测试指南](#测试指南)
- [贡献指南](#贡献指南)

## 🛠️ 开发环境准备

### 必需工具

- **Python 3.11+** - 后端开发
- **Node.js 18+** - 前端开发
- **PostgreSQL 12+** - 数据库
- **Git** - 版本控制
- **IDE 推荐**:
  - **后端**: PyCharm Professional/Community, VS Code
  - **前端**: WebStorm, VS Code

### 可选工具

- **uv** - 现代 Python 包管理器（推荐）
- **Docker** - 容器化开发
- **Postman/Insomnia** - API 测试
- **Chrome DevTools** - 前端调试

### 环境安装

#### Linux 环境

```bash
# 安装 Python 3.11+
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# CentOS/RHEL
sudo yum install python3.11 python3.11-pip

# 安装 Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装 uv (推荐)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows 环境

##### 1. 安装 Python 3.11+

```powershell
# 方法一：使用官方安装包（推荐）
# 1. 访问 https://www.python.org/downloads/
# 2. 下载 Python 3.11+ Windows 安装包
# 3. 运行安装包，勾选 "Add Python to PATH"
# 4. 验证安装
python --version
pip --version

# 方法二：使用 Chocolatey
choco install python311

# 方法三：使用 winget
winget install Python.Python.3.11
```

##### 2. 安装 Node.js 18+

```powershell
# 方法一：使用官方安装包（推荐）
# 1. 访问 https://nodejs.org/
# 2. 下载 LTS 版本安装包
# 3. 运行安装包，按默认设置安装
# 4. 验证安装
node --version
npm --version

# 方法二：使用 Chocolatey
choco install nodejs

# 方法三：使用 winget
winget install OpenJS.NodeJS
```

##### 3. 安装 PostgreSQL

```powershell
# 方法一：使用官方安装包（推荐）
# 1. 访问 https://www.postgresql.org/download/windows/
# 2. 下载 PostgreSQL 安装包
# 3. 运行安装包，设置密码为 'sqlbot'
# 4. 安装完成后，将 PostgreSQL bin 目录添加到 PATH

# 方法二：使用 Chocolatey
choco install postgresql

# 方法三：使用 Docker Desktop for Windows
# 推荐使用 Docker 方式，避免复杂的本地安装
```

##### 4. 安装 uv (Python 包管理器)

```powershell
# 方法一：使用官方安装脚本
# 在 PowerShell 中运行（需要管理员权限）
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 方法二：使用 pip 安装
pip install uv

# 方法三：手动下载安装
# 1. 访问 https://github.com/astral-sh/uv/releases
# 2. 下载 Windows 版本的 uv.exe
# 3. 将 uv.exe 放到 PATH 环境变量包含的目录中

# 验证安装
uv --version
```

##### 5. 安装 Git

```powershell
# 方法一：使用官方安装包（推荐）
# 1. 访问 https://git-scm.com/download/win
# 2. 下载 Git for Windows 安装包
# 3. 运行安装包，按默认设置安装

# 方法二：使用 Chocolatey
choco install git

# 方法三：使用 winget
winget install Git.Git
```

##### 6. 安装 Chocolatey (可选，用于简化安装)

```powershell
# 以管理员身份运行 PowerShell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 验证安装
choco --version
```

#### macOS 环境

```bash
# 安装 Python 3.11+
brew install python@3.11

# 安装 Node.js 18+
brew install node@18

# 安装 PostgreSQL
brew install postgresql@14

# 安装 uv (推荐)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 🏗️ 项目结构

```
SQLBot/
├── backend/                 # FastAPI 后端服务
│   ├── apps/               # 应用模块
│   │   ├── ai_model/       # AI 模型管理
│   │   ├── chat/           # 聊天功能
│   │   ├── dashboard/      # 仪表板
│   │   ├── datasource/     # 数据源管理
│   │   ├── system/         # 系统管理
│   │   └── template/       # 模板管理
│   ├── common/             # 公共模块
│   │   ├── core/           # 核心功能
│   │   ├── utils/          # 工具函数
│   │   └── error.py        # 错误处理
│   ├── db/                 # 数据库相关
│   ├── alembic/            # 数据库迁移
│   ├── main.py             # 应用入口
│   └── pyproject.toml      # 项目配置
├── frontend/                # Vue 3 前端应用
│   ├── src/                # 源代码
│   │   ├── api/            # API 接口
│   │   ├── components/     # 组件
│   │   ├── views/          # 页面
│   │   ├── stores/         # 状态管理
│   │   └── utils/          # 工具函数
│   ├── package.json        # 依赖配置
│   └── vite.config.ts      # Vite 配置
├── g2-ssr/                  # 图表渲染服务
├── installer/               # 安装脚本
├── docs/                    # 项目文档
└── scripts/                 # 构建脚本
```

### 技术架构

- **后端**: FastAPI + SQLModel + Alembic + PostgreSQL
- **前端**: Vue 3 + TypeScript + Vite + Element Plus
- **图表**: @antv/g2 + @antv/g2-ssr
- **包管理**: uv (Python) + npm (Node.js)

## 🚀 本地开发

### 1. 克隆项目

#### Linux/macOS 环境

```bash
git clone https://github.com/dataease/SQLBot.git
cd SQLBot
```

#### Windows 环境

```powershell
# 使用 PowerShell 或 Git Bash
git clone https://github.com/dataease/SQLBot.git
cd SQLBot

# 或者使用 Windows 命令提示符
git clone https://github.com/dataease/SQLBot.git
cd SQLBot
```

### 2. 启动数据库

#### 使用 Docker（推荐，跨平台）

```bash
# Linux/macOS 环境
docker run -d \
  --name sqlbot-db \
  --restart always \
  -p 5432:5432 \
  -e POSTGRES_DB=sqlbot \
  -e POSTGRES_USER=sqlbot \
  -e POSTGRES_PASSWORD=sqlbot \
  pgvector/pgvector:pg17

# 或使用 docker-compose
docker-compose up -d sqlbot-db
```

```powershell
# Windows 环境 (PowerShell)
docker run -d `
  --name sqlbot-db `
  --restart always `
  -p 5432:5432 `
  -e POSTGRES_DB=sqlbot `
  -e POSTGRES_USER=sqlbot `
  -e POSTGRES_PASSWORD=sqlbot `
  pgvector/pgvector:pg17

# 或使用 docker-compose
docker-compose up -d sqlbot-db
```

#### Windows 本地 PostgreSQL 安装

如果不想使用 Docker，可以在 Windows 上安装本地 PostgreSQL：

```powershell
# 1. 启动 PostgreSQL 服务
# 在 Windows 服务管理器中启动 "postgresql-x64-14" 服务
# 或者使用命令行
net start postgresql-x64-14

# 2. 创建数据库和用户
# 使用 pgAdmin 或命令行
psql -U postgres
CREATE DATABASE sqlbot;
CREATE USER sqlbot WITH PASSWORD 'sqlbot';
GRANT ALL PRIVILEGES ON DATABASE sqlbot TO sqlbot;
\q
```

### 3. 配置环境变量

#### 后端配置 (`backend/.env`)

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

#### 前端配置 (`frontend/.env.development`)

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=SQLBot Dev
VITE_DEBUG=true
```

### 4. 启动开发服务

#### Linux/macOS 环境

```bash
# 启动后端服务
cd backend
uv venv && uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端服务
cd frontend
npm install && npm run dev

# 启动图表服务 (可选)
cd g2-ssr
npm install && npm start
```

#### Windows 环境

```powershell
# 启动后端服务
cd backend
uv venv
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端服务
cd frontend
npm install
npm run dev

# 启动图表服务 (可选)
cd g2-ssr
npm install
npm start
```

#### Windows 环境注意事项

1. **路径分隔符**: Windows 使用反斜杠 `\`，但在 PowerShell 中也可以使用正斜杠 `/`
2. **权限问题**: 如果遇到权限问题，请以管理员身份运行 PowerShell
3. **防火墙**: 确保 Windows 防火墙允许相关端口访问
4. **杀毒软件**: 某些杀毒软件可能会阻止 Python 或 Node.js 进程，请添加例外
5. **编码问题**: 确保 PowerShell 使用 UTF-8 编码，避免中文显示问题

### 5. 访问服务

- **前端**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **图表服务**: http://localhost:3000

## 🔧 调试指南

### 后端调试 (PyCharm)

#### Linux/macOS 调试配置

```json
{
  "name": "SQLBot Backend Debug",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": ["main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
  "cwd": "${workspaceFolder}/backend",
  "python": "${workspaceFolder}/backend/.venv/bin/python",
  "env": {
    "PYTHONPATH": "${workspaceFolder}/backend"
  }
}
```

#### Windows 调试配置

```json
{
  "name": "SQLBot Backend Debug (Windows)",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": ["main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
  "cwd": "${workspaceFolder}/backend",
  "python": "${workspaceFolder}/backend\\.venv\\Scripts\\python.exe",
  "env": {
    "PYTHONPATH": "${workspaceFolder}/backend"
  }
}
```

#### 推荐断点位置

```python
# apps/api.py - API 路由
@router.get("/health")
async def health_check():
    # 设置断点
    return {"status": "ok"}

# apps/chat/api/chat.py - 聊天 API
@router.post("/chat")
async def chat(request: ChatRequest):
    # 设置断点
    response = await chat_service.process_chat(request)
    return response
```

### 前端调试 (WebStorm)

#### Chrome 调试配置

```json
{
  "name": "Frontend Chrome Debug",
  "type": "chrome",
  "request": "launch",
  "url": "http://localhost:5173",
  "webRoot": "${workspaceFolder}/frontend/src",
  "sourceMapPathOverrides": {
    "webpack:///src/*": "${webRoot}/*"
  }
}
```

#### 推荐断点位置

```typescript
// src/main.ts - 应用入口
import { createApp } from 'vue'
import App from './App.vue'
// 设置断点

// src/views/chat/ChatList.vue - 聊天列表
<script setup lang="ts">
const loadChatList = async () => {
  // 设置断点
  const response = await chatApi.getChatList()
  return response.data
}
</script>
```

### 调试工具

#### 跨平台工具

- **PyCharm**: 后端 Python 代码调试
- **WebStorm**: 前端 JavaScript/TypeScript 调试
- **VS Code**: 轻量级代码编辑器，支持多种语言
- **Chrome DevTools**: 浏览器调试
- **Vue DevTools**: Vue 组件调试
- **Postman/Insomnia**: API 接口测试

#### Windows 特定工具

- **Windows Terminal**: 现代化的终端模拟器，支持 PowerShell、CMD、WSL
- **PowerShell ISE**: PowerShell 集成脚本环境
- **Git Bash**: Git for Windows 提供的 Bash 环境
- **WSL (Windows Subsystem for Linux)**: 在 Windows 上运行 Linux 环境
- **Docker Desktop for Windows**: Windows 平台的 Docker 环境

## 📝 代码规范

### Python 代码规范

#### 代码风格
- 遵循 PEP 8 规范
- 使用 Black 进行代码格式化
- 使用 isort 进行导入排序
- 使用 flake8 进行代码检查

#### 类型注解
```python
from typing import List, Optional, Dict, Any
from sqlmodel import SQLModel

class ChatRequest(SQLModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
```

#### 异步编程
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    # 异步处理
    result = await chat_service.process_chat(request, db)
    return result
```

### TypeScript 代码规范

#### 代码风格
- 使用 ESLint + Prettier
- 遵循 Airbnb 规范
- 使用 TypeScript 严格模式

#### 类型定义
```typescript
interface ChatRequest {
  message: string;
  context?: Record<string, any>;
  userId?: number;
}

interface ChatResponse {
  id: string;
  message: string;
  timestamp: string;
}
```

#### Vue 3 组合式 API
```typescript
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { chatApi } from '@/api'

const chatList = ref<ChatItem[]>([])
const loading = ref(false)

const loadChatList = async () => {
  loading.value = true
  try {
    const response = await chatApi.getChatList()
    chatList.value = response.data
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadChatList()
})
</script>
```

## 🧪 测试指南

### 后端测试

```bash
# 安装测试依赖
cd backend
uv add --dev pytest pytest-asyncio pytest-cov

# 运行测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=apps --cov-report=html

# 运行特定测试
uv run pytest tests/test_chat.py::test_chat_api
```

### 前端测试

```bash
# 安装测试依赖
cd frontend
npm install --save-dev vitest @vue/test-utils

# 运行测试
npm run test

# 运行测试并生成覆盖率报告
npm run test:coverage
```

### 集成测试

```bash
# 启动测试环境
docker-compose -f docker-compose.test.yml up -d

# 运行集成测试
./scripts/test.sh

# 清理测试环境
docker-compose -f docker-compose.test.yml down
```

## 🤝 贡献指南

### 开发流程

1. **Fork 项目** - 在 GitHub 上 Fork 项目
2. **创建分支** - 创建功能分支 `git checkout -b feature/your-feature`
3. **开发功能** - 编写代码和测试
4. **提交代码** - 提交代码 `git commit -m "feat: add new feature"`
5. **推送分支** - 推送到远程分支 `git push origin feature/your-feature`
6. **创建 PR** - 在 GitHub 上创建 Pull Request

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建过程或辅助工具的变动
```

### 代码审查

- 所有代码变更需要经过代码审查
- 确保代码符合项目规范
- 添加必要的测试用例
- 更新相关文档

## 🚨 Windows 环境故障排除

### 常见问题及解决方案

#### 1. Python 环境问题

**问题**: `python` 命令无法识别
```powershell
# 解决方案 1: 检查 PATH 环境变量
echo $env:PATH

# 解决方案 2: 重新安装 Python，确保勾选 "Add Python to PATH"
# 解决方案 3: 手动添加 Python 路径到 PATH
$env:PATH += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311"
```

**问题**: `uv` 命令无法识别
```powershell
# 解决方案 1: 重新安装 uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 解决方案 2: 使用 pip 安装
pip install uv

# 解决方案 3: 检查 PATH 中是否包含 uv 安装路径
```

#### 2. Node.js 环境问题

**问题**: `npm` 命令无法识别
```powershell
# 解决方案 1: 重新安装 Node.js
# 解决方案 2: 检查 PATH 环境变量
echo $env:PATH

# 解决方案 3: 重启 PowerShell 或命令提示符
```

**问题**: npm 安装依赖失败
```powershell
# 解决方案 1: 清理 npm 缓存
npm cache clean --force

# 解决方案 2: 使用国内镜像源
npm config set registry https://registry.npmmirror.com

# 解决方案 3: 以管理员身份运行 PowerShell
```

#### 3. 数据库连接问题

**问题**: PostgreSQL 连接失败
```powershell
# 解决方案 1: 检查 PostgreSQL 服务状态
Get-Service postgresql*

# 解决方案 2: 启动 PostgreSQL 服务
Start-Service postgresql-x64-14

# 解决方案 3: 检查防火墙设置
# 在 Windows 防火墙中添加 PostgreSQL 端口 5432 的入站规则
```

**问题**: Docker 无法启动
```powershell
# 解决方案 1: 检查 Docker Desktop 是否正在运行
# 解决方案 2: 重启 Docker Desktop
# 解决方案 3: 检查 WSL 2 是否启用
wsl --status
```

#### 4. 权限和路径问题

**问题**: 权限不足
```powershell
# 解决方案 1: 以管理员身份运行 PowerShell
# 解决方案 2: 修改执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 解决方案 3: 检查文件和文件夹权限
icacls "C:\path\to\your\project"
```

**问题**: 路径过长
```powershell
# 解决方案 1: 启用长路径支持
# 在注册表中启用 LongPathsEnabled
# 解决方案 2: 将项目放在较短的路径下
# 例如: C:\dev\sqlbot 而不是 C:\Users\username\Documents\projects\sqlbot
```

#### 5. 网络和代理问题

**问题**: 无法下载依赖包
```powershell
# 解决方案 1: 配置代理
$env:HTTP_PROXY="http://proxy.company.com:8080"
$env:HTTPS_PROXY="http://proxy.company.com:8080"

# 解决方案 2: 使用国内镜像源
# Python: 配置 pip 镜像源
# Node.js: 配置 npm 镜像源

# 解决方案 3: 检查防火墙和杀毒软件设置
```

### Windows 开发最佳实践

1. **使用 WSL 2**: 在 Windows 上获得完整的 Linux 开发环境
2. **使用 Windows Terminal**: 现代化的终端体验
3. **配置 PowerShell 配置文件**: 自定义别名和函数
4. **使用 Chocolatey**: 简化 Windows 软件安装
5. **定期更新**: 保持系统和开发工具的最新版本

---

详细调试指南请参考：[调试指南](./DEBUG_GUIDE.md)
