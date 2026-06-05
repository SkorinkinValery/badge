# Промпт: реализация одного milestone по TDD

## Как использовать

Передай агенту этот файл + номер этапа, например:

```
Реализуй milestone M0 по промпту docs/dev/implement-milestone.md
```

---

## Задача

Ты — разработчик MVP «Аудиобейдж». Реализуй **один milestone** (передаётся параметром, например `M0`).
Работай последовательно по всем задачам этапа в **TDD**: red → green → refactor.
Заканчивай milestone, когда все задачи этапа выполнены и CI зелёный — затем **останавливайся и
делай финальный отчёт**.

---

## Что прочитать ПЕРЕД началом работы

Прочитай все четыре файла целиком — не пропускай ни один:

1. `docs/PLAN.md` — стек, архитектура ports & adapters, структура монорепо (§2.2), модель данных.
2. `docs/TZ-audiobadge-mvp.md` — требования заказчика (для понимания «зачем»).
3. `docs/dev/tasks/README.md` — глобальные соглашения: TDD-цикл, слои тестов, инструменты,
   глобальный DoD, сквозные инварианты архитектуры.
4. `docs/dev/tasks/{MILESTONE}.md` — конкретные задачи этапа (Цель / Зависит от / TDD / DoD).

При расхождении ТЗ и `docs/PLAN.md` — приоритет у `docs/PLAN.md`.

---

## Рабочий цикл (выполнять для каждой задачи в порядке M*-T1, T2, …)

### 1. Прочитай задачу

Из шарда `docs/dev/tasks/{MILESTONE}.md` возьми очередную задачу `M{N}-T{k}`:
- убедись, что все её зависимости (`Зависит от:`) уже выполнены;
- если зависимость не выполнена — скажи об этом явно и остановись.

### 2. Проверь внешние зависимости (ключи, creds, сервисы)

Если задача требует **внешнего ключа или аккаунта** (OpenAI API key, Google Sheets service account,
MinIO bucket, работающий Docker daemon, GPU и т.п.):

> **СТОП.** Сообщи пользователю: что именно нужно, в каком виде (env-переменная, файл, флаг),
> и жди явного подтверждения или предоставления ресурса.
> Не «проверяй наличие ключа в коде» — останавливайся до начала реализации задачи.

Для задач M0–M3 внешних ключей нет (faster-whisper self-host, стаб-адаптеры, Docker Compose локально).

### 3. TDD: Red

1. Напиши **падающие тесты** (файл и кейсы указаны в поле `TDD → Red` задачи).
2. Убедись, что тесты падают по **правильной причине** (не синтаксическая ошибка, а именно
   отсутствие реализации / нарушение контракта).
3. Запусти `pytest <тест-файл> -v` — убедись, что красный.

### 4. TDD: Green

4. Напиши **минимальную реализацию**, делающую тесты зелёными — ничего лишнего.
5. Запусти `pytest <тест-файл> -v` — убедись, что зелёный.
6. Запусти `ruff check <новые файлы>` и `mypy <новые файлы>` — исправь все ошибки.

### 5. TDD: Refactor

7. Почисти код без изменения поведения (именование, дублирование, структура).
8. Убедись, что тесты остаются зелёными.

### 6. Definition of Done задачи

Задача завершена, когда все критерии из поля `Definition of Done:` выполнены:
- тесты зелёные; ruff/mypy ок на новом коде;
- нет хардкода провайдеров/KPI/весов — всё из конфига;
- сохранён инвариант ports & adapters (ядро не зависит от адаптеров);
- провайдер меняется только конфигом (`base_url`/`model`/`api_key`/выбор адаптера);
- структурные логи и обработка ошибок там, где требует задача.

Переходи к следующей задаче только после выполнения DoD текущей.

---

## Сквозные инварианты — проверяй при каждой задаче

- **Ports & adapters**: код ядра (`core/`) не импортирует ничего из `adapters/`; зависимость
  направлена только внутрь (адаптеры → порты, не наоборот).
- **Сменность только конфигом**: никогда не хардкодить `model="gpt-4o-mini"` или
  `base_url="https://api.openai.com"` в коде — только в `providers.yaml` / env.
- **Config-driven**: KPI, веса, язык — из `kpi.yaml`/`weights.yaml`, не в коде.
- **Стабы перспективы**: `BadgeSource`, `TelephonySource` — заглушки (raise NotImplementedError
  или pass), созданы с самого начала, чтобы не ломать ядро позже.
- **LangGraph-граф**: статусная машина — это состояние графа, не самописный enum/switch.
  Checkpointer — Postgres.
- **ПДн**: `consent_flag` в `recording`, доступ ограничен ролью, `retention_until` — где
  задача затрагивает модель данных.

---

## Структура монорепозитория (из docs/PLAN.md §2.2)

Создавай файлы строго по этой структуре:

```
backend/
  app/
    core/
      ports/        # Protocol/ABC: AudioSource, STTEngine, Analyzer, CRMExporter
      domain/       # сущности: Recording, Transcript, Analysis, Manager, Script, User
      pipeline/     # LangGraph-граф стадий + State + checkpointer
    adapters/
      audio/        # FileSource, MicSource; стабы: BadgeSource, TelephonySource
      stt/          # FasterWhisperEngine; стабы: YandexSttEngine
      analyzer/     # OpenAICompatibleAnalyzer + KpiResult schema; StubAnalyzer
      crm/          # GoogleSheetsExporter (дефолт MVP); JSONExporter; стабы: Bitrix24, Webhook
    services/       # use-cases: ingest, process, score, export, daily_summary
    api/            # FastAPI: uploads, recordings, ws_mic, managers, scripts, admin, auth
    workers/        # фоновый раннер LangGraph-графа
    db/             # SQLAlchemy-модели, репозитории, Alembic
    config/         # pydantic-settings; загрузчик kpi.yaml/weights.yaml/providers
    main.py
  tests/
    unit/           # чистые функции (скоринг, нормализация весов, конфиги)
    contract/       # контракт-тесты портов (прогоняются против fake/stub и реальных адаптеров)
    integration/    # LangGraph-граф со стаб-STT/LLM; переходы статусов; checkpointer
    api/            # FastAPI через httpx
frontend/
infra/
  docker-compose.yml
  config/
    kpi.yaml
    weights.yaml
    providers.yaml
scripts/
  eval_wer.py
  eval_kpi.py
  regression_harness.py
```

---

## Инструменты (запускай именно этими командами)

```bash
# тесты
pytest backend/tests/ -v
pytest backend/tests/unit/         # только unit
pytest backend/tests/contract/     # только контракт
pytest backend/tests/integration/  # только интеграция

# lint + типы
ruff check backend/
mypy backend/ --strict

# запуск инфраструктуры (для интеграционных тестов)
docker compose -f infra/docker-compose.yml up -d postgres minio
docker compose -f infra/docker-compose.yml down

# миграции
alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini revision --autogenerate -m "<message>"
```

Используй фиктивные данные и стаб-адаптеры для интеграционных тестов — не обращайся к реальным
внешним сервисам без явного подтверждения пользователя.

---

## Финальный отчёт (после выполнения всех задач milestone)

Когда все задачи этапа завершены, выведи отчёт строго по форме:

```
## Milestone {M*} — выполнен

### Задачи
- [x] M*-T1: <название> — тесты зелёные, ruff/mypy ок
- [x] M*-T2: <название> — ...
- ...

### Тесты (итог)
- Всего: N | Пройдено: N | Провалено: 0
- Команда: `pytest backend/tests/ -v` — все зелёные

### Созданные/изменённые файлы
<список ключевых файлов>

### Инварианты (самопроверка)
- [ ] Ports & adapters: ядро не импортирует адаптеры
- [ ] Провайдеры — только в конфиге, не в коде
- [ ] Config-driven KPI/веса
- [ ] Стабы Badge/Telephony на месте
- [ ] ruff + mypy чистые

### Открытые вопросы / что нужно от пользователя
<список: ключи, creds, решения, подтверждения — если есть>

### Следующий шаг
Готов к **{M*+1}**: `docs/dev/tasks/{M*+1}.md`.
Запусти: «Реализуй milestone M{*+1} по промпту docs/dev/implement-milestone.md»
```

---

## Чего НЕ делать

- Не реализовывать задачи следующего milestone — только текущий.
- Не писать код без предшествующего падающего теста (кроме чисто конфиг/скаффолд шагов M0-T1/T2).
- Не хардкодить провайдеров, URL, ключи в исходном коде.
- Не менять `docs/PLAN.md`, `docs/TZ-audiobadge-mvp.md`, `docs/dev/tasks/*` — только читать.
- Не пропускать ruff/mypy после каждой задачи.
- Не продолжать задачу при красных тестах — разберись с причиной.
