# M1 — Ядро: порты, доменные сущности, LangGraph-граф, стабы

> Этап `docs/PLAN.md §5 M1`. Базовые соглашения, TDD-цикл, слои тестов и глобальный DoD — см.
> [README.md](README.md) (§2–§4).

## Цель этапа

Собрать **автономное ядро** за портами: порты `AudioSource`/`STTEngine`/`Analyzer`/`CRMExporter`
(Protocol/ABC), доменные сущности (`docs/PLAN.md §3`), модель данных (SQLAlchemy + Alembic), LangGraph-граф
стадий с состоянием/checkpointer и стаб-адаптеры (включая `BadgeSource`/`TelephonySource`).
Ничего внешнего не вызывается — всё на стабах.

## Входные предпосылки

- M0 завершён: каркас, конфиги, Alembic baseline, CI.

## Выходной результат (DoD этапа)

- Порты определены как Protocol/ABC; для каждого есть **контракт-тест**, проходимый стаб-адаптером.
- Доменные сущности и SQLAlchemy-модели (+ миграция) соответствуют `docs/PLAN.md §3` / ТЗ §10.
- LangGraph-граф `normalizing→transcribing→analyzing→scoring→exporting` гоняется на стабах,
  переходы статусов и ветка `failed` покрыты интеграционным тестом, состояние персистится через checkpointer.
- `consent_flag`/`retention_until` присутствуют в модели `recording`.

## Чек-лист задач

- [ ] M1-T1 — Доменные сущности (dataclasses/Pydantic): Recording, Transcript, Analysis, Manager, Script, User
- [ ] M1-T2 — Определение портов (Protocol/ABC) + DTO портов
- [ ] M1-T3 — Контракт-тесты портов + общий «контракт-харнесс»
- [ ] M1-T4 — Стаб-адаптеры всех портов (+ BadgeSource/TelephonySource заглушки)
- [ ] M1-T5 — SQLAlchemy-модели + репозитории + Alembic-миграция (по §3)
- [ ] M1-T6 — LangGraph-граф стадий + State + checkpointer (Postgres)
- [ ] M1-T7 — Воркер-раннер графа (job-runner) + проекция State→recording.status

---

### M1-T1: Доменные сущности

- **Цель / зачем:** Зафиксировать внутренние сущности ядра независимо от БД и провайдеров.
- **Зависит от:** M0-T4
- **Затрагивает:** `app/core/domain/{recording,transcript,analysis,manager,script,user}.py`.
- **TDD:**
  1. *Red* — `backend/tests/core/domain/test_entities.py` — кейсы: `Recording` хранит `manager_id`, `channel`,
     `consent_flag`, `status`, `retention_until`; `Transcript` — `segments[]` (с таймкодами), `detected_language`;
     `Analysis` — `summary`, `kpi_json`, `score`, `verdict(+|~|-)`, `mode(baseline|script)`, `script_version_id?`,
     `weights_version`; `verdict`/`mode`/`status` — Enum'ы; недопустимое значение → ошибка.
  2. *Green* — dataclasses/Pydantic-модели + Enum'ы статусов и вердиктов.
  3. *Refactor* — общий модуль `enums.py`; неизменяемость (frozen) где уместно.
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + сущности не импортируют SQLAlchemy/адаптеры (чистое ядро).
- **Acceptance / как проверить:** `pytest backend/tests/core/domain/test_entities.py`.
- **Заметки по портам/конфигу:** домен — внутренний контракт; адаптеры мапят свои типы в эти сущности.

---

### M1-T2: Определение портов (Protocol/ABC) + DTO

- **Цель / зачем:** Объявить интерфейсы провайдеров — главный инвариант ports & adapters.
- **Зависит от:** M1-T1
- **Затрагивает:** `app/core/ports/{audio_source,stt_engine,analyzer,crm_exporter}.py`.
- **TDD:**
  1. *Red* — `backend/tests/core/ports/test_port_signatures.py` — кейсы: `AudioSource.fetch()→AudioPayload`
     (нормализованное аудио+метаданные: менеджер/канал/время/согласие); `STTEngine.transcribe(audio)→Transcript`
     (segments[], timecodes, detected_language); `Analyzer.analyze(transcript, script?)→AnalysisResult(summary,kpi_json)`;
     `CRMExporter.export(analysis, recording)→ExportResult`; проверка, что это `Protocol`/`ABC` и сигнатуры стабильны.
  2. *Green* — Protocol-классы (`typing.Protocol`, `runtime_checkable`) + DTO (`AudioPayload`, `ExportResult`).
  3. *Refactor* — единый `ports/__init__.py` реэкспорт; docstring-контракты (pre/postconditions).
- **Слой тестов:** контракт (сигнатуры) / unit.
- **Definition of Done:** глобальный DoD + порты не зависят от адаптеров; `Analyzer.analyze` принимает
  опциональный `script` (ТЗ §4.4 два режима).
- **Acceptance / как проверить:** `mypy backend/app/core/ports`; `pytest backend/tests/core/ports/test_port_signatures.py`.
- **Заметки по портам/конфигу:** интерфейс `Analyzer` спроектирован под будущий map-reduce по чанкам
  (`docs/PLAN.md §4`, длинные звонки) — метод допускает потоковую/чанковую реализацию без смены сигнатуры ядра.

---

### M1-T3: Контракт-тесты портов (общий харнесс)

- **Цель / зачем:** Один набор тестов на порт, проходимый любой реализацией (стаб и реальной) — гарантия
  взаимозаменяемости адаптеров.
- **Зависит от:** M1-T2
- **Затрагивает:** `backend/tests/contracts/{test_audio_source.py,test_stt_engine.py,test_analyzer.py,test_crm_exporter.py}`,
  `backend/tests/contracts/conftest.py` (фикстуры-параметризация по реализациям).
- **TDD:**
  1. *Red* — контракт-кейсы (пока без реализаций → красные/skipped): STT возвращает непустые сегменты с
     монотонными таймкодами и `detected_language`; Analyzer возвращает `summary` и `kpi_json`, ключи которого ⊆ KPI из
     конфига; CRMExporter возвращает `ExportResult` с признаком успеха/идемпотентностью; AudioSource отдаёт
     нормализованный payload с обязательными метаданными.
  2. *Green* — оформить параметризацию `@pytest.mark.parametrize("impl", [...])`, подключаемую реализациями
     (стабы — в M1-T4).
  3. *Refactor* — вынести общие ассерты (валидность сегментов, схема kpi) в хелперы.
- **Слой тестов:** контракт.
- **Definition of Done:** глобальный DoD + каждый порт имеет контракт-набор; набор переиспользуется реальными
  адаптерами (M3/M4/M8) без изменений.
- **Acceptance / как проверить:** `pytest backend/tests/contracts`.
- **Заметки по портам/конфигу:** контракт — это и есть формальная гарантия «сменности конфигом»: любая
  реализация обязана пройти один и тот же набор.

---

### M1-T4: Стаб-адаптеры всех портов

- **Цель / зачем:** Дать ядру работать **автономно** (без внешних ключей) и наполнить контракт-тесты
  реализациями; заложить стабы перспективы.
- **Зависит от:** M1-T3
- **Затрагивает:** `app/adapters/audio/{file_stub,badge_source,telephony_source}.py`,
  `app/adapters/stt/stub_stt.py`, `app/adapters/analyzer/stub_analyzer.py`, `app/adapters/crm/json_exporter.py`
  (минимальная версия для стаба).
- **TDD:**
  1. *Red* — подключить стабы к контракт-параметризации (M1-T3) — кейсы становятся зелёными для стабов;
     отдельно `backend/tests/adapters/test_stub_perspective.py`: `BadgeSource`/`TelephonySource` реализуют порт,
     но `fetch()` бросает `NotImplementedError`/`NotSupportedYet` — **не ломая импорт ядра**.
  2. *Green* — стаб-STT (детерминированный транскрипт), стаб-Analyzer (фиксированный summary + валидный по
     `kpi.yaml` kpi_json), `JSONExporter` (пишет файл/возвращает payload), стаб `FileSource`.
  3. *Refactor* — общий модуль фикстур-данных для стабов; параметризация языка/числа сегментов.
- **Слой тестов:** контракт + unit.
- **Definition of Done:** глобальный DoD + контракт-тесты зелёные на стабах; `BadgeSource`/`TelephonySource`
  существуют как заглушки и не ломают ядро (инвариант «стабы перспективы»).
- **Acceptance / как проверить:** `pytest backend/tests/contracts backend/tests/adapters/test_stub_perspective.py`.
- **Заметки по портам/конфигу:** стаб-Analyzer выбирается через `providers.yaml` (`active_llm=stub`) — для
  CI/офлайн-разработки (инвариант автономности ядра, `docs/PLAN.md §5 M4`).

---

### M1-T5: SQLAlchemy-модели + репозитории + миграция

- **Цель / зачем:** Персист модели данных (`docs/PLAN.md §3` / ТЗ §10) с поддержкой ПДн-полей и версионирования.
- **Зависит от:** M1-T1, M0-T6
- **Затрагивает:** `app/db/models/{manager,script,script_ver,recording,transcript,analysis,user}.py`,
  `app/db/repositories/`, `app/db/migrations/<rev>_core_schema.py`.
- **TDD:**
  1. *Red* — `backend/tests/db/test_models.py` (на тест-Postgres) — кейсы: создаются все таблицы из §3;
     `recording` имеет `consent_flag`, `status`, `stage_error`, `retention_until`, FK на `manager`;
     `script_ver` версионирует `script` (контент + привязка KPI); `analysis` хранит `score`, `verdict`,
     `mode`, `script_version_id?`, `weights_version`; репозитории `get/create/update_status` работают.
  2. *Green* — модели SQLAlchemy 2.0 (typed), репозитории, Alembic-ревизия `core_schema`.
  3. *Refactor* — базовый `Repository`-протокол; индексы по `manager_id`+`дата`, `status`.
- **Слой тестов:** интеграция (БД).
- **Definition of Done:** глобальный DoD + миграция применяется/откатывается; `retention_until` и `consent_flag`
  в схеме (ПДн); версионирование скриптов и `weights_version`/`script_version_id` в `analysis` (воспроизводимость).
- **Acceptance / как проверить:** `alembic upgrade head && pytest backend/tests/db/test_models.py`.
- **Заметки по портам/конфигу:** доменные сущности (M1-T1) ≠ ORM-модели; репозитории мапят одно в другое
  (ядро не зависит от SQLAlchemy).

---

### M1-T6: LangGraph-граф стадий + State + checkpointer

- **Цель / зачем:** Единый граф пайплайна для всех источников (`docs/PLAN.md §2.3`) с персистентным состоянием.
- **Зависит от:** M1-T2, M1-T4, M1-T5
- **Затрагивает:** `app/core/pipeline/{state.py,graph.py,nodes.py}`.
- **TDD:**
  1. *Red* — `backend/tests/core/pipeline/test_graph.py` (со стаб-STT/Analyzer/Exporter) — кейсы: граф проходит
     `normalizing→transcribing→analyzing→scoring→exporting`; `State.status` обновляется на каждой стадии и
     проецируется в `recording.status`; узел, бросивший исключение, переводит в `failed` с сохранением стадии,
     ошибки и инкрементом `retry`; условный переход `failed` (после N retry) не зацикливается; checkpointer
     персистит State и **возобновляет** прогон с последней стадии.
  2. *Green* — `State` (TypedDict/Pydantic) с полями `recording_id,status,stage_error,retry,...`; узлы вызывают
     порты; рёбра + условные переходы; Postgres-checkpointer.
  3. *Refactor* — общий декоратор узла (логирование + retry-политика + перевод в `failed`).
- **Слой тестов:** интеграция (граф + checkpointer).
- **Definition of Done:** глобальный DoD + структурные логи на каждой стадии; retry/ошибки в стадиях;
  checkpointer = Postgres; статусы строго из `docs/PLAN.md §2.3`.
- **Acceptance / как проверить:** `pytest backend/tests/core/pipeline/test_graph.py`.
- **Заметки по портам/конфигу:** узлы вызывают порты, а не адаптеры напрямую; смена провайдера не меняет граф —
  единый контракт для file/mic/badge/telephony.

---

### M1-T7: Воркер-раннер графа (job-runner)

- **Цель / зачем:** Фоновый лёгкий процесс, который забирает job и гоняет граф (`docs/PLAN.md §1/§2.3`).
- **Зависит от:** M1-T6
- **Затрагивает:** `app/workers/runner.py`, `app/services/process.py`.
- **TDD:**
  1. *Red* — `backend/tests/workers/test_runner.py` — кейсы: положенный job (recording в статусе `queued`)
     подхватывается раннером и доводится до `done` на стабах; упавший прогон оставляет `failed` + `stage_error`;
     повторный запуск возобновляет с checkpoint'а, а не с нуля.
  2. *Green* — простой поллинг/очередь по статусу `queued`; вызов графа; обновление `recording.status`.
  3. *Refactor* — graceful shutdown; ограничение конкурентности; структурные логи job-id.
- **Слой тестов:** интеграция.
- **Definition of Done:** глобальный DoD + воркер — отдельный процесс (compose-сервис `worker`); идемпотентность
  возобновления; логи с job-id.
- **Acceptance / как проверить:** `pytest backend/tests/workers/test_runner.py`.
- **Заметки по портам/конфигу:** источник лишь кладёт job (статус `queued`) — раннер и граф одинаковы для всех
  источников (file/mic/перспектива).
