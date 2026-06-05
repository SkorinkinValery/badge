# M4 — Анализ + скоринг: `OpenAICompatibleAnalyzer` + движок скоринга

> Этап `docs/PLAN.md §5 M4`. Базовые соглашения, TDD-цикл, слои тестов и глобальный DoD — см.
> [README.md](README.md) (§2–§4).

## Цель этапа

Замкнуть сквозной пайплайн за портами: `OpenAICompatibleAnalyzer` (облако `gpt-4o-mini`, structured/JSON
output по Pydantic-схеме) → `summary` + `kpi_json`; чистая функция скоринга (`kpi_json + weights → score/verdict`);
экспорт на этом этапе — `JSONExporter`. Для офлайн-разработки/CI — стаб-`Analyzer` за тем же портом.
Два режима (baseline / script-based) выбираются автоматически.

## Входные предпосылки

- M3 завершён: транскрипт с сегментами в БД.

## Выходной результат (DoD этапа)

- `OpenAICompatibleAnalyzer` проходит контракт `Analyzer`; стаб-Analyzer тоже (взаимозаменяемость).
- Pydantic-схема `KpiResult` даёт схемно-валидный JSON; промпт с поведенческими якорями и цитатой-доказательством.
- Скоринг — чистая функция с нормализацией весов под доступный набор пунктов; в `analysis` пишутся
  `weights_version` и `script_version_id?` (воспроизводимость).
- Сквозной граф `normalizing→…→exporting` доходит до `done` со стаб-LLM в CI и с `gpt-4o-mini` боево.
- Смена `gpt-4o-mini`↔локальный vLLM↔RU-облако — только конфигом (задел под M9).

## Чек-лист задач

- [ ] M4-T1 — Pydantic-схема `KpiResult` (structured output) + валидация по `kpi.yaml`
- [ ] M4-T2 — Конструктор промпта (рубрика + якоря + цитата-доказательство + few-shot + два режима)
- [ ] M4-T3 — Адаптер `OpenAICompatibleAnalyzer` (проходит контракт `Analyzer`)
- [ ] M4-T4 — Движок скоринга: чистая функция `kpi_json + weights → score/verdict`
- [ ] M4-T5 — Нормализация весов под доступный набор (baseline vs script-based сопоставимы)
- [ ] M4-T6 — Узлы `analyzing` + `scoring` графа + персист `analysis`
- [ ] M4-T7 — `JSONExporter` + узел `exporting` (замыкание пайплайна)
- [ ] M4-T8 — `GET /api/recordings/{id}/analysis` + ручная корректировка оценки

---

### M4-T1: Pydantic-схема `KpiResult` (structured output)

- **Цель / зачем:** Гарантировать схемно-валидный JSON от LLM (ТЗ §4.4, `docs/PLAN.md §4`); одна схема — для
  облака (`response_format`) и self-host (`guided_json`).
- **Зависит от:** M0-T4
- **Затрагивает:** `app/core/domain/kpi_result.py`, `app/adapters/analyzer/schema.py`.
- **TDD:**
  1. *Red* — `backend/tests/adapters/analyzer/test_kpi_schema.py` — кейсы: схема строится **из `kpi.yaml`**
     (динамически, не хардкод полей); каждый пункт = `value(да|нет|частично|шкала)`, `quote(цитата)`, `comment`;
     `fact`-KPI → бинарное значение, `scale`-KPI → числовая шкала; невалидный JSON LLM → ошибка валидации;
     лишние/недостающие KPI → ошибка.
  2. *Green* — генерация Pydantic-модели/JSON-schema из загруженного `KpiConfig`.
  3. *Refactor* — кэш схемы по версии конфига; экспорт JSON-schema для `guided_json` (M9).
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + схема порождается из `kpi.yaml` (config-driven), не хардкодится;
  на каждый KPI требуется цитата-доказательство (ТЗ §4.4).
- **Acceptance / как проверить:** `pytest backend/tests/adapters/analyzer/test_kpi_schema.py`.
- **Заметки по портам/конфигу:** одна схема для всех LLM-провайдеров — переключение конфигом без правок.

---

### M4-T2: Конструктор промпта (рубрика + якоря + два режима)

- **Цель / зачем:** Снизить разброс/галлюцинации (поведенческие якоря, апгрейд №2 §12 ТЗ) и поддержать
  baseline/script-based (ТЗ §4.4) с цитатами и few-shot.
- **Зависит от:** M4-T1
- **Затрагивает:** `app/adapters/analyzer/prompt.py`.
- **TDD:**
  1. *Red* — `backend/tests/adapters/analyzer/test_prompt.py` — кейсы: промпт включает system-роль, рубрику с
     якорями **из конфига** для каждого KPI, требование цитаты-доказательства на пункт, few-shot из датасета (если
     есть); **baseline** (нет скрипта) → generic-рубрика; **script-based** (есть активный скрипт) → добавляется
     сверка с эталоном + поиск нарушений регламента; пустой датасет → промпт без few-shot, не падает.
  2. *Green* — функция `build_prompt(transcript, kpi_config, script?, few_shot?)`.
  3. *Refactor* — шаблонизация (Jinja/функции); разнести system/rubric/examples.
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + якоря/рубрика — из `kpi.yaml`; режим выбирается по наличию скрипта;
  few-shot опционален и не ломает пустой датасет.
- **Acceptance / как проверить:** `pytest backend/tests/adapters/analyzer/test_prompt.py`.
- **Заметки по портам/конфигу:** промпт — часть адаптера, но рубрика config-driven; смена модели промпт не меняет.

---

### M4-T3: Адаптер `OpenAICompatibleAnalyzer`

- **Цель / зачем:** Боевой анализ через OpenAI-совместимый API (`gpt-4o-mini`), structured output; один адаптер
  для облака/vLLM/RU-облака (`docs/PLAN.md §1`).
- **Зависит от:** M1-T3, M4-T1, M4-T2
- **Затрагивает:** `app/adapters/analyzer/openai_compatible.py`.
- **TDD:**
  1. *Red* — подключить `OpenAICompatibleAnalyzer` к контракт-набору `backend/tests/contracts/test_analyzer.py`
     (LLM замокан/записан через VCR) — кейсы: `analyze(transcript, script?)` → `AnalysisResult(summary, kpi_json)`;
     `kpi_json` валиден по схеме (M4-T1); невалидный ответ → retry/ошибка; `base_url`/`model`/`api_key` берутся из конфига.
  2. *Green* — клиент OpenAI-совместимого API с `response_format`=схема; маппинг ответа в `AnalysisResult`.
  3. *Refactor* — retry с backoff; таймауты; структурные логи (токены/латентность); вынести транспорт.
- **Слой тестов:** контракт (`Analyzer`); сетевой вызов замокан в CI.
- **Definition of Done:** глобальный DoD + `base_url`/`model`/`api_key` только из конфига; стаб-Analyzer и
  боевой проходят один контракт; **на пилоте — учёт ПДн** (транскрипты уходят в облако только с согласием;
  целевое снятие риска — M9).
- **Acceptance / как проверить:** `pytest backend/tests/contracts/test_analyzer.py`.
- **Заметки по портам/конфигу:** **главный инвариант сменности** — переключение `gpt-4o-mini`→vLLM/Qwen→RU-облако
  меняет только `providers.yaml`/env, схема и контракт одни (см. M9).

---

### M4-T4: Движок скоринга (чистая функция)

- **Цель / зачем:** Детерминированный, тестируемый скоринг `kpi_json + weights → score 0–100 + verdict (+|~|-)`
  (ТЗ §4.5, `docs/PLAN.md §4`) — ядро ценности, покрывается в первую очередь.
- **Зависит от:** M0-T4, M4-T1
- **Затрагивает:** `app/services/score.py`.
- **TDD:**
  1. *Red* — `backend/tests/services/test_scoring.py` — кейсы: известный `kpi_json` + `weights` → ожидаемый
     `score` и `verdict`; пороги `+`/`~`/`-` (из конфига); `fact`-KPI (да/нет) маппится в 0/1×вес; `scale`-KPI —
     по шкале; KPI с `include_in_score=false` исключается; отсутствующий пункт → нормализация (M4-T5);
     детерминированность (одинаковый вход → одинаковый выход).
  2. *Green* — чистая функция без побочных эффектов.
  3. *Refactor* — таблица маппинга значений; вынести пороги в конфиг.
- **Слой тестов:** unit (критичная логика — приоритет).
- **Definition of Done:** глобальный DoD + функция чистая (без I/O); пороги/маппинг config-driven; покрытие высоким.
- **Acceptance / как проверить:** `pytest backend/tests/services/test_scoring.py`.
- **Заметки по портам/конфигу:** веса и пороги — из `weights.yaml`; никакого хардкода.

---

### M4-T5: Нормализация весов под доступный набор

- **Цель / зачем:** Сделать baseline и script-based баллы сопоставимыми (ТЗ §4.5) — при отсутствии KPI #9
  (скрипт) или исключённых пунктов вес перераспределяется.
- **Зависит от:** M4-T4
- **Затрагивает:** `app/services/score.py` (нормализатор), `app/config/kpi.py`.
- **TDD:**
  1. *Red* — `backend/tests/services/test_weight_normalization.py` — кейсы: при выпадении KPI #9 (нет скрипта)
     сумма весов нормализуется к 100%; результат baseline сопоставим со script-based на одинаковых пунктах;
     KPI «соблюдение регламента» без скрипта — исключается **или** оценивается по общим критериям (флаг в конфиге);
     вырожденный случай (один пункт) корректен.
  2. *Green* — функция нормализации весов по доступному набору.
  3. *Refactor* — отделить выбор доступного набора от нормализации.
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + правило нормализации — из `weights.yaml`; флаг поведения KPI #9 — в конфиге.
- **Acceptance / как проверить:** `pytest backend/tests/services/test_weight_normalization.py`.
- **Заметки по портам/конфигу:** правило нормализации config-driven; в `analysis` пишется `weights_version`.

---

### M4-T6: Узлы `analyzing` + `scoring` графа + персист `analysis`

- **Цель / зачем:** Встроить анализ и скоринг в граф, выбрать режим по наличию скрипта, сохранить `analysis`.
- **Зависит от:** M1-T6, M3-T4, M4-T3, M4-T4, M4-T5
- **Затрагивает:** `app/core/pipeline/nodes.py` (узлы `analyzing`, `scoring`), `app/services/process.py`,
  `app/db/repositories/analysis.py`.
- **TDD:**
  1. *Red* — `backend/tests/core/pipeline/test_analyze_score_nodes.py` (стаб-Analyzer через порт) — кейсы:
     `analyzing` создаёт `summary`+`kpi_json`; режим = `script` если у менеджера активный скрипт, иначе `baseline`;
     `scoring` пишет `score`/`verdict`/`weights_version`/`script_version_id?`; ошибка LLM → `failed`+retry;
     `analysis` читается из БД.
  2. *Green* — узлы вызывают порт `Analyzer` (по конфигу) и чистый скоринг; персист через репозиторий.
  3. *Refactor* — общий выбор режима (наличие активного скрипта менеджера) в сервис.
- **Слой тестов:** интеграция (граф).
- **Definition of Done:** глобальный DoD + режим выбирается автоматически; воспроизводимость (`weights_version`,
  `script_version_id`) сохранена; ошибки→`failed`.
- **Acceptance / как проверить:** `pytest backend/tests/core/pipeline/test_analyze_score_nodes.py`.
- **Заметки по портам/конфигу:** узлы зависят от порта `Analyzer`; стаб/боевой/локальный — выбор конфигом.

---

### M4-T7: `JSONExporter` + узел `exporting`

- **Цель / зачем:** Замкнуть сквозной пайплайн до `done` (на M4 экспорт = JSON-файл, `docs/PLAN.md §5 M4`);
  полноценный `GoogleSheetsExporter` — на M8.
- **Зависит от:** M1-T3, M4-T6
- **Затрагивает:** `app/adapters/crm/json_exporter.py`, `app/core/pipeline/nodes.py` (узел `exporting`).
- **TDD:**
  1. *Red* — подключить `JSONExporter` к контракт-набору `backend/tests/contracts/test_crm_exporter.py` +
     `backend/tests/core/pipeline/test_exporting_node.py` — кейсы: `export(analysis, recording)→ExportResult`
     пишет JSON-payload (summary/kpi/score/verdict/метаданные); узел `exporting` доводит граф до `done`;
     ошибка экспорта → `failed`+retry; идемпотентность.
  2. *Green* — `JSONExporter` (в файл/MinIO); узел `exporting`.
  3. *Refactor* — общий сериализатор payload (переиспользуется в webhook/sheets на M8).
- **Слой тестов:** контракт (`CRMExporter`) + интеграция (граф).
- **Definition of Done:** глобальный DoD + сквозной граф доходит до `done` на стабах; экспортер сменный конфигом.
- **Acceptance / как проверить:** `pytest backend/tests/contracts/test_crm_exporter.py backend/tests/core/pipeline/test_exporting_node.py`.
- **Заметки по портам/конфигу:** `active_crm` в конфиге; на M8 переключается на `google_sheets` без правок ядра.

---

### M4-T8: `GET /api/recordings/{id}/analysis` + ручная корректировка оценки

- **Цель / зачем:** Отдать summary/KPI/балл в карточку и дать ручную корректировку для разметки/калибровки
  (ТЗ §4.7).
- **Зависит от:** M4-T6, M3-T6
- **Затрагивает:** `app/api/recordings.py` (sub-routes), `app/db/repositories/analysis.py`.
- **TDD:**
  1. *Red* — `backend/tests/api/test_analysis_endpoint.py` — кейсы: `GET …/analysis` отдаёт `summary`,
     `kpi_json` (с цитатами), `score`, `verdict`, `mode`; `PATCH …/analysis` корректирует оценку (с пометкой
     ручной правки/автора); запись без анализа → 404; доступ под ролью добавляется в M5.
  2. *Green* — роутеры GET/PATCH + схемы.
  3. *Refactor* — аудит ручных правок (кто/когда) для калибровки.
- **Слой тестов:** API.
- **Definition of Done:** глобальный DoD + ручная правка не теряет оригинальную авто-оценку (для eval/калибровки M10).
- **Acceptance / как проверить:** `pytest backend/tests/api/test_analysis_endpoint.py`.
- **Заметки по портам/конфигу:** API отдаёт доменный `Analysis`, не зависит от LLM-провайдера.
