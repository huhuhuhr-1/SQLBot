# SQLBot 项目说明

## 1. 项目组成

SQLBot 是一个基于大模型与 RAG 的问数系统，源代码主要包含以下模块：

- **backend**：使用 FastAPI 构建的后端服务，依赖 pydantic、sqlmodel 等 Python 库【F:backend/pyproject.toml†L1-L46】；
- **frontend**：基于 Vue 3 和 Vite 的前端界面，提供交互式问数体验【F:frontend/package.json†L1-L16】；
- **g2-ssr**：用于图表渲染的 Node.js 服务，依赖 @antv/g2-ssr 和 node-canvas 等组件【F:g2-ssr/package.json†L1-L17】；
- **start.sh**：容器启动脚本，分别启动 g2-ssr 服务和两个 Uvicorn 实例【F:start.sh†L1-L8】；
- **Dockerfile** 与 **docker-compose.yaml**：提供容器化部署方案，包含多阶段构建和运行时配置【F:Dockerfile†L1-L72】【F:docker-compose.yaml†L1-L43】；
- **installer**：离线/在线安装脚本及模板，可用于打包发行。

## 2. 编译与构建

### 后端
1. 安装 Python 3.10+ 与 [uv](https://github.com/astral-sh/uv)。
2. 在 `backend` 目录下执行：
   ```bash
   uv sync            # 安装依赖
   uv build --wheel   # 生成 wheel 至 dist/
   ```
   生成的 wheel 可用于部署；开发时可运行：
   ```bash
   uvicorn main:app --reload
   ```

### 前端
1. 安装 Node.js 与 npm。
2. 在 `frontend` 目录下执行：
   ```bash
   npm install
   npm run build   # 生成 dist
   ```
   如需开发模式，可使用 `npm run dev`。

### g2-ssr
1. 安装 Node.js 与 npm。
2. 在 `g2-ssr` 目录下执行：
   ```bash
   npm install
   node app.js
   ```

### 汇总：从源码到构建产物
按上述步骤依次在三个子模块中执行，即可得到：
- `backend/dist/*.whl`：后端 Python wheel 包；
- `frontend/dist`：前端静态资源；
- `g2-ssr/`：Node 服务源码。
这些产物将用于后续的 RPM 打包或 Docker 鏗像构建。

### 一键脚本
为方便自动化，项目根目录提供 `build_from_source.sh`（Linux/macOS）和 `build_from_source.ps1`（Windows），可一次性完成以上编译并尝试生成 RPM 与 Docker 鏗像：

```bash
./build_from_source.sh          # Linux/macOS
# 或
pwsh ./build_from_source.ps1    # Windows
```

脚本会依赖已安装的 `uv`、`npm`、`fpm` 与 `docker`，缺失时将自动跳过相应步骤。

## 3. 生成 RPM 与 Docker 镜像

### Docker 鏗像
项目根目录提供了多阶段构建的 `Dockerfile`，在构建現像时会自动执行前述源码编译步骤，将前端、后端及 g2-ssr 一体化打包：
```bash
docker build -t sqlbot:latest .
# 或使用 buildx 构建多架构現像
docker buildx build --platform linux/amd64,linux/arm64 -t sqlbot:latest .
```

### RPM 包
仓库未提供现成的 RPM 规格文件，可通过 [fpm](https://github.com/jordansissel/fpm) 自行打包：
1. 按上一节"从源码到构建产物"得到的三个目录准备前端 `frontend/dist`、后端 `backend/dist/*.whl` 和 `g2-ssr` 源码。
2. 创建打包目录并拷贝文件：
   ```bash
   mkdir -p package/opt/sqlbot/{backend,frontend,g2-ssr}
   cp backend/dist/*.whl package/opt/sqlbot/backend/
   cp -r frontend/dist package/opt/sqlbot/frontend/
   cp -r g2-ssr package/opt/sqlbot/g2-ssr/
   cp start.sh package/opt/sqlbot/
   ```
3. 依赖 Ruby 环境安装 fpm 后，在项目根目录执行：
   ```bash
   fpm -s dir -t rpm -n sqlbot -v 1.0.0 \
       -C package opt/sqlbot
   ```
   生成的 RPM 可通过 `rpm -ivh sqlbot-1.0.0-1.x86_64.rpm` 安装。

## 4. 安装与部署

### 安装 RPM
1. 在目标机器上安装生成的 RPM：
   ```bash
   sudo rpm -ivh sqlbot-1.0.0-1.x86_64.rpm
   ```
   程序默认解压至 `/opt/sqlbot`。
2. 进入安装目录并启动：
   ```bash
   cd /opt/sqlbot
   ./start.sh
   ```
   该脚本会同时启动 g2-ssr 与两个 Uvicorn 实例。

### 运行 Docker 鏗像
构建現像后可通过以下方式运行：
```bash
docker run --rm -p 8000:8000 sqlbot:latest
```

## 5. 离线Docker镜像包

项目提供了完整的离线Docker镜像包，适用于内网环境部署。

### 镜像文件清单
- **alpine.tar** - Alpine Linux基础镜像 (7.4MB)
- **uv.tar** - Python包管理工具uv镜像 (39MB)
- **postgres.tar** - PostgreSQL 17.6数据库镜像 (431MB)
- **python-3.11-slim-bookworm.tar** - Python 3.11 slim基础镜像 (131MB)
- **maxkb-vector-model.tar** - MaxKB向量模型镜像 (831MB)
- **sqlbot-base.tar** - SQLBot基础运行环境镜像 (811MB)
- **sqlbot-python-pg.tar** - 包含Python 3.11和PostgreSQL环境镜像 (1.4GB)
- **dataease-sqlbot.tar** - 完整的SQLBot应用镜像 (3.9GB)
- **sqlbot-pycharm-dev.tar** - PyCharm开发环境专用镜像 (1008MB)

### 离线环境部署命令
```bash
# 加载所有Docker镜像
docker load -i alpine.tar
docker load -i uv.tar
docker load -i postgres.tar
docker load -i python-3.11-slim-bookworm.tar
docker load -i maxkb-vector-model.tar
docker load -i sqlbot-base.tar
docker load -i sqlbot-python-pg.tar
docker load -i dataease-sqlbot.tar
docker load -i sqlbot-pycharm-dev.tar

# 验证镜像加载成功
docker images | grep -E "(alpine|uv|postgres|python|maxkb|sqlbot)"
```

## 6. PyCharm开发环境

专门准备了适合PyCharm远程开发的Docker环境，适用于内网开发环境。

### 文件位置
- `dev/Dockerfile.pycharm` - PyCharm开发环境Dockerfile
- `dev/pycharm-dev-guide.md` - 详细使用指南
- `images/sqlbot-pycharm-dev.tar` - 预构建的镜像文件

### 启动开发容器
```bash
# 启动PyCharm开发环境容器
docker run -d --name sqlbot-pycharm-dev -p 2222:22 -p 18000:8000 -p 13000:3000 -p 18001:8001 sqlbot-pycharm-dev:latest
```

### 容器访问信息
- **SSH服务**: 端口2222
- **用户名**: root
- **密码**: pycharm_dev
- **Python版本**: 3.11.13
- **Node.js版本**: 18.20.8
- **工作目录**: `/workspace/sqlbot`
- **虚拟环境**: `/workspace/sqlbot/backend/.venv`

### 使用方法
1. 在内网环境中加载镜像：
   ```bash
   docker load -i images/sqlbot-pycharm-dev.tar
   ```
2. 启动开发容器：
   ```bash
   docker run -d --name sqlbot-pycharm-dev -p 2222:22 sqlbot-pycharm-dev:latest
   ```
3. 配置PyCharm连接到容器SSH服务进行开发

详情请参考 `dev/pycharm-dev-guide.md` 文档。

---
如需进一步定制安装流程，可参考 `installer` 目录中的脚本并结合自身环境调整。