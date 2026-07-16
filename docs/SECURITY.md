# Security Guide

## Container security
- All application containers run as non-root UID 1000
- Multi-stage, slim base images; no build tools in the final worker/backend layer beyond what `uv sync` needs
- Images scanned via Trivy in `.github/workflows/security.yml`

## Secrets
- Never committed; `.env` / `.env.production` are gitignored
- `JWT_SECRET_KEY`, database credentials, and Groq/Google keys are
  injected via environment variables only
- `GET /auth/config` exposes only the public Google OAuth client ID,
  never the client secret

## Network
- Nginx terminates all external traffic; backend/worker/beat/postgres/redis
  are not exposed externally in the production compose file
- Rate limiting (`slowapi`, Part 10) + Nginx `limit_req` provide two
  independent layers of abuse protection
- CSP, HSTS, X-Frame-Options, X-Content-Type-Options set on every
  response (Part 10 `security/headers.py`)

## Dependency & code scanning
- `pip-audit` and `bandit` run in CI (`security.yml`), non-blocking by
  default — tighten to blocking once the project has a security triage
  process in place

## Data protection
- Passwords hashed with bcrypt; JWTs short-lived (access) + rotating
  (refresh)
- All persisted queries/feedback are scoped to the owning user; CRUD
  layer enforces ownership checks (see `feedback/crud.py`)