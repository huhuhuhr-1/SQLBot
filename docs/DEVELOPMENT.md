# 本地开发指南

本文档面向需要从源码运行、调试或参与开发的贡献者。

## 目录结构概览

- **backend/** — Python 后端（FastAPI、业务逻辑、数据库）
- **frontend/** — 前端（Vue 等）
- **build/** — Docker 构建与多平台打包脚本
- **installer/** — 离线安装包脚本与配置
- **docs/** — 项目文档

## 后端开发

### 环境要求

- Python 3.11
- 建议使用 uv 或 venv 管理依赖

### 安装依赖与启动

```bash
cd backend
uv sync   # 或 pip install -e .
# 需配置数据库等环境变量，可复制 .env.example 为 .env 并修改
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

数据库需单独准备（如 PostgreSQL）。MCP 服务若需本地调试，可另起进程运行对应入口。

### 常用脚本（backend/scripts）

- `format.sh` — 代码格式化
- `lint.sh` — 静态检查
- `test.sh` / `tests-start.sh` — 测试
- `alembic/exec.sh`、`alembic/auto.sh` — 数据库迁移

## 前端开发

```bash
cd frontend
npm install
npm run dev
```

按前端项目内说明配置代理或 API 地址，指向本地后端（如 8000 端口）。

## 构建与打包

- **快速构建当前平台镜像**（根目录）：`./quick.sh`
- **完整构建与多平台**：进入 `build/` 目录，使用统一入口：

  ```bash
  cd build
  ./build.sh          # 查看用法
  ./build.sh base     # 基础镜像
  ./build.sh quick    # 仅更新后端代码的快速镜像
  ```

详细说明见 [build/README.md](../build/README.md)。

## 根目录脚本说明

| 文件 | 说明 |
|------|------|
| `start.sh` | 容器内启动脚本（PostgreSQL + g2-ssr + 主应用） |
| `quick.sh` | 本地一键构建当前平台 Docker 镜像 |

## 文档与规范

- 安装与部署：[INSTALL.md](INSTALL.md)
- 安全与待办：[SECURITY_TODO.md](SECURITY_TODO.md)
- 代码架构与流程可参考项目根目录 `CODE_ANALYSIS.md`（若存在）

如有问题可提交 Issue 或参考主 [README.md](../README.md) 中的社区联系方式。
