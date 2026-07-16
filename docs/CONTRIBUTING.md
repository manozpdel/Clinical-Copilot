# Contributing

## Setup

```bash
uv sync --all-extras --dev
cp .env.example .env
uv run python scripts/create_db.py
uv run python scripts/ingest_data.py
```

## Development workflow

```bash
make lint
make format
make test
```

## Commit conventions

Use Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
Milestone branches follow `feature/<milestone-name>`.

## Architecture rules

- Never mix responsibilities across a module's stated single purpose
  (see each package's module docstrings)
- Business logic never lives in FastAPI route handlers — always
  delegate to a `service.py` / `*_service.py`
- Never duplicate logic that already exists in an earlier milestone's
  module; import and reuse it

## Tests

- `uv run pytest -m "not slow"` for the full fast suite
- `uv run pytest tests/test_e2e.py -m e2e` requires a running stack
  (`make dev` first)