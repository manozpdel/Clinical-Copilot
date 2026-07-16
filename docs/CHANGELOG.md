# Changelog

## [1.0.0] - Production Release

### Added
- Parts 1-13: full RAG + agentic clinical assistant (ingestion,
  retrieval, LangGraph agent, mock clinical tools, voice pipeline,
  FastAPI + frontend, PostgreSQL persistence, JWT/Google auth, rate
  limiting & quotas, observability, human feedback system, real-time
  SSE/WebSocket streaming)
- Part 15: Docker Compose (dev + prod), Celery worker/beat with Redis,
  Nginx reverse proxy with SSE/WebSocket support, GitHub Actions
  CI/CD/security/release workflows, backup/restore/migrate/deploy
  scripts, production documentation, end-to-end and smoke tests

### Security
- Non-root containers across all images
- Trivy image scanning, pip-audit, bandit in CI
- CSP/HSTS/security headers, rate limiting, JWT auth on all sensitive
  endpoints