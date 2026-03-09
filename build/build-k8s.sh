#!/bin/bash
# K8s 构建脚本：构建镜像 → 打 tag → 可选推送 → 可选 Helm 安装/升级
# 环境变量: REGISTRY, IMAGE_NAME, IMAGE_TAG, HELM_NAMESPACE, HELM_RELEASE_NAME

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HELM_CHART_PATH="$ROOT_DIR/deploy/helm/sqlbot"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 默认值
VERSION="${VERSION:-20251130}"
BASE_IMAGE="sqlbot-dev-${VERSION}:latest"
QUICK_IMAGE="zf-sqlbot:latest"
REGISTRY="${REGISTRY:-}"
IMAGE_NAME="${IMAGE_NAME:-dataease/sqlbot}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
HELM_NAMESPACE="${HELM_NAMESPACE:-default}"
HELM_RELEASE_NAME="${HELM_RELEASE_NAME:-sqlbot}"

DO_PUSH=false
DO_HELM_INSTALL=false

usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --push           构建后打 tag 并推送到镜像仓库（需设置 REGISTRY/IMAGE_NAME/IMAGE_TAG）"
    echo "  --helm-install   构建（及推送）后执行 helm upgrade --install"
    echo "  -h, --help       显示此帮助"
    echo ""
    echo "环境变量:"
    echo "  REGISTRY            镜像仓库地址（如 registry.cn-qingdao.aliyuncs.com）"
    echo "  IMAGE_NAME          镜像名（如 dataease/sqlbot）"
    echo "  IMAGE_TAG           镜像 tag（默认 latest，可取自 git）"
    echo "  HELM_NAMESPACE      Helm 安装的命名空间（默认 default）"
    echo "  HELM_RELEASE_NAME   Helm release 名称（默认 sqlbot）"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --push)          DO_PUSH=true; shift ;;
        --helm-install)   DO_HELM_INSTALL=true; shift ;;
        -h|--help)        usage ;;
        *)               echo "未知选项: $1"; usage ;;
    esac
done

# 可选：从 git 生成 tag
if [[ -z "$IMAGE_TAG" || "$IMAGE_TAG" == "latest" ]]; then
    if command -v git &>/dev/null && [[ -d "$ROOT_DIR/.git" ]]; then
        IMAGE_TAG="$(git rev-parse --short HEAD 2>/dev/null || echo latest)"
    fi
    IMAGE_TAG="${IMAGE_TAG:-latest}"
fi

echo -e "${BLUE}🔧 SQLBot K8s 构建${NC}"
echo -e "${BLUE}===================${NC}"

# 1. 构建镜像
if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${BASE_IMAGE}$"; then
    echo -e "${GREEN}📦 使用快速构建（基础镜像已存在）${NC}"
    cd "$SCRIPT_DIR" && ./build-quick.sh
    LOCAL_IMAGE="$QUICK_IMAGE"
else
    echo -e "${GREEN}📦 使用完整构建（基础镜像不存在）${NC}"
    cd "$SCRIPT_DIR" && ./build-base.sh
    LOCAL_IMAGE="$BASE_IMAGE"
fi

# 2. 打 tag
if [[ -n "$REGISTRY" ]]; then
    FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
else
    FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
fi

echo -e "${GREEN}🏷️  标记镜像: ${LOCAL_IMAGE} -> ${FULL_IMAGE}${NC}"
docker tag "$LOCAL_IMAGE" "$FULL_IMAGE"

# 3. 推送
if [[ "$DO_PUSH" == true ]]; then
    if [[ -z "$REGISTRY" ]]; then
        echo -e "${RED}❌ --push 需要设置 REGISTRY 环境变量${NC}"
        exit 1
    fi
    echo -e "${BLUE}📤 推送镜像: ${FULL_IMAGE}${NC}"
    docker push "$FULL_IMAGE" || { echo -e "${RED}❌ 推送失败${NC}"; exit 1; }
    echo -e "${GREEN}✅ 推送完成${NC}"
fi

# 4. Helm 安装/升级
if [[ "$DO_HELM_INSTALL" == true ]]; then
    if ! command -v helm &>/dev/null; then
        echo -e "${RED}❌ 未找到 helm，请先安装 Helm 3${NC}"
        exit 1
    fi
    if [[ ! -d "$HELM_CHART_PATH" ]]; then
        echo -e "${RED}❌ Chart 路径不存在: $HELM_CHART_PATH${NC}"
        exit 1
    fi
    # Helm 中 image.repository 可含 registry，image.tag 单独
    REPO_FOR_HELM="${REGISTRY:+${REGISTRY}/}${IMAGE_NAME}"
    echo -e "${BLUE}📋 Helm upgrade --install ${HELM_RELEASE_NAME} in ${HELM_NAMESPACE} (image: ${REPO_FOR_HELM}:${IMAGE_TAG})${NC}"
    helm upgrade --install "$HELM_RELEASE_NAME" "$HELM_CHART_PATH" \
        --namespace "$HELM_NAMESPACE" \
        --set image.repository="$REPO_FOR_HELM" \
        --set image.tag="$IMAGE_TAG" \
        --create-namespace
    echo -e "${GREEN}✅ Helm 部署完成${NC}"
fi

echo -e "${GREEN}🎉 K8s 构建流程完成${NC}"
echo -e "  本地镜像: ${LOCAL_IMAGE}"
echo -e "  目标镜像: ${FULL_IMAGE}"
