# SQLBot 构建与打包

本目录包含 Docker 镜像构建与多平台打包脚本，用于本地开发、离线部署及 CI 使用。

## 构建思路

- **阶段一：完整构建（依赖 + 代码）**  
  使用项目根目录的 `Dockerfile`，生成包含系统依赖、Python 环境、前端构建、数据库驱动等的基础镜像。  
  适合：首次构建、依赖或前端变更后。

- **阶段二：快速构建（仅代码更新）**  
  基于阶段一的基础镜像，仅覆盖 backend 代码，复用所有依赖。  
  适合：日常开发、仅改后端代码时，构建耗时约 1–2 分钟。

## 脚本一览

| 脚本 | 说明 | 使用场景 |
|------|------|----------|
| `build-base.sh` | 构建基础镜像（根目录 Dockerfile） | 首次构建或依赖/前端变更 |
| `build-quick.sh` | 快速构建（仅覆盖 backend） | 日常后端代码更新 |
| `build-quick-x86.sh` | 仅 x86 快速构建 | 本机 x86 开发 |
| `build-quick-arm64.sh` | 仅 ARM64 快速构建 | 本机 ARM64 开发 |
| `build-multiplatform.sh` | 多平台基础镜像（x86 + arm64） | 需同时产出多架构镜像 |
| `build-multiplatform-optimized.sh` | 多平台构建（优化缓存） | 多架构 + 利用本地缓存 |

根目录的 `quick.sh` 为单脚本一键构建当前平台最终镜像（不区分基础/快速，适合快速试跑）。

## 使用方法

### 推荐：使用统一入口

```bash
cd build
./build.sh [目标]
```

**目标**（可选）：

- `base` — 执行 `build-base.sh`
- `quick` — 执行 `build-quick.sh`
- `quick-x86` — 执行 `build-quick-x86.sh`
- `quick-arm64` — 执行 `build-quick-arm64.sh`
- `multiplatform` — 执行 `build-multiplatform.sh`
- `multiplatform-optimized` — 执行 `build-multiplatform-optimized.sh`
- 不传参数 — 打印上述用法说明

### 直接调用具体脚本

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

**仅构建当前平台（根目录）：**

```bash
./quick.sh
```

### 手动构建示例

```bash
# 基础镜像（使用根目录 Dockerfile）
docker build -t sqlbot-dev-20251130:latest .

# 快速构建（仅 backend）
docker build -t zf-sqlbot:latest -f build/Dockerfile.update .
```

## 镜像与文件说明

- **基础镜像**：`sqlbot-dev-20251130:latest`（x86）、`sqlbot-dev-20251130:arm64`（ARM64）
- **快速构建产出**：`zf-sqlbot:latest`（x86）、`zf-sqlbot:arm64`（ARM64）
- 根目录 **Dockerfile**：完整构建用（build-base 使用）。
- **build/Dockerfile.update**：快速构建用，仅复制 backend；x86 直接使用，arm64 由脚本内 `sed` 替换 `FROM` 后使用，不再维护单独的 `.x86`/`.arm64` 文件。

## 注意事项

- 基础镜像构建耗时较长（约 30–60 分钟），快速构建约 1–2 分钟。
- 更新 Python 依赖或前端后，需重新执行 `build-base.sh`（或对应多平台脚本）。
- 多平台脚本依赖 `docker buildx`，未安装时需先安装对应插件。

更多安装与部署说明见项目根目录 [README.md](../README.md) 与 [docs/GUIDE.md](../docs/GUIDE.md)。
