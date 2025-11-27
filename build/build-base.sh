#!/bin/bash

# 构建基础镜像：基于现有Dockerfile
# 构建完成后标记为 sqlbot-dev-20251130:latest

VERSION="20251130"
BASE_IMAGE="sqlbot-dev-${VERSION}:latest"
TEMP_TAG="temp-sqlbot-build:latest"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏗️  构建SQLBot基础镜像${NC}"
echo -e "${BLUE}===========================${NC}"

# 启用 BuildKit
export DOCKER_BUILDKIT=1

# 选择构建工具
if docker buildx version >/dev/null 2>&1; then
    BUILD_TOOL="buildx"
    BUILD_CMD="docker buildx build --load"
else
    BUILD_TOOL="docker"
    BUILD_CMD="docker build"
fi

echo -e "${GREEN}📋 构建信息：${NC}"
echo -e "  使用现有: ${YELLOW}Dockerfile${NC}"
echo -e "  构建工具: ${YELLOW}${BUILD_TOOL}${NC}"
echo -e "  目标镜像: ${YELLOW}${BASE_IMAGE}${NC}"
echo

# 检查是否存在基础镜像
if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "${BASE_IMAGE}"; then
    echo -e "${YELLOW}⚠️  基础镜像 ${BASE_IMAGE} 已存在${NC}"
    read -p "是否重建？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}✅ 跳过构建${NC}"
        exit 0
    fi
fi

echo -e "${BLUE}🔨 开始构建...${NC}"

# 回到项目根目录（从build/目录）
cd ..

# 使用现有的Dockerfile构建
$BUILD_CMD -t ${TEMP_TAG} . || {
    echo -e "${RED}❌ 构建失败${NC}"
    exit 1
}

# 重新打标签为目标版本
docker tag ${TEMP_TAG} ${BASE_IMAGE}
docker rmi ${TEMP_TAG} 2>/dev/null || true

echo -e "${GREEN}✅ 基础镜像构建完成${NC}"
echo
echo -e "${GREEN}📊 镜像信息：${NC}"
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep -E "(REPOSITORY|${BASE_IMAGE})"

echo
echo -e "${GREEN}💡 提示：${NC}"
echo -e "  现在可以使用快速构建: ${YELLOW}./build-quick.sh${NC}"
echo -e "  基础镜像包含完整的依赖环境，适合离线使用"