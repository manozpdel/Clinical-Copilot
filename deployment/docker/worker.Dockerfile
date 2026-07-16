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
COPY ingest ./ingest
COPY rag ./rag
COPY llm ./llm
COPY evaluation ./evaluation
COPY agent ./agent
COPY tools ./tools
COPY voice ./voice
COPY database ./database
COPY auth ./auth
COPY security ./security
COPY observability ./observability
COPY feedback ./feedback
COPY streaming ./streaming
COPY worker ./worker

RUN chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD uv run celery -A worker.celery_app inspect ping -d celery@$HOSTNAME || exit 1

CMD ["uv", "run", "celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=4"]