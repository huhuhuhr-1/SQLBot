# Build sqlbot
FROM ghcr.io/1panel-dev/maxkb-vector-model:v1.0.1 AS vector-model

FROM registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest AS sqlbot-builder

# Set build environment variables
ENV PYTHONUNBUFFERED=1
ENV SQLBOT_HOME=/opt/sqlbot
ENV APP_HOME=${SQLBOT_HOME}/app
ENV UI_HOME=${SQLBOT_HOME}/frontend
ENV PYTHONPATH=${SQLBOT_HOME}/app
ENV PATH="${APP_HOME}/.venv/bin:$PATH"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV DEBIAN_FRONTEND=noninteractive

# Create necessary directories
RUN mkdir -p ${APP_HOME} ${UI_HOME}
WORKDIR ${APP_HOME}

COPY frontend /tmp/frontend
RUN cd /tmp/frontend && npm install && npm run build && mv dist ${UI_HOME}/dist

# Install dependencies (keeps original semantics; buildkit mounts respected when using docker buildx/buildkit)
RUN test -f "./uv.lock" && \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project || echo "uv.lock file not found, skipping intermediate-layers"

COPY ./backend ${APP_HOME}

# Final sync to ensure all dependencies are installed
RUN --mount=type=cache,target=/root/.cache/uv \
   uv sync --extra cpu


# Build g2-ssr
FROM registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest AS ssr-builder
WORKDIR /app
COPY g2-ssr/app.js g2-ssr/package.json /app/
COPY g2-ssr/charts/* /app/charts/
RUN npm install


# Runtime stage (基于预构建的开发基础镜像)
FROM sqlbot-base-dev:latest

# 可通过 --build-arg 调整默认 SSH 端口（容器内配置），运行时你可以把宿主端口映射到它。
ARG SSH_PORT=22
ENV SSH_PORT=${SSH_PORT}
ENV PYTHONUNBUFFERED=1
ENV SQLBOT_HOME=/opt/sqlbot
ENV PYTHONPATH=${SQLBOT_HOME}/app
ENV PATH="${SQLBOT_HOME}/app/.venv/bin:$PATH"

# Copy necessary files from builder
COPY build/dev/start.sh /opt/sqlbot/app/start.sh
COPY g2-ssr/*.ttf /usr/share/fonts/truetype/liberation/
COPY --from=sqlbot-builder ${SQLBOT_HOME} ${SQLBOT_HOME}
COPY --from=ssr-builder /app /opt/sqlbot/g2-ssr
COPY --from=vector-model /opt/maxkb/app/model /opt/sqlbot/models

WORKDIR ${SQLBOT_HOME}/app

# Ensure directories exist
RUN mkdir -p /opt/sqlbot/images /opt/sqlbot/g2-ssr /opt/sqlbot/frontend/dist

# Create SSH runtime dir
RUN mkdir -p /var/run/sshd

# Create sqlbot user and set password (username/password 都是 sqlbot)
RUN useradd -m -s /bin/bash sqlbot \
 && echo 'sqlbot:sqlbot' | chpasswd \
 && usermod -aG sudo sqlbot \
 && echo "sqlbot ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Configure sshd (set port via ARG SSH_PORT at build time)
RUN sed -i "s/#Port 22/Port ${SSH_PORT}/g" /etc/ssh/sshd_config || true \
 && sed -i "s/#PasswordAuthentication yes/PasswordAuthentication yes/g" /etc/ssh/sshd_config || true \
 && sed -i "s/#PermitRootLogin prohibit-password/PermitRootLogin no/g" /etc/ssh/sshd_config || true \
 && echo "ClientAliveInterval 60" >> /etc/ssh/sshd_config \
 && echo "ClientAliveCountMax 5" >> /etc/ssh/sshd_config

# Ensure directories exist and set permissions for sqlbot user
RUN mkdir -p /opt/sqlbot/data/file /opt/sqlbot/data/excel /opt/sqlbot/models /opt/sqlbot/app/logs \
    && chown -R sqlbot:sqlbot /opt/sqlbot/data /opt/sqlbot/images /opt/sqlbot/app/logs /opt/sqlbot/frontend

# Ensure python venv exists (if builder didn't create), then install debugpy as root into system or venv
RUN if [ ! -f "${SQLBOT_HOME}/app/.venv/bin/pip" ]; then python3 -m venv ${SQLBOT_HOME}/app/.venv; fi \
 && ${SQLBOT_HOME}/app/.venv/bin/pip install --upgrade pip setuptools wheel \
 && ${SQLBOT_HOME}/app/.venv/bin/pip install --no-cache-dir debugpy

# Expose ports: SSH (container internal), app ports, debug port
ENV PY_DEBUG_PORT=5678
ENV DEBUG_MODE=false

EXPOSE ${SSH_PORT} 3000 8000 8001 ${PY_DEBUG_PORT}

# Use root user to avoid permission issues in development environment
USER root
WORKDIR ${SQLBOT_HOME}/app

# Copy entrypoint script (will run ssh and app; defined below)
COPY build/dev/start-container-dev.sh /opt/sqlbot/app/start-container.sh

RUN chmod +x /opt/sqlbot/app/start-container.sh

# Healthcheck (runs as container runtime user; using curl - if missing, skip)
USER root
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000 || exit 1

# Use start-container.sh to decide starting ssh + debug or normal start
USER root
ENTRYPOINT ["/opt/sqlbot/app/start-container.sh"]
