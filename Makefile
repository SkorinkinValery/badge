# Audiobadge MVP — local dev Makefile
# Загружает .env и экспортирует переменные во все рецепты.

include .env
export

COMPOSE      := docker compose --env-file .env -f infra/docker-compose.yml
COMPOSE_TEST := docker compose -f infra/docker-compose.test.yml
UVICORN     := uv run uvicorn app.main:app --app-dir backend
ALEMBIC     := uv run alembic -c backend/alembic.ini
BACKEND_PORT ?= 8000

.DEFAULT_GOAL := help

.PHONY: help install up down stop ps logs migrate revision dev backend frontend \
        test test-fast test-up test-down lint typecheck clean

help: ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) \
		| sort | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости backend (uv) и frontend (npm)
	uv sync
	cd frontend && npm install

up: ## Поднять инфраструктуру (Postgres + MinIO)
	$(COMPOSE) up -d postgres minio
	@echo "Postgres :$(POSTGRES_PORT)  MinIO :$(MINIO_API_PORT) (console :$(MINIO_CONSOLE_PORT))"

down: ## Остановить инфраструктуру
	$(COMPOSE) down

stop: ## Остановить ВСЁ от make dev: backend + frontend + инфраструктуру
	-@pkill -f "uvicorn app.main:app" 2>/dev/null && echo "backend остановлен" || echo "backend не запущен"
	-@pkill -f "next-server" 2>/dev/null; pkill -f "next dev" 2>/dev/null; echo "frontend остановлен"
	$(COMPOSE) down

ps: ## Статус контейнеров
	$(COMPOSE) ps

logs: ## Логи инфраструктуры (Ctrl-C для выхода)
	$(COMPOSE) logs -f postgres minio

migrate: ## Применить миграции БД (alembic upgrade head)
	$(ALEMBIC) upgrade head

revision: ## Создать миграцию: make revision m="описание"
	$(ALEMBIC) revision --autogenerate -m "$(m)"

dev: up migrate ## Запустить ВСЁ разом: инфра + миграции + backend + frontend (Ctrl-C останавливает оба)
	@echo "→ backend  http://localhost:$(BACKEND_PORT)  (docs: /docs)"
	@echo "→ frontend http://localhost:3000"
	@echo "Ctrl-C для остановки обоих сервисов."
	@trap 'kill 0' INT TERM EXIT; \
		$(UVICORN) --reload --port $(BACKEND_PORT) & \
		( cd frontend && npm run dev ) & \
		wait

backend: ## Запустить FastAPI (uvicorn --reload) на :$(BACKEND_PORT)
	$(UVICORN) --reload --port $(BACKEND_PORT)

frontend: ## Запустить Next.js dev-сервер на :3000
	cd frontend && npm run dev

test-up: ## Поднять ИЗОЛИРОВАННУЮ тестовую инфру (Postgres :5435, MinIO :9100)
	$(COMPOSE_TEST) up -d --wait
	@echo "тестовая БД готова: postgres :5435/badge_test, minio :9100"

test-down: ## Остановить и удалить тестовую инфру (данные эфемерны)
	$(COMPOSE_TEST) down -v

test: ## Все backend-тесты на ЧИСТОЙ изолированной тестовой БД (НЕ трогает dev)
	-$(COMPOSE_TEST) down -v >/dev/null 2>&1
	$(COMPOSE_TEST) up -d --wait
	uv run pytest backend/tests/ -q

test-fast: test-up ## Быстро: переиспользует поднятую тестовую БД, без heavy (GPU/модели)
	uv run pytest backend/tests/ -m "not heavy" -q

lint: ## ruff
	uv run ruff check backend/

typecheck: ## mypy --strict
	uv run mypy backend/app --strict

clean: ## Остановить инфраструктуру и удалить тома (данные БД/MinIO!)
	$(COMPOSE) down -v
