#!/bin/bash

# 快速构建：基于基础镜像只更新backend代码

VERSION="20251130"
BASE_IMAGE="sqlbot-dev-${VERSION}:latest"
FINAL_IMAGE="zf-sqlbot:latest"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}⚡ SQLBot 快速构建${NC}"
echo -e "${BLUE}===================${NC}"

echo -e "${GREEN}📋 构建信息：${NC}"
echo -e "  基础镜像: ${YELLOW}${BASE_IMAGE}${NC}"
echo -e "  最终镜像: ${YELLOW}${FINAL_IMAGE}${NC}"
echo -e "  更新内容: ${YELLOW}backend代码覆盖${NC}"
echo

# 检查基础镜像是否存在
if ! docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "${BASE_IMAGE}"; then
    echo -e "${RED}❌ 基础镜像 ${BASE_IMAGE} 不存在${NC}"
    echo -e "${YELLOW}请先运行: ./build-base.sh 构建基础镜像${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 找到基础镜像: ${BASE_IMAGE}${NC}"

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

echo -e "${BLUE}🔨 开始快速构建...${NC}"

# 回到项目根目录（从build/目录）
cd ..

# 复制.dockerignore到根目录供构建使用
cp build/.dockerignore . 2>/dev/null || echo "Using root .dockerignore"

# 验证 .dockerignore 文件存在且包含正确的排除规则
if [ -f .dockerignore ]; then
    echo -e "${GREEN}✅ 使用 .dockerignore 排除不必要的文件${NC}"
    echo -e "   排除内容：$(grep -E '\.venv|__pycache__|\.git' .dockerignore | tr '\n' ' ')"
else
    echo -e "${YELLOW}⚠️  警告：未找到 .dockerignore 文件${NC}"
fi

# 构建最终镜像
$BUILD_CMD -f build/Dockerfile.update -t ${FINAL_IMAGE} . || {
    echo -e "${RED}❌ 快速构建失败${NC}"
    exit 1
}

# 清理临时文件
rm -f .dockerignore

echo -e "${GREEN}🎉 快速构建完成！${NC}"
echo
echo -e "${GREEN}📊 镜像信息：${NC}"
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep -E "(REPOSITORY|${FINAL_IMAGE})"

echo
echo -e "${GREEN}💡 提示：${NC}"
echo -e "  离线环境：只支持backend代码更新"
echo -e "  Python依赖变更：需有网络环境，运行 ${YELLOW}./build-base.sh${NC}"
echo -e "  前端变更：需有网络环境，运行 ${YELLOW}./build-base.sh${NC}"