# Troubleshooting

## Backend won't start
- Check `docker compose logs backend`
- Confirm `DATABASE_URL` is reachable: `bash deployment/scripts/healthcheck.sh`
- Run migrations manually: `bash deployment/scripts/migrate.sh`

## Celery worker not picking up tasks
- Confirm broker/backend URLs match between `backend` and `worker`/`beat` services
- `docker compose exec worker uv run celery -A worker.celery_app inspect ping`

## SSE stream hangs / never emits tokens
- Confirm Nginx has `proxy_buffering off` on `/stream/` (already set in
  `deployment/nginx/nginx.conf`) — buffering is the most common cause
  of "stuck" streams behind a reverse proxy
- Check `GENERATION_API_KEY` quota/rate limits (Groq 429s surface as an
  `error` stream event, not a silent hang)

## 401 on every request after deploy
- `JWT_SECRET_KEY` differs between old and new deployment — rotating
  it invalidates all existing tokens; this is expected, not a bug

## Chroma "collection not found" after fresh deploy
- Run ingestion once: `docker compose exec backend uv run python scripts/ingest_data.py`

## High Groq latency / rate limiting
- Check `/feedback/analytics`-adjacent... actually check `/metrics` for
  `llm_call_duration_seconds` and `llm_rate_limited_retrying` log lines
- Consider raising `LLM_REQUESTS_PER_MINUTE` per-key or splitting roles
  across more Groq API keys (Part 4 pattern)