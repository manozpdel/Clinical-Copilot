# Deployment Guide

## Prerequisites

- Docker Engine 24+, Docker Compose v2
- A `.env.production` file (copy from `.env.production.example`)
- Groq API keys (generation, faithfulness, relevance, transcription)
- A PostgreSQL-capable host with persistent volume support

## Development stack

```bash
make dev
```

Starts Postgres, Redis, backend, worker, and beat with hot-reload-friendly
defaults. Frontend is served directly by the backend at `/app`.

## Production stack

```bash
cp deployment/compose/.env.production.example .env.production
# edit .env.production with real secrets
make prod
```

This builds and starts: Postgres, Redis, 2x backend replicas, 2x Celery
workers, Celery beat, and Nginx (reverse proxy + static frontend) on
port 80.

## Manual step-by-step

```bash
docker compose -f deployment/compose/docker-compose.prod.yml --env-file .env.production build
docker compose -f deployment/compose/docker-compose.prod.yml --env-file .env.production up -d postgres redis
bash deployment/scripts/migrate.sh
docker compose -f deployment/compose/docker-compose.prod.yml --env-file .env.production up -d
bash deployment/scripts/healthcheck.sh
```

## Rolling back

```bash
docker compose -f deployment/compose/docker-compose.prod.yml down
bash deployment/scripts/restore.sh backups/postgres_<timestamp>.dump backups/chroma_<timestamp>.tar.gz
```

## Backups

Automate `deployment/scripts/backup.sh` via cron or the bundled Celery
beat schedule extension point in `worker/celery_app.py`.