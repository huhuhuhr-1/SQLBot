#!/bin/bash

# 生成带日期的版本号（格式：YYYYMMDD）
VERSION=$(date +%Y%m%d)
IMAGE_NAME="zf-sqlbot:v1.1.2.${VERSION}"
#IMAGE_NAME="zf-sqlbot:v1.1.2.20250930"

echo "🚀 开始构建 SQLBot，版本号：${IMAGE_NAME}"

# 检查并创建Buildx构建实例（仅首次执行）
if ! docker buildx inspect sqlbot-builder >/dev/null 2>&1; then
    echo "🔧 初始化Buildx并行构建环境..."
    docker buildx create --name sqlbot-builder --use
fi

# 启用BuildKit加速构建
export DOCKER_BUILDKIT=1

# 使用Buildx进行国内加速构建
docker buildx build \
    # 基础镜像拉取加速（国内稳定源）
    --registry-mirror=https://registry.cn-hangzhou.aliyuncs.com \
    --registry-mirror=https://docker.mirrors.ustc.edu.cn \
    # 前端npm国内源
    --build-arg NPM_REGISTRY=https://registry.npmmirror.com \
    # 后端Python国内源
    --build-arg UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    # 镜像标签（包含日期版本号）
    -t ${IMAGE_NAME} \
    # 显示详细构建进度
    --progress=plain \
    # 构建后加载到本地Docker
    --load \
    # 构建上下文
    .

# 构建结果检查
if [ $? -eq 0 ]; then
    echo -e "\n✅ 构建成功！镜像名称：${IMAGE_NAME}"
    echo -e "📌 启动命令示例：docker run -p 8000:8000 ${IMAGE_NAME}"
else
    echo -e "\n❌ 构建失败！请查看上方错误日志排查问题"
    exit 1
fi
