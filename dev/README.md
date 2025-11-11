# SQLBot PyCharm Docker开发环境

## 概述

为PyCharm远程开发准备的Docker环境，特别适合内网环境使用。该环境预装了SQLBot开发所需的核心依赖。

## 包含的文件

- `Dockerfile.pycharm` - PyCharm开发环境的Dockerfile
- `pycharm-dev-guide.md` - 详细使用指南
- `images/sqlbot-pycharm-dev.tar` - 构建好的镜像文件

## 使用流程

### 1. 在外网环境构建镜像（已完成）
镜像已经构建完成，保存在 `images/sqlbot-pycharm-dev.tar` 中

### 2. 传输镜像文件到内网环境
将 `images/sqlbot-pycharm-dev.tar` 文件传输到内网环境

### 3. 在内网加载镜像
```bash
docker load -i images/sqlbot-pycharm-dev.tar
```

### 4. 启动开发容器
```bash
docker run -d --name sqlbot-pycharm-dev -p 2222:22 sqlbot-pycharm-dev:latest
```

### 5. 配置PyCharm连接
参考 `pycharm-dev-guide.md` 中的详细说明进行PyCharm连接配置

## 特性

- 预装Python 3.11和Node.js 18.x环境
- 包含SQLBot开发所需的核心Python包（fastapi, pydantic, sqlmodel等）
- SSH服务支持PyCharm远程连接
- 预配置虚拟环境
- 包含完整的开发工具链
- 适合内网离线环境使用
- 镜像大小仅1008MB（相比完整版的3.9GB）

## 与完整环境的区别

此开发环境特意精简了以下大型AI/ML组件以保持轻量化：
- MaxKB向量模型库
- LangGraph相关组件
- Llama-index (RAG框架)
- Torch等大型AI库

如需完整的AI/ML功能，可使用完整的 `dataease-sqlbot` 镜像。

## 完整的离线镜像清单

项目提供的完整离线Docker镜像包:
- `alpine.tar` - Alpine Linux基础镜像 (7.4MB)
- `uv.tar` - Python包管理工具uv镜像 (39MB)
- `postgres.tar` - PostgreSQL 17.6数据库镜像 (431MB)
- `python-3.11-slim-bookworm.tar` - Python 3.11 slim基础镜像 (131MB)
- `maxkb-vector-model.tar` - MaxKB向量模型镜像 (831MB)
- `sqlbot-base.tar` - SQLBot基础运行环境镜像 (811MB)
- `sqlbot-python-pg.tar` - 包含Python 3.11和PostgreSQL环境镜像 (1.4GB)
- `dataease-sqlbot.tar` - 完整的SQLBot应用镜像 (3.9GB)
- `sqlbot-pycharm-dev.tar` - PyCharm开发环境专用镜像 (1008MB)