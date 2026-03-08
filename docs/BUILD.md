# SQLBot 构建指南

本文档详细说明 SQLBot 的 Docker 镜像构建方式、各脚本用途及使用场景。

---

## 一、构建产物总览

### 1.1 镜像类型

| 产物类型 | 镜像名称 | 架构 | 用途 |
|---------|---------|------|------|
| **基础镜像** | `sqlbot-dev-20251130:latest` | x86_64 | 包含完整依赖环境，作为快速构建的基础 |
| **基础镜像** | `sqlbot-dev-20251130:arm64` | ARM64 | ARM64 架构的基础镜像 |
| **最终镜像** | `zf-sqlbot:latest` | x86_64 | 可直接运行的应用镜像 |
| **最终镜像** | `zf-sqlbot:arm64` | ARM64 | ARM64 架构的可运行应用镜像 |

### 1.2 两阶段构建设计

```
┌─────────────────────────────────────────────────────────────┐
│  阶段一：完整构建（基础镜像）                                 │
│  docker build -t sqlbot-dev-20251130:latest .              │
│  包含：系统依赖、Python 环境 (uv)、前端构建、g2-ssr、向量模型    │
│  耗时：30-60 分钟                                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  基础镜像就绪  │
              └───────┬───────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段二：快速构建（最终镜像）                                 │
│  docker build -f Dockerfile.update -t zf-sqlbot:latest .   │
│  仅覆盖 backend 代码，复用所有依赖                             │
│  耗时：1-2 分钟                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、构建脚本详解

### 2.1 脚本总览

所有构建脚本位于 `build/` 目录：

| 脚本 | 说明 | 产物 |
|------|------|------|
| `build.sh` | 统一入口（调度脚本） | - |
| `build-base.sh` | 构建基础镜像 | `sqlbot-dev-20251130:latest` |
| `build-quick.sh` | 快速构建（仅 backend） | `zf-sqlbot:latest` |
| `build-quick-x86.sh` | x86 平台快速构建 | `zf-sqlbot:latest` |
| `build-quick-arm64.sh` | ARM64 平台快速构建 | `zf-sqlbot:arm64` |
| `build-multiplatform.sh` | 多平台基础镜像 | x86 + ARM64 |
| `build-multiplatform-optimized.sh` | 多平台构建（缓存优化） | x86 + ARM64 |

根目录另有一个独立脚本：

| 脚本 | 说明 | 产物 |
|------|------|------|
| `quick.sh` | 一键完整构建（不区分阶段） | `zf-sqlbot:latest` |

### 2.2 脚本关系图

```
项目根目录
├── quick.sh ──────────────────────────────────────────────┐
│    │                                                     │
│    └─> 直接执行完整构建 (docker build .)                 │
│         特点：一键式，不区分基础/快速，适合快速试跑        │
│                                                         │
└── build/ ───────────────────────────────────────────────┘
     ├── build.sh (统一入口)
     │    ├── base ──────────────> build-base.sh
     │    ├── quick ─────────────> build-quick.sh
     │    ├── quick-x86 ─────────> build-quick-x86.sh
     │    ├── quick-arm64 ───────> build-quick-arm64.sh
     │    ├── multiplatform ─────> build-multiplatform.sh
     │    └── multiplatform-optimized -> build-multiplatform-optimized.sh
     │
     ├── build-base.sh ──> 构建基础镜像 sqlbot-dev-VERSION:latest
     ├── build-quick.sh ─> 基于基础镜像快速构建 zf-sqlbot:latest
     └── Dockerfile.update ──> 快速构建使用的 Dockerfile
```

### 2.3 quick.sh 与 build/quick 的区别

| 特性 | `quick.sh` | `build/build.sh quick` |
|------|-----------|------------------------|
| **构建方式** | 完整构建（从 0 开始） | 增量构建（基于基础镜像） |
| **Dockerfile** | 根目录 `Dockerfile` | `build/Dockerfile.update` |
| **耗时** | 30-60 分钟 | 1-2 分钟 |
| **适用场景** | 首次尝试、依赖/前端变更 | 日常后端开发 |
| **产物** | `zf-sqlbot:latest` | `zf-sqlbot:latest` |

**核心区别**：
- `quick.sh` = 每次都重新完整构建（类似 `build-base.sh`，但最终镜像命名为 `zf-sqlbot`）
- `build/build.sh quick` = 复用已构建的基础镜像，只更新代码层

---

## 三、使用方法

### 3.1 推荐：使用统一入口

```bash
cd build
./build.sh <目标>
```

**目标参数：**

| 参数 | 说明 |
|------|------|
| `base` | 执行 `build-base.sh` - 构建基础镜像 |
| `quick` | 执行 `build-quick.sh` - 快速构建 |
| `quick-x86` | 执行 `build-quick-x86.sh` - x86 平台快速构建 |
| `quick-arm64` | 执行 `build-quick-arm64.sh` - ARM64 平台快速构建 |
| `multiplatform` | 执行 `build-multiplatform.sh` - 多平台基础镜像 |
| `multiplatform-optimized` | 执行 `build-multiplatform-optimized.sh` - 优化版多平台构建 |
| 不传参数 | 打印用法说明 |

### 3.2 场景化使用指南

| 你的场景 | 推荐命令 |
|---------|---------|
| 第一次构建，想看看能不能成功 | `./quick.sh` |
| 首次构建基础镜像 | `cd build && ./build.sh base` |
| 改了 Python 依赖 (`uv.lock`) | `cd build && ./build.sh base` |
| 改了前端代码 | `cd build && ./build.sh base` |
| 只改了后端 Python 代码 | `cd build && ./build.sh quick` |
| 在 M 系列 Mac 上开发 | `cd build && ./build.sh quick-arm64` |
| 需要同时发布 x86 和 ARM | `cd build && ./build.sh multiplatform` |

### 3.3 直接调用具体脚本

**首次或依赖/前端变更后：**
```bash
cd build
./build-base.sh
```

**仅后端代码更新：**
```bash
cd build
./build-quick.sh
```

**根目录一键快速构建：**
```bash
./quick.sh
```

### 3.4 手动构建示例

```bash
# 基础镜像（使用根目录 Dockerfile）
docker build -t sqlbot-dev-20251130:latest .

# 快速构建（仅 backend，基于基础镜像）
docker build -f build/Dockerfile.update -t zf-sqlbot:latest .
```

---

## 四、多平台构建

### 4.1 多平台脚本对比

| 脚本 | 特点 |
|------|------|
| `build-multiplatform.sh` | 标准多平台构建，生成 x86 + ARM64 基础镜像 |
| `build-multiplatform-optimized.sh` | 增加本地缓存优化，重复构建时更快 |

### 4.2 多平台构建流程

```bash
cd build
./build.sh multiplatform
```

执行后会：
1. 检查并创建 `docker buildx` 构建器
2. 分别构建 `linux/amd64` 和 `linux/arm64` 基础镜像
3. 自动创建/更新平台特定的快速构建脚本
4. 提示下一步使用 `./build-quick-x86.sh` 或 `./build-quick-arm64.sh`

### 4.3 产物说明

- **基础镜像**：
  - `sqlbot-dev-20251130:latest`（x86_64）
  - `sqlbot-dev-20251130:arm64`（ARM64）

- **最终镜像**：
  - `zf-sqlbot:latest`（x86_64）
  - `zf-sqlbot:arm64`（ARM64）

---

## 五、Dockerfile 说明

### 5.1 根目录 Dockerfile

完整构建用，包含多个构建阶段：

1. **vector-model** - 拉取向量模型
2. **sqlbot-ui-builder** - 构建前端
3. **sqlbot-builder** - 构建 Python 后端
4. **ssr-builder** - 构建 G2-SSR 图表渲染服务
5. **Runtime stage** - 运行阶段，整合所有组件

### 5.2 build/Dockerfile.update

快速构建用，仅复制 backend 代码：

```dockerfile
FROM sqlbot-dev-20251130:latest
COPY ./backend ${APP_HOME}
RUN uv sync --extra cpu
```

- x86 平台直接使用
- ARM64 平台由 `build-quick-arm64.sh` 通过 `sed` 动态替换 `FROM` 指令

---

## 六、运行构建产物

### 6.1 启动容器

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
  zf-sqlbot:latest
```

### 6.2 端口说明

| 端口 | 服务 |
|------|------|
| 8000 | 主应用（Web + API） |
| 8001 | MCP 服务 |
| 5432 | 内嵌 PostgreSQL |
| 5678 | debugpy 调试（仅 `SQLBOT_DEBUG=1` 时） |

### 6.3 调试模式

```bash
docker run -d \
  -e SQLBOT_DEBUG=1 \
  -p 5678:5678 \
  ... \
  zf-sqlbot:latest
```

IDE 使用远程附加连接到 `localhost:5678` 进行调试。

---

## 七、注意事项

1. **基础镜像构建耗时较长**（约 30-60 分钟），建议在网络良好的环境下执行
2. **快速构建约 1-2 分钟**，适合日常开发迭代
3. **更新 Python 依赖或前端后**，需重新执行 `build-base.sh`
4. **多平台脚本依赖 `docker buildx`**，未安装时需先安装对应插件
5. **BuildKit** 已默认启用，用于支持 `--platform` 参数和构建缓存

---

## 八、相关文件

- [build/README.md](../build/README.md) - build 目录说明
- [GUIDE.md](GUIDE.md) - 完整指南
- [DEBUG.md](DEBUG.md) - 调试指南
- [../README.md](../README.md) - 项目主文档
