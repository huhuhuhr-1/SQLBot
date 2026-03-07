# 安装与部署

本文档说明 SQLBot 的多种安装与部署方式。

## 方式一：Docker 一键运行（推荐）

适用于已安装 Docker 的环境，拉取官方镜像直接运行。

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

## 方式二：离线安装包

内网或无法访问 Docker Hub 时，可使用离线安装包。

1. 从 [社区下载页](https://community.fit2cloud.com/#/products/sqlbot/downloads) 获取离线包。
2. 解压后在目录中执行安装脚本：

```bash
cd installer
./install.sh
```

安装过程会检查环境、安装依赖并启动服务，详细配置见 `install.conf`。卸载使用同目录下的 `uninstall.sh`。

## 方式三：自建 Docker 镜像

从源码构建并运行自己的镜像，适合二次开发或定制。

1. **构建镜像**  
   使用项目内构建脚本（推荐）：

   ```bash
   cd build
   ./build.sh base    # 首次或依赖变更后
   ./build.sh quick   # 仅后端代码更新时
   ```

   或使用根目录快速构建：

   ```bash
   ./quick.sh
   ```

2. **运行容器**  
   将上述命令中的 `dataease/sqlbot` 替换为你的镜像名（如 `zf-sqlbot:latest`），其余参数可保持不变。

更多构建选项（多平台、仅 x86/ARM64）见 [build/README.md](../build/README.md)。

## 端口与数据

- **8000**：主应用（Web + API）
- **8001**：MCP 服务
- 数据与日志建议通过 `-v` 挂载到宿主机，便于备份与升级。

## 更多说明

- 英文安装说明：[docs/README.en.md](README.en.md)
- 构建与打包详解：[build/README.md](../build/README.md)
- 本地开发环境：[DEVELOPMENT.md](DEVELOPMENT.md)
