# SQLBot PyCharm开发环境使用指南

## 概述

为PyCharm远程开发准备的Docker环境，特别适合内网环境使用。该环境预装了SQLBot开发所需的核心依赖包。

## 镜像构建

镜像已经构建完成并保存到项目根目录的`images`文件夹中：
```
images/sqlbot-pycharm-dev.tar
```

### 加载镜像到Docker
```bash
docker load -i images/sqlbot-pycharm-dev.tar
```

## 启动开发容器

```bash
# 启动容器并映射相关端口
docker run -d --name sqlbot-pycharm-dev -p 2222:22 -p 18000:8000 -p 13000:3000 -p 18001:8001 sqlbot-pycharm-dev:latest
```

## 容器信息

- **SSH服务端口**: 2222 (映射到容器22端口)
- **用户名**: root
- **密码**: pycharm_dev
- **Python版本**: 3.11.13
- **Node.js版本**: 18.20.8
- **工作目录**: `/workspace/sqlbot`
- **虚拟环境路径**: `/workspace/sqlbot/backend/.venv`

## PyCharm连接配置

### 1. 添加Docker服务器
- 打开PyCharm
- 进 `File` → `Settings` → `Build, Execution, Deployment` → `Docker`
- 点击 `+` 添加新的Docker服务器
- 选择 `Docker for Linux` 或相应配置

### 2. 配置远程Python解释器
- 进 `File` → `Settings` → `Project` → `Python Interpreter`
- 点击 `⚙️` → `Add...`
- 选择 `SSH Interpreter`
- 配置SSH连接:
  - Host: `localhost`
  - Port: `2222`
  - Username: `root`
  - Password: `pycharm_dev`

### 3. 配置项目路径映射
- 在解释器配置中，将本地项目路径映射到容器中的 `/workspace/sqlbot`
- 例如：本地 `/home/user/SQLBot` → 容器中 `/workspace/sqlbot`

## 容器特性

- 预装Python 3.11虚拟环境
- 包含SQLBot开发所需的核心依赖（fastapi, pydantic, sqlmodel等）
- 预配置SSH服务用于PyCharm连接
- 工作目录：`/workspace/sqlbot`
- 虚拟环境路径：`/workspace/sqlbot/backend/.venv`

## 开发工作流

1. 启动容器：`docker run -d --name sqlbot-pycharm-dev -p 2222:22 sqlbot-pycharm-dev:latest`
2. 配置PyCharm连接到容器的SSH服务
3. 在PyCharm中打开项目，路径映射到 `/workspace/sqlbot`
4. 使用容器中的Python解释器进行开发和调试

## 注意事项

- 如果SSH连接失败，可以进入容器重置密码：
  ```bash
  docker exec -it sqlbot-pycharm-dev bash
  echo 'root:pycharm_dev' | chpasswd
  ```
- 容器启动时会自动激活后端虚拟环境
- 所有Python依赖包已预安装到虚拟环境中