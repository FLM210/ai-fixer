.PHONY: install lint type test fmt run build-ui dev-ui up up-dev down down-dev logs

install:
	uv sync

lint:
	uv run ruff check app tests

fmt:
	uv run ruff format app tests
	uv run ruff check --fix app tests

type:
	uv run mypy app

test:
	uv run pytest

run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

migrate:
	uv run alembic upgrade head

# 前端
build-ui:
	cd frontend && npm run build

dev-ui:
	cd frontend && npm run dev

# Docker Compose 全量启动（含 PG + Redis）
up:
	docker-compose up -d --build

down:
	docker-compose down

logs:
	docker-compose logs -f

# Docker Compose 仅前后端（复用本机 infra-postgres / infra-redis）
up-dev:
	docker-compose -f docker-compose.dev.yml up -d --build

down-dev:
	docker-compose -f docker-compose.dev.yml down

logs-dev:
	docker-compose -f docker-compose.dev.yml logs -f
