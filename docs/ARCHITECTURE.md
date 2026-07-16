# Architecture Overview

Clinical Copilot is built incrementally across 13 implemented milestones
(Parts 1–13; the numbering continues to 15 for infra/release milestones):

1. FastAPI bootstrap
2. Synthetic data ingestion → ChromaDB
3. Semantic retrieval (RAG)
4. LLM answer generation + evaluation (Groq)
5. LangGraph agent orchestration
6. Mock clinical tools (EHR, Notes, Wearables) + rule-based routing
7. Voice pipeline (Groq Whisper) + conversation memory
8. FastAPI REST API + vanilla JS frontend
9. PostgreSQL persistence + JWT/Google OAuth
10. Rate limiting, quotas, security middleware
11. Observability (structured logs, OpenTelemetry, Prometheus, LangSmith)
12. Human feedback (likes, ratings, comments, reports, analytics)
13. Real-time streaming (SSE + WebSocket)
15. Production deployment (this milestone)

## Request flow (text query, streaming)
Browser (EventSource)
-> Nginx (/stream/query)
-> FastAPI (auth via JWT query param)
-> StreamingService
-> agent.planner (pure fn)
-> tools.router | rag.search (pure fn)
-> llm.client.generate_stream (Groq streaming)
-> agent.evaluator_node (pure fn)
-> PostgreSQL (conversation/query persistence)
-> SSE events back to browser

## Background jobs

Celery workers (Redis broker/backend) run: scheduled evaluation
re-runs, embedding regeneration, feedback analytics refresh, and quota
resets — all wrapping existing pure functions from earlier milestones,
never reimplementing them.

## Data stores

- **PostgreSQL**: users, conversations, queries, usage logs, quotas,
  feedback, ratings, hallucination reports
- **ChromaDB**: persistent vector store for clinical note embeddings
- **Redis**: Celery broker/backend, rate-limit state