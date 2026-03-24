# SQLBot 项目上下文

## 项目概述

SQLBot 是一款基于大语言模型（LLM）和 RAG（检索增强生成）的智能问数系统（ChatBI），由 DataEase 开源项目组开发。用户可以通过自然语言对话方式进行数据分析，快速获取数据信息和可视化图表。

### 核心功能
- **对话式数据分析**：自然语言转 SQL（Text-to-SQL）
- **RAG 增强**：术语库、SQL 示例校准、向量检索
- **多数据源支持**：PostgreSQL、MySQL、Oracle、SQL Server、ClickHouse、Elasticsearch 等
- **可视化图表**：自动生成图表配置
- **MCP 服务**：支持与 n8n、Dify、MaxKB、DataEase 等应用集成

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11, FastAPI, SQLModel, Alembic, LangChain, LangGraph |
| 前端 | Vue 3, TypeScript, Vite, Element Plus, Pinia, @antv/g2 |
| 数据库 | PostgreSQL + pgvector（向量扩展） |
| 容器化 | Docker, Docker Compose |
| 包管理 | uv（后端）, npm（前端） |

---

## 目录结构

```
SQLBot/
├── backend/                 # Python 后端
│   ├── apps/               # 业务模块
│   │   ├── ai_model/       # LLM 模型工厂（OpenAI, vLLM, Azure 等）
│   │   ├── chat/           # 聊天核心逻辑、SQL 生成
│   │   ├── datasource/     # 数据源管理
│   │   ├── terminology/    # 术语库
│   │   ├── data_training/  # SQL 示例训练
│   │   ├── system/         # 用户、权限、认证
│   │   ├── mcp/            # MCP 服务
│   │   └── openapi/        # 开放 API
│   ├── common/             # 公共模块（配置、缓存、工具）
│   ├── templates/          # 提示词模板（template.yaml）
│   ├── alembic/            # 数据库迁移
│   ├── main.py             # FastAPI 入口
│   └── pyproject.toml      # Python 依赖
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── api/           # API 调用
│   │   ├── views/         # 页面组件
│   │   ├── components/    # 通用组件
│   │   ├── stores/        # Pinia 状态管理
│   │   └── router/        # 路由配置
│   └── package.json
├── build/                  # Docker 构建脚本
├── docs/                   # 项目文档
├── installer/              # 离线安装脚本
└── g2-ssr/                # 图表服务端渲染
```

---

## 构建与运行

### Docker 一键部署（推荐）

```bash
docker run -d \
  --name sqlbot \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 8001:8001 \
  -v ./data/sqlbot/excel:/opt/sqlbot/data/excel \
  -v ./data/sqlbot/file:/opt/sqlbot/data/file \
  -v ./data/sqlbot/images:/opt/sqlbot/images \
  -v ./data/sqlbot/logs:/opt/sqlbot/app/logs \
  -v ./data/postgresql:/var/lib/postgresql/data \
  --privileged=true \
  dataease/sqlbot
```

访问：`http://<服务器IP>:8000/`，默认账号：`admin` / `SQLBot@123456`

### 本地开发

#### 后端

```bash
cd backend
uv sync                                    # 安装依赖
cp .env.example ../.env                    # 配置环境变量（需修改数据库连接）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend
npm install
npm run dev                                # 开发服务器 http://localhost:5173
```

### 本地构建 Docker 镜像

```bash
./quick.sh                                 # 一键构建当前平台镜像
# 或
cd build && ./build.sh base                # 首次或依赖/前端变更后
cd build && ./build.sh quick               # 仅后端代码更新时
```

---

## 端口说明

| 端口 | 服务 |
|------|------|
| 8000 | 主应用（Web + API） |
| 8001 | MCP 服务 |
| 5173 | 前端开发服务器 |
| 5678 | debugpy 调试端口（需设置 `SQLBOT_DEBUG=1`） |

---

## 开发规范

### 后端（Python）

- **代码风格**：使用 Ruff 进行 lint 和 format
- **类型检查**：使用 mypy（strict 模式）
- **测试**：使用 pytest
- **提交前检查**：pre-commit hooks（ruff, trailing-whitespace, end-of-file-fixer）

```bash
cd backend
ruff check .          # Lint
ruff format .         # Format
mypy .                # 类型检查
pytest                # 测试
```

### 前端（Vue 3 + TypeScript）

- **构建工具**：Vite
- **UI 框架**：Element Plus
- **状态管理**：Pinia
- **代码风格**：ESLint + Prettier

```bash
cd frontend
npm run lint          # Lint 检查
npm run build         # 生产构建
```

### Git 提交规范

项目使用 pre-commit hooks，提交前自动执行代码检查。

---

## 核心架构

### 启动流程

1. `backend/main.py` 定义 FastAPI 应用
2. `lifespan` 上下文管理器执行：数据库迁移、缓存初始化、动态 CORS、嵌入数据填充
3. 挂载路由、中间件（认证、CORS、响应处理）
4. 初始化 MCP 服务

### SQL 生成流程

1. **LLMService 初始化**：加载聊天记录、数据源、创建 LLM 实例
2. **Schema 提取**：`get_table_schema` 生成 M-Schema 格式表结构
3. **术语匹配**：模糊匹配 + 向量检索生成术语提示
4. **提示构建**：`ChatQuestion.sql_sys_question` 填充系统提示
5. **流式生成**：`generate_sql` 调用 LLM 流式生成 SQL
6. **SQL 校验与补全**：权限过滤、动态 SQL 处理
7. **执行与返回**：SSE 流式返回前端

### 配置管理

- 配置文件：`backend/common/core/config.py`
- 环境变量：项目根目录 `.env` 文件
- 关键配置项：
  - `POSTGRES_*` / `SQLBOT_DB_URL`：数据库连接
  - `SECRET_KEY`：JWT 密钥
  - `DEFAULT_PWD`：默认密码
  - `CACHE_TYPE`：缓存类型（memory/redis）
  - `EMBEDDING_*`：向量嵌入配置

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [docs/GUIDE.md](docs/GUIDE.md) | 完整指南：安装、构建、开发、架构 |
| [docs/DEBUG.md](docs/DEBUG.md) | 本地调试：PyCharm、前后端联调、容器 debugpy |
| [docs/BUILD.md](docs/BUILD.md) | 构建与打包详细说明 |
| [docs/SECURITY_TODO.md](docs/SECURITY_TODO.md) | 安全问题与修复计划 |

---

## 注意事项

1. **环境变量**：`.env` 文件应放在项目根目录（与 `backend` 同级）
2. **数据库**：本地开发需准备 PostgreSQL 数据库
3. **安全**：生产环境务必修改 `SECRET_KEY` 和 `DEFAULT_PWD`
4. **代理**：代码启动时会清除代理环境变量，避免 LangChain/httpx 使用 SOCKS 代理报错