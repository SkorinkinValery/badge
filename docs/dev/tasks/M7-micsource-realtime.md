# M7 — `MicSource`: near-realtime захват с микрофона

> Этап `docs/PLAN.md §5 M7`. Базовые соглашения, TDD-цикл, слои тестов и глобальный DoD — см.
> [README.md](README.md) (§2–§4).

## Цель этапа

Второй источник: захват с микрофона ПК/ноута в браузере (MediaRecorder → WebSocket → буфер чанков →
near-realtime STT). `MicSource` проходит контракт `AudioSource`; кладёт job в тот же единый граф.
Не low-latency стриминг (это перспектива/телефония) — буферизация чанков.

## Входные предпосылки

- M3 (STT), M4 (анализ/скоринг) завершены; M5 (auth, UI-каркас) желателен для UI кнопок.
  Можно вести параллельно с M5/M6/M8 после M3+M4.

## Выходной результат (DoD этапа)

- WebSocket-эндпоинт принимает аудио-чанки, буферизует, прогоняет near-realtime STT.
- `MicSource` проходит контракт `AudioSource`; запись доходит до того же графа `normalizing→…→exporting`.
- UI: кнопки старт/стоп записи, near-realtime транскрипт в карточке.
- Контракт WS спроектирован под будущий полноценный стриминг/телефонию (задел).

## Чек-лист задач

- [ ] M7-T1 — Протокол WS-сообщений (контракт чанков/контроля) + DTO
- [ ] M7-T2 — Буфер чанков + near-realtime агрегация → нормализация
- [ ] M7-T3 — Адаптер `MicSource` (проходит контракт `AudioSource`)
- [ ] M7-T4 — `WS /api/ws_mic`: приём чанков → recording + job + near-realtime STT
- [ ] M7-T5 — UI: захват MediaRecorder → WS (старт/стоп)
- [ ] M7-T6 — UI: near-realtime транскрипт в карточке

---

### M7-T1: Протокол WS-сообщений + DTO

- **Цель / зачем:** Зафиксировать контракт WS (типы сообщений: старт/чанк/стоп/ack/ошибка), спроектированный
  под будущий стриминг (`docs/PLAN.md §1`).
- **Зависит от:** M1-T2
- **Затрагивает:** `app/api/ws_mic.py` (схемы), `app/adapters/audio/mic_protocol.py`.
- **TDD:**
  1. *Red* — `backend/tests/api/test_ws_protocol.py` — кейсы: сериализация/десериализация сообщений
     `start{manager_id,consent_flag,channel=mic}`, `chunk{seq,bytes}`, `stop`, серверных `ack`/`partial_transcript`/`error`;
     неверный тип/порядок (chunk до start) → ошибка протокола; монотонность `seq`.
  2. *Green* — Pydantic-модели сообщений + (де)сериализация.
  3. *Refactor* — версия протокола в сообщении (форвард-совместимость для телефонии).
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + контракт WS документирован; `consent_flag` передаётся в `start` (ПДн).
- **Acceptance / как проверить:** `pytest backend/tests/api/test_ws_protocol.py`.
- **Заметки по портам/конфигу:** контракт WS — задел под `TelephonySource` (тот же внутренний контракт: на выходе транскрипт+метаданные).

---

### M7-T2: Буфер чанков + near-realtime агрегация

- **Цель / зачем:** Собрать чанки в нормализуемые окна (near-realtime), без low-latency стриминга (ТЗ §2 прим.).
- **Зависит от:** M7-T1, M2-T3
- **Затрагивает:** `app/services/mic_buffer.py`.
- **TDD:**
  1. *Red* — `backend/tests/services/test_mic_buffer.py` — кейсы: чанки накапливаются до порога окна
     (время/размер из конфига) → отдаются на нормализацию+STT; финальный `stop` флашит остаток; пропуск/переупорядочивание
     `seq` обрабатывается; буфер очищается по завершении.
  2. *Green* — оконный буфер с порогом из конфига.
  3. *Refactor* — backpressure; лимит памяти на сессию.
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + размер окна config-driven; near-realtime (буфер), не стриминг.
- **Acceptance / как проверить:** `pytest backend/tests/services/test_mic_buffer.py`.
- **Заметки по портам/конфигу:** окно/пороги — в конфиге.

---

### M7-T3: Адаптер `MicSource`

- **Цель / зачем:** Реализация порта `AudioSource` для микрофона; пройти контракт (взаимозаменяемость с FileSource).
- **Зависит от:** M1-T3, M7-T2
- **Затрагивает:** `app/adapters/audio/mic_source.py`.
- **TDD:**
  1. *Red* — подключить `MicSource` к контракт-набору `backend/tests/contracts/test_audio_source.py` — кейсы:
     из буфера чанков отдаёт нормализованный payload + метаданные (менеджер/`channel=mic`/время/`consent_flag`);
     контракт зелёный наравне с FileSource.
  2. *Green* — `MicSource` поверх буфера (M7-T2) и нормализации (M2-T3).
  3. *Refactor* — переиспользовать storage/нормализацию; сохранить сырое аудио в MinIO.
- **Слой тестов:** контракт (`AudioSource`).
- **Definition of Done:** глобальный DoD + `MicSource` неотличим от `FileSource` на контракте; аудио в периметре.
- **Acceptance / как проверить:** `pytest backend/tests/contracts/test_audio_source.py`.
- **Заметки по портам/конфигу:** граф один для file/mic — источник лишь кладёт job (`docs/PLAN.md §2.3`).

---

### M7-T4: `WS /api/ws_mic` → recording + job + near-realtime STT

- **Цель / зачем:** Боевой WebSocket: приём чанков, создание записи, near-realtime транскрипт, постановка в граф.
- **Зависит от:** M7-T1, M7-T2, M7-T3, M3-T2, M1-T7, M5-T3
- **Затрагивает:** `app/api/ws_mic.py`, `app/services/ingest.py`.
- **TDD:**
  1. *Red* — `backend/tests/api/test_ws_mic.py` (httpx/websocket) — кейсы: `start` создаёт `recording`
     (`channel=mic`, `consent_flag`, `manager_id`); `chunk`-поток буферизуется и даёт `partial_transcript`;
     `stop` финализирует → job в граф → полный анализ; разрыв соединения корректно завершает/помечает запись;
     аутентификация WS по JWT.
  2. *Green* — WS-роутер поверх буфера+STT+ingest; финализация → enqueue.
  3. *Refactor* — таймауты/heartbeat; обработка реконнекта.
- **Слой тестов:** API (WS) + интеграция.
- **Definition of Done:** глобальный DoD + WS под auth; `consent_flag` обязателен (ПДн); после `stop` — тот же граф до `done`.
- **Acceptance / как проверить:** `pytest backend/tests/api/test_ws_mic.py`; ручной сценарий `docs/PLAN.md §6.3`.
- **Заметки по портам/конфигу:** STT — через порт (whisper/RU-облако конфигом); граф единый.

---

### M7-T5: UI — захват MediaRecorder → WS

- **Цель / зачем:** Кнопки старт/стоп записи в браузере, отправка чанков по WS (ТЗ §4.1, `docs/PLAN.md §1`).
- **Зависит от:** M7-T4, M5-T4
- **Затрагивает:** `frontend/app/recordings/record/` (компонент записи), `frontend/lib/ws.ts`.
- **TDD:**
  1. *Red* — компонент-тесты — кейсы: запрос доступа к микрофону; старт → открывает WS, шлёт `start`+чанки;
     стоп → шлёт `stop`, закрывает WS; индикатор записи/ошибки доступа; выбор менеджера и галка согласия перед стартом.
  2. *Green* — MediaRecorder → WebSocket; UI старт/стоп.
  3. *Refactor* — обработка прав/ошибок устройства; реконнект.
- **Слой тестов:** frontend unit/e2e.
- **Definition of Done:** глобальный DoD + согласие (`consent_flag`) собирается до старта (ПДн); кроссплатформенно (браузер).
- **Acceptance / как проверить:** `npm test`; ручной сценарий `docs/PLAN.md §6.3`.
- **Заметки по портам/конфигу:** транспорт WS, без desktop-агента (`docs/PLAN.md §1`).

---

### M7-T6: UI — near-realtime транскрипт в карточке

- **Цель / зачем:** Показывать частичный транскрипт по мере записи (ТЗ §4.1, `docs/PLAN.md §6.3`).
- **Зависит от:** M7-T5, M5-T6
- **Затрагивает:** `frontend/app/recordings/record/` (живой транскрипт).
- **TDD:**
  1. *Red* — компонент-тест — кейсы: `partial_transcript` из WS дописывается в живой вид; после `stop` —
     переход к полной карточке; ошибка STT отображается.
  2. *Green* — подписка на серверные сообщения, инкрементальный рендер.
  3. *Refactor* — дебаунс/склейка частичных сегментов.
- **Слой тестов:** frontend unit.
- **Definition of Done:** глобальный DoD + near-realtime отображение; после финализации — единая карточка (M5-T6).
- **Acceptance / как проверить:** `npm test`; ручной сценарий `docs/PLAN.md §6.3` (near-realtime транскрипт).
- **Заметки по портам/конфигу:** —
