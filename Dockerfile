# Build sqlbot
FROM ghcr.io/1panel-dev/maxkb-vector-model:v1.0.1 AS vector-model
FROM --platform=${BUILDPLATFORM} registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest AS sqlbot-ui-builder
ENV SQLBOT_HOME=/opt/sqlbot
ENV APP_HOME=${SQLBOT_HOME}/app
ENV UI_HOME=${SQLBOT_HOME}/frontend
ENV DEBIAN_FRONTEND=noninteractive

RUN mkdir -p ${APP_HOME} ${UI_HOME}

COPY frontend /tmp/frontend
RUN cd /tmp/frontend && npm config set registry https://registry.npmmirror.com && npm install && npm run build && mv dist ${UI_HOME}/dist


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

COPY  --from=sqlbot-ui-builder ${UI_HOME} ${UI_HOME}
# Optional: sync with frozen lock if present (mounts from build context, no COPY backend yet)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=/tmp/uv.lock,readonly \
    --mount=type=bind,source=backend/pyproject.toml,target=/tmp/pyproject.toml,readonly \
    sh -c 'cp /tmp/uv.lock /tmp/pyproject.toml . 2>/dev/null || true; test -f uv.lock && uv sync --frozen --no-install-project || echo "uv.lock not found, skipping"'

COPY ./backend ${APP_HOME}

# Final sync to ensure all dependencies are installed
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --extra cpu

# Install debugpy for IDE remote attach (dev/debug container use)
RUN uv pip install debugpy

# Build g2-ssr
FROM registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest AS ssr-builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3 pkg-config \
    libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev \
    libpixman-1-dev libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# configure npm (use China mirror for faster downloads)
RUN npm config set fund false \
    && npm config set audit false \
    && npm config set progress false \
    && npm config set registry https://registry.npmmirror.com

COPY g2-ssr/app.js g2-ssr/package.json /app/
COPY g2-ssr/charts/* /app/charts/
RUN npm install

# Runtime stage
FROM registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-python-pg:latest

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1
ENV SQLBOT_HOME=/opt/sqlbot
ENV PYTHONPATH=${SQLBOT_HOME}/app
ENV PATH="${SQLBOT_HOME}/app/.venv/bin:$PATH"

ENV POSTGRES_DB=sqlbot
ENV POSTGRES_USER=root
ENV POSTGRES_PASSWORD=Password123@pg

# Copy necessary files from builder
COPY start.sh /opt/sqlbot/app/start.sh
COPY start-debug.sh /opt/sqlbot/app/start-debug.sh
COPY g2-ssr/*.ttf /usr/share/fonts/truetype/liberation/
COPY --from=sqlbot-builder ${SQLBOT_HOME} ${SQLBOT_HOME}
COPY --from=ssr-builder /app /opt/sqlbot/g2-ssr
COPY --from=vector-model /opt/maxkb/app/model /opt/sqlbot/models

# Copy Data Agent skills directory
COPY .claude/skills ${SQLBOT_HOME}/.claude/skills

WORKDIR ${SQLBOT_HOME}/app

RUN mkdir -p /opt/sqlbot/images /opt/sqlbot/g2-ssr

EXPOSE 3000 8000 8001 5432 5678

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000 || exit 1

ENTRYPOINT ["sh", "start.sh"]
