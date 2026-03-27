# 本地调试指南

本文档说明如何在本地用 PyCharm（或其它 IDE）调试 SQLBot 后端，以及前后端联调方式。容器内远程调试（debugpy）见文末。

---

## 一、环境准备

- **Python 3.11**（后端）
- **Node.js**（前端，仅需联调页面时）
- **PostgreSQL**（本地或远程，需在 `.env` 中配置）
- **PyCharm** 或其它支持 Python 调试的 IDE

---

## 二、Backend 调试（PyCharm）

### 2.1 安装依赖

在项目根目录执行（**必须加 `--extra cpu`**，否则会装 CUDA 版 PyTorch，本机无 GPU 驱动时会报 `libcudart.so.12` / `libcublas.so` 找不到）：

```bash
cd backend
uv sync --extra cpu
```

会在 `backend/.venv` 下创建虚拟环境并安装依赖，其中 PyTorch 为 **CPU 版**，无需本机安装 CUDA。

若未安装 uv，可用：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[cpu]"     # 必须带 [cpu]，安装 CPU 版 torch
```

### 2.2 配置环境变量

应用从**项目根目录**的 `.env` 读取配置（见 `backend/common/core/config.py`）。

1. 在**项目根**复制示例并改名：
   ```bash
   cp backend/.env.example .env
   ```
2. 编辑 `.env`，至少配置数据库（本地 PostgreSQL 或已有库）：
   - `POSTGRES_SERVER`、`POSTGRES_PORT`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`  
   或直接设 `SQLBOT_DB_URL=postgresql+psycopg://user:pass@host:port/dbname`
3. 本地联调前端时建议保留或设置：
   - `FRONTEND_HOST=http://localhost:5173`
   - `BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost"]`

### 2.3 PyCharm 解释器

1. `File` → `Settings` → `Project: SQLBot` → `Python Interpreter`
2. `Add Interpreter` → `Add Local Interpreter` → `Existing`
3. 选择 **`backend/.venv/bin/python`**（或你创建的 `.venv` 路径），确定

### 2.4 运行/调试配置

1. `Run` → `Edit Configurations` → `+` → `Python`
2. 配置方式二选一：

**方式 A：用 uvicorn 启动（推荐）**

- **Name**：`SQLBot Backend`
- **Module name**：`uvicorn`
- **Parameters**：`main:app --reload --host 0.0.0.0 --port 8000`
- **Working directory**：选项目下的 **`backend`** 目录（必须）
- **Environment variables**：若需覆盖可在此添加；否则使用项目根 `.env`

**方式 B：直接运行 main**

- **Script path**：选择项目中的 **`backend/main.py`**
- **Working directory**：**`backend`**
- **Parameters** 留空时需在代码里用 `uvicorn.run(app, host="0.0.0.0", port=8000)` 等方式启动，否则用方式 A 更简单。

3. 保存后点击 **Debug**（虫子图标）即可断点调试；后端运行在 **http://localhost:8000**。

### 2.5 数据库

- 本地需有 PostgreSQL；首次启动会自动执行 Alembic 迁移（`lifespan` 中）。
- 若使用 Docker 跑 Postgres：  
  `docker run -d --name pg -e POSTGRES_USER=root -e POSTGRES_PASSWORD=Password123@pg -e POSTGRES_DB=sqlbot -p 5432:5432 postgres:15`

---

## 三、Frontend 联调（可选）

需要完整 Web 界面或调前端时：

1. 安装并启动前端开发服务：
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. 前端默认运行在 **http://localhost:5173**；API 请求需指向后端 **http://localhost:8000**（一般在 frontend 的 env 或 request 配置中设置）。
3. 后端已默认带 `FRONTEND_HOST=http://localhost:5173` 和 CORS，无需改 backend 即可被 5173 访问。
4. 浏览器打开 **http://localhost:5173**，后端用 PyCharm Debug 跑在 8000，即可前后端联调并断点后端。

---

## 四、仅调试后端 API（不跑前端）

- 只启动 Backend（按第二节用 PyCharm Debug 运行）。
- 使用 **Postman**、**curl** 或浏览器访问 `http://localhost:8000/docs`（Swagger）调试接口。
- 断点打在 `backend` 任意位置即可。

---

## 五、容器内远程调试（debugpy）

若希望对**已运行在 Docker 里的应用**下断点（而非本地进程）：

1. 运行容器时加环境变量并映射端口：
   ```bash
   docker run -e SQLBOT_DEBUG=1 -p 5678:5678 -p 8000:8000 -p 8001:8001 ... zf-sqlbot:latest
   ```
2. 在 PyCharm：`Run` → `Edit Configurations` → `+` → `Python Debug Server`（或「远程调试」），监听端口 **5678**，连接方式选「Attach」。
3. 启动该调试配置后，在容器内运行的主应用会连上 IDE，即可在本地断点调试容器内代码。

VS Code 用户可使用「Reopen in Container」并配合根目录 `.devcontainer/devcontainer.json`（已配置 `SQLBOT_DEBUG=1` 与 5678 端口转发）。

---

## 六、常见问题

### 6.1 `libcudart.so.12` / `libcublas.so` 找不到（本地 PyCharm 启动报错）

**是哪一段代码导致的？**

- **直接触发点**：不是本仓库里的业务代码，而是 **PyCharm 调试器** 自带的模块。用 PyCharm 点 **Debug** 时，进程会先加载 `pydevd`，其内部 `_pydevd_bundle/pydevd_utils.py` 约第 9 行会执行 `import torch`。
- **使用的 torch 从哪来**：当前进程的解释器是 `backend/.venv`，所以这个 `import torch` 会加载 **`.venv` 里安装的 torch**。若之前用 `uv sync`（未加 `--extra cpu`）或 pip 装了带 CUDA 的 PyTorch，这里的 torch 就是 CUDA 版。
- **为何报错**：CUDA 版 torch 在 `import` 时会加载 `libcudart.so.12`、`libcublas.so` 等；本机若未安装 CUDA 12 或未把 CUDA 的 lib 路径加入 `LD_LIBRARY_PATH`，就会报 `cannot open shared object file` / `libcublas.so.* not found`。
- **业务里会不会也 import torch？**：会。例如通过 `langchain_huggingface.HuggingFaceEmbeddings` → `sentence_transformers` → torch。即使用 **Run** 不点 Debug，首次用到 embedding 时也会 import torch；若 .venv 里仍是 CUDA 版且本机无对应 CUDA 库，同样会报错。因此根本解决办法是让 **.venv 里使用 CPU 版 torch**。

**推荐做法（无需本机装 CUDA）**

在 backend 下用 **CPU 版** 重装依赖，与 Docker 一致：

```bash
cd backend
rm -rf .venv   # 可选，清空后重装更干净
uv sync --extra cpu
```

再用 PyCharm 选 `backend/.venv` 并启动（Run 或 Debug 均可）。若用 pip：`pip install -e ".[cpu]"`。

**可选做法（保留 CUDA 版 torch）**

若必须在本机用 GPU：安装 CUDA 12.x Toolkit，并把其 lib 路径加入 `LD_LIBRARY_PATH`，例如：

```bash
export LD_LIBRARY_PATH=/usr/local/cuda-12.x/lib64:$LD_LIBRARY_PATH
```

注意：当前报错是缺 **CUDA 12** 的库；若本机只装了 CUDA 13，需安装支持 CUDA 13 的 PyTorch 或改装 CUDA 12。

### 6.2 其它

- **找不到 `.env`**：确认 `.env` 在**项目根**，且运行配置的 Working directory 为 **`backend`**（应用会从根目录加载 `.env`）。
- **数据库连接失败**：检查 `.env` 中 `POSTGRES_*` 或 `SQLBOT_DB_URL` 与本地/远程 PostgreSQL 一致；库需已创建。
- **前端请求跨域**：确保 `.env` 中 `BACKEND_CORS_ORIGINS` 包含 `http://localhost:5173`（或前端实际 origin）。
- **迁移报错**：在 `backend` 目录执行 `alembic upgrade head` 检查迁移；必要时检查数据库连接与历史表。

更多开发与项目结构见 [GUIDE.md](GUIDE.md)。
