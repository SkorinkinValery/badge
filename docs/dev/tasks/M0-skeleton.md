# M0 — Каркас (skeleton)

> Этап `docs/PLAN.md §5 M0`. Базовые соглашения, TDD-цикл, слои тестов и глобальный DoD — см.
> [README.md](README.md) (§2–§4). Ниже указаны только специфичные для задачи критерии.

## Цель этапа

Поднять монорепо, локальную инфраструктуру (Docker Compose: postgres/minio), `pydantic-settings`
+ загрузчик `kpi.yaml`/`weights.yaml`/`providers`, Alembic baseline и CI (lint + mypy + tests).
Ядро на этом этапе автономно — **без внешних API-ключей**.

## Входные предпосылки

- Пустой greenfield-репозиторий (только `docs/PLAN.md`, ТЗ, `.gitignore`).

## Выходной результат (DoD этапа)

- `docker compose up` поднимает postgres + minio локально.
- `pytest` запускается зелёным (хотя бы smoke-тесты конфига и health-роута).
- CI-пайплайн гоняет `ruff` + `mypy` + `pytest` на каждый PR.
- Конфиги `kpi.yaml`/`weights.yaml`/`providers.yaml` существуют и читаются типизированно.
- Alembic настроен, есть пустая baseline-миграция.

## Чек-лист задач

- [ ] M0-T1 — Скелет монорепо + менеджер зависимостей + ruff/mypy конфиг
- [ ] M0-T2 — Docker Compose: postgres + minio (+ caddy-заглушка)
- [ ] M0-T3 — `pydantic-settings` + загрузчик `providers`/env
- [ ] M0-T4 — Загрузчик `kpi.yaml` / `weights.yaml` (config-driven, с валидацией)
- [ ] M0-T5 — FastAPI `main.py` + `/health` + smoke-тест
- [ ] M0-T6 — Alembic baseline + CI (lint + mypy + tests)

---

### M0-T1: Скелет монорепо + зависимости + ruff/mypy

- **Цель / зачем:** Завести структуру каталогов из `docs/PLAN.md §2.2` и инструменты качества, чтобы все
  последующие задачи писались по единым правилам.
- **Зависит от:** нет
- **Затрагивает:** корень репо, `backend/`, `backend/app/{core,adapters,services,api,workers,db,config}`,
  `backend/tests/`, `frontend/`, `infra/`, `scripts/`, `datasets/`, `docs/`, `pyproject.toml`,
  `ruff.toml`/`[tool.ruff]`, `[tool.mypy]`.
- **TDD:**
  1. *Red* — `backend/tests/test_repo_layout.py` — кейсы: импортируется пакет `app`; существуют каталоги
     `app/core/ports`, `app/core/domain`, `app/core/pipeline`, `app/adapters/{audio,stt,analyzer,crm}`,
     `app/config`; `ruff`/`mypy` доступны как dev-зависимости.
  2. *Green* — создать дерево каталогов с `__init__.py`, `pyproject.toml` с зависимостями
     (fastapi, sqlalchemy, alembic, pydantic, pydantic-settings, langgraph, pytest, httpx, mypy, ruff, jiwer),
     пустые пакеты-заглушки.
  3. *Refactor* — вынести группы зависимостей (`dev`, `eval`) в extras; выровнять namespace-пакеты.
- **Слой тестов:** unit (smoke структуры).
- **Definition of Done:** глобальный DoD + структура каталогов строго по `docs/PLAN.md §2.2`;
  `ruff` и `mypy` конфиги в `pyproject.toml`.
- **Acceptance / как проверить:** `ruff check backend`, `mypy backend/app`, `pytest backend/tests/test_repo_layout.py`.
- **Заметки по портам/конфигу:** каталоги `core/ports` и `adapters/*` физически разделены — фундамент
  инварианта ports & adapters.

---

### M0-T2: Docker Compose — postgres + minio (+ caddy-заглушка)

- **Цель / зачем:** Локальная инфраструктура для разработки и интеграционных тестов; аудио хранится
  в периметре (MinIO).
- **Зависит от:** M0-T1
- **Затрагивает:** `infra/docker-compose.yml`, `infra/caddy/Caddyfile`, `infra/config/` (точка монтирования
  конфигов), `.env.example`.
- **TDD:**
  1. *Red* — `backend/tests/infra/test_compose_config.py` — кейсы: `docker compose config` валиден; описаны
     сервисы `postgres`, `minio`; проброшены порты и volume; есть healthcheck у postgres и minio.
     (Тест парсит YAML, не поднимает контейнеры.)
  2. *Green* — написать `docker-compose.yml` с сервисами postgres + minio, healthcheck'и, named volumes;
     caddy-сервис как заглушка TLS-прокси.
  3. *Refactor* — вынести креды в `.env`/`.env.example`; параметризовать версии образов.
- **Слой тестов:** unit (валидация compose-конфига), опционально интеграция (поднять контейнеры в CI-джобе с docker).
- **Definition of Done:** глобальный DoD + `docker compose up postgres minio` поднимается локально;
  healthcheck'и зелёные.
- **Acceptance / как проверить:** `docker compose -f infra/docker-compose.yml config`; `docker compose up -d postgres minio`.
- **Заметки по портам/конфигу:** сервисы MVP по `docs/PLAN.md §1`: api, worker, postgres, minio, frontend, caddy;
  `vLLM` НЕ добавляется (он на M9). MinIO = S3-совместимое self-host хранилище (аудио в периметре).

---

### M0-T3: `pydantic-settings` + загрузчик `providers`/env

- **Цель / зачем:** Единая типизированная точка чтения окружения и активных провайдеров (STT/LLM/CRM/язык) —
  фундамент сменности конфигом.
- **Зависит от:** M0-T1
- **Затрагивает:** `app/config/settings.py`, `infra/config/providers.yaml`, `.env.example`.
- **TDD:**
  1. *Red* — `backend/tests/config/test_settings.py` — кейсы: читается `DATABASE_URL`, `MINIO_*`;
     `providers.yaml` парсится в типизированную модель (`active_stt`, `active_llm{base_url,model,api_key}`,
     `active_crm`, `default_language="ru"`); отсутствие обязательного поля → понятная ошибка валидации;
     env переопределяет yaml.
  2. *Green* — `Settings(BaseSettings)` + модель `ProvidersConfig`; загрузчик yaml→pydantic.
  3. *Refactor* — кэшировать settings через `lru_cache`; разнести секции (db/storage/providers).
- **Слой тестов:** unit (парсинг конфигов).
- **Definition of Done:** глобальный DoD + дефолты MVP зашиты в `providers.yaml`
  (`active_stt=faster_whisper`, `active_llm.model=gpt-4o-mini`, `active_crm=json` на M4 / `google_sheets` на M8),
  `api_key` читается из env, не из yaml (секрет).
- **Acceptance / как проверить:** `pytest backend/tests/config/test_settings.py`.
- **Заметки по портам/конфигу:** **ключевой инвариант** — выбор адаптера STT/LLM/CRM и `base_url`/`model`/`api_key`
  целиком здесь; смена провайдера = правка `providers.yaml`/env, без кода.

---

### M0-T4: Загрузчик `kpi.yaml` / `weights.yaml`

- **Цель / зачем:** KPI и веса — config-driven (ТЗ §4.4/§4.5, `docs/PLAN.md §2.4`), не хардкод; основа скоринга и промпта.
- **Зависит от:** M0-T3
- **Затрагивает:** `app/config/kpi.py`, `infra/config/kpi.yaml`, `infra/config/weights.yaml`.
- **TDD:**
  1. *Red* — `backend/tests/config/test_kpi_loader.py` — кейсы: парсится список KPI с полями
     `id, label, type(scale|fact), weight, anchors[], applies_to(baseline|script), include_in_score`;
     стартовый набор из 10 KPI (ТЗ §5) валиден; KPI #9 «соблюдение регламента» помечен `applies_to=script`;
     поведенческие якоря (`anchors`) присутствуют (апгрейд №2 §12 ТЗ); невалидный `type` → ошибка;
     `weights.yaml` ссылается на существующие `id`, сумма/нормализация описана.
  2. *Green* — Pydantic-модели `KpiItem`, `KpiConfig`, `WeightsConfig`; загрузчики yaml.
  3. *Refactor* — вынести валидацию связности (`weights` ⊆ `kpi.id`) в отдельный валидатор.
- **Слой тестов:** unit (парсинг конфигов).
- **Definition of Done:** глобальный DoD + стартовые 10 KPI из ТЗ §5 лежат в `kpi.yaml` с якорями;
  никакого хардкода KPI в коде.
- **Acceptance / как проверить:** `pytest backend/tests/config/test_kpi_loader.py`.
- **Заметки по портам/конфигу:** `kpi.yaml`/`weights.yaml` — единственный источник KPI/весов;
  скоринг (M4) и промпт (M4) читают только отсюда.

---

### M0-T5: FastAPI `main.py` + `/health` + smoke-тест

- **Цель / зачем:** Поднять ASGI-приложение и точку входа, чтобы API-роутеры наращивались поверх.
- **Зависит от:** M0-T3
- **Затрагивает:** `app/main.py`, `app/api/__init__.py`.
- **TDD:**
  1. *Red* — `backend/tests/api/test_health.py` (httpx ASGI) — кейсы: `GET /health` → 200 `{"status":"ok"}`;
     приложение стартует с тестовыми settings.
  2. *Green* — `FastAPI()` app + роутер `/health`; подключить settings через DI.
  3. *Refactor* — вынести фабрику `create_app()`; структурный логгер на старте.
- **Слой тестов:** API.
- **Definition of Done:** глобальный DoD + структурный логгер инициализирован; `create_app()` параметризуем
  настройками (для тестов).
- **Acceptance / как проверить:** `pytest backend/tests/api/test_health.py`.
- **Заметки по портам/конфигу:** app собирается из settings (M0-T3) — провайдеры не импортируются напрямую.

---

### M0-T6: Alembic baseline + CI (lint + mypy + tests)

- **Цель / зачем:** Готовность к миграциям модели данных (M1) и автоматический quality-gate на каждый PR.
- **Зависит от:** M0-T2, M0-T5
- **Затрагивает:** `app/db/__init__.py`, `app/db/base.py`, `alembic.ini`, `app/db/migrations/`,
  `.github/workflows/ci.yml` (или аналог).
- **TDD:**
  1. *Red* — `backend/tests/db/test_alembic.py` — кейсы: `alembic upgrade head` применяется к чистой тест-БД
     без ошибок; `alembic check`/heads — одна голова. CI-конфиг содержит шаги `ruff`, `mypy`, `pytest`.
  2. *Green* — настроить `alembic.ini` + `env.py` под SQLAlchemy 2.0 metadata; пустая baseline-ревизия;
     CI-workflow с джобами lint/typecheck/test и **некритичной** eval-джобой (`continue-on-error`, skip без datasets).
  3. *Refactor* — кэш зависимостей в CI; матрица только по нужной версии Python (3.11).
- **Слой тестов:** интеграция (миграции против тест-БД).
- **Definition of Done:** глобальный DoD + CI зелёный на пустом проекте; eval-джоба не блокирует merge;
  одна alembic-голова.
- **Acceptance / как проверить:** `alembic upgrade head` на тест-БД; прогон CI на PR.
- **Заметки по портам/конфигу:** checkpointer LangGraph (M1) будет жить в той же Postgres; baseline готовит почву.
