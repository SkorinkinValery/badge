# M9 — Self-host LLM (целевой) + RU-облако fallback

> Этап `docs/PLAN.md §5 M9`. **Пост-MVP, целевой шаг под ПДн.** Базовые соглашения, TDD-цикл, слои тестов и
> глобальный DoD — см. [README.md](README.md) (§2–§4).

## Цель этапа

Перевести анализ на локальный **vLLM + Qwen2.5** (целевое решение под ПДн — транскрипты не уходят в облако)
**сменой конфига**, без правок кода ядра. Добавить адаптеры RU-облака (Yandex/Sber STT, YandexGPT/GigaChat)
за теми же портами как fallback. Доказать инвариант сменности: тот же пайплайн/контракт/схема.

## Входные предпосылки

- M4 завершён: порт `Analyzer`, схема `KpiResult`, `OpenAICompatibleAnalyzer`, контракт `Analyzer`.
  M3 — порт `STTEngine` и контракт. Можно вести параллельно с M8/M10.

## Выходной результат (DoD этапа)

- vLLM + Qwen2.5 подключён через **тот же** `OpenAICompatibleAnalyzer` сменой `base_url`/`model`/`api_key`;
  `guided_json` по той же схеме `KpiResult`.
- `+vLLM` в `docker-compose` как отдельный сервис (только на этом этапе).
- RU-облако STT (Yandex/Sber) и LLM (YandexGPT/GigaChat) — адаптеры за портами, проходят контракты.
- Доказано тестом: переключение провайдеров конфигом не меняет код ядра/графа.

## Чек-лист задач

- [ ] M9-T1 — vLLM-сервис в compose (+ Qwen2.5) + конфиг провайдера
- [ ] M9-T2 — Прогон `OpenAICompatibleAnalyzer` против vLLM (`guided_json`, та же схема) через конфиг
- [ ] M9-T3 — `YandexSttEngine` / `SberSttEngine` (fallback) — проходят контракт `STTEngine`
- [ ] M9-T4 — RU-облако LLM (YandexGPT/GigaChat) за портом `Analyzer` — проходит контракт
- [ ] M9-T5 — Тест инварианта сменности: один пайплайн на разных провайдерах (конфиг-only)
- [ ] M9-T6 — ADR + документация переключения; ПДн-обоснование

---

### M9-T1: vLLM-сервис в compose + Qwen2.5 + конфиг

- **Цель / зачем:** Инфраструктура self-host LLM (`docs/PLAN.md §1` GPU-бюджет) — целевое снятие ПДн-риска.
- **Зависит от:** M4-T3
- **Затрагивает:** `infra/docker-compose.yml` (+`vllm`), `infra/config/providers.yaml` (профиль self-host).
- **TDD:**
  1. *Red* — `backend/tests/infra/test_vllm_compose.py` — кейсы: compose-конфиг валиден с сервисом `vllm`
     (GPU-резервация, том модели, OpenAI-совместимый порт); профиль `self-host` в `providers.yaml` указывает
     `base_url` на vLLM и `model=Qwen2.5-...`.
  2. *Green* — добавить сервис vllm; профиль конфига.
  3. *Refactor* — параметризовать размер модели (7B/14B-AWQ) и VRAM; последовательное выполнение STT/LLM при дележе карты.
- **Слой тестов:** unit (compose) + интеграция (опц., с GPU — под маркером).
- **Definition of Done:** глобальный DoD + `vLLM` появляется только на этом этапе; размер модели/VRAM — из конфига.
- **Acceptance / как проверить:** `docker compose --profile self-host config`; `pytest backend/tests/infra/test_vllm_compose.py`.
- **Заметки по портам/конфигу:** vLLM даёт OpenAI-совместимый API → тот же адаптер, что и облако.
- **Открытый вопрос:** GPU/VRAM под пилот определяет размер Qwen2.5 (`docs/PLAN.md §8`, README §6.2).

---

### M9-T2: `OpenAICompatibleAnalyzer` против vLLM (та же схема)

- **Цель / зачем:** Доказать, что переключение на self-host LLM — **только конфиг** (`docs/PLAN.md §1/§4`).
- **Зависит от:** M9-T1, M4-T1, M4-T3
- **Затрагивает:** `app/adapters/analyzer/openai_compatible.py` (поддержка `guided_json`), `providers.yaml`.
- **TDD:**
  1. *Red* — `backend/tests/adapters/analyzer/test_vllm_guided_json.py` (vLLM замокан/записан) — кейсы: тот же
     `OpenAICompatibleAnalyzer` с `base_url` на vLLM возвращает JSON, валидный по **той же** схеме `KpiResult`;
     `guided_json` строится из экспортированной JSON-schema (M4-T1); код адаптера не разветвляется по провайдеру.
  2. *Green* — прокинуть `guided_json`/`response_format` единообразно из схемы.
  3. *Refactor* — общий слой «structured output» для облака/vLLM/RU-облака.
- **Слой тестов:** контракт (`Analyzer`).
- **Definition of Done:** глобальный DoD + один адаптер обслуживает облако и vLLM; **код ядра не меняется**.
- **Acceptance / как проверить:** `pytest backend/tests/adapters/analyzer/test_vllm_guided_json.py`; ручной сценарий `docs/PLAN.md §6.5`.
- **Заметки по портам/конфигу:** схема одна, путь переключается конфигом — целевой инвариант ПДн.

---

### M9-T3: `YandexSttEngine` / `SberSttEngine` (fallback)

- **Цель / зачем:** RU-облако STT как fallback (RU-дружественная юрисдикция, апгрейд №5 §12 ТЗ, `docs/PLAN.md §1`).
- **Зависит от:** M3-T2, M1-T3
- **Затрагивает:** `app/adapters/stt/yandex_stt.py`, `app/adapters/stt/sber_stt.py`.
- **TDD:**
  1. *Red* — контракт-набор `test_stt_engine.py` (API замокан) — кесы: возвращает сегменты с таймкодами и
     `detected_language`; креды/endpoint из конфига; ошибка API → ошибка/retry; проходит тот же контракт, что whisper.
  2. *Green* — клиенты Yandex SpeechKit / Sber SaluteSpeech → маппинг в `Transcript`.
  3. *Refactor* — общий базовый клиент RU-облака.
- **Слой тестов:** контракт (`STTEngine`).
- **Definition of Done:** глобальный DoD + выбор `active_stt=yandex|sber` конфигом; контракт един.
- **Acceptance / как проверить:** `pytest backend/tests/contracts/test_stt_engine.py`; `docs/PLAN.md §6.5`.
- **Заметки по портам/конфигу:** fallback STT — тем же портом; smena конфигом.

---

### M9-T4: RU-облако LLM (YandexGPT/GigaChat) за портом `Analyzer`

- **Цель / зачем:** Дополнительная страховка качества/юрисдикции (`docs/PLAN.md §1/§7`).
- **Зависит от:** M4-T1, M4-T3, M1-T3
- **Затрагивает:** `app/adapters/analyzer/yandexgpt.py` / `gigachat.py` (или через OpenAI-совместимый слой, если поддерживается).
- **TDD:**
  1. *Red* — контракт-набор `test_analyzer.py` (API замокан) — кейсы: `analyze`→`AnalysisResult`, `kpi_json`
     валиден по схеме `KpiResult`; креды/endpoint из конфига; невалидный ответ → retry; проходит общий контракт.
  2. *Green* — клиент RU-LLM + маппинг в `AnalysisResult` (по возможности переиспользуя structured-слой M9-T2).
  3. *Refactor* — унифицировать с OpenAI-совместимым слоем, где допустимо.
- **Слой тестов:** контракт (`Analyzer`).
- **Definition of Done:** глобальный DoD + выбор `active_llm=yandexgpt|gigachat` конфигом; контракт един.
- **Acceptance / как проверить:** `pytest backend/tests/contracts/test_analyzer.py`.
- **Заметки по портам/конфигу:** fallback LLM — тем же портом; ядро не меняется.

---

### M9-T5: Тест инварианта сменности (конфиг-only)

- **Цель / зачем:** Формально зафиксировать главный архитектурный инвариант: один пайплайн на разных
  провайдерах без правок кода (`docs/PLAN.md §6.5`).
- **Зависит от:** M9-T2, M9-T3, M9-T4
- **Затрагивает:** `backend/tests/integration/test_provider_swappability.py`.
- **TDD:**
  1. *Red* — кейсы: прогон графа с разными `providers.yaml` (whisper+gpt-4o-mini / whisper+vLLM /
     RU-STT+RU-LLM / stub) даёт корректный `analysis` тем же кодом графа; смена провайдера — только данные конфига;
     ни один импорт ядра не зависит от конкретного адаптера.
  2. *Green* — параметризовать интеграционный прогон по наборам конфигов.
  3. *Refactor* — вынести наборы конфигов в фикстуры.
- **Слой тестов:** интеграция (граф) + контракт.
- **Definition of Done:** глобальный DoD + тест доказывает: переключение конфигом, код ядра неизменен.
- **Acceptance / как проверить:** `pytest backend/tests/integration/test_provider_swappability.py`.
- **Заметки по портам/конфигу:** это «исполняемая спецификация» инварианта сменности.

---

### M9-T6: ADR + документация переключения + ПДн-обоснование

- **Цель / зачем:** Зафиксировать решение о переходе на self-host LLM под ПДн и инструкцию переключения
  (глобальный DoD: ADR при изменении решения).
- **Зависит от:** M9-T2, M9-T5
- **Затрагивает:** `docs/adr/` (новый ADR), `infra/config/providers.yaml` (профили облако/self-host/RU).
- **TDD:** (документационная задача — без red/green)
  - Описать: дефолты MVP, профиль self-host, профиль RU-fallback; как и когда переключать; ПДн-обоснование
    (транскрипты не покидают периметр на self-host).
- **Слой тестов:** —
- **Definition of Done:** глобальный DoD (часть про ADR) + есть ADR и рабочая инструкция переключения профилей.
- **Acceptance / как проверить:** ревью ADR; проверка профилей конфига командой из M9-T5.
- **Заметки по портам/конфигу:** документирует инвариант сменности и ПДн-мотивацию (`docs/PLAN.md §Context/§7`).
