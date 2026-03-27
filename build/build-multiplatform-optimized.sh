#!/bin/bash

# 多平台构建优化版：强制使用本地镜像缓存
# 基于 Dockerfile 构建，生成不同架构的基础镜像供 Dockerfile.update 使用

VERSION="20251130"
X86_IMAGE="sqlbot-dev-${VERSION}:latest"
ARM_IMAGE="sqlbot-dev-${VERSION}:arm64"
PLATFORMS="linux/amd64,linux/arm64"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏗️  SQLBot 多平台基础镜像构建 (优化版)${NC}"
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}📋 构建目标：${NC}"
echo -e "  x86_64: ${YELLOW}${X86_IMAGE}${NC}"
echo -e "  ARM64:  ${YELLOW}${ARM_IMAGE}${NC}"
echo

# 检查 Docker BuildKit
if ! docker buildx version >/dev/null 2>&1; then
    echo -e "${RED}❌ 需要安装 docker buildx 支持多平台构建${NC}"
    echo -e "${YELLOW}请安装: apt-get install docker-buildx-plugin${NC}"
    exit 1
fi

# 创建并使用 buildx builder
BUILDER_NAME="sqlbot-multiarch"
if ! docker buildx ls | grep -q "$BUILDER_NAME"; then
    echo -e "${BLUE}🔧 创建多平台构建器...${NC}"
    docker buildx create --name $BUILDER_NAME --driver docker-container --bootstrap
fi

echo -e "${BLUE}🔧 使用构建器: ${BUILDER_NAME}${NC}"
docker buildx use $BUILDER_NAME

# 检查本地关键镜像
echo -e "${BLUE}📋 检查本地关键镜像...${NC}"

VECTOR_MODEL_LOCAL=false
SQLBOT_BASE_LOCAL=false
SQLBOT_PG_LOCAL=false

if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "ghcr.io/1panel-dev/maxkb-vector-model:v1.0.1"; then
    VECTOR_MODEL_LOCAL=true
    echo -e "${GREEN}✅ 找到本地 vector-model 镜像${NC}"
else
    echo -e "${RED}❌ 缺少 vector-model 镜像${NC}"
fi

if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest"; then
    SQLBOT_BASE_LOCAL=true
    echo -e "${GREEN}✅ 找到本地 sqlbot-base 镜像${NC}"
else
    echo -e "${RED}❌ 缺少 sqlbot-base 镜像${NC}"
fi

if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-python-pg:latest"; then
    SQLBOT_PG_LOCAL=true
    echo -e "${GREEN}✅ 找到本地 sqlbot-python-pg 镜像${NC}"
else
    echo -e "${RED}❌ 缺少 sqlbot-python-pg 镜像${NC}"
fi

echo

# 检查现有目标镜像
echo -e "${BLUE}📋 检查现有目标镜像...${NC}"
X86_EXISTS=false
ARM_EXISTS=false

if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${X86_IMAGE}$"; then
    X86_EXISTS=true
    echo -e "${YELLOW}⚠️  x86 镜像 ${X86_IMAGE} 已存在${NC}"
fi

if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${ARM_IMAGE}$"; then
    ARM_EXISTS=true
    echo -e "${YELLOW}⚠️  ARM 镜像 ${ARM_IMAGE} 已存在${NC}"
fi

# 询问是否重建
if [ "$X86_EXISTS" = true ] || [ "$ARM_EXISTS" = true ]; then
    echo
    read -p "是否重建已存在的镜像？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}✅ 跳过现有镜像的构建${NC}"

        # 设置构建标志
        BUILD_X86=false
        BUILD_ARM=false

        if [ "$X86_EXISTS" = false ]; then
            BUILD_X86=true
        fi
        if [ "$ARM_EXISTS" = false ]; then
            BUILD_ARM=true
        fi
    else
        BUILD_X86=true
        BUILD_ARM=true
    fi
else
    BUILD_X86=true
    BUILD_ARM=true
fi

echo
echo -e "${GREEN}🔨 构建计划：${NC}"
[ "$BUILD_X86" = true ] && echo -e "  ✅ x86_64 (${X86_IMAGE})"
[ "$BUILD_ARM" = true ] && echo -e "  ✅ ARM64 (${ARM_IMAGE})"
echo

# 启用 BuildKit
export DOCKER_BUILDKIT=1

# 回到项目根目录（从build/目录）
cd ..

# 构建 x86_64 镜像
if [ "$BUILD_X86" = true ]; then
    echo -e "${BLUE}🔨 构建 x86_64 基础镜像...${NC}"
    echo -e "${GREEN}💡 使用本地镜像缓存加速构建${NC}"

    docker buildx build \
        --platform linux/amd64 \
        --load \
        -t ${X86_IMAGE} \
        --cache-from type=local,src=/tmp/.buildx-cache \
        --cache-to type=local,dest=/tmp/.buildx-cache \
        . || {
        echo -e "${RED}❌ x86_64 镜像构建失败${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ x86_64 基础镜像构建完成${NC}"
fi

# 构建 ARM64 镜像
if [ "$BUILD_ARM" = true ]; then
    echo -e "${BLUE}🔨 构建 ARM64 基础镜像...${NC}"
    echo -e "${GREEN}💡 使用本地镜像缓存加速构建${NC}"

    docker buildx build \
        --platform linux/arm64 \
        --load \
        -t ${ARM_IMAGE} \
        --cache-from type=local,src=/tmp/.buildx-cache \
        --cache-to type=local,dest=/tmp/.buildx-cache \
        . || {
        echo -e "${RED}❌ ARM64 镜像构建失败${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ ARM64 基础镜像构建完成${NC}"
fi

echo
echo -e "${GREEN}🎉 多平台基础镜像构建完成！${NC}"
echo

# 显示镜像信息
echo -e "${GREEN}📊 镜像信息：${NC}"
echo
if docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep -E "(REPOSITORY|${X86_IMAGE}|${ARM_IMAGE})"; then
    echo
else
    echo -e "${YELLOW}未找到构建的镜像${NC}"
fi

echo -e "${GREEN}💡 使用说明：${NC}"
echo -e "  x86_64: 基础镜像 ${YELLOW}${X86_IMAGE}${NC}"
echo -e "  ARM64:  基础镜像 ${YELLOW}${ARM_IMAGE}${NC}"
echo
echo -e "${GREEN}📝 下一步操作：${NC}"
echo -e "  1. 修改 ${YELLOW}build/Dockerfile.update${NC} 中的 FROM 指令"
echo -e "  2. x86_64: FROM ${X86_IMAGE}"
echo -e "  3. ARM64:  FROM ${ARM_IMAGE}"
echo -e "  4. 运行 ${YELLOW}./build-quick.sh${NC} 构建最终镜像"

# 快速构建脚本统一使用 build/Dockerfile.update（x86 直接用，arm64 用 sed 替换 FROM）
echo -e "${GREEN}✅ 使用统一 Dockerfile.update，无需生成 .x86/.arm64 文件${NC}"

chmod +x build/build-quick-x86.sh build/build-quick-arm64.sh 2>/dev/null || true
echo -e "  ${YELLOW}build/build-quick-x86.sh${NC}  使用 build/Dockerfile.update"
echo -e "  ${YELLOW}build/build-quick-arm64.sh${NC} 由 Dockerfile.update 动态替换 FROM"

echo
echo -e "${GREEN}🎯 多平台构建环境已准备就绪！${NC}"