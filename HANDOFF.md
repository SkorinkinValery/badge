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
| **M8 — Экспорт результатов (CRM)** | ✅ | `b69b651` |
| **M9 — Self-host LLM (vLLM + Qwen2.5) + RU-облако fallback** | ✅ | `7c4d90a` |
| **M10 — Data & Metrics (eval_wer, eval_kpi, regression, calibrate, few_shot)** | ✅ | текущий |

**Тесты на текущий момент: 652 backend (изолированная БД `badge_test`, `make test`) + 59 frontend** — зелёные; ruff + mypy --strict — зелёные.

### Что сделано в M10 (последний milestone)
- **`scripts/dataset.py`** — `DatasetEntry`/`GoldenTranscript`/`KpiLabel`/`EntryMeta` Pydantic-схемы; `load_dataset(dir)` — загрузка набора из `datasets/<id>/{meta,golden_transcript,kpi_labels}.json`; валидация KPI-ключей по `kpi.yaml`; пустой/отсутствующий каталог → `[]`.
- **`scripts/eval_wer.py`** — `compute_wer(hypothesis, reference, normalize)` через jiwer; `eval_wer_dataset(dir, hypothesis_fn, normalize)` → `WerResult(n_records, wer, per_record)`.
- **`scripts/eval_kpi.py`** — `compute_kpi_metrics(pred, gold, fact_kpi_ids)` — MAE для scale-KPI, precision/recall/F1 для fact-KPI; `eval_kpi_dataset` — агрегирование по датасету.
- **`scripts/regression_harness.py`** — `compare_metrics(current, baseline, thresholds)` с порогами `wer=0.05, kpi_mae=0.50`; `run_harness` сохраняет baseline при первом запуске, предупреждает о регрессии без raise; пустой датасет → `None` (skip).
- **`scripts/few_shot.py`** — `load_few_shot_examples(dir, n=3)` → `[{transcript, output}]`; пустой датасет → `[]`; инжектируется в промпт через `build_prompt(transcript, few_shot=examples)`.
- **`scripts/calibrate.py`** — `calibrate(candidates, datasets_dir, eval_fn, report_file)` → `CalibrationResult(best_candidate, best_score, ranked)`; сохраняет JSON-отчёт.
- **`datasets/.gitignore`** — исключает аудиофайлы; `pyproject.toml` — `pythonpath = ["backend", "."]`; `.gitignore` — треки `datasets/**/*.wav` вместо `datasets/`.
- **`.github/workflows/ci.yml`** — шаг `regression_harness.py` в eval.
- **Тесты** — `tests/scripts/test_dataset_loader.py` (9), `test_eval_wer.py` (9), `test_eval_kpi.py` (8), `test_regression_harness.py` (7), `test_eval_ci_guard.py` (6), `test_calibrate.py` (5); `tests/adapters/analyzer/test_few_shot.py` (6).

### Новые зависимости в M10
- **backend:** `jiwer>=3.0` (WER-вычисление, уже был в pyproject через M10)

### Что сделано в M9 (предпоследний milestone)
- **`infra/docker-compose.yml`** — сервис `vllm` (профиль `self-host`, GPU-резервация, OpenAI-совместимый порт 8000, том модели).
- **`infra/config/providers.yaml`** — секция `llm_profiles` (cloud / self_host / ru_cloud) с параметрами base_url, model, vram_gb, gpu_memory_utilization.
- **`config/settings.py`** — поле `LLMProviderConfig.structured_output_mode: str` ("json_object" | "guided_json").
- **`adapters/analyzer/openai_compatible.py`** — поддержка `guided_json` через `extra_body` для vLLM; один адаптер для облака и self-host.
- **`adapters/stt/yandex_stt.py`** — `YandexSttEngine(api_key, folder_id)` — Yandex SpeechKit REST, маппинг в `Transcript`.
- **`adapters/stt/sber_stt.py`** — `SberSttEngine(auth_token)` — Sber SaluteSpeech REST.
- **`adapters/analyzer/yandexgpt.py`** — `YandexGptAnalyzer(api_key, folder_id)` — Yandex Foundation Models API.
- **`adapters/analyzer/gigachat.py`** — `GigaChatAnalyzer(auth_token, scope)` — Sber GigaChat OpenAI-compatible API.
- **`adapters/analyzer/ru_llm_base.py`** — общий `parse_kpi_response()` для RU-облако адаптеров.
- **`tests/infra/test_vllm_compose.py`** — 10 тестов compose-конфига vLLM.
- **`tests/adapters/analyzer/test_vllm_guided_json.py`** — 5 тестов guided_json в OpenAICompatibleAnalyzer.
- **`tests/contract/test_ru_stt_engines.py`** — 14 тестов контракта STTEngine (Yandex + Sber).
- **`tests/contract/test_ru_llm_analyzers.py`** — 14 тестов контракта Analyzer (YandexGPT + GigaChat).
- **`tests/integration/test_provider_swappability.py`** — 6 тестов инварианта сменности (stub/cloud/vLLM/RU-cloud).
- **`docs/adr/ADR-001-llm-provider-strategy.md`** — ADR с ПДн-обоснованием и инструкцией переключения.

### Новые зависимости в M9
- Нет новых зависимостей (httpx уже был, vLLM — только в Docker-образе)

### Что сделано в M8 (предпоследний milestone)
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
    migrations/versions/  # baseline, core_schema, 4b47e88b70e8 (analysis), m6schema, cc27a3cf97ac (user.is_active)
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

## 5. Следующий шаг

Все 10 milestone (M0–M10) завершены. MVP-ядро готово.

**✅ Исправлена ошибка галлюцинированного транскрипта при записи с микрофона** (коммит после M10):

**Причина:** `main.py` не инициализировал `app.state.stt_engine` → `_get_stt()` в `ws_mic.py` всегда возвращал `StubSTTEngine`. Стаб выдаёт фиксированную строку `"Добрый день, чем могу помочь? Хорошо, понял вас."` для каждого окна буфера (~10 окон за сессию = ~10 повторений).

**Что исправлено:**
- `main.py` — добавлен `_make_stt_engine(active_stt)` + `app.state.stt_engine` инициализируется из `providers.active_stt` при старте.
- `adapters/stt/config.py` — добавлены anti-hallucination поля: `condition_on_previous_text=False`, `no_speech_threshold=0.6`, `compression_ratio_threshold=2.4`, `log_prob_threshold=-1.0`.
- `adapters/stt/faster_whisper_engine.py` — новые поля передаются в `model.transcribe()`.
- `tests/api/test_stt_engine_init.py` — 5 новых тестов; `tests/adapters/stt/test_stt_config.py` — +4 теста на новые поля конфига.

**✅ Ревизия в 4 роли (Wiring/Production Readiness/Test Coverage/Security) + полное устранение находок:**

- **C1** — `stt_engine`/`analyzer` теперь прокидываются через `build_graph()`/`run_job()` от `app.state` до графа на всех путях запуска (`uploads.py`, `recordings.py`, `ws_mic.py`) — раньше пайплайн всегда работал на стабах независимо от `providers.yaml`.
- **C2** — `main.py:_make_analyzer()` инициализирует реальный `Analyzer` (`openai_compatible`/`yandexgpt`/`gigachat`/`stub`) из `providers.active_llm` и кладёт в `app.state.analyzer`.
- **C3** — устранён риск с `audio/webm`: вместо нарезки по байтовому окну `ws_mic.py` накапливает весь сессионный поток в `audio_accum` и транскрибирует один раз на `stop` — WebM-контейнер остаётся целым.
- **C5** — `websocket.accept()` перенесён ПОСЛЕ проверки JWT (был до — анонимные клиенты могли держать соединение открытым/DoS).
- **C6/W1/W2** — убран silent fallback на стаб при неизвестном провайдере: `_make_stt_engine`/`_make_analyzer` бросают `ValueError`, ошибки конфига логируются (`log.error("providers_config_failed", ...)`).
- **W3/W8/W9** — `assert` → явные проверки; rate limiting на `/api/auth/login` (5 попыток/60с, состояние в `app.state.login_attempts` — НЕ модульный global, чтобы не протекало между тестами); `CORSMiddleware` с `cors_origins` из настроек.
- **W4** — автоудаление по retention теперь реально работает: `_retention_loop()` в lifespan вызывает `purge_expired_recordings` раз в час.
- **Баг в `runner.py` (найден при прогоне тестов, не из ревизии)** — финальное обновление статуса делало `create_engine(db_url)` с `+asyncpg` URL в синхронном контексте → `MissingGreenlet` при каждом завершении джобы (запись навсегда оставалась в `queued`, реальный финальный статус никогда не персистился). Исправлено на `create_engine(sync_url)`.

**Тесты:** весь backend-сьют (639 тестов, без skip — 4) зелёный, включая ранее падавшие из-за отсутствия `jiwer` (он объявлен как extra `eval` в `pyproject.toml` — нужно `uv sync --extra eval`).

**✅ Показ KPI в UI + персист результатов анализа (фикс после ревизии):**

Симптом: в карточке разговора не было видно KPI. Найдено три причины:

- **Schema-баг (критический): любой baseline-анализ падал.** `build_kpi_result_model` делал ВСЕ KPI обязательными, но промпт не запрашивает script-only KPI (`script_compliance`), когда скрипт не назначен → каждая запись падала с `script_compliance Field required`. Исправлено: `build_kpi_result_model(cfg, include_script)` + `applicable_kpis()` фильтруют script-only KPI; `openai_compatible.py` и `ru_llm_base.py` строят модель per-call и итерируют только включённые KPI.
- **Результаты не сохранялись (корень 404): `run_job` сохранял только статус recording.** `TranscriptModel`/`AnalysisModel` не создавались нигде → `/transcript` и `/analysis` всегда 404 → KPI неоткуда взять. Добавлен `_persist_results()` в `runner.py` — идемпотентный upsert transcript + analysis (summary, kpi_json, score, auto_score, verdict, mode, weights_version) после `graph.invoke`.
- **Фронт падал на пустых данных.** Карточка `recordings/[id]` делала `Object.entries(analysis.kpi_json)` даже на ответе `{"detail":"Analysis not found"}` → пустой экран. Переписана: `fetchOk()` глотает не-2xx, корректные empty-state («Анализ ещё не готов», «Транскрипт недоступен»), KPI-чек-лист с человекочитаемыми лейблами, fact-KPI как ✓/✗, scale как `N/10`, крупный балл + вердикт (+/~/-), `stage_error` для `failed`.
- **Новый эндпоинт `GET /api/kpi`** (`api/kpi.py`) отдаёт рубрику (id, label, type, weight, applies_to, include_in_score) из `kpi.yaml`, чтобы фронт показывал лейблы, а не сырые id.

Проверено end-to-end живым аплоадом: запись → `done` → `/analysis` отдаёт 9 baseline KPI (без `script_compliance`), `/transcript` отдаёт 200. Эталонные скрипты грузятся на `admin/scripts` (был и раньше).

**Тесты после этого блока:** backend 644 passed / 4 skipped; frontend 55 passed; ruff (мои файлы) + mypy --strict зелёные.

**✅ Изоляция тестовой БД + единая схема CI + починка миграций (после KPI-фикса):**

Симптом, давший толчок: интеграционные тесты ходили в тот же dev-Postgres `localhost:5434/badge`, что и `make dev`, стирали `user`/`recording` → падал логин админа (`admin`/`admin123` → "Invalid credentials").

- **`infra/docker-compose.test.yml`** (новый) — отдельные эфемерные Postgres (`:5435/badge_test`) и MinIO (`:9100`), проект `badge-test`, `tmpfs`-тома. `backend/tests/conftest.py` (новый, корневой) переопределяет `DATABASE_URL`/`MINIO_*` на тестовые порты ДО импорта тестовых модулей — но только если URL пуст или указывает на dev (`:5434`); явный сторонний URL не трогается.
- **`Makefile`** — `make test` теперь = чистая тестовая БД (`down -v && up --wait`) + pytest; `make test-up`/`test-down`/`test-fast` — управление инфрой отдельно.
- **`.github/workflows/ci.yml`** — job `test` приведён к той же схеме `badge_test` (поднимает `docker-compose.test.yml` вместо инлайновых `services: postgres` на `:5432`), плюс шаг валидации миграций (см. ниже).
- **Починены миграции `alembic upgrade head` с нуля** — `core_schema` (`b0d89f191dbd`) имела пустой `upgrade(): pass`, на чистой БД деплой падал (`relation "analysis" does not exist`). Дописан полный `op.create_table`/`op.drop_table` для всех 7 core-таблиц (БЕЗ колонок, добавляемых позже: `analysis.auto_score/corrected_by`, `script.active_version_id`, `recording.duration_seconds`, `user.is_active`). Проверено сравнением со схемой `Base.metadata.create_all` — побайтово идентичны.
- **Починен `env.py`** — не импортировал `app.db.models` → `target_metadata` был пуст → `alembic revision --autogenerate` выдавал мусор (предлагал дропнуть все таблицы). Добавлен `import app.db.models`; теперь autogenerate на смигрированной БД даёт пустой diff — модели и миграции в синхроне, `make revision m="..."` снова можно использовать как обычно.

**Тесты после этого блока:** backend 648 passed; CI-job `test` локально прогнан end-to-end (инфра → валидация миграций → pytest) — зелёный; dev-БД `:5434` больше не трогается тестами.

**✅ Исправлен критический баг: пайплайн всегда обрабатывал тишину вместо реального аудио + добавлена UI-форма загрузки записей** (коммиты `4c2ec2a`, `6286b5f`):

**Причина:** узел `normalizing` в `core/pipeline/nodes.py` всегда вызывал `FileStubSource()`, игнорируя `recording.audio_path` из БД, и клал в `audio_payload["audio_data"]` placeholder-строку `"<bytes>"`. Узел `transcribing` не находил там `bytes` и подставлял `b"\x00" * 100` (тишину) → STT-движок транскрибировал тишину → пустой транскрипт → анализ по пустому тексту → счёт 0/100 на любой реальной записи. Баг касался обоих каналов: `channel=file` (как описано) и `channel=mic` (вторично — `audio_accum` из `ws_mic.py` никогда не загружался в MinIO, `recording.audio_path` оставался `None`).

**Что исправлено:**
- `core/pipeline/state.py` — добавлены поля `audio_path`, `manager_id`, `consent_flag`, `channel`.
- `core/pipeline/nodes.py` / `graph.py` — `make_nodes`/`build_graph` принимают `storage: ObjectStorage | None`; `normalizing` при наличии `storage`+`audio_path` вызывает уже существующие (написанные ещё в M2, но не подключённые к графу) `normalize_audio()`/`FileSource` и кладёт в `audio_payload` ключ нормализованного файла в MinIO (а не сырые байты — чтобы не раздувать LangGraph/Postgres checkpoint); `transcribing` дозагружает реальные байты через `FileSource.fetch()`. Без `storage`/`audio_path` (юнит-тесты, легаси-записи) — прежнее поведение на стабах.
- `workers/runner.py` — перед `graph.invoke` запрашивает `RecordingRepository.get(recording_id)`, кладёт реальные `audio_path`/`manager_id`/`consent_flag`/`channel` в `initial_state`; принимает и прокидывает `storage`.
- `main.py` — инициализирует `app.state.storage = ObjectStorage(...)` при старте; `uploads.py`/`recordings.py`/`ws_mic.py` прокидывают `storage` в `run_job`/`_kick_pipeline`.
- `ws_mic.py` — добавлен `_persist_mic_audio()`: при `stop` накопленные байты `audio_accum` загружаются в MinIO (`make_key(recording_id, "original", ".webm")`), `recording.audio_path` обновляется в БД — устранён вторичный mic-баг.
- **Новая UI-страница** `frontend/src/app/(app)/recordings/upload/page.tsx` — форма загрузки готового аудиофайла (выбор менеджера, согласие `consent_flag`, файл) с вызовом `POST /api/uploads`; добавлена ссылка в навигацию (`(app)/layout.tsx`).
- Тесты: `test_normalizing_node.py` (новый), расширены `test_transcribing_node.py`, `test_runner.py` (реальный WAV через MinIO + `CapturingSTTEngine`, проверка что байты ≠ стаб), `test_ws_mic.py` (проверка `audio_path` после `stop`), `upload-page.test.tsx`.

Проверено живым e2e-прогоном на реальной записи `a5e05a52-...`: пере-запуск пайплайна дал `/transcript` на 2829 символов / 71 сегмент с точным русским текстом разговора (бронирование детского праздника в «Хиропарк»), `/analysis` — score 70/100 с KPI, обоснованными цитатами из реального звонка (раньше — пустой транскрипт и 0/100).

**✅ Исправлена 404 на `/admin/managers/new` — добавлена форма создания менеджера:**

**Причина:** кнопка «Добавить менеджера» на `frontend/src/app/(app)/admin/managers/page.tsx` уже делала `router.push("/admin/managers/new")`, но самой страницы/роута не существовало.

**Что сделано:**
- Новая страница `frontend/src/app/(app)/admin/managers/new/page.tsx` — форма (ФИО, должность, Device ID опционально, выбор скрипта по умолчанию из активных `/api/scripts`), `POST /api/managers`, редирект на список менеджеров после успеха, читаемые ошибки (`409 device_id already in use` и т.п.) — по образцу `recordings/upload/page.tsx`.
- Тесты `frontend/src/test/new-manager-page.test.tsx` (4) — фильтр активных скриптов, дизейбл кнопки до заполнения обязательных полей, сабмит/редирект, отображение ошибки.

**Тесты:** frontend 63 passed (было 59); ruff/mypy не затронуты (фронтенд-таск).

**Возможные дальнейшие шаги:**
- Detail-страница менеджера `admin/managers/[id]` тоже отсутствует (список делает `router.push(`/admin/managers/${m.id}`)`) — аналогичная 404, не входила в эту задачу, но стоит проверить.

**Возможные дальнейшие шаги:**
- Раскатка на staging/prod (Docker Compose → k8s или аналог).
- Наполнение `datasets/` реальными размеченными звонками и запуск `scripts/eval_wer.py` + `scripts/eval_kpi.py`.
- Калибровка промптов: `scripts/calibrate.py` с реальным `eval_fn`.
- Self-host vLLM: `docker compose --profile self-host up vllm`.
- Bitrix24: задать `field_mapping` в `providers.yaml`, переключить `active_crm: bitrix24`.

## 6. Команды разработки

```bash
# Порт 5432 занят системным Postgres → badge-postgres на 5434, MinIO на 9000
POSTGRES_PORT=5434 docker compose -f infra/docker-compose.yml up -d postgres minio
docker compose -f infra/docker-compose.yml down

# Все тесты — на ИЗОЛИРОВАННОЙ тестовой БД (Postgres :5435/badge_test, MinIO :9100),
# НЕ трогает dev-данные на :5434. Поднимает/гасит инфру сама:
make test
# или вручную: make test-up && uv run pytest backend/tests/ -q && make test-down

# Линт/типы
uv run ruff check backend/
uv run mypy backend/app --strict

# Миграции (на dev-БД :5434)
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
