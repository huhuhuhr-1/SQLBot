# SQLBot 优化构建方案

## 构建思路

这个构建方案解决了离线环境包构建困难的问题：

### 阶段1：完整构建（依赖+代码）
- **使用**: 根目录的原始`Dockerfile`
- **目标镜像**: `sqlbot-dev-20251130:latest`
- **包含内容**:
  - 所有系统依赖、Python环境（uv sync）
  - 前端构建结果（npm build）
  - 数据库驱动和模型文件
  - g2-ssr服务
  - 完整的backend代码

### 阶段2：快速构建（仅代码更新）
- **目标镜像**: `zf-sqlbot:latest`
- **基础镜像**: `sqlbot-dev-20251130:latest`
- **操作**: 只覆盖backend代码，复用所有依赖
- **优势**: 构建速度极快（1-2分钟），适合频繁开发

## 文件说明

- `build-base.sh`: 基础镜像构建脚本，使用根目录Dockerfile
- `build-quick.sh`: 快速构建脚本，基于基础镜像只更新backend代码
- `Dockerfile.update`: 快速构建用的Dockerfile，只覆盖backend代码

## 使用方法

### 首次构建或依赖更新时：
```bash
cd build
./build-base.sh
```

### 后续backend代码更新时：
```bash
cd build
./build-quick.sh
```

### 手动构建：
```bash
# 构建基础镜像（使用根目录Dockerfile）
cd .. && docker build -t sqlbot-dev-20251130:latest .

# 快速构建（仅backend代码）
docker build -t zf-sqlbot:latest -f build/Dockerfile.update .
```

## 优势

1. **构建效率高**: 后续更新只需复制backend代码，无需重新安装依赖
2. **离线友好**: 基础镜像包含所有依赖，离线环境只需要代码覆盖
3. **版本管理**: 基础镜像带有版本号，便于管理和回滚
4. **灵活性强**: 可以选择性构建，节省时间

## 镜像大小说明

- 基础镜像：~2-3GB（包含所有依赖）
- 最终镜像：与基础镜像相当（主要是代码层的覆盖）

## 注意事项

- 基础镜像构建需要较长的时间（30-60分钟）
- 快速构建通常只需要1-2分钟
- 如需更新uv依赖或前端，必须重新构建基础镜像