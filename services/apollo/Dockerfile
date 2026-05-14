# syntax=docker/dockerfile:1.7-labs
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /repo
COPY packages/pantheon-core /repo/packages/pantheon-core
COPY services/apollo /repo/services/apollo

WORKDIR /repo/services/apollo
RUN uv sync --frozen --no-dev || uv sync --no-dev

ENV PYTHONPATH=/repo/packages/pantheon-core/src:/repo/services/apollo/src

EXPOSE 8001
CMD ["uv", "run", "python", "-m", "apollo.cli", "serve"]
