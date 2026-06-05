# M3 — STT: `FasterWhisperEngine` (self-host) → транскрипт с таймкодами

> Этап `docs/PLAN.md §5 M3`. Базовые соглашения, TDD-цикл, слои тестов и глобальный DoD — см.
> [README.md](README.md) (§2–§4).

## Цель этапа

Реализовать self-host STT за портом `STTEngine`: `faster-whisper` → транскрипт с сегментами/таймкодами
и `detected_language`. Этап **полностью офлайн** (аудио и транскрипты не покидают периметр — ключевой
ПДн-инвариант, `docs/PLAN.md §Context`). Узел `transcribing` графа использует порт.

## Входные предпосылки

- M2 завершён: загрузка, нормализация, job в графе.

## Выходной результат (DoD этапа)

- `FasterWhisperEngine` проходит контракт-тест `STTEngine`.
- Стадия `transcribing` графа выдаёт `transcript` (текст + `segments[]` с таймкодами + `detected_language`),
  персистит его в БД.
- Язык по умолчанию RU (из конфига) + автоопределение (ТЗ §4.2); `initial_prompt`/словарь конфигурируем.
- Размер модели (`large-v3`/`medium`) и устройство (GPU/CPU) — из конфига.
- В CI STT-движок мокается/скипается (модель не качаем), но контракт-тест прогоняется на стаб + лёгкой реальной проверке.

## Чек-лист задач

- [ ] M3-T1 — Конфиг STT-провайдера (модель/устройство/язык/initial_prompt)
- [ ] M3-T2 — Адаптер `FasterWhisperEngine` (проходит контракт `STTEngine`)
- [ ] M3-T3 — Маппинг сегментов faster-whisper → доменный `Transcript`
- [ ] M3-T4 — Интеграция узла `transcribing` графа + персист транскрипта
- [ ] M3-T5 — `initial_prompt`/словарь лексики (товары/имена) — config-driven
- [ ] M3-T6 — `GET /api/recordings/{id}/transcript` + отдача сегментов

---

### M3-T1: Конфиг STT-провайдера

- **Цель / зачем:** Сделать STT сменным/настраиваемым конфигом (модель, устройство, язык, prompt) без правок кода.
- **Зависит от:** M0-T3
- **Затрагивает:** `infra/config/providers.yaml` (секция STT), `app/config/settings.py`,
  `app/adapters/stt/config.py`.
- **TDD:**
  1. *Red* — `backend/tests/adapters/stt/test_stt_config.py` — кейсы: парсятся `model_size(large-v3|medium|...)`,
     `device(cuda|cpu)`, `compute_type`, `default_language=ru`, `initial_prompt?`, `vad_filter?`; дефолты MVP
     корректны; невалидный `device` → ошибка.
  2. *Green* — Pydantic-модель `WhisperConfig` + чтение из providers.
  3. *Refactor* — общий базовый `SttProviderConfig` (для будущих Yandex/Sber).
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + дефолт `faster_whisper`; для пилота допустим CPU/`medium` (`docs/PLAN.md §1`).
- **Acceptance / как проверить:** `pytest backend/tests/adapters/stt/test_stt_config.py`.
- **Заметки по портам/конфигу:** активный STT и его параметры — только в конфиге; fallback RU-облако (M9) — тем же портом.

---

### M3-T2: Адаптер `FasterWhisperEngine`

- **Цель / зачем:** Боевая self-host реализация порта `STTEngine`.
- **Зависит от:** M1-T3, M3-T1
- **Затрагивает:** `app/adapters/stt/faster_whisper_engine.py`.
- **TDD:**
  1. *Red* — подключить `FasterWhisperEngine` к контракт-набору `backend/tests/contracts/test_stt_engine.py`
     — кейсы: на коротком sample-wav возвращает непустые сегменты с монотонными таймкодами и `detected_language`;
     язык по умолчанию ru, но автоопределение работает; пустое/тишина → пустой/корректный результат, не падение.
     (В CI реальная модель — за маркером `@pytest.mark.heavy`/skip без GPU; контракт на стабе всегда зелёный.)
  2. *Green* — обёртка над `faster_whisper.WhisperModel`; segments→DTO.
  3. *Refactor* — ленивая загрузка модели (singleton); тайминги/логи; обработка ошибок→`failed`.
- **Слой тестов:** контракт (`STTEngine`).
- **Definition of Done:** глобальный DoD + аудио не покидает периметр (self-host); реальный прогон под маркером,
  не обязателен в базовом CI.
- **Acceptance / как проверить:** `pytest -m heavy backend/tests/contracts/test_stt_engine.py` (с моделью);
  `pytest backend/tests/contracts/test_stt_engine.py` (стаб).
- **Заметки по портам/конфигу:** контракт един для whisper и RU-облака (M9) — взаимозаменяемость гарантирована.

---

### M3-T3: Маппинг сегментов → доменный `Transcript`

- **Цель / зачем:** Привести вывод движка к единому `Transcript` (текст + `segments(jsonb)` + `detected_language`).
- **Зависит от:** M1-T1, M3-T2
- **Затрагивает:** `app/adapters/stt/mapping.py`, `app/core/domain/transcript.py`.
- **TDD:**
  1. *Red* — `backend/tests/adapters/stt/test_mapping.py` — кейсы: сегменты с `start/end/text` → доменные
     сегменты; таймкоды монотонны и неотрицательны; сборка полного текста из сегментов; `detected_language`
     прокидывается; опционально — speaker turns (базовая «диаризация» через сегменты, ТЗ §4.2).
  2. *Green* — чистая функция маппинга.
  3. *Refactor* — нормализация пробелов/пунктуации; вынести в утилиты.
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + формат `segments` совместим с `transcript.segments(jsonb)` (M1-T5).
- **Acceptance / как проверить:** `pytest backend/tests/adapters/stt/test_mapping.py`.
- **Заметки по портам/конфигу:** доменный `Transcript` — внутренний контракт; downstream (Analyzer) не знает о whisper.
- **Открытый вопрос:** точная диаризация — перспектива; в MVP только сегменты STT (см. README §6.2).

---

### M3-T4: Интеграция узла `transcribing` + персист

- **Цель / зачем:** Включить STT в граф и сохранить транскрипт в БД (стадия `transcribing`).
- **Зависит от:** M1-T6, M3-T2, M3-T3, M1-T5
- **Затрагивает:** `app/core/pipeline/nodes.py` (узел `transcribing`), `app/services/process.py`,
  `app/db/repositories/transcript.py`.
- **TDD:**
  1. *Red* — `backend/tests/core/pipeline/test_transcribing_node.py` (стаб-STT через порт) — кейсы: после
     `normalizing` узел `transcribing` создаёт `transcript` и переводит статус; ошибка STT → `failed`+`stage_error`+retry;
     транскрипт читается из БД.
  2. *Green* — узел вызывает `STTEngine` (выбранный конфигом), пишет `transcript` через репозиторий.
  3. *Refactor* — единая обработка ошибок узла (из M1-T6); структурные логи (длительность, язык).
- **Слой тестов:** интеграция (граф).
- **Definition of Done:** глобальный DoD + транскрипт персистится; переход статуса корректный; ошибки→`failed`.
- **Acceptance / как проверить:** `pytest backend/tests/core/pipeline/test_transcribing_node.py`.
- **Заметки по портам/конфигу:** узел зависит от порта `STTEngine`, не от faster-whisper напрямую.

---

### M3-T5: `initial_prompt`/словарь лексики — config-driven

- **Цель / зачем:** Поднять WER на RU-продажах (жаргон, имена товаров) через словарь/`initial_prompt`
  вместо дообучения (ТЗ §7, `docs/PLAN.md §7`).
- **Зависит от:** M3-T1, M3-T2
- **Затрагивает:** `infra/config/providers.yaml` (`stt.initial_prompt`/`vocabulary`), `app/adapters/stt/faster_whisper_engine.py`.
- **TDD:**
  1. *Red* — `backend/tests/adapters/stt/test_initial_prompt.py` — кейсы: `initial_prompt`/словарь из конфига
     прокидывается в движок; пустой конфиг → prompt не передаётся; смена словаря не требует правок кода.
  2. *Green* — прокинуть `initial_prompt` из конфига в вызов `transcribe`.
  3. *Refactor* — сборка prompt из списка терминов; лимит длины.
- **Слой тестов:** unit/контракт.
- **Definition of Done:** глобальный DoD + словарь полностью config-driven; влияние на WER замеряется в M10.
- **Acceptance / как проверить:** `pytest backend/tests/adapters/stt/test_initial_prompt.py`.
- **Заметки по портам/конфигу:** лексика — в конфиге, не хардкод; апгрейд VAD-преднарезки (№4 §12 ТЗ) — задел,
  но не реализуется в MVP.

---

### M3-T6: `GET /api/recordings/{id}/transcript`

- **Цель / зачем:** Отдать транскрипт с сегментами для карточки разговора (ТЗ §4.7).
- **Зависит от:** M3-T4, M2-T6
- **Затрагивает:** `app/api/recordings.py` (sub-route), `app/db/repositories/transcript.py`.
- **TDD:**
  1. *Red* — `backend/tests/api/test_transcript_endpoint.py` — кейсы: для готовой записи возвращает текст +
     сегменты с таймкодами + `detected_language`; для записи без транскрипта → 404/пусто; доступ позже под ролью (M5).
  2. *Green* — роутер + схема ответа.
  3. *Refactor* — общий сериализатор сегментов.
- **Слой тестов:** API.
- **Definition of Done:** глобальный DoD + формат сегментов стабилен (используется UI плеером для перехода по таймкодам).
- **Acceptance / как проверить:** `pytest backend/tests/api/test_transcript_endpoint.py`.
- **Заметки по портам/конфигу:** API не знает о STT-провайдере — отдаёт доменный `Transcript`.
