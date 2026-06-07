"""Глобальная конфигурация тестов — изоляция от dev/боевой БД.

Integration/db-тесты подключаются к `os.environ['DATABASE_URL']`. Без этого
файла они шли бы в dev-БД (`make dev` → :5434/badge) и стирали реальные данные
(пользователей, записи). Здесь мы ПЕРЕОПРЕДЕЛЯЕМ окружение ДО импорта любого
тестового модуля (модульные DB_URL читаются на уровне импорта), поэтому тесты
не могут обращаться к dev-сервисам — только к одноразовым тестовым
(`infra/docker-compose.test.yml`: Postgres :5435/badge_test, MinIO :9100).

Правило: перенаправляем на тестовую БД, только если DATABASE_URL пуст ИЛИ
указывает на dev-инстанс (порт 5434). Явно заданный сторонний URL (например, в
CI — эфемерный Postgres) не трогаем.

Запуск локально: `make test` (поднимает тестовую инфру) или
`make test-up && uv run pytest`.
"""

from __future__ import annotations

import os

_TEST_DATABASE_URL = "postgresql+asyncpg://badge:badge@localhost:5435/badge_test"
_TEST_MINIO_ENDPOINT = "http://localhost:9100"

# Сигнатура dev-инстанса из `make dev` (порт Postgres из .env).
_DEV_DB_MARKER = ":5434/"

_current_db = os.environ.get("DATABASE_URL", "")
if _current_db == "" or _DEV_DB_MARKER in _current_db:
    os.environ["DATABASE_URL"] = _TEST_DATABASE_URL
    os.environ["MINIO_ENDPOINT"] = _TEST_MINIO_ENDPOINT
    os.environ["MINIO_API_PORT"] = "9100"
