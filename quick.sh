#!/bin/bash

# Get the current date in the format YYYYMMDD
VERSION=$(date +%Y%m%d)

echo "🚀 快速构建 SQLBot..."

export DOCKER_BUILDKIT=1

WITH_VECTOR=true
BUILDER_BASE=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest
SSR_BASE=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest
RUNTIME_BASE=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-python-pg:latest

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--no-vector)
      WITH_VECTOR=false
      shift
      ;;
    -p|--no-pg|--lite)
      BUILDER_BASE=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base-lite:latest
      SSR_BASE=$BUILDER_BASE
      RUNTIME_BASE=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-python-lite:latest
      shift
      ;;
    --builder-base)
      BUILDER_BASE="$2"
      shift 2
      ;;
    --ssr-base)
      SSR_BASE="$2"
      shift 2
      ;;
    --runtime-base)
      RUNTIME_BASE="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "未知参数: $1" >&2
      exit 1
      ;;
  esac
done

docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --progress=plain \
  --build-arg INCLUDE_VECTOR=$WITH_VECTOR \
  --build-arg BUILDER_BASE=$BUILDER_BASE \
  --build-arg SSR_BASE=$SSR_BASE \
  --build-arg RUNTIME_BASE=$RUNTIME_BASE \
  -t zf-sqlbot:v1.2.0.$VERSION .

echo "✅ 完成！"
