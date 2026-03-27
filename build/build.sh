#!/bin/bash
# SQLBot 构建统一入口：根据参数调度对应构建脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
    echo "用法: $0 <目标>"
    echo ""
    echo "目标:"
    echo "  base                  构建基础镜像 (build-base.sh)"
    echo "  quick                 快速构建/仅 backend (build-quick.sh)"
    echo "  quick-x86             x86 快速构建 (build-quick-x86.sh)"
    echo "  quick-arm64           ARM64 快速构建 (build-quick-arm64.sh)"
    echo "  multiplatform         多平台基础镜像 (build-multiplatform.sh)"
    echo "  multiplatform-optimized  多平台构建-优化版 (build-multiplatform-optimized.sh)"
    echo "  k8s                   K8s 构建 (build-k8s.sh)，支持 --push --helm-install"
    echo ""
    echo "示例: $0 quick"
    echo "      $0 k8s --push --helm-install"
    exit 0
}

case "${1:-}" in
    base)                   ./build-base.sh ;;
    quick)                   ./build-quick.sh ;;
    quick-x86)               ./build-quick-x86.sh ;;
    quick-arm64)             ./build-quick-arm64.sh ;;
    multiplatform)           ./build-multiplatform.sh ;;
    multiplatform-optimized) ./build-multiplatform-optimized.sh ;;
    k8s)                     shift; ./build-k8s.sh "$@" ;;
    -h|--help|"")            usage ;;
    *)                      echo "未知目标: $1"; usage ;;
esac
