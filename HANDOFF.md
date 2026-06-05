# HANDOFF

## 1. Цель
MVP «Аудиобейдж» — расширяемое ядро AI-анализа звонков менеджеров (аудио → текст → summary → KPI → выгрузка).
Архитектура: **ports & adapters**. Принцип старта: **недорогое/бесплатное** (faster-whisper, gpt-4o-mini, Google Sheets).

## 2. Текущее состояние

| Артефакт | Статус |
|----------|--------|
| `docs/PLAN.md` | Утверждён |
| `docs/dev/tasks/` (72 задачи, M0–M10) | Готово |
| **M0 — Каркас** | ✅ Завершён, закоммичен `51cb847` |
| **M1 — Ядро/порты/граф** | ✅ Завершён (не закоммичен) |
| M2–M10 | Не начато |

### M1 — что сделано (не закоммичено)

- **T1** — Доменные сущности: `Recording`, `Transcript`, `Analysis`, `Manager`, `Script`, `User` + Enum'ы (`RecordingStatus`, `Verdict`, `AnalysisMode`, `UserRole`) — `app/core/domain/`
- **T2** — Порты (Protocol/`runtime_checkable`): `AudioSource`, `STTEngine`, `Analyzer`, `CRMExporter` + DTO (`AudioPayload`, `AnalysisResult`, `ExportResult`) — `app/core/ports/`
- **T3** — Контракт-тесты портов: `backend/tests/contract/` (параметризованные харнессы для каждого порта)
- **T4** — Стаб-адаптеры: `FileStubSource`, `StubSTTEngine`, `StubAnalyzer`, `JSONExporter`; стабы перспективы `BadgeSource`/`TelephonySource` (бросают `NotImplementedError`)
- **T5** — SQLAlchemy 2.0 модели: `ManagerModel`, `ScriptModel`, `ScriptVerModel`, `RecordingModel`, `TranscriptModel`, `AnalysisModel`, `UserModel` + репозитории + Alembic миграция `core_schema`
- **T6** — LangGraph граф: `normalizing→transcribing→analyzing→scoring→exporting`, ветка `failed`, `MemorySaver`/`PostgresSaver` checkpointer — `app/core/pipeline/`
- **T7** — Воркер-раннер: `app/workers/runner.py` — `run_job(recording_id, db_url)` с Postgres checkpointer, идемпотентный resume
- **171 тест** (было 49), ruff + mypy --strict — зелёные

### Добавленные зависимости
- `langgraph-checkpoint-postgres==3.1.0` (psycopg + psycopg-pool) — добавлены через `uv add`

### Postgres в dev-окружении
Порт 5432 занят системным Postgres. Badge-postgres запускается на **5434**:
```bash
POSTGRES_PORT=5434 docker compose -f infra/docker-compose.yml up -d postgres
DATABASE_URL=postgresql+asyncpg://badge:badge@localhost:5434/badge uv run pytest backend/tests/ -v
```

## 3. Ключевые технологические решения

| Область | Выбор MVP | Целевое (после MVP) |
|---------|-----------|---------------------|
| **STT** | faster-whisper self-host (бесплатно, офлайн) | — |
| **LLM** | `gpt-4o-mini` через OpenAI-совместимый API | vLLM + Qwen2.5 (M9, под ПДн) |
| **CRM/экспорт** | `GoogleSheetsExporter` | Bitrix24 / GenericWebhook |
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
backend/
  app/
    core/
      domain/     # Recording, Transcript, Analysis, Manager, Script, User, enums
      ports/      # AudioSource, STTEngine, Analyzer, CRMExporter + DTO
      pipeline/   # state.py, nodes.py, graph.py (LangGraph)
    adapters/
      audio/      # file_stub.py, badge_source.py, telephony_source.py
      stt/        # stub_stt.py
      analyzer/   # stub_analyzer.py
      crm/        # json_exporter.py
    db/
      models/     # 7 ORM-моделей + __init__.py
      repositories/  # ManagerRepository, RecordingRepository
      migrations/versions/  # baseline + core_schema
    workers/      # runner.py (run_job)
    config/       # settings.py, kpi.py
    api/          # health.py
    main.py
  tests/
    unit/ contract/ integration/ api/ config/ infra/ db/
    adapters/ core/{domain,ports,pipeline}/ workers/
infra/
  docker-compose.yml
  config/{providers.yaml,kpi.yaml,weights.yaml}
docs/
  PLAN.md  TZ-audiobadge-mvp.md
  dev/tasks/M0–M10.md
```

## 5. Следующий шаг — M2

**Запустить агента:**
```
Реализуй milestone M2 по промпту docs/dev/implement-milestone.md
```

M2 собирает `FileSource` (upload API multipart mp3/wav/m4a, валидация) → MinIO → нормализация ffmpeg → job (статус `queued`).
Детали: `docs/dev/tasks/M2-filesource-upload.md`.

**Перед M2 нужно:**
1. Закоммитить M1 (`git add backend/ pyproject.toml && git commit`)
2. Убедиться что MinIO поднят: `docker compose -f infra/docker-compose.yml up -d minio`

## 6. Инструменты разработки

```bash
# виртуальное окружение / запуск (uv установлен)
# Для тестов без БД:
uv run pytest backend/tests/ --ignore=backend/tests/db -v

# Для тестов с БД (badge-postgres на 5434):
POSTGRES_PORT=5434 docker compose -f infra/docker-compose.yml up -d postgres
DATABASE_URL=postgresql+asyncpg://badge:badge@localhost:5434/badge uv run pytest backend/tests/ -v

uv run ruff check backend/
uv run mypy backend/app --strict

# инфраструктура
POSTGRES_PORT=5434 docker compose -f infra/docker-compose.yml up -d postgres minio
docker compose -f infra/docker-compose.yml down

# миграции
DATABASE_URL=postgresql+asyncpg://badge:badge@localhost:5434/badge uv run alembic -c backend/alembic.ini upgrade head
DATABASE_URL=postgresql+asyncpg://badge:badge@localhost:5434/badge uv run alembic -c backend/alembic.ini revision --autogenerate -m "<msg>"
```

## 7. Открытые вопросы к заказчику

1. **Облачный LLM**: провайдер (OpenAI / совместимый), бюджет `gpt-4o-mini`, допустимость отправки транскриптов в облако на пилоте (`LLM_API_KEY` в env — нужен на M4).
2. **Google Sheets** (M8): сервисный аккаунт + ID таблицы.
3. **GPU под пилот**: только под faster-whisper на MVP; объём VRAM определит размер Qwen2.5 на M9.
4. **Bitrix24**: целевая сущность и маппинг полей — для M8+.
5. **Retention**: срок хранения записей для `retention_until` и джобы удаления.
6. Согласие/уведомление клиентов готовит заказчик (вне системы).

## 8. Юридический контекст (РБ, неизменно)

Голос + содержание разговора = ПДн. Трансграничная передача в США (OpenAI) без согласия каждого клиента — нарушение. Поэтому:
- STT self-host с самого начала (аудио не покидает периметр).
- LLM облако (`gpt-4o-mini`) — на пилотных/обезличенных данных с согласием; full self-host vLLM/Qwen — целевое решение (M9).
- РФ — надлежащая юрисдикция (RU-облако как fallback допустимо).
