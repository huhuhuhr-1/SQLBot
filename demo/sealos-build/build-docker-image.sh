# 首先构建当前的 Docker 镜像
docker build -t sqlbot:latest .

# 如果您需要推送到镜像仓库
# docker tag sqlbot:latest your-registry/sqlbot:latest
# docker push your-registry/sqlbot:latest