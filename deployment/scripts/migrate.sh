#!/usr/bin/env bash
set -euo pipefail

BACKEND_CONTAINER="${BACKEND_CONTAINER:-clinical-copilot-dev-backend-1}

echo "Waiting for database to accept connections..."
for i in $(seq 1 30); do
    if docker exec "$BACKEND_CONTAINER" uv run python -c \
        "import asyncio; from database.session import engine
async def check():
    async with engine.connect() as c:
        pass
asyncio.run(check())" 2>/dev/null; then
        echo "Database is ready."
        break
    fi
    echo "Waiting for database... ($i/30)"
    sleep 2
done

echo "Applying Alembic migrations..."
docker exec "$BACKEND_CONTAINER" uv run alembic upgrade head

echo "Migrations applied successfully."