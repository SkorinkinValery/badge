# HANDOFF

## 1. Цель
- Спроектировать и затем реализовать MVP «Аудиобейдж» — расширяемое ядро AI-анализа звонков менеджеров (аудио → текст → summary → KPI → выгрузка в CRM) по ТЗ `docs/TZ-audiobadge-mvp.md`.
- Выход: детальный план (`docs/PLAN.md`, ГОТОВ) + пошаговая декомпозиция по этапам с TDD (`docs/dev/tasks/`, ГОТОВА) + последующая реализация. Развилки «на подумать» (§6 ТЗ) выбраны с аргументацией.

## 2. Текущее состояние
- `docs/PLAN.md` **утверждён** и обновлён под дешёвый/быстрый старт при сохранении ports & adapters (см. §4 — пересмотр решения).
- **Пошаговый TDD-план разработки сгенерирован:** `docs/dev/tasks/` — `README.md` (индекс) + 11 шардов `M0…M10`, **72 задачи** по шаблону (Цель / Зависит от / Затрагивает / TDD red→green→refactor / Слой тестов / DoD / Acceptance / Заметки по портам-конфигу). Промпт-генератор: `docs/dev/generate-dev-plan.md`.
- **Кода нет**, реализация не начата, M0 не запущен.
- Принятые решения (актуальные):
  - **Сквозной принцип:** каждый внешний провайдер (LLM/STT/CRM-экспорт) — сменный адаптер за портом; дешёвый/облачный вариант (MVP) и локальный (перспектива) различаются **только конфигом** (`base_url`/`model`/`api_key`/выбор адаптера), не кодом. Технологии старта — недорогие/бесплатные.
  - **STT — self-host** faster-whisper (бесплатно, приватно; аудио не покидает периметр уже на MVP).
  - **LLM — облако** через OpenAI-совместимый API, по умолчанию **`gpt-4o-mini`** (structured/JSON output). Self-host **vLLM + Qwen2.5** — целевое решение, **следующий шаг после MVP** (под ПДн). RU-облако (YandexGPT/GigaChat) — доп. fallback.
  - **CRM/экспорт — дефолт MVP `GoogleSheetsExporter`** (бесплатно, видимый результат без CRM-аккаунта); `JSONExporter`/`GenericWebhookExporter`/`Bitrix24Exporter` — опции/перспектива.
  - **Оркестрация — LangGraph** (стадии = узлы графа, состояние + checkpointer в Postgres, retry/условные переходы) — вместо самописной state machine и Celery+Redis.
  - Стек: Python 3.11 + FastAPI, PostgreSQL + SQLAlchemy 2.0 + Alembic, MinIO, Next.js + Mantine, Docker Compose, JWT + argon2 (роли admin/viewer).
  - Архитектура: ports & adapters + единый пайплайн-граф для всех источников.
- Память проекта (`~/.claude/projects/-home-arelaw-Projects-badge/memory/`) обновлена под пересмотр: `hosting-self-host-decision.md`, `core-autonomous-first.md`, индекс `MEMORY.md`.

## 3. Артефакты и факты
- Файлы (вне git пока: `HANDOFF.md`, `docs/PLAN.md`, `docs/dev/`): `docs/TZ-audiobadge-mvp.md` (ТЗ), `docs/PLAN.md` (план), `docs/dev/generate-dev-plan.md` (промпт-генератор), `docs/dev/tasks/` (72 задачи), `.gitignore`.
- Порты: `AudioSource` (FileSource, MicSource — MVP; Badge/Telephony — стабы), `STTEngine` (FasterWhisper; Yandex/Sber — опц. fallback), `Analyzer` (`OpenAICompatibleAnalyzer` — один адаптер: облако `gpt-4o-mini` / локальный vLLM / RU-облако через `base_url`/`model`/`api_key`), `CRMExporter` (`GoogleSheetsExporter` дефолт; JSON, GenericWebhook, Bitrix24).
- Пайплайн — **LangGraph-граф**, стадии-узлы: `normalizing → transcribing → analyzing → scoring → exporting`. Статусы `uploaded → queued → … → done` (+`failed`, retry) — состояние графа, персист через checkpointer (Postgres), проецируется в `recording.status`.
- Config-driven: `kpi.yaml` (id, label, type scale|fact, weight, anchors, applies_to, include_in_score), `weights.yaml` (нормализация baseline vs script-based), `providers` (STT/LLM `base_url`/`model`/`api_key`/CRM/язык=ru).
- Модель данных: manager, script + script_ver (версионирование), recording (consent_flag, retention_until, status), transcript (segments jsonb, detected_language), analysis (kpi_json, score 0–100, verdict +/~/-, mode baseline|script, weights_version, script_version_id), user.
- Скоринг — чистая функция `kpi_json + weights → score + verdict`. Два режима выбираются авто: есть активный скрипт у менеджера → script-based, иначе baseline.
- Этапы: A (M0 каркас, M1 ядро/порты/граф, M2 FileSource+MinIO+ffmpeg, M3 STT, M4 Analyzer облако `gpt-4o-mini` + скоринг + `JSONExporter` — сквозной пайплайн) → B (M5 auth+UI, M6 админка, M7 MicSource near-realtime через MediaRecorder→WebSocket) → C (M8 экспорт — `GoogleSheetsExporter` первым, M9 self-host LLM vLLM/Qwen + RU-fallback, M10 датасет 16–20ч + метрики WER/F1 + regression-харнесс).
- Юр-факт (драйвер решений): РБ; голос + содержание = ПДн; РФ — надлежащая юрисдикция; США/OpenAI — нет → отсюда self-host LLM как целевое решение.

## 4. Пересмотр решения (заменяет прежний «полный self-host без ключей»)
- Прежний хэндофф фиксировал **полный self-host** (faster-whisper + Qwen/vLLM на своей GPU) и сборку ядра **без внешних API-ключей**. По указанию пользователя (дешёвый/быстрый старт, согласовано с §3/§4.6/§6 ТЗ) **решение пересмотрено** — принцип ports & adapters сохранён, меняются только техвыборы:
  - STT остаётся self-host (приватно, аудио в периметре).
  - LLM на MVP — **облако `gpt-4o-mini`** за портом `Analyzer`; self-host vLLM/Qwen — целевой пост-MVP шаг, подключается **только конфигом**.
  - Оркестрация — LangGraph (не Celery+Redis). Дефолтный экспорт — Google Sheets (не JSONExporter).
- **ПДн-риск облачного LLM** (транскрипт уходит провайдеру) принят на MVP **только** на пилотных/обезличенных данных с согласием; целевое снятие риска — переход на self-host LLM (M9).
- Чего НЕ делать: не использовать платные премиум-STT (Deepgram/AssemblyAI) как основной путь — только опция; не отправлять боевые ПДн в глобальное облако без согласия/обезличивания.

## 5. Следующий шаг
- Запустить **M0** по `docs/dev/tasks/M0-skeleton.md`: scaffold монорепо (`backend/`, `frontend/`, `infra/`, `scripts/`), Docker Compose (**postgres/minio — без redis**), pydantic-settings + `infra/config/kpi.yaml`, Alembic baseline, CI (ruff + mypy + pytest), **TDD с самого начала**. Не зависит от открытых вопросов. Ожидается команда пользователя «начинаем».

## 6. Риски и открытые вопросы
- **Облачный LLM:** подтвердить провайдера (OpenAI / совместимый), бюджет на `gpt-4o-mini` и допустимость отправки транскриптов в облако на пилоте.
- **Google Sheets:** нужен сервисный аккаунт + доступ к таблице для `GoogleSheetsExporter`.
- **GPU VRAM** под пилот не определён → на MVP нужен только под whisper; объём решает размер Qwen2.5 на этапе self-host LLM (M9).
- **Bitrix24** не подтверждён (целевая сущность/маппинг полей) — для следующего шага; на MVP экспорт = Google Sheets.
- **Retention** (срок хранения записей) не задан — нужен для `retention_until` и джобы удаления.
- Качество KPI требует калибровки на датасете 16–20 ч (его пока нет).
- Согласие/уведомление клиентов готовит заказчик (вне системы).
- **Расхождение docs/PLAN.md ↔ ТЗ по дефолтной CRM** (ТЗ — Bitrix24, docs/PLAN.md — Google Sheets): приоритет у docs/PLAN.md, зафиксировано в `docs/dev/tasks/README.md` §6.
