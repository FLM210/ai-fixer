# syntax=docker/dockerfile:1.7

# ---- 前端构建阶段 ----
FROM node:20-alpine AS ui-builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
ARG APP_VERSION=v0.1.0
ENV VITE_APP_VERSION=$APP_VERSION
RUN npm run build


# ---- Python 构建阶段 ----
FROM python:3.11-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock /app/
COPY README.md /app/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.11-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 fixer && useradd -m -u 1000 -g fixer fixer

COPY --from=builder --chown=fixer:fixer /app /app
COPY --from=ui-builder --chown=fixer:fixer /app/dist /app/static

# 创建自定义插件目录
RUN mkdir -p /app/custom_plugins && chown fixer:fixer /app/custom_plugins

USER fixer

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8080/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
