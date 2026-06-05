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
| M1 — Ядро/порты/граф | **Следующий шаг** |
| M2–M10 | Не начато |

### M0 — что сделано (коммит `51cb847`)
- Структура монорепо строго по `docs/PLAN.md §2.2`
- `pyproject.toml`: fastapi, sqlalchemy 2.0, langgraph, pydantic-settings, alembic, ruff, mypy --strict
- `infra/docker-compose.yml`: postgres + minio + caddy (без redis, без vLLM)
- `infra/config/providers.yaml` — STT/LLM/CRM сменные конфигом; `api_key` только из env
- `infra/config/kpi.yaml` — 10 KPI с поведенческими якорями; `infra/config/weights.yaml`
- `app/config/settings.py`: `Settings(BaseSettings)` + `ProvidersConfig` (lru_cache)
- `app/config/kpi.py`: `KpiItem`/`KpiConfig`/`WeightsConfig`, валидация связности весов
- `app/main.py`: `create_app()` + structlog + `GET /health`
- `app/db/`: `DeclarativeBase` + Alembic baseline revision
- `.github/workflows/ci.yml`: lint / typecheck / test + eval (continue-on-error, skip без датасетов)
- **49 тестов**, ruff + mypy --strict — зелёные

### Незакоммиченное (мелочи)
- `.gitignore` расширен агентом (добавлены стандартные Python-паттерны) — не закоммичен
- `uv.lock` — не закоммичен (можно добавить в `.gitignore` или закоммитить, на усмотрение)

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
    core/{ports,domain,pipeline}/   # ← M1 заполнит
    adapters/{audio,stt,analyzer,crm}/
    config/{settings.py,kpi.py}
    api/health.py
    db/{base.py,migrations/}
    main.py
  tests/{unit,contract,integration,api,config,infra,db}/
infra/
  docker-compose.yml
  config/{providers.yaml,kpi.yaml,weights.yaml}
  caddy/Caddyfile
docs/
  PLAN.md
  TZ-audiobadge-mvp.md
  dev/
    implement-milestone.md    # промпт для агента реализации
    generate-dev-plan.md      # промпт-генератор плана
    tasks/README.md + M0–M10  # 72 задачи
.github/workflows/ci.yml
pyproject.toml
.env.example
```

## 5. Следующий шаг — M1

**Запустить агента:**
```
Реализуй milestone M1 по промпту docs/dev/implement-milestone.md
```

M1 собирает автономное ядро: порты (`AudioSource`/`STTEngine`/`Analyzer`/`CRMExporter`),
доменные сущности, SQLAlchemy-модели + миграция, LangGraph-граф стадий
(`normalizing→transcribing→analyzing→scoring→exporting`) с checkpointer, стаб-адаптеры
(включая `BadgeSource`/`TelephonySource`). Внешних ключей не нужно — всё на стабах.

Детали задач: `docs/dev/tasks/M1-core-ports-graph.md`.

## 6. Инструменты разработки

```bash
# виртуальное окружение / запуск (uv установлен)
uv run pytest backend/tests/ -v --ignore=backend/tests/db
uv run pytest backend/tests/db/ -v          # нужен postgres
uv run ruff check backend/
uv run mypy backend/app --strict

# инфраструктура
docker compose -f infra/docker-compose.yml up -d postgres minio
docker compose -f infra/docker-compose.yml down

# миграции
uv run alembic -c backend/alembic.ini upgrade head
uv run alembic -c backend/alembic.ini revision --autogenerate -m "<msg>"
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
