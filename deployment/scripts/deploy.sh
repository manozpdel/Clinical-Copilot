#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="deployment/compose/docker-compose.prod.yml"
ENV_FILE="${ENV_FILE:-.env.production}"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found. Copy .env.production.example first."
    exit 1
fi

echo "Pulling / building images..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build

echo "Starting infrastructure (postgres, redis)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d postgres redis

echo "Running database migrations..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm backend \
    uv run alembic upgrade head

echo "Starting all services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo "Running post-deploy health checks..."
sleep 10
BASE_URL="http://localhost:8080" bash deployment/scripts/healthcheck.sh

echo "Deployment complete."