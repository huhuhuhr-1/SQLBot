# syntax=docker/dockerfile:1.7

# Build sqlbot
ARG VECTOR_IMAGE=ghcr.io/1panel-dev/maxkb-vector-model:v1.0.1
ARG BUILDER_BASE=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest
ARG SSR_BASE=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest
ARG RUNTIME_BASE=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-python-pg:latest
ARG INCLUDE_VECTOR=true
ARG ENABLE_LOCAL_PG=true

FROM ${VECTOR_IMAGE} AS vector-model
FROM ${BUILDER_BASE} AS sqlbot-builder

# Set build environment variables
ENV PYTHONUNBUFFERED=1     SQLBOT_HOME=/opt/sqlbot     APP_HOME=/opt/sqlbot/app     UI_HOME=/opt/sqlbot/frontend     PYTHONPATH=/opt/sqlbot/app     PATH="/opt/sqlbot/app/.venv/bin:$PATH"     UV_COMPILE_BYTECODE=1     UV_LINK_MODE=copy     DEBIAN_FRONTEND=noninteractive

RUN mkdir -p ${APP_HOME} ${UI_HOME}

# --------------------
# Build frontend assets
# --------------------
WORKDIR /tmp/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY frontend/ ./
RUN npm run build
RUN rm -rf ${UI_HOME}/dist && mv dist ${UI_HOME}/dist

# --------------------
# Python dependencies & source
# --------------------
WORKDIR ${APP_HOME}
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv     sh -c 'if [ -f uv.lock ]; then uv sync --frozen --no-install-project; else uv sync --no-install-project; fi'
COPY backend/ ${APP_HOME}/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --extra cpu

# --------------------
# Build g2-ssr
# --------------------
FROM ${SSR_BASE} AS ssr-builder

WORKDIR /app
COPY g2-ssr/package.json /app/
RUN --mount=type=cache,target=/root/.npm npm install
COPY g2-ssr/ /app/

# --------------------
# Runtime stage
# --------------------
FROM ${RUNTIME_BASE}
ARG ENABLE_LOCAL_PG

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime &&     echo "Asia/Shanghai" > /etc/timezone

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1     SQLBOT_HOME=/opt/sqlbot     PYTHONPATH=/opt/sqlbot/app     PATH="/opt/sqlbot/app/.venv/bin:$PATH"     POSTGRES_DB=sqlbot     POSTGRES_USER=root     POSTGRES_PASSWORD=Password123@pg     ENABLE_LOCAL_PG=${ENABLE_LOCAL_PG}

# Copy necessary files from builder
COPY start.sh /opt/sqlbot/app/start.sh
COPY --from=sqlbot-builder ${SQLBOT_HOME} ${SQLBOT_HOME}
COPY --from=ssr-builder /app /opt/sqlbot/g2-ssr
COPY --from=ssr-builder /app/*.ttf /usr/share/fonts/truetype/liberation/
RUN mkdir -p /opt/sqlbot/models
COPY --from=vector-model /opt/maxkb/app/model /tmp/vector-model
RUN if [ "${INCLUDE_VECTOR}" = "true" ]; then \
      cp -a /tmp/vector-model/. /opt/sqlbot/models/; \
    fi && rm -rf /tmp/vector-model

WORKDIR ${SQLBOT_HOME}/app

RUN mkdir -p /opt/sqlbot/images /opt/sqlbot/g2-ssr

EXPOSE 3000 8000 8001 5432

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3     CMD curl -f http://localhost:8000 || exit 1

ENTRYPOINT ["sh", "start.sh"]
