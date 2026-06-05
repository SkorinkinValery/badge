# M8 — Экспорт результатов: `GoogleSheetsExporter` (дефолт MVP) → webhook → bitrix24

> Этап `docs/PLAN.md §5 M8`. Базовые соглашения, TDD-цикл, слои тестов и глобальный DoD — см.
> [README.md](README.md) (§2–§4).
>
> ⚠️ **Расхождение docs/PLAN.md ↔ ТЗ:** ТЗ §4.6 ставит дефолтом `Bitrix24Exporter`, docs/PLAN.md §1/§5 M8 — `GoogleSheetsExporter`.
> По приоритету docs/PLAN.md дефолт MVP = **`GoogleSheetsExporter`**; Bitrix24/webhook — опции. См. README §6.1 п.1.

## Цель этапа

Полноценный экспорт за портом `CRMExporter`: `GoogleSheetsExporter` первым (дефолт MVP), затем как опции —
`GenericWebhookExporter` и `Bitrix24Exporter`. Выбор провайдера — в конфиге/админке, **без правок ядра**.

## Входные предпосылки

- M4 завершён: `JSONExporter` + узел `exporting` + контракт `CRMExporter`. Можно вести параллельно с M5–M7.

## Выходной результат (DoD этапа)

- `GoogleSheetsExporter` пишет строку результата в таблицу; проходит контракт `CRMExporter`; дефолт в конфиге.
- `GenericWebhookExporter` (JSON-payload на произвольный URL) и `Bitrix24Exporter` — как опции, тоже проходят контракт.
- Переключение `json`↔`google_sheets`↔`webhook`↔`bitrix24` — только конфигом, ядро не меняется.
- Выбор провайдера доступен в админке (или конфиге).

## Чек-лист задач

- [ ] M8-T1 — Общий сериализатор export-payload (переиспользуем из M4-T7)
- [ ] M8-T2 — `GoogleSheetsExporter` (дефолт MVP) — проходит контракт `CRMExporter`
- [ ] M8-T3 — Реестр/выбор активного экспортера по конфигу + дефолт в `providers.yaml`
- [ ] M8-T4 — `GenericWebhookExporter` (опция) — проходит контракт
- [ ] M8-T5 — `Bitrix24Exporter` (опция) — проходит контракт
- [ ] M8-T6 — UI/конфиг: выбор активного CRM-провайдера в админке

---

### M8-T1: Общий сериализатор export-payload

- **Цель / зачем:** Единый payload (summary/kpi/score/verdict/метаданные) для всех экспортеров — DRY и
  стабильный контракт.
- **Зависит от:** M4-T7
- **Затрагивает:** `app/adapters/crm/payload.py`.
- **TDD:**
  1. *Red* — `backend/tests/adapters/crm/test_payload.py` — кейсы: из `analysis`+`recording` собирается payload
     с менеджером/датой/каналом/summary/баллом/вердиктом/KPI; стабильные ключи; сериализуем в JSON.
  2. *Green* — функция `build_export_payload(analysis, recording)`.
  3. *Refactor* — вынести из `JSONExporter` (M4-T7) общий код.
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + payload переиспользуется всеми экспортерами.
- **Acceptance / как проверить:** `pytest backend/tests/adapters/crm/test_payload.py`.
- **Заметки по портам/конфигу:** один payload — все адаптеры за портом `CRMExporter`.

---

### M8-T2: `GoogleSheetsExporter` (дефолт MVP)

- **Цель / зачем:** Бесплатный видимый результат без CRM-аккаунта (`docs/PLAN.md §1`) — строка в Google Sheets.
- **Зависит от:** M1-T3, M8-T1
- **Затрагивает:** `app/adapters/crm/google_sheets.py`.
- **TDD:**
  1. *Red* — подключить к контракт-набору `backend/tests/contracts/test_crm_exporter.py` (Google API замокан) —
     кейсы: `export(analysis, recording)→ExportResult` добавляет строку с payload-полями; повтор не дублирует
     (идемпотентность по recording_id); ошибка API → `failed`/ошибка экспорта; креды сервисного аккаунта из конфига.
  2. *Green* — клиент Google Sheets (сервисный аккаунт), append-row.
  3. *Refactor* — заголовки колонок из payload-ключей; батчинг (опционально).
- **Слой тестов:** контракт (`CRMExporter`); сетевой вызов замокан.
- **Definition of Done:** глобальный DoD + креды (сервисный аккаунт/ID таблицы) из конфига/env; идемпотентность.
- **Acceptance / как проверить:** `pytest backend/tests/contracts/test_crm_exporter.py`; ручной сценарий `docs/PLAN.md §6.2/§6.6`.
- **Заметки по портам/конфигу:** дефолт `active_crm=google_sheets`; смена на webhook/bitrix24 — конфигом.
- **Открытый вопрос:** Google-аккаунт/таблица (сервисный аккаунт, доступ к Sheets) — готовит заказчик (README §6.2).

---

### M8-T3: Реестр/выбор активного экспортера по конфигу

- **Цель / зачем:** Сделать выбор CRM-провайдера config-driven (`active_crm`) — инвариант сменности.
- **Зависит от:** M8-T2, M0-T3
- **Затрагивает:** `app/adapters/crm/registry.py`, `infra/config/providers.yaml` (секция CRM),
  `app/core/pipeline/nodes.py` (узел `exporting` берёт экспортер из реестра).
- **TDD:**
  1. *Red* — `backend/tests/adapters/crm/test_registry.py` — кейсы: по `active_crm` резолвится нужный адаптер
     (`json`/`google_sheets`/`webhook`/`bitrix24`); неизвестный провайдер → понятная ошибка; смена значения
     меняет адаптер без правок узла графа.
  2. *Green* — фабрика/реестр экспортеров по имени.
  3. *Refactor* — единый интерфейс конфигурации экспортера (креды/URL).
- **Слой тестов:** unit/интеграция (граф).
- **Definition of Done:** глобальный DoD + дефолт `google_sheets` в `providers.yaml`; узел `exporting` берёт
  экспортер из реестра, не хардкодит.
- **Acceptance / как проверить:** `pytest backend/tests/adapters/crm/test_registry.py`.
- **Заметки по портам/конфигу:** **ключевой инвариант** — переключение CRM конфигом, ядро не меняется.

---

### M8-T4: `GenericWebhookExporter` (опция)

- **Цель / зачем:** Отправка JSON-payload на произвольный URL — fallback/интеграция с чем угодно (ТЗ §4.6).
- **Зависит от:** M8-T1, M8-T3
- **Затрагивает:** `app/adapters/crm/webhook.py`.
- **TDD:**
  1. *Red* — контракт-набор `test_crm_exporter.py` (HTTP замокан) — кейсы: POST payload на URL из конфига;
     2xx → success; 4xx/5xx → ошибка/retry; таймаут обрабатывается; подпись/заголовки из конфига (опц.).
  2. *Green* — httpx-клиент POST; маппинг ответа в `ExportResult`.
  3. *Refactor* — retry/backoff из общего модуля.
- **Слой тестов:** контракт (`CRMExporter`).
- **Definition of Done:** глобальный DoD + URL/заголовки из конфига; проходит общий контракт.
- **Acceptance / как проверить:** `pytest backend/tests/contracts/test_crm_exporter.py`.
- **Заметки по портам/конфигу:** выбирается `active_crm=webhook`; ядро не меняется.

---

### M8-T5: `Bitrix24Exporter` (опция)

- **Цель / зачем:** Экспорт в Bitrix24 через REST/webhook (ТЗ §4.6) — опция, не дефолт (по docs/PLAN.md).
- **Зависит от:** M8-T1, M8-T3, M8-T4
- **Затрагивает:** `app/adapters/crm/bitrix24.py`.
- **TDD:**
  1. *Red* — контракт-набор `test_crm_exporter.py` (Bitrix REST замокан) — кейсы: создание/обновление сущности
     (дело/комментарий/поле сделки) из payload; маппинг полей из конфига; ошибка API → retry/ошибка; идемпотентность
     по recording_id.
  2. *Green* — клиент Bitrix24 REST/webhook; маппинг payload→поля.
  3. *Refactor* — вынести маппинг полей в конфиг.
- **Слой тестов:** контракт (`CRMExporter`).
- **Definition of Done:** глобальный DoD + маппинг полей config-driven; проходит общий контракт.
- **Acceptance / как проверить:** `pytest backend/tests/contracts/test_crm_exporter.py`.
- **Заметки по портам/конфигу:** `active_crm=bitrix24` конфигом.
- **Открытый вопрос:** целевая сущность и маппинг полей Bitrix24 (дело/комментарий/поле сделки) — подтвердить с
  заказчиком (`docs/PLAN.md §7`, README §6.2).

---

### M8-T6: UI/конфиг — выбор активного CRM-провайдера

- **Цель / зачем:** Дать выбрать CRM-провайдера в админке (ТЗ §4.6 — выбор в конфиге/админке).
- **Зависит от:** M8-T3, M6-T5 (админ-каркас)
- **Затрагивает:** `app/api/admin.py` (настройка провайдера), `frontend/app/admin/settings/`.
- **TDD:**
  1. *Red* — `backend/tests/api/test_crm_settings.py` + компонент-тест — кейсы: admin выбирает активный CRM из
     доступных; значение валидируется реестром (M8-T3); смена применяется к новым экспортам; невалидный выбор → 422.
  2. *Green* — API чтения/смены `active_crm` + UI-селект; персист настройки.
  3. *Refactor* — единый источник настройки (конфиг ↔ БД); подсказки по обязательным кредам провайдера.
- **Слой тестов:** API + frontend unit.
- **Definition of Done:** глобальный DoD + только admin; смена провайдера не требует деплоя/кода.
- **Acceptance / как проверить:** `pytest backend/tests/api/test_crm_settings.py`; ручной сценарий `docs/PLAN.md §6.6`.
- **Заметки по портам/конфигу:** замыкает инвариант: провайдер CRM меняется конфигом/админкой, ядро неизменно.
