FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY database ./database
COPY worker ./worker
COPY evaluation ./evaluation
COPY ingest ./ingest
COPY feedback ./feedback
COPY security ./security

RUN mkdir -p /app/celerybeat && chown -R appuser:appuser /app
USER appuser

CMD ["uv", "run", "celery", "-A", "worker.celery_app", "beat", "--loglevel=info", \
     "--schedule=/app/celerybeat/celerybeat-schedule"]