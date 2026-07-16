.PHONY: dev prod build up down logs test lint format migrate backup restore

COMPOSE_DEV=deployment/compose/docker-compose.yml
COMPOSE_PROD=deployment/compose/docker-compose.prod.yml

dev:
	docker compose -f $(COMPOSE_DEV) up -d --build
	@echo "Dev stack running. Backend: http://localhost:8000  Frontend: http://localhost:8000/app"

prod:
	bash deployment/scripts/deploy.sh

build:
	docker compose -f $(COMPOSE_DEV) build

up:
	docker compose -f $(COMPOSE_DEV) up -d

down:
	docker compose -f $(COMPOSE_DEV) down

logs:
	docker compose -f $(COMPOSE_DEV) logs -f

test:
	uv run pytest -m "not slow"

lint:
	uv run ruff check .

format:
	uv run ruff format .

migrate:
	bash deployment/scripts/migrate.sh

backup:
	bash deployment/scripts/backup.sh

restore:
	bash deployment/scripts/restore.sh $(DUMP) $(CHROMA)