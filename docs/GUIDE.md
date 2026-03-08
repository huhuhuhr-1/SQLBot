# SQLBot 完整指南：从安装部署到项目深度分析

本文档涵盖安装部署、构建打包、本地开发与调试，以及项目架构与核心流程的深度分析。

---

## 一、安装与部署

### 1.1 Docker 一键运行（推荐）

已安装 Docker 的环境可直接拉取官方镜像运行：

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

- 访问：http://\<服务器IP\>:8000/
- 默认账号：admin / SQLBot@123456

也可通过 [1Panel 应用商店](https://apps.fit2cloud.com/1panel) 或内网 [离线安装包](https://community.fit2cloud.com/#/products/sqlbot/downloads) 部署。

### 1.2 离线安装包

1. 从社区下载页获取离线包并解压。
2. 在 `installer` 目录执行：`./install.sh`。配置见 `install.conf`，卸载使用 `uninstall.sh`。

### 1.3 自建 Docker 镜像

从源码构建并运行自己的镜像（适合二次开发或定制）：

```bash
cd build
./build.sh base    # 首次或依赖/前端变更后
./build.sh quick   # 仅后端代码更新时
```

或根目录一键构建：`./quick.sh`。运行容器时将镜像名改为自建镜像（如 `zf-sqlbot:latest`），其余参数同上。

详细构建说明见 **[BUILD.md](BUILD.md)**。

### 1.4 端口与数据

| 端口 | 说明 |
|------|------|
| 8000 | 主应用（Web + API） |
| 8001 | MCP 服务 |
| 5678 | 调试用（仅当 `SQLBOT_DEBUG=1` 时 debugpy 监听） |

数据与日志建议通过 `-v` 挂载到宿主机，便于备份与升级。

---

## 二、构建与打包

完整构建指南见 **[BUILD.md](BUILD.md)**。

### 2.1 两阶段设计

- **阶段一（完整构建）**：根目录 `Dockerfile` + `build/build-base.sh`，产出基础镜像 `sqlbot-dev-20251130:latest`（含前端、uv 依赖、g2-ssr、向量模型、PostgreSQL 等）。首次或依赖/前端变更时执行。
- **阶段二（快速构建）**：`build/Dockerfile.update` + `build/build-quick.sh`，基于基础镜像仅覆盖 backend 代码，产出 `zf-sqlbot:latest`。日常仅改后端时执行，约 1–2 分钟。

### 2.2 快速参考

| 你的场景 | 推荐命令 |
|---------|---------|
| 第一次构建，想看看能不能成功 | `./quick.sh` |
| 首次构建基础镜像 | `cd build && ./build.sh base` |
| 改了 Python 依赖或前端代码 | `cd build && ./build.sh base` |
| 只改了后端 Python 代码 | `cd build && ./build.sh quick` |
| 在 M 系列 Mac 上开发 | `cd build && ./build.sh quick-arm64` |
| 需要同时发布 x86 和 ARM | `cd build && ./build.sh multiplatform` |

### 2.3 脚本一览

| 脚本 | 说明 |
|------|------|
| `build/build.sh` | 统一入口，参数：base \| quick \| quick-x86 \| quick-arm64 \| multiplatform \| multiplatform-optimized |
| `build/build-base.sh` | 构建基础镜像 |
| `build/build-quick.sh` | 快速构建（仅 backend） |
| `build/build-quick-x86.sh` / `build-quick-arm64.sh` | 分架构快速构建 |
| `build/build-multiplatform.sh` / `build-multiplatform-optimized.sh` | 多平台基础镜像（amd64 + arm64） |
| 根目录 `quick.sh` | 单脚本一键构建当前平台最终镜像 |

### 2.4 多架构

- 多平台基础镜像产出：`sqlbot-dev-20251130:latest`（amd64）、`sqlbot-dev-20251130:arm64`（arm64）。
- 快速构建产出：`zf-sqlbot:latest`（x86）、`zf-sqlbot:arm64`（arm64）。仅维护一份 `build/Dockerfile.update`，arm64 由脚本内 `sed` 替换 FROM 生成。

---

## 三、本地开发与调试

### 3.1 目录结构

- **backend/** — Python 后端（FastAPI、业务逻辑、数据库）
- **frontend/** — 前端（Vue 等）
- **build/** — Docker 构建与多平台脚本
- **installer/** — 离线安装脚本与配置
- **docs/** — 项目文档

### 3.2 后端开发

- 环境：Python 3.11，建议 uv 或 venv。
- 安装与启动：

  ```bash
  cd backend
  uv sync
  # 配置 .env（可复制 .env.example）
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```

  数据库需单独准备（如 PostgreSQL）。MCP 可另起进程调试。

- 常用脚本：`backend/scripts/format.sh`、`lint.sh`、`test.sh`、`tests-start.sh`，以及 `alembic/exec.sh`、`alembic/auto.sh`。

### 3.3 前端开发

```bash
cd frontend
npm install
npm run dev
```

按项目说明配置代理或 API 地址指向本地后端（如 8000）。

### 3.4 容器内远程调试（IDE 附加）

镜像内已安装 `debugpy`，可用于对运行中的主应用下断点。

- 启用：运行容器时设置 `SQLBOT_DEBUG=1`，入口会执行 `start-debug.sh`，主应用通过 debugpy 监听 `0.0.0.0:5678`。
- 端口：`docker run` 时增加 `-p 5678:5678`，IDE 使用「远程附加」连接该端口。
- VS Code：使用「Reopen in Container」，根目录 [.devcontainer/devcontainer.json](../.devcontainer/devcontainer.json) 已配置 `SQLBOT_DEBUG=1` 与端口转发（含 5678、8000、8001）。

### 3.5 根目录脚本

| 文件 | 说明 |
|------|------|
| `start.sh` | 容器内启动（PostgreSQL + g2-ssr + 主应用） |
| `start-debug.sh` | 调试入口，主应用由 debugpy 启动，监听 5678 |
| `quick.sh` | 本地一键构建当前平台镜像 |

### 3.6 PyCharm 本地调试

> 详细步骤、环境变量、常见问题见 **[docs/DEBUG.md](DEBUG.md)**。

**Backend（必做）**

1. **打开项目**：用 PyCharm 打开仓库根目录（或至少包含 `backend` 的目录）。
2. **解释器**：`File` → `Settings` → `Project` → `Python Interpreter`，添加解释器：
   - 若已用 uv：选 `Add Interpreter` → `Existing`，指向 `backend/.venv/bin/python`；
   - 若未建 venv：在 `backend` 下执行 `uv sync`（或 `python -m venv .venv` + `pip install -e .`），再在 PyCharm 里选该 `.venv`。
3. **工作目录与环境变量**：
   - 运行/调试时「Working directory」设为 **`backend`**（或项目根，取决于你把 `.env` 放在哪）；
   - 配置从 **项目根目录** 的 `.env` 加载（见 `backend/common/core/config.py`），因此请在 **项目根** 放一份 `.env`（可复制 `backend/.env.example` 并改库连接等）。
4. **运行配置**：
   - `Run` → `Edit Configurations` → `+` → `Python`；
   - **Script path** 选 `backend` 下的 `main.py`（或 **Module name** 填 `uvicorn`，Parameters 填 `main:app --reload --host 0.0.0.0 --port 8000`，Working directory 填 `backend`）；
   - 若用 Module：Module name: `uvicorn`，Parameters: `main:app --reload --host 0.0.0.0 --port 8000`，Working directory: `backend`。
5. **数据库**：本地需有 PostgreSQL（或修改 `.env` 里 `POSTGRES_*` / `SQLBOT_DB_URL` 指向已有库）。首次启动会执行迁移。
6. **断点**：在 `backend` 代码里打断点，用 Debug 运行上述配置即可。

**Frontend（必做，否则无法访问完整 Web 界面）**

1. 在 **frontend** 目录安装依赖并启动开发服务器：
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   默认会跑在 `http://localhost:5173`，并代理 API 到后端（见 `frontend/vite.config.ts` 或类似配置）。
2. 后端配置里已包含 `FRONTEND_HOST=http://localhost:5173` 和 CORS（如 `BACKEND_CORS_ORIGINS` 含 5173），一般无需改。
3. 浏览器访问 `http://localhost:5173` 即可使用前端；后端用 PyCharm Debug 跑在 8000，前端通过代理或 CORS 访问 8000。

**可选：只调后端 API**

若只调试后端逻辑、不跑前端页面，可仅启动 Backend（同上），用 PyCharm Debug 或 curl/Postman 访问 `http://localhost:8000/api/v1/...`。

---

## 四、项目深度分析

### 4.1 启动流程与全局配置

- **入口**：`backend/main.py` 定义 FastAPI 应用。启动时通过 `lifespan` 执行数据库迁移、缓存初始化、动态 CORS、嵌入数据填充等；关闭时做清理与日志。
- **路由**：通过 `custom_generate_unique_id` 为路由生成可读 ID，挂载路由、异常处理与中间件。
- **配置**：`backend/common/core/config.py` 中 `Settings` 使用 pydantic-settings 从 `.env` 加载，提供 API 前缀、数据库、CORS、日志等。数据库连接优先使用 `SQLBOT_DB_URL`，否则由 Postgres 相关参数构造。

### 4.2 配置与数据库

- 全局配置集中在 `Settings`，数据库 URI 通过计算属性得到。
- 迁移由 Alembic 管理，在 `lifespan` 中执行 `run_migrations()`（`command.upgrade` to head）。

### 4.3 模型工厂与 LLM 接入

- `backend/apps/ai_model/model_factory.py`：`LLMConfig` 描述模型类型、名称、API 信息等并实现哈希；`LLMFactory.create_llm` 根据 `model_type` 创建 OpenAI、vLLM、Azure 等实例。
- `get_default_config` 从数据库加载默认模型配置、解密 API 信息并构造 `LLMConfig`。

### 4.4 数据模型与提示模板

- `ChatQuestion`（`backend/apps/chat/models/chat_model.py`）继承自 `AiModelQuestion`，封装问题、数据源、语言等，提供 `sql_sys_question`、`sql_user_question` 等方法按模板生成系统/用户提示。
- 模板：`backend/templates/template.yaml`（以及相关 yaml）中定义 SQL 生成角色、规则与示例，要求模型返回含 `success`、`sql`、`tables` 等字段的 JSON。

### 4.5 LLMService 与 SQL 生成全流程

- **初始化与上下文**：构造函数加载聊天记录与数据源，解析数据库版本与 schema，创建 LLM 实例；初始化消息时附加系统提示，并回放最近若干条历史到 `sql_message`/`chart_message`。
- **Schema 与术语**：通过 `get_table_schema` 生成 M-Schema 格式表结构；`get_terminology_template` 做模糊匹配与向量检索，生成 `<terminologies>` 等片段；`ChatQuestion.sql_sys_question` 将引擎、schema、术语填入系统提示。
- **流式生成 SQL**：`generate_sql` 将问题包装成用户消息，经 `llm.stream` 拉取输出，逐块拼接 SQL 与推理文本并记录 token；完成后追加到消息列表并写库。
- **解析与补全**：`check_sql` 从返回 JSON 提取 `sql` 与表名；`check_save_sql` 持久化并统计耗时；`generate_with_sub_sql`、`build_table_filter` 等用于子查询与行级权限过滤。
- **run_task 执行链**：若未绑定数据源则先由模型选择；校验连通性后调用 `generate_sql`；根据配置进行动态 SQL、权限过滤等补全；执行 SQL、缓存结果、调用模型生成图表配置并持久化，经 SSE 流式返回前端。

### 4.6 路由与 API

- `backend/apps/chat/api/chat.py`：主要接口包括 `/chat/start` 创建会话、`/chat/question` 提问并流式返回。`/chat/question` 中创建 `LLMService`、记录提问、启动异步任务，通过 `StreamingResponse` 返回 SSE。
- 其他模块：`apps/api.py` 挂载 openapi、chat、dashboard、datasource、system、mcp 等路由；鉴权、权限、审计等见 `apps/system`、`common/audit` 等。

### 4.7 逆向与扩展建议

1. 从 `main.py` 的 `lifespan` 入手，观察迁移与缓存初始化。
2. 跟踪 `LLMService` 初始化与 `generate_sql`，理解消息格式与日志。
3. 阅读 `template.yaml` 中 SQL 生成规则与示例。
4. 通过 `chat.py` 理解前后端协议与 SSE 流式返回。
5. 数据源与表结构：`apps/datasource/crud/datasource.py`（如 `get_table_schema`）；术语与向量：`apps/terminology`、pgvector 等。

---

## 五、文档与安全

- **构建指南**：[BUILD.md](BUILD.md) — 详细构建方式、脚本说明、使用场景。
- **本地调试**：[DEBUG.md](DEBUG.md) — PyCharm/本地运行、前后端联调、容器 debugpy 远程附加。
- **英文说明**：[README.en.md](README.en.md)
- **安全与待办**：[SECURITY_TODO.md](SECURITY_TODO.md) — 记录已知安全项与修复计划，开发与上线前请关注。
- **主 README**：[../README.md](../README.md) — 快速开始与社区入口。

以上内容覆盖从安装部署到项目深度分析，可作为运维、开发与二次扩展的统一参考。
