FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create and set permissions for uv cache
RUN mkdir -p /home/appuser/.cache/uv && chown -R appuser:appuser /home/appuser/.cache

COPY pyproject.toml uv.lock README.md ./

# Give appuser ownership of /app before switching
RUN chown -R appuser:appuser /app

# Switch to appuser to run uv sync
USER appuser
RUN uv sync --frozen --no-dev

# Switch back to root to copy application files
USER root

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
COPY alembic ./alembic
COPY alembic.ini ./
COPY frontend ./frontend

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]