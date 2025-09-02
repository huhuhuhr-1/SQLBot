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

RUN cd /tmp/frontend; npm install; npm run build; mv dist ${UI_HOME}/dist

# Install dependencies
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

FROM registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest AS python-builder
# Runtime stage
# FROM registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest
FROM registry.cn-qingdao.aliyuncs.com/dataease/postgres:17.6

# python environment
COPY --from=python-builder /usr/local /usr/local

RUN python --version && pip --version

# Install uv tool
COPY --from=ghcr.io/astral-sh/uv:0.7.8 /uv /uvx /bin/

ARG DEPENDENCIES="                \
    wait-for-it                   \
    build-essential               \
    curl                          \
    gnupg                         \
    gcc                           \
    g++                           \
    libcairo2-dev                 \
    libpango1.0-dev               \
    libjpeg-dev                   \
    libgif-dev                    \
    librsvg2-dev"

RUN apt-get update && apt-get install -y --no-install-recommends $DEPENDENCIES \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && chmod g-xr /usr/local/bin/* /usr/bin/* /bin/* /usr/sbin/* /sbin/* /usr/lib/postgresql/17/bin/* \
    && chmod g+xr /usr/bin/ld.so \
    && chmod g+x /usr/local/bin/python*

# ENV PGDATA=/var/lib/postgresql/data \
#     POSTGRES_USER=root \
#     POSTGRES_PASSWORD=Password123@pg \
#     POSTGRES_DB=sqlbot

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1
ENV SQLBOT_HOME=/opt/sqlbot
ENV PYTHONPATH=${SQLBOT_HOME}/app
ENV PATH="${SQLBOT_HOME}/app/.venv/bin:$PATH"

# Copy necessary files from builder
COPY start.sh /opt/sqlbot/app/start.sh
COPY g2-ssr/*.ttf /usr/share/fonts/truetype/liberation/
COPY --from=sqlbot-builder ${SQLBOT_HOME} ${SQLBOT_HOME}
COPY --from=ssr-builder /app /opt/sqlbot/g2-ssr
COPY --from=vector-model /opt/maxkb/app/model /opt/sqlbot/models

WORKDIR ${SQLBOT_HOME}/app

RUN mkdir -p /opt/sqlbot/images /opt/sqlbot/g2-ssr

EXPOSE 3000 8000 8001 5432

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000 || exit 1

ENTRYPOINT ["sh", "start.sh"]
