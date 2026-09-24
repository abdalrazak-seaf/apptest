# [APP_NAME] developer commands. Run `make help` for the list.
SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose -f infra/docker-compose.yml
INFRA_SERVICES := postgres redis minio mailpit
TEST_DATABASE_URL ?= postgresql+asyncpg://thiqa:thiqa@localhost:5432/thiqa_test

.PHONY: help setup infra-up infra-down infra-reset dev dev-mobile up-full migrate migration \
	seed admin test test-unit test-py test-js e2e lint format api-client clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Install all dependencies and git hooks
	uv sync --all-packages
	pnpm install
	uv run pre-commit install
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")

infra-up: ## Start Postgres, Redis, MinIO and Mailpit (waits until healthy)
	$(COMPOSE) up -d --build --wait $(INFRA_SERVICES)
	$(COMPOSE) run --rm minio-init

infra-down: ## Stop infra containers (keeps data)
	$(COMPOSE) down

infra-reset: ## Stop infra and DELETE all local data volumes
	$(COMPOSE) down -v

dev: infra-up migrate ## Run infra + API + worker + web with hot reload
	pnpm turbo run dev --filter=@thiqa/api --filter=@thiqa/worker --filter=@thiqa/web

dev-mobile: ## Start the Expo dev server (scan the QR code with Expo Go)
	pnpm --filter @thiqa/mobile start

up-full: ## Run everything in containers (production-like images)
	$(COMPOSE) --profile app up -d --build --wait

migrate: ## Apply database migrations
	cd apps/api && uv run alembic upgrade head

migration: ## Create a migration: make migration name="add listings"
	@test -n "$(name)" || (echo 'usage: make migration name="describe change"' && exit 1)
	cd apps/api && uv run alembic revision --autogenerate -m "$(name)"

seed: ## Load development seed data
	cd apps/api && uv run python -m api.scripts.seed

admin: ## Grant admin to a phone number: make admin PHONE=0501234567
	@test -n "$(PHONE)" || (echo 'usage: make admin PHONE=0501234567' && exit 1)
	cd apps/api && uv run python -m api.scripts.promote_admin "$(PHONE)"

test: test-py test-js ## Run all tests (needs `make infra-up` for integration tests)

test-unit: ## Run tests that need no infrastructure
	uv run pytest apps -m "not integration"
	pnpm turbo run test

test-py: ## Python tests, including integration tests against the test database
	DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest apps

test-js: ## TypeScript tests (Vitest + Jest)
	pnpm turbo run test

e2e: ## Playwright end-to-end tests (builds the web app first)
	pnpm --filter @thiqa/web build
	pnpm --filter @thiqa/web e2e

lint: ## Lint, format-check and type-check everything
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	pnpm format:check
	pnpm turbo run lint typecheck

format: ## Auto-format Python and TypeScript
	uv run ruff check --fix .
	uv run ruff format .
	pnpm format

api-client: ## Regenerate the TypeScript API client from FastAPI's OpenAPI spec
	uv run python -m api.scripts.export_openapi packages/api-client/openapi.json
	pnpm --filter @thiqa/api-client generate

clean: ## Remove build outputs and caches
	rm -rf apps/web/.next apps/mobile/.expo .turbo **/.turbo .pytest_cache .mypy_cache .ruff_cache
