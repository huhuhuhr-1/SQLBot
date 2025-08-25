# SQLBot 调试完整指南

## 📋 目录

- [环境准备](#环境准备)
- [后端调试 (PyCharm)](#后端调试-pycharm)
- [前端调试 (WebStorm)](#前端调试-webstorm)
- [uv 包管理器](#uv-包管理器)
- [常见问题](#常见问题)

## 🚀 环境准备

### 必需工具
- **PyCharm Professional/Community** (后端开发)
- **WebStorm** (前端开发)
- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 数据库**
- **Chrome 浏览器**

### 项目启动顺序

```bash
# 1. 启动数据库
docker-compose up -d sqlbot-db

# 2. 启动后端服务
cd backend
uv venv
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. 启动前端服务
cd frontend
npm install
npm run dev
```

## 🔧 后端调试 (PyCharm)

### 环境配置

#### 环境变量 (`backend/.env`)
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

### 调试配置

#### FastAPI 调试配置
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

### 断点设置

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

## 🎨 前端调试 (WebStorm)

### 环境配置

#### 环境变量 (`frontend/.env.development`)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=SQLBot Dev
VITE_DEBUG=true
```

### 调试配置

#### Chrome 调试配置
```json
{
  "name": "Frontend Chrome Debug",
  "type": "chrome",
  "request": "launch",
  "url": "http://localhost:5173",
  "webRoot": "${workspaceFolder}/frontend/src"
}
```

### 断点设置

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

## 📦 uv 包管理器

### 基本使用

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 项目初始化
cd backend
uv venv
source .venv/bin/activate  # Linux/macOS
uv sync

# 添加依赖
uv add fastapi uvicorn sqlmodel
uv add --dev pytest black

# 运行脚本
uv run pytest
uv run uvicorn main:app --reload
```

### PyCharm 集成

1. 设置 Python 解释器为 `backend/.venv/bin/python`
2. 创建 uv 运行配置：
```json
{
  "name": "uv sync",
  "type": "python",
  "request": "launch",
  "module": "uv",
  "args": ["sync"],
  "cwd": "${workspaceFolder}/backend"
}
```

## 🚨 常见问题

### 后端问题

**Q: 模块导入错误？**
A: 检查 Python 解释器路径，使用 `uv sync` 重新安装依赖

**Q: 数据库连接失败？**
A: 确保 PostgreSQL 服务正在运行，检查连接参数

**Q: 端口冲突？**
A: 检查端口占用 `lsof -i :8000` 并杀死进程

### 前端问题

**Q: API 连接失败？**
A: 确保后端服务正在运行，检查 CORS 配置

**Q: 依赖问题？**
A: 清理并重新安装 `rm -rf node_modules package-lock.json && npm install`

### uv 问题

**Q: uv 命令未找到？**
A: 重新安装 uv 并添加到 PATH

**Q: 依赖安装失败？**
A: 清理缓存 `uv cache clean` 并重新同步

## 🎯 调试最佳实践

1. **分层调试**: UI层 → 业务层 → 数据层 → 网络层
2. **工具组合**: PyCharm + WebStorm + Chrome DevTools + Vue DevTools
3. **断点策略**: 在关键位置设置断点，使用条件断点
4. **数据追踪**: 追踪数据流向和状态变化

---

详细调试指南请参考：
- [PyCharm 调试指南](./PYCHARM_DEBUG_GUIDE.md)
- [WebStorm 前端调试指南](./WEBSTORM_FRONTEND_DEBUG_GUIDE.md)
- [uv 包管理器指南](./PYCHARM_UV_GUIDE.md)

