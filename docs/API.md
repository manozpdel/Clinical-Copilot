# API Reference (Summary)

Full interactive docs: `GET /docs` (Swagger UI), `GET /redoc`.

## Public
- `GET /` — root
- `GET /health` — liveness
- `GET /api/version` — version/environment
- `POST /auth/register`, `/auth/login`, `/auth/refresh`
- `POST /login/google`

## Authenticated
- `POST /api/query` — text question → agent answer (blocking)
- `POST /api/voice` — audio upload → transcript + answer (blocking)
- `GET /stream/query` — SSE streamed answer
- `POST /stream/voice` — SSE-shaped streamed voice answer
- `GET /ws` — WebSocket, bidirectional multi-turn
- `GET /auth/me` — current user profile
- `GET /health/detailed` — dependency health (DB, Chroma, Groq, LangSmith, disk, memory)
- `GET /metrics` — Prometheus exposition

## Feedback
- `POST /feedback`, `PUT /feedback/{id}`, `DELETE /feedback/{id}`
- `POST /feedback/rating`, `POST /feedback/report`
- `GET /feedback/history`, `GET /feedback/compare`
- `GET /feedback/analytics`, `GET /feedback/export` (admin only)

All authenticated endpoints accept `Authorization: Bearer <access_token>`.
SSE/WebSocket also accept `?token=<access_token>` since browser
`EventSource`/`WebSocket` cannot set custom headers.