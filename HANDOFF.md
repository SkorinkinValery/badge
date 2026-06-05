# HANDOFF

## 1. Цель
MVP «Аудиобейдж» — расширяемое ядро AI-анализа звонков менеджеров (аудио → текст → summary → KPI → выгрузка).
Архитектура: **ports & adapters**. Принцип старта: **недорогое/бесплатное** (faster-whisper, gpt-4o-mini, Google Sheets).

## 2. Текущее состояние

| Milestone | Статус | Коммит |
|-----------|--------|--------|
| `docs/PLAN.md` + `docs/dev/tasks/` (72 задачи, M0–M10) | Утверждён | `fb0dbd4` |
| **M0 — Каркас** (монорепо, Docker Compose, FastAPI, Alembic, CI) | ✅ | `51cb847` |
| **M1 — Ядро/порты/граф** (domain, ports, LangGraph, стаб-адаптеры) | ✅ | `c5da828` |
| **M2 — FileSource + MinIO + ffmpeg** (загрузка/нормализация/uploads API) | ✅ | `d0008e1` |
| **M3 — FasterWhisperEngine + STT API** | ✅ | `2271e78` |
| **M4 — OpenAICompatibleAnalyzer + анализ + scoring + API** | ✅ | `2cca3d6` |
| **M5 — Auth (JWT) + UI (Next.js + Mantine)** | ✅ | `9ce778c` |
| **M6 — Админка: менеджеры, скрипты, дневная сводка** | ✅ | `a10c5e0` |
| M7–M10 | Не начато | — |

**Тесты на текущий момент: 356 backend + 34 frontend** — зелёные; ruff + mypy --strict (80 файлов) — зелёные.

### Что сделано в M6 (последний milestone)
- **Менеджеры** — CRUD (`app/api/managers.py`): admin-only create/update/delete, any-user list/get, soft-delete, уникальность `device_id`.
- **Скрипты** — загрузка txt/md с версионированием и выбором активной версии (`app/api/scripts.py`, `app/services/scripts.py`, `app/db/repositories/script_repo.py`).
- **Резолвер режима анализа** — `resolve_analysis_mode` (baseline vs script по активному скрипту менеджера, `script_version_id` для воспроизводимости) — `app/services/process.py`.
- **Дневная сводка** — агрегация кол-ва/длительности/балла/KPI-статистики/нарушений/топ-проблем — `app/services/daily_summary.py`, `app/api/admin.py`.
- **UI** (`frontend/src/app/admin/`) — страницы `managers/`, `scripts/`, `summary/` с auth guard.
- **Схема БД** — миграция `m6schema`: `script.active_version_id` (UUID, nullable), `recording.duration_seconds` (Float, nullable). Новых зависимостей нет.

### Сжатый журнал M1–M5
- **M1** — `core/domain` (Recording, Transcript, Analysis, Manager, Script, User, enums), `core/ports` (AudioSource, STTEngine, Analyzer, CRMExporter + DTO), `core/pipeline` (state/nodes/graph на LangGraph), стаб-адаптеры, baseline-миграция.
- **M2** — `services/storage.py` (S3/boto3), `services/ingest.py` (валидация magic-bytes/ext/size), `services/normalize.py` (ffmpeg 16 kHz mono), `adapters/audio/file_source.py`, `api/uploads.py` + `api/recordings.py`.
- **M3** — `adapters/stt/` (`faster_whisper_engine.py` с lazy-singleton, `config.py`, `mapping.py`), DI STTEngine в узел `transcribing`, `GET /api/recordings/{id}/transcript`.
- **M4** — `adapters/analyzer/` (`openai_compatible.py`, `schema.py` динамический Pydantic, `prompt.py`), `services/score.py` (нормализация весов), узлы `analyzing`/`scoring`/`exporting`, `GET`/`PATCH /api/recordings/{id}/analysis` (`auto_score` + `corrected_by`).
- **M5** — `services/auth.py` (argon2, `UserRole`, `seed_admin_if_missing`), `api/auth.py` (login → JWT), `api/deps.py` (`require_role`, guards на всех роутах), Next.js 14 App Router + Mantine v7, страницы логина / списка записей / карточки записи / формы коррекции балла.

### Добавленные зависимости (накопительно)
- **M2:** `boto3`, `types-boto3`, `python-magic`
- **M3:** `faster-whisper>=1.2.1`
- **M5 backend:** `argon2-cffi>=23.1`, `python-jose[cryptography]>=3.3`, `types-python-jose`
- **M5 frontend:** Next.js 14, Mantine v7, Vitest 1.x, @testing-library/react
- **M4/M6:** новых зависимостей нет

## 3. Ключевые технологические решения

| Область | Выбор MVP | Целевое (после MVP) |
|---------|-----------|---------------------|
| **STT** | faster-whisper self-host (бесплатно, офлайн) | — |
| **LLM** | `gpt-4o-mini` через OpenAI-совместимый API | vLLM + Qwen2.5 (M9, под ПДн) |
| **CRM/экспорт** | `GoogleSheetsExporter` (M8) | Bitrix24 / GenericWebhook |
| **Оркестрация** | LangGraph (граф стадий, checkpointer Postgres) | — |
| **БД** | PostgreSQL + SQLAlchemy 2.0 + Alembic | — |
| **Хранилище аудио** | MinIO (S3-совместимое, self-host) | — |
| **Фронтенд** | Next.js (App Router) + Mantine | — |

**Сквозной принцип:** каждый провайдер (LLM/STT/CRM) — сменный адаптер за портом;
смена = только конфиг (`base_url`/`model`/`api_key`/выбор адаптера), никаких правок кода.

**Чего НЕ делать:**
- Платные STT (Deepgram/AssemblyAI) — не основной путь, только опция
- redis — не нужен (LangGraph + Postgres checkpointer)
- vLLM в compose — только на M9
- Хардкодить провайдеров/KPI/веса в коде

## 4. Структура репозитория (актуальная)

```
backend/app/
  core/
    domain/     # Recording, Transcript, Analysis, Manager, Script, User, enums
    ports/      # AudioSource, STTEngine, Analyzer, CRMExporter + DTO
    pipeline/   # state.py, nodes.py, graph.py (LangGraph)
  adapters/
    audio/      # file_stub, file_source, badge_source, telephony_source
    stt/        # stub_stt, faster_whisper_engine, config, mapping
    analyzer/   # stub_analyzer, openai_compatible, schema, prompt
    crm/        # json_exporter
  services/     # storage, ingest, normalize, score, auth, scripts, process, daily_summary
  db/
    models/         # analysis, recording, transcript, manager, script, user
    repositories/   # manager_repo, recording_repo, script_repo
    migrations/versions/  # baseline, core_schema, 4b47e88b70e8 (analysis), m6schema
    session.py
  workers/      # runner.py (run_job)
  config/       # settings.py, kpi.py
  api/          # health, auth, deps, uploads, recordings, managers, scripts, admin
  main.py
backend/tests/  # unit/ contract/ integration/ api/ config/ infra/ db/ adapters/ core/ services/ workers/
frontend/src/
  app/          # login, recordings, recordings/[id], admin/{managers,scripts,summary}
  lib/          # auth.ts (sessionStorage), api.ts
  test/         # Vitest + @testing-library
infra/
  docker-compose.yml
  config/{providers.yaml,kpi.yaml,weights.yaml}
docs/
  PLAN.md  TZ-audiobadge-mvp.md  dev/tasks/M0–M10.md
```

## 5. Следующий шаг — M7

**Запустить агента:** `Реализуй milestone M7 по промпту docs/dev/implement-milestone.md`

M7 — **MicSource near-realtime** (микрофон → WebSocket → пайплайн).
Детали: `docs/dev/tasks/M7-micsource-realtime.md`.

**Перед M7 поднять окружение:**
1. MinIO + Postgres: `POSTGRES_PORT=5434 docker compose -f infra/docker-compose.yml up -d postgres minio`
2. `LLM_API_KEY` в env (для тестов с реальным LLM; unit-тесты работают без ключа)
3. Frontend-тесты: `cd frontend && npm test`

## 6. Команды разработки

```bash
# Порт 5432 занят системным Postgres → badge-postgres на 5434, MinIO на 9000
POSTGRES_PORT=5434 docker compose -f infra/docker-compose.yml up -d postgres minio
docker compose -f infra/docker-compose.yml down

# Тесты без внешних сервисов (unit + contract):
uv run pytest backend/tests/ --ignore=backend/tests/db --ignore=backend/tests/workers -q

# Все тесты (с MinIO + Postgres на 5434):
DATABASE_URL=postgresql+asyncpg://badge:badge@localhost:5434/badge \
  uv run pytest backend/tests/ -q

# Линт/типы
uv run ruff check backend/
uv run mypy backend/app --strict

# Миграции
DATABASE_URL=postgresql+asyncpg://badge:badge@localhost:5434/badge \
  uv run alembic -c backend/alembic.ini upgrade head
DATABASE_URL=postgresql+asyncpg://badge:badge@localhost:5434/badge \
  uv run alembic -c backend/alembic.ini revision --autogenerate -m "<msg>"

# Frontend
cd frontend && npm test
```

## 7. Открытые вопросы к заказчику

1. **Облачный LLM**: провайдер (OpenAI / совместимый), бюджет `gpt-4o-mini`, допустимость отправки транскриптов в облако на пилоте (`LLM_API_KEY` в env).
2. **Google Sheets** (M8): сервисный аккаунт + ID таблицы.
3. **GPU под пилот**: на MVP только под faster-whisper; объём VRAM определит размер Qwen2.5 на M9.
4. **Bitrix24** (M8+): целевая сущность и маппинг полей.
5. **Retention**: срок хранения записей для `retention_until` и джобы удаления.
6. Согласие/уведомление клиентов готовит заказчик (вне системы).

## 8. Юридический контекст (РБ, неизменно)

Голос + содержание разговора = ПДн. Трансграничная передача в США (OpenAI) без согласия каждого клиента — нарушение. Поэтому:
- STT self-host с самого начала (аудио не покидает периметр).
- LLM облако (`gpt-4o-mini`) — на пилотных/обезличенных данных с согласием; full self-host vLLM/Qwen — целевое решение (M9).
- РФ — надлежащая юрисдикция (RU-облако как fallback допустимо).
