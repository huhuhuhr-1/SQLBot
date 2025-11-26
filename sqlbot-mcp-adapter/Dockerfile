# 使用 SQLBot 基础镜像
FROM registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 设置工作目录
WORKDIR /app

# 从 pyproject.toml 安装依赖 (使用 pip)
RUN pip install "fastapi[standard]>=0.115.12" \
    "python-multipart>=0.0.7" \
    "pydantic>2.0" \
    "alembic>=1.12.1,<2.0.0" \
    "httpx>=0.25.1,<1.0.0" \
    "sqlmodel>=0.0.21,<1.0.0" \
    "pydantic-settings>=2.2.1,<3.0.0" \
    "pyjwt>=2.8.0,<3.0.0" \
    "python-dotenv>=1.0.0" \
    "uvicorn[standard]>=0.24.0" \
    "fastapi-mcp>=0.4.0"

# 复制源代码
COPY main.py ./
COPY config.py ./
COPY sqlbot_client.py ./
COPY docker-entrypoint.sh ./

# 设置启动脚本权限
RUN chmod +x docker-entrypoint.sh

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 设置入口点
ENTRYPOINT ["./docker-entrypoint.sh"]