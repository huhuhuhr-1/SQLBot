# 基于现有镜像进行二次开发
FROM dataease/sqlbot:v1.0.0

# 设置运行时环境变量（添加构建优化）
ENV PYTHONUNBUFFERED=1
ENV SQLBOT_HOME=/opt/sqlbot
ENV PYTHONPATH=${SQLBOT_HOME}/app
ENV PATH="${SQLBOT_HOME}/app/.venv/bin:$PATH"
# 添加优化设置
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# 设置工作目录
WORKDIR ${SQLBOT_HOME}/app

# 复制新增依赖文件
COPY build/requirements-extra.txt ./
# 使用 uv pip 安装新增依赖
RUN uv pip install --no-cache-dir -r requirements-extra.txt

# 强制覆盖目标目录的所有内容
COPY backend/ ./
# 确保启动脚本有执行权限
RUN chmod +x start.sh

# 同步最终依赖并创建必要目录
RUN uv sync && \
    mkdir -p /opt/sqlbot/images /opt/sqlbot/g2-ssr

# 如果需要更新字体文件
# COPY g2-ssr/*.ttf /usr/share/fonts/truetype/liberation/

# 暴露端口
EXPOSE 3000 8000 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 设置启动命令
ENTRYPOINT ["sh", "start.sh"]
