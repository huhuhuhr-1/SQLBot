FROM alpine:latest
LABEL version="1.0"
LABEL description="Simple demo app for Sealos"

# 安装必要工具
RUN apk add --no-cache \
    curl \
    bash \
    && rm -rf /var/cache/apk/*

# 创建一个简单的应用
RUN mkdir -p /app
WORKDIR /app

# 创建一个简单的脚本
RUN echo '#!/bin/bash\nwhile true; do echo "Sealos Demo App Running..."; sleep 30; done' > /app/app.sh
RUN chmod +x /app/app.sh

CMD ["/app/app.sh"]