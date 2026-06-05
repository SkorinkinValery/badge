# План разработки: MVP «Аудиобейдж» — AI-анализ коммуникаций менеджеров

## Context (зачем и что делаем)

Greenfield-проект. В репозитории только ТЗ (`docs/TZ-audiobadge-mvp.md`) и пустой `.gitignore`.
Цель MVP — **расширяемое ядро** (ports & adapters), которое превращает аудио разговора в
`текст → summary → KPI-оценку → выгрузку в CRM`, причём источник аудио и провайдеры STT/LLM/CRM
сменные. Вход на MVP — без бейджей: микрофон ПК (near-realtime) и загрузка файлов. Пилот: 2–3
менеджера, 16–20 ч переговоров для калибровки.

**Сквозной принцип (ports & adapters):** каждый внешний провайдер — **LLM, STT, CRM/экспорт** — это
сменный адаптер за портом. Дешёвый/облачный вариант на MVP и локальный/самостоятельный вариант на
перспективу различаются **только конфигом** (`base_url`/`model`/`api_key`/выбор адаптера), **не кодом**.
Технологический принцип старта — **недорогое или бесплатное**: faster-whisper (STT), gpt-4o-mini (LLM),
Google Sheets (экспорт); без платных премиум-сервисов (Deepgram/AssemblyAI и т.п.).

**Развилка §6 ТЗ — приватность (ПДн):** записи реальных клиентов = ПДн, трансграничная передача в
недружественную юрисдикцию практически нелегальна без явного согласия каждого клиента. Поэтому
**полный self-host LLM** (vLLM/Qwen) зафиксирован как **целевое решение — следующий шаг после MVP**;
RU-облако (РФ признана РБ надлежащей юрисдикцией) — дополнительный fallback. На MVP анализ идёт через
дешёвую облачную модель (gpt-4o-mini) за портом `Analyzer` — переключение на локальную модель не
требует правок кода. **STT с самого старта self-host** (whisper): аудио и транскрипты не покидают
периметр уже на MVP. Это упрощает и будущую интеграцию с локальной телефонией (А1) через порт
`TelephonySource`.

---

## 1. Выбор стека по пунктам «на подумать» (с аргументацией)

| Область               | Выбор                                                                                                                                             | Почему                                                                                                                                                                                                                           |
|-----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Хостинг AI**        | **STT — self-host; LLM — облако (gpt-4o-mini) на MVP, self-host (vLLM/Qwen) целевой**; RU-облако как fallback                                       | Дешёвый/быстрый старт: аудио (ПДн) не покидает периметр уже на MVP (whisper self-host), анализ идёт дешёвой облачной моделью за сменным портом. Полный self-host LLM — следующий шаг под юр-требование ПДн.                       |
| **STT**               | **faster-whisper** (self-host, GPU/CPU) за портом `STTEngine`; опциональный fallback — RU-облако (Yandex SpeechKit/Sber)                            | **Бесплатно и приватно** (офлайн), таймкоды по сегментам, `initial_prompt` под лексику (товары/имена). Платные облачные STT (Deepgram/AssemblyAI) — не основной путь, только опция. Размер модели (`large-v3`/`medium`) — по GPU. |
| **LLM (KPI/summary)** | **Облако через OpenAI-совместимый API, по умолчанию `gpt-4o-mini`** (structured/JSON output по Pydantic-схеме) за портом `Analyzer`; целевой self-host — **vLLM + Qwen2.5** (после MVP); доп. fallback — YandexGPT/GigaChat | Дёшево и быстро стартовать; structured output даёт схемно-валидный JSON. OpenAI-совместимый контракт → **один адаптер** для облака, локального vLLM и RU-облака — переключение только конфигом (`base_url`/`model`/`api_key`), без правок кода. |
| **Бэкенд**            | **Python 3.11 + FastAPI**                                                                                                                         | ML/STT-экосистема нативно, async, WebSocket для микрофона.                                                                                                                                                                       |
| **Оркестрация пайплайна** | **LangGraph** (стадии — узлы графа, состояние + checkpointer в Postgres, retry/условные переходы); фоновый прогон — лёгкий воркер-процесс     | Явный граф стадий `normalizing→transcribing→analyzing→scoring→exporting` и встроенное состояние/checkpointing вместо самописной state machine и Celery-обвязки. LangGraph (а не LangChain): нужен именно граф стадий с персистентным состоянием, а не цепочка вызовов LLM. |
| **БД**                | **PostgreSQL + SQLAlchemy 2.0 + Alembic**                                                                                                         | Реляционная модель (§10 ТЗ), миграции, версионирование скриптов/весов.                                                                                                                                                           |
| **Хранилище аудио**   | **MinIO** (S3-совместимое, self-host)                                                                                                             | Аудио остаётся в периметре; тот же S3-API, что и облако, — миграция тривиальна.                                                                                                                                                  |
| **Реалтайм-микрофон** | Браузер **MediaRecorder → WebSocket → буфер чанков → near-realtime STT**                                                                          | Кроссплатформенно, без desktop-агента; контракт WS спроектируем под будущий полноценный стриминг.                                                                                                                                |
| **Фронтенд**          | **Next.js (App Router) + Mantine**                                                                                                                | UI и админка в одном приложении с role-роутами; Mantine даёт готовые таблицы/формы/даты для админки (быстрее MVP). Альтернатива — shadcn/ui.                                                                                     |
| **Аутентификация**    | **JWT (OAuth2 password) + argon2**, 2 роли (admin/viewer)                                                                                         | Просто, как в §4.8 ТЗ; без сложного RBAC.                                                                                                                                                                                        |
| **CRM / экспорт**     | Дефолт MVP — **`GoogleSheetsExporter`** за портом `CRMExporter`; `JSONExporter`/`GenericWebhookExporter`/`Bitrix24Exporter` — опции/перспектива   | На первое время CRM не подключаем: Google Sheets **бесплатен** и сразу даёт заказчику видимый результат без CRM-аккаунта. Порт позволяет заменить Sheets на реальную CRM (Bitrix24 и др.) **без правок ядра**.                    |
| **Деплой**            | **Docker Compose** на одной VPS (GPU — под whisper)                                                                                               | Под пилот достаточно; сервисы MVP: api, worker, postgres, minio, frontend, caddy (TLS). `vLLM` добавляется на этапе self-host LLM (после MVP).                                                                                                                                 |

> **GPU-бюджет (на подтверждение):** на MVP на GPU работает только faster-whisper (`large-v3` ≈ 4–5 ГБ VRAM;
> для пилота допустим CPU/`medium`) — LLM-анализ идёт в облаке (gpt-4o-mini), VRAM под него не нужна.
> На этапе **self-host LLM** добавляется Qwen2.5 через vLLM (14B-AWQ ≈ 16–18 ГБ → ~24 ГБ карта RTX 4090/L4;
> минимум — 7B); при дележе одной карты STT и LLM выполняются последовательно в стадиях графа.

---

## 2. Архитектура (ports & adapters)

### 2.1 Порты (ядро не зависит от реализаций)

- **`AudioSource`** — нормализованный аудиопоток/файл + метаданные (менеджер, канал, время, согласие).
  Адаптеры: `FileSource`, `MicSource` (MVP); `BadgeSource`, `TelephonySource` (заглушки-стабы на перспективу).
- **`STTEngine`** — `transcribe(audio) → Transcript(segments[], timecodes, detected_language)`.
  Адаптеры: `FasterWhisperEngine` (MVP), `YandexSttEngine`/`SberSttEngine` (fallback).
- **`Analyzer`** — `analyze(transcript, script?) → AnalysisResult(summary, kpi_json)`.
  Адаптер: `OpenAICompatibleAnalyzer` — на MVP облако `gpt-4o-mini`, переключается на локальный vLLM/Qwen
  и RU-облако **только конфигом** (`base_url`/`model`/`api_key`).
- **`CRMExporter`** — `export(analysis, recording) → ExportResult`.
  Адаптеры: `GoogleSheetsExporter` (дефолт MVP); `JSONExporter`, `GenericWebhookExporter`,
  `Bitrix24Exporter` (опции/перспектива — реальная CRM подключается без правок ядра).

### 2.2 Структура монорепозитория

```
backend/
  app/
    core/
      ports/        # AudioSource, STTEngine, Analyzer, CRMExporter (Protocol/ABC)
      domain/       # сущности: Recording, Transcript, Analysis, Manager, Script, User
      pipeline/     # LangGraph-граф стадий + состояние/checkpointer
    adapters/
      audio/  stt/  analyzer/  crm/   # crm: google_sheets (дефолт), json, webhook, bitrix24
    services/       # use-cases: ingest, process, score, export, daily_summary
    api/            # FastAPI-роутеры: uploads, recordings, ws_mic, managers, scripts, admin, auth
    workers/        # фоновый прогон LangGraph-графа (job-раннер)
    db/             # SQLAlchemy-модели, репозитории, Alembic
    config/         # pydantic-settings + загрузчик kpi.yaml/weights.yaml/providers
    main.py
  tests/
frontend/           # Next.js (UI + админка)
infra/              # docker-compose.yml, caddy, config/{kpi.yaml,weights.yaml,providers.yaml}
scripts/            # eval_wer.py, eval_kpi.py, regression_harness.py, calibrate.py
datasets/           # размеченный eval-набор, golden-транскрипты (крупные файлы — в .gitignore)
docs/               # ТЗ + ADR-решения
```

### 2.3 Пайплайн как LangGraph-граф (единый для всех источников)

Пайплайн — **LangGraph-граф**, стадии — узлы:
`normalizing → transcribing → analyzing → scoring → exporting`.
Статусы записи (`uploaded → queued → normalizing → … → exporting → done`, + `failed` на любой стадии:
сохраняем стадию, ошибку, счётчик retry) — это **состояние графа (`State`)**, персистится через
**checkpointer** (Postgres) и проецируется в поле `recording.status`. Узлы вызывают порты
(`STTEngine`, `Analyzer`, `CRMExporter`); retry и ветка `failed` описаны рёбрами/условными переходами
графа. Источник лишь кладёт job — дальше граф один для всех источников (это и есть «единый контракт»
из §3.1 ТЗ). Микрофон в MVP — near-realtime: буфер чанков → узел STT. Фоновый прогон графа выполняет
лёгкий воркер-процесс.

### 2.4 Config-driven (не хардкод)

- **`kpi.yaml`** — список KPI:
  `id, label, type (scale|fact), weight, anchors[], applies_to (baseline|script), include_in_score`.
  Поведенческие якоря закладываем сразу (снижают разброс/галлюцинации LLM — апгрейд №2 из §12 ТЗ).
- **`weights.yaml`** — веса + правило нормализации под доступный набор пунктов (чтобы baseline и
  script-based баллы были сопоставимы; §4.5 ТЗ).
- **`providers`** (env/yaml) — активный STT, LLM (`base_url`/`model`/`api_key`), CRM, язык по умолчанию (ru).

---

## 3. Модель данных (SQLAlchemy + Alembic, по §10 ТЗ)

```
manager     id, ФИО, должность, device_id, активен, default_script_id?
script      id, название, активен                         # «голова»
script_ver  id, script_id, версия, контент, привязка_KPI  # версионирование для воспроизводимости
recording   id, manager_id, дата/время, канал, consent_flag, audio_path, status,
            stage_error?, retention_until                  # retention_until — под юр-требование удаления
transcript  id, recording_id, текст, segments(jsonb), detected_language
analysis    id, recording_id, summary, kpi_json(jsonb), score, verdict(+/~/-),
            mode(baseline|script), script_version_id?, weights_version
user        id, логин, argon2_hash, роль(admin|viewer)
```

Доступ к записям ограничен ролью; `consent_flag` обязателен для боевых записей; джоба чистит
просроченные `retention_until` (юр-момент §8 ТЗ).

---

## 4. Анализ (ядро ценности) и скоринг

- **Строгий JSON (MVP):** structured/JSON output OpenAI-совместимого API (`gpt-4o-mini`, `response_format`
  по Pydantic-схеме `KpiResult`) → схемно-валидный вывод. На self-host тот же контракт даёт vLLM
  `guided_json` по той же схеме — путь переключается конфигом, схема одна.
- **Промпт:** system-роль + рубрика с поведенческими якорями на каждый KPI + требование цитаты-доказательства
  из транскрипта на каждый пункт + few-shot из размеченного датасета.
- **Два режима (выбор автоматически):** есть активный скрипт у менеджера → *script-based* (baseline +
  строгая сверка с эталоном, поиск нарушений регламента); нет → *baseline* (generic-рубрика, работает всегда).
- **Скоринг** — чистая функция `kpi_json + weights → score 0–100 + verdict`. Нормализация весов под
  доступные пункты; в `analysis` пишем `weights_version` и `script_version_id` для воспроизводимости.
- **Длинные звонки** (перспектива): интерфейс `Analyzer` спроектировать под map-reduce по чанкам.

---

## 5. Этапы разработки (автономность ядра — в первую очередь)

### Фаза A — Фундамент (ядро за портами; M0–M3 автономны, провайдеры — сменные конфигом)

- **M0. Каркас:** монорепо, Docker Compose (postgres/minio), pydantic-settings + `kpi.yaml`,
  Alembic baseline, CI (lint + tests).
- **M1. Ядро:** порты + доменные сущности + LangGraph-граф стадий (состояние/checkpointer) + стаб-адаптеры.
- **M2. `FileSource`:** upload API (multipart, mp3/wav/m4a, валидация) → MinIO → нормализация (ffmpeg) → job.
- **M3. STT:** `FasterWhisperEngine` (self-host) → `transcript` с таймкодами. *Полностью офлайн.*
- **M4. Анализ+скоринг:** `OpenAICompatibleAnalyzer` на облаке (`gpt-4o-mini`, structured/JSON output) → summary + KPI;
  движок скоринга (baseline). Для офлайн-разработки/CI — стаб-Analyzer (и опция локального vLLM) за тем же портом;
  экспорт на этом этапе — `JSONExporter`. *Сквозной пайплайн собран за портами, провайдер меняется конфигом.*

### Фаза B — Продуктовая поверхность

- **M5. Auth + минимальный UI:** список записей (статусы) + карточка (плеер + транскрипт + summary +
  KPI-таблица с цитатами + балл) + ручная корректировка оценки (для разметки/калибровки).
- **M6. Админка:** менеджеры (CRUD) + загрузка/версионирование скриптов + включение *script-based*-режима +
  дневная сводка (кол-во/длительность/средний балл/% по KPI/нарушения; фильтры менеджер+дата).
- **M7. `MicSource`:** реалтайм-захват (MediaRecorder → WebSocket → буфер → near-realtime STT).

### Фаза C — Интеграции и качество

- **M8. Экспорт результатов:** `GoogleSheetsExporter` (дефолт MVP) первым; затем как опции —
  `GenericWebhookExporter` и `Bitrix24Exporter` (выбор провайдера в конфиге/админке, без правок ядра).
- **M9. Self-host LLM (целевой) + RU-облако fallback:** перевод анализа на локальный **vLLM + Qwen2.5**
  (целевое решение под ПДн, +`vLLM` в compose) сменой конфига; адаптеры RU-облака (Yandex/Sber STT,
  YandexGPT/GigaChat) за теми же портами как fallback. Код ядра не меняется.
- **M10. Данные и метрики:** загрузка 16–20 ч размеченного набора; `eval_wer.py` (jiwer) + `eval_kpi.py`
  (accuracy/F1 по каждому KPI); regression-харнесс по golden-set (апгрейд №7 §12); калибровка промптов/весов.

**Сквозное (с самого начала):** config-driven KPI/веса/провайдеры, структурные логи, retry/ошибки в
пайплайне, `consent_flag` + retention. Стабы `BadgeSource`/`TelephonySource` — чтобы перспектива не ломала ядро.

---

## 6. Verification (как проверяем end-to-end)

1. `docker compose up` (postgres, minio, api, worker, frontend, caddy; `vLLM` — на этапе self-host LLM).
2. **Файл:** загрузить sample mp3 → наблюдать переходы статусов → открыть карточку → увидеть
   транскрипт/summary/KPI/балл → отредактировать оценку → проверить экспорт (на M4 — файл `JSONExporter`, на M8 — строка в Google Sheets).
3. **Микрофон:** запись старт/стоп → near-realtime транскрипт в карточке.
4. **Админка:** создать менеджера → загрузить скрипт → запись этого менеджера уходит в *script-based* →
   дневная сводка показывает агрегаты и нарушения.
5. **Сменность провайдеров:** переключить конфиг `Analyzer` с `gpt-4o-mini` на локальный vLLM/Qwen (и STT на RU-облако) → тот же пайплайн без правок кода.
6. **Экспорт:** дефолт — `GoogleSheetsExporter` (строка в таблице); переключить на `GenericWebhookExporter`/`Bitrix24Exporter` конфигом — ядро не меняется.
7. **Тесты:** unit на скоринг (чистая функция); контракт-тесты портов с fake-адаптерами; интеграционный
   прогон пайплайна со стаб-STT/LLM; `scripts/eval_wer.py` и `scripts/eval_kpi.py` на размеченном наборе.

---

## 7. Риски и открытые вопросы

- **GPU-VRAM:** на MVP на GPU только whisper (LLM в облаке). Вопрос совмещения whisper + Qwen на одной
  карте относится к этапу self-host LLM (см. оценку в §1); при нехватке — последовательное выполнение стадий.
- **Строгий JSON:** на MVP — structured output облачной модели (надёжно из коробки); на self-host —
  `guided_json` vLLM по той же схеме. RU-облако — дополнительная страховка качества.
- **Облачный LLM и ПДн:** транскрипты уходят к облачному провайдеру. На MVP допустимо на пилотных данных
  с согласием/обезличиванием; целевое снятие риска — переход на self-host LLM (M9), переключение конфигом.
- **WER на реальных RU-продажах** (жаргон, имена товаров): `initial_prompt`/словарь; мерим на 16–20 ч.
- **Реалтайм:** MVP — near-realtime (буфер), не low-latency стриминг (это перспектива/телефония).
- **Bitrix24:** подтвердить целевую сущность и маппинг полей (дело/комментарий/поле сделки) с заказчиком.
- **Юр-момент:** заказчик готовит согласие/уведомление; в системе — `consent_flag`, ограничение доступа,
  срок хранения/удаление.

## 8. Открытые вопросы к заказчику/вам

1. Какой GPU под пилот (свой / аренда, объём VRAM)? — на MVP нужен только под whisper; объём VRAM определит размер Qwen2.5 на этапе self-host LLM.
2. На MVP экспорт — Google Sheets; подтвердить Bitrix24 как целевую CRM и схему сущностей (дело/комментарий/поле) для следующего шага.
3. Срок хранения записей (retention) по требованиям заказчика.
4. Облачный LLM-провайдер для MVP (OpenAI / совместимый), бюджет на `gpt-4o-mini` и допустимость отправки транскриптов в облако на пилоте.
5. Google-аккаунт/таблица для `GoogleSheetsExporter` (сервисный аккаунт, доступ к Sheets).
