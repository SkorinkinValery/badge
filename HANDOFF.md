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
| **M7 — MicSource near-realtime** | ✅ | `e09924c` |
| **M8 — Экспорт результатов (CRM)** | ✅ | текущий |
| M9–M10 | Не начато | — |

**Тесты на текущий момент: 462 backend + 49 frontend** — зелёные; ruff + mypy --strict — зелёные.

### Что сделано в M8 (последний milestone)
- **`payload.py`** — `build_export_payload(analysis, recording, score=None, verdict=None) → dict`. `score`/`verdict` — опциональные параметры (не поля AnalysisResult).
- **`google_sheets.py`** — `GoogleSheetsExporter(spreadsheet_id, worksheet_name, credentials_json)` — gspread, ADC-fallback.
- **`webhook.py`** — `GenericWebhookExporter(url, headers, timeout)` — httpx POST + raise_for_status.
- **`bitrix24.py`** — `Bitrix24Exporter(webhook_url, field_mapping)` — REST webhook, опциональный маппинг полей.
- **`registry.py`** — `get_exporter(name, cfg)`, `AVAILABLE_PROVIDERS`, `UnknownCrmProviderError` — единая точка выбора адаптера по конфигу.
- **`nodes.py`** — `exporting`-узел использует `registry.get_exporter` вместо хардкода `JSONExporter`; CRM-конфиг приходит из `state["crm_config"]`.
- **`state.py`** — добавлено поле `crm_config: dict | None`.
- **`runner.py`** — принимает `crm_config` параметром (fallback — `load_providers_config()`), передаёт в initial_state.
- **`providers.yaml`** — `active_crm: google_sheets` + секция `crm` с параметрами для каждого провайдера.
- **`admin.py`** — `GET/PUT /api/admin/settings` (смена активного CRM, in-memory, требует роль admin).
- **`settings.py`** — `ProvidersConfig.crm: dict[str, dict]` + метод `crm_params()`.
- **`main.py`** — `app.state.crm_config` инициализируется из `providers.yaml` при старте.
- **UI** — `frontend/src/app/admin/settings/page.tsx` (Select провайдера + поля params для gs/webhook/b24).
- **Контрактный тест** — `test_crm_exporter.py` покрывает все 4 адаптера через мок HTTP/gspread.

### Новые зависимости в M8
- **backend:** `gspread==6.2.1` (через `uv add gspread`)

### Что сделано в M7 (последний закоммиченный milestone)
- **Протокол WS** — Pydantic-DTO (`start`/`chunk`/`stop`/`ack`/`partial_transcript`/`error`), `SessionProtocol` (монотонность seq, порядок), `parse_client_msg` — `app/adapters/audio/mic_protocol.py`.
- **Буфер чанков** — `ChunkBuffer` (оконная агрегация config-driven, backpressure, дубликаты seq) — `app/services/mic_buffer.py`.
- **MicSource** — адаптер `AudioSource` для микрофонного ввода, проходит контракт наравне с `FileSource` — `app/adapters/audio/mic_source.py`.
- **WS-эндпоинт** — `WS /api/ws/mic` (JWT через query param, `consent_flag` обязателен, near-realtime STT через StubSTTEngine/config, запись в БД, статус QUEUED после `stop`) — `app/api/ws_mic.py`.
- **Settings** — добавлены `mic_window_bytes`, `mic_max_bytes` (алиасы `MIC_WINDOW_BYTES`, `MIC_MAX_BYTES`).
- **UI** — `frontend/src/app/recordings/record/page.tsx` (выбор менеджера, согласие, старт/стоп, near-realtime транскрипт), `frontend/src/lib/ws.ts` (`useRecordWs` hook).

### Сжатый журнал M1–M6
- **M1** — `core/domain`, `core/ports`, `core/pipeline` (LangGraph), стаб-адаптеры.
- **M2** — `services/storage.py`, `services/ingest.py`, `services/normalize.py`, `adapters/audio/file_source.py`, `api/uploads.py` + `api/recordings.py`.
- **M3** — `adapters/stt/faster_whisper_engine.py`, DI STTEngine, `GET /api/recordings/{id}/transcript`.
- **M4** — `adapters/analyzer/openai_compatible.py`, `services/score.py`, узлы `analyzing`/`scoring`/`exporting`, `GET`/`PATCH /api/recordings/{id}/analysis`.
- **M5** — `services/auth.py` (argon2, JWT), `api/auth.py`, `api/deps.py`, Next.js 14 App Router + Mantine v7.
- **M6** — `api/managers.py`, `api/scripts.py`, `services/scripts.py`, `services/daily_summary.py`, `api/admin.py`, UI admin pages, миграция `m6schema`.

### Добавленные зависимости (накопительно)
- **M2:** `boto3`, `types-boto3`, `python-magic`
- **M3:** `faster-whisper>=1.2.1`
- **M5 backend:** `argon2-cffi>=23.1`, `python-jose[cryptography]>=3.3`, `types-python-jose`
- **M5 frontend:** Next.js 14, Mantine v7, Vitest 1.x, @testing-library/react
- **M4/M6/M7:** новых зависимостей нет

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
| **Микрофон** | MediaRecorder → WebSocket → ChunkBuffer → near-realtime STT | — |

**Сквозной принцип:** каждый провайдер (LLM/STT/CRM) — сменный адаптер за портом;
смена = только конфиг (`base_url`/`model`/`api_key`/выбор адаптера), никаких правок кода.

**WS-auth:** JWT передаётся query-param `?token=...` (браузер не поддерживает `Authorization` header для WS).

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
    audio/      # file_stub, file_source, badge_source, telephony_source, mic_source, mic_protocol
    stt/        # stub_stt, faster_whisper_engine, config, mapping
    analyzer/   # stub_analyzer, openai_compatible, schema, prompt
    crm/        # json_exporter, payload, google_sheets, webhook, bitrix24, registry
  services/     # storage, ingest, normalize, score, auth, scripts, process, daily_summary, mic_buffer
  db/
    models/         # analysis, recording, transcript, manager, script, user
    repositories/   # manager_repo, recording_repo, script_repo
    migrations/versions/  # baseline, core_schema, 4b47e88b70e8 (analysis), m6schema
    session.py
  workers/      # runner.py (run_job)
  config/       # settings.py, kpi.py
  api/          # health, auth, deps, uploads, recordings, managers, scripts, admin, ws_mic
  main.py
backend/tests/  # unit/ contract/ integration/ api/ config/ infra/ db/ adapters/ core/ services/ workers/
frontend/src/
  app/          # login, recordings, recordings/[id], recordings/record, admin/{managers,scripts,summary}
  lib/          # auth.ts (sessionStorage), api.ts, ws.ts (useRecordWs hook)
  test/         # Vitest + @testing-library
infra/
  docker-compose.yml
  config/{providers.yaml,kpi.yaml,weights.yaml}
docs/
  PLAN.md  TZ-audiobadge-mvp.md  dev/tasks/M0–M10.md
```

## 5. Следующий шаг — M9

**Запустить агента:** `Реализуй milestone M9 по промпту docs/dev/implement-milestone.md`

M9 — **Self-host LLM (vLLM + Qwen2.5)** — замена `gpt-4o-mini` на локальную модель под ПДн-требования.
Детали: `docs/dev/tasks/M9-*.md`.

**Перед M9:**
- GPU / объём VRAM под Qwen2.5 (см. открытые вопросы п.3).
- Поднять окружение: `POSTGRES_PORT=5434 docker compose -f infra/docker-compose.yml up -d postgres minio`

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
- WS-захват: `consent_flag=true` обязателен в `start`-сообщении; запись создаётся только при согласии.
