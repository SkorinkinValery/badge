# M2 — `FileSource`: upload API → MinIO → нормализация → job

> Этап `docs/PLAN.md §5 M2`. Базовые соглашения, TDD-цикл, слои тестов и глобальный DoD — см.
> [README.md](README.md) (§2–§4).

## Цель этапа

Реализовать первый боевой источник: загрузка файлов (multipart, mp3/wav/m4a, валидация) → сохранение в
MinIO → нормализация (ffmpeg к единому формату до STT) → постановка job в граф. Адаптер `FileSource`
проходит контракт `AudioSource`.

## Входные предпосылки

- M1 завершён: порты, домен, модель данных, граф, воркер, стабы.

## Выходной результат (DoD этапа)

- `POST /api/uploads` принимает mp3/wav/m4a, валидирует формат/длительность, кладёт аудио в MinIO,
  создаёт `recording` (со `status=queued`, `consent_flag`, `manager_id`) и job для графа.
- Нормализация приводит любой вход к единому sample rate/кодеку до STT (downstream не зависит от формата).
- `FileSource` проходит контракт-тест порта `AudioSource`.
- `GET /api/recordings` / `GET /api/recordings/{id}` отдают статус.

## Чек-лист задач

- [ ] M2-T1 — S3/MinIO-клиент (storage-порт-обёртка) + тесты
- [ ] M2-T2 — Валидация загрузки (формат/длительность/размер)
- [ ] M2-T3 — Нормализация аудио (ffmpeg) до единого формата
- [ ] M2-T4 — Адаптер `FileSource` (проходит контракт `AudioSource`)
- [ ] M2-T5 — `POST /api/uploads` (multipart) → MinIO → recording + job
- [ ] M2-T6 — `GET /api/recordings` + `GET /api/recordings/{id}` (статусы)

---

### M2-T1: S3/MinIO storage-обёртка

- **Цель / зачем:** Единая точка работы с аудио-хранилищем (put/get/presigned), S3-совместимая — миграция
  на облачный S3 тривиальна (`docs/PLAN.md §1`).
- **Зависит от:** M0-T2, M0-T3
- **Затрагивает:** `app/services/storage.py`, `app/config/settings.py` (секция MinIO).
- **TDD:**
  1. *Red* — `backend/tests/services/test_storage.py` (против локального MinIO) — кейсы: `put_object` кладёт байты
     и возвращает ключ/путь; `get_object` читает их обратно; генерируется presigned URL; несуществующий ключ → ошибка.
  2. *Green* — клиент поверх `boto3`/`minio`; конфиг из settings.
  3. *Refactor* — выделить интерфейс `ObjectStorage`; неймспейс ключей (`recordings/{id}/...`).
- **Слой тестов:** интеграция (MinIO).
- **Definition of Done:** глобальный DoD + бакет создаётся при старте/миграции; ключи детерминированы.
- **Acceptance / как проверить:** `pytest backend/tests/services/test_storage.py`.
- **Заметки по портам/конфигу:** S3-endpoint/креды — из settings; смена MinIO→S3 = смена конфига, не кода.

---

### M2-T2: Валидация загрузки

- **Цель / зачем:** Отсечь неподдерживаемые/битые файлы до сохранения и обработки (ТЗ §4.1).
- **Зависит от:** M1-T1
- **Затрагивает:** `app/services/ingest.py` (валидаторы), `app/api/uploads.py` (схемы).
- **TDD:**
  1. *Red* — `backend/tests/services/test_upload_validation.py` — кейсы: mp3/wav/m4a — ок; неподдерживаемый
     формат (например, ogg/exe) → ошибка валидации; превышение лимита длительности/размера → ошибка;
     валидация по MIME/сигнатуре, а не только по расширению.
  2. *Green* — валидатор формата (по magic-байтам) + лимиты из конфига.
  3. *Refactor* — вынести лимиты в `providers.yaml`/settings; единый тип `ValidationError`→HTTP 422.
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + лимиты длительности/размера config-driven; понятные коды ошибок.
- **Acceptance / как проверить:** `pytest backend/tests/services/test_upload_validation.py`.
- **Заметки по портам/конфигу:** лимиты — в конфиге, не хардкод.

---

### M2-T3: Нормализация аудио (ffmpeg)

- **Цель / зачем:** Привести любой источник к единому внутреннему формату (sample rate/кодек) до STT — чтобы
  downstream не зависел от железа/формата (ТЗ §3.1, `docs/PLAN.md §5 M2`).
- **Зависит от:** M2-T1
- **Затрагивает:** `app/services/normalize.py` (стадия `normalizing` графа), `app/core/pipeline/nodes.py`.
- **TDD:**
  1. *Red* — `backend/tests/services/test_normalize.py` — кейсы: вход mp3/wav/m4a → выход единый PCM/wav
     16 kHz mono (целевой формат для whisper); длительность сохраняется (±допуск); битый файл → стадия `failed`
     с ошибкой; результат кладётся в MinIO рядом с оригиналом.
  2. *Green* — обёртка над `ffmpeg` (subprocess) → нормализованный файл; интеграция в узел `normalizing`.
  3. *Refactor* — параметры формата в конфиг; временные файлы через `tempfile`, очистка.
- **Слой тестов:** интеграция (ffmpeg + MinIO) + интеграция графа (узел `normalizing`).
- **Definition of Done:** глобальный DoD + целевой формат параметризован (по умолчанию 16 kHz mono wav);
  ошибки ffmpeg → `failed` с `stage_error`.
- **Acceptance / как проверить:** `pytest backend/tests/services/test_normalize.py`.
- **Заметки по портам/конфигу:** целевой формат STT-агностичен на уровне порта; смена STT не требует смены нормализации.

---

### M2-T4: Адаптер `FileSource`

- **Цель / зачем:** Реализовать порт `AudioSource` для файлов; пройти общий контракт-тест.
- **Зависит от:** M1-T3, M2-T1, M2-T3
- **Затрагивает:** `app/adapters/audio/file_source.py`.
- **TDD:**
  1. *Red* — подключить `FileSource` к контракт-параметризации (`backend/tests/contracts/test_audio_source.py`)
     — кейсы: `fetch()` отдаёт нормализованный payload + метаданные (менеджер/канал=`file`/время/`consent_flag`);
     контракт-набор зелёный.
  2. *Green* — `FileSource` читает объект из MinIO, отдаёт нормализованный поток + метаданные.
  3. *Refactor* — переиспользовать storage-обёртку (M2-T1) и нормализацию (M2-T3).
- **Слой тестов:** контракт (`AudioSource`).
- **Definition of Done:** глобальный DoD + `FileSource` неотличим от стаба на уровне контракта (взаимозаменяемость).
- **Acceptance / как проверить:** `pytest backend/tests/contracts/test_audio_source.py`.
- **Заметки по портам/конфигу:** выбор источника не зашит — граф работает с любым `AudioSource`.

---

### M2-T5: `POST /api/uploads` → MinIO → recording + job

- **Цель / зачем:** Боевой вход файлов: создать запись, сохранить аудио, поставить job в граф (ТЗ §4.1).
- **Зависит от:** M2-T2, M2-T4, M1-T7
- **Затрагивает:** `app/api/uploads.py`, `app/services/ingest.py`, `app/db/repositories/recording.py`.
- **TDD:**
  1. *Red* — `backend/tests/api/test_uploads.py` (httpx, multipart) — кейсы: валидный mp3 → 201 с `recording_id`,
     аудио в MinIO, `recording.status=queued`, передан `manager_id` и `consent_flag`; невалидный формат → 422;
     отсутствие `consent_flag` для боевой записи → ошибка/предупреждение (ПДн); job появляется для воркера.
  2. *Green* — роутер multipart → валидация → storage → создать `recording` → enqueue (`status=queued`).
  3. *Refactor* — транзакционность (сначала storage, затем БД); идемпотентность по хэшу файла.
- **Слой тестов:** API + интеграция.
- **Definition of Done:** глобальный DoD + `consent_flag` обязателен для боевых записей (ПДн);
  `retention_until` проставляется из конфигурируемого срока.
- **Acceptance / как проверить:** `curl -F file=@sample.mp3 -F manager_id=.. -F consent_flag=true /api/uploads`;
  `pytest backend/tests/api/test_uploads.py`.
- **Заметки по портам/конфигу:** API кладёт job — дальше единый граф; источник заменяем.

---

### M2-T6: `GET /api/recordings` + `GET /api/recordings/{id}`

- **Цель / зачем:** Видимость статусов обработки для UI (ТЗ §4.7, список + карточка).
- **Зависит от:** M2-T5
- **Затрагивает:** `app/api/recordings.py`, `app/db/repositories/recording.py`.
- **TDD:**
  1. *Red* — `backend/tests/api/test_recordings.py` — кейсы: список отдаёт записи со статусами
     (`uploaded/queued/normalizing/.../done/failed`); фильтр по менеджеру/дате; детальный эндпоинт отдаёт
     запись + (если есть) transcript/analysis; несуществующий id → 404.
  2. *Green* — роутеры + репозиторий-запросы + Pydantic-схемы ответа.
  3. *Refactor* — пагинация; проекция статуса из State графа.
- **Слой тестов:** API.
- **Definition of Done:** глобальный DoD + статусы соответствуют `docs/PLAN.md §2.3`; доступ позже ограничится ролью (M5).
- **Acceptance / как проверить:** `pytest backend/tests/api/test_recordings.py`.
- **Заметки по портам/конфигу:** статус — проекция State графа, единая для всех источников.
