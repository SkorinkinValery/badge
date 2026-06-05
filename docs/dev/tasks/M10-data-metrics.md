# M10 — Данные и метрики качества

> Этап `docs/PLAN.md §5 M10`. Базовые соглашения, TDD-цикл, слои тестов и глобальный DoD — см.
> [README.md](README.md) (§2–§4).

## Цель этапа

Завести eval-инфраструктуру: загрузка 16–20 ч размеченного набора; `eval_wer.py` (jiwer) для STT;
`eval_kpi.py` (accuracy/F1 по каждому KPI); regression-харнесс по golden-set (апгрейд №7 §12 ТЗ);
калибровка промптов/весов. Eval-скрипты — **некритичный** quality-gate (не блокируют CI на пустом датасете).

## Входные предпосылки

- M3 (STT), M4 (анализ/скоринг) завершены: есть транскрипты и `analysis` для сравнения с разметкой.
  Можно вести параллельно с M8/M9. Финальная калибровка — после набора 16–20 ч.

## Выходной результат (DoD этапа)

- Формат размеченного датасета и golden-транскриптов определён; загрузчик читает `datasets/`.
- `scripts/eval_wer.py` считает WER (jiwer) на golden-наборе.
- `scripts/eval_kpi.py` считает accuracy/F1 по каждому KPI против ручной разметки.
- `scripts/regression_harness.py` прогоняет golden-set и сравнивает метрики (защита от тихой деградации промпта).
- Калибровка: процедура подбора `initial_prompt`/весов/промпта по метрикам.
- Все eval-скрипты skip/xfail на пустом `datasets/`; eval-джоба CI некритична.

## Чек-лист задач

- [ ] M10-T1 — Формат датасета/golden + загрузчик `datasets/`
- [ ] M10-T2 — `eval_wer.py` (jiwer) — WER STT
- [ ] M10-T3 — `eval_kpi.py` — accuracy/F1 по каждому KPI
- [ ] M10-T4 — `regression_harness.py` — golden-set + сравнение метрик
- [ ] M10-T5 — Few-shot из размеченного набора → в промпт (связка M4-T2)
- [ ] M10-T6 — Процедура калибровки промптов/весов (`calibrate.py`)
- [ ] M10-T7 — Некритичная eval-джоба CI (skip без датасета)

---

### M10-T1: Формат датасета/golden + загрузчик

- **Цель / зачем:** Зафиксировать структуру размеченного набора (KPI-разметка + golden-транскрипты) для всех eval.
- **Зависит от:** M4-T8
- **Затрагивает:** `datasets/` (схема/README формата), `scripts/dataset.py` (загрузчик).
- **TDD:**
  1. *Red* — `backend/tests/scripts/test_dataset_loader.py` — кейсы: загрузчик читает запись датасета
     (аудио-ref, golden-транскрипт, ручная KPI-разметка, метаданные менеджера/скрипта); пустой `datasets/` →
     корректный пустой результат, не ошибка; невалидная разметка → понятная ошибка.
  2. *Green* — схема (Pydantic) + загрузчик; крупные файлы — в `.gitignore` (`docs/PLAN.md §2.2`).
  3. *Refactor* — версия формата; валидация связности KPI-ключей с `kpi.yaml`.
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + формат документирован; пустой датасет не ломает загрузку.
- **Acceptance / как проверить:** `pytest backend/tests/scripts/test_dataset_loader.py`.
- **Заметки по портам/конфигу:** KPI-ключи разметки сверяются с `kpi.yaml` (config-driven).

---

### M10-T2: `eval_wer.py` (jiwer)

- **Цель / зачем:** Мерить WER STT на 16–20 ч размеченного набора (ТЗ §9, `docs/PLAN.md §6.7`).
- **Зависит от:** M10-T1, M3-T4
- **Затрагивает:** `scripts/eval_wer.py`.
- **TDD:**
  1. *Red* — `backend/tests/scripts/test_eval_wer.py` — кейсы: на синтетической паре (gold/hyp) jiwer даёт
     ожидаемый WER; нормализация текста (регистр/пунктуация) применяется; пустой датасет → skip/0 записей,
     не падение; агрегат по набору.
  2. *Green* — обёртка над `jiwer` + чтение golden (M10-T1) + прогон STT.
  3. *Refactor* — конфиг нормализации; вывод per-record и агрегата.
- **Слой тестов:** eval (некритичный) + unit на расчёт.
- **Definition of Done:** глобальный DoD + не блокирует CI на пустом датасете; WER измеряется на реальном наборе.
- **Acceptance / как проверить:** `python scripts/eval_wer.py --dataset datasets/...`; `pytest backend/tests/scripts/test_eval_wer.py`.
- **Заметки по портам/конфигу:** STT — через порт; eval сравнивает любой STT-провайдер.

---

### M10-T3: `eval_kpi.py` (accuracy/F1)

- **Цель / зачем:** Мерить качество KPI-анализа против ручной разметки (ТЗ §9, `docs/PLAN.md §6.7`).
- **Зависит от:** M10-T1, M4-T6
- **Затрагивает:** `scripts/eval_kpi.py`.
- **TDD:**
  1. *Red* — `backend/tests/scripts/test_eval_kpi.py` — кейсы: на синтетических предсказаниях/разметке считаются
     accuracy и F1 **по каждому KPI**; fact-KPI (бинарные) → precision/recall/F1; scale-KPI → согласованность/MAE;
     пустой датасет → skip; агрегат по набору и по KPI.
  2. *Green* — расчёт метрик per-KPI + прогон `Analyzer` (или из сохранённых `analysis`).
  3. *Refactor* — общий модуль метрик; отчёт per-KPI.
- **Слой тестов:** eval (некритичный) + unit на расчёт.
- **Definition of Done:** глобальный DoD + не блокирует CI пустым датасетом; метрики по каждому KPI.
- **Acceptance / как проверить:** `python scripts/eval_kpi.py --dataset datasets/...`; `pytest backend/tests/scripts/test_eval_kpi.py`.
- **Заметки по портам/конфигу:** Analyzer — через порт; eval сравнивает любой LLM-провайдер (gpt-4o-mini/vLLM/RU).

---

### M10-T4: `regression_harness.py` (golden-set)

- **Цель / зачем:** Защита от тихой деградации при изменении промпта/весов (апгрейд №7 §12 ТЗ, `docs/PLAN.md §6.7`).
- **Зависит от:** M10-T2, M10-T3
- **Затрагивает:** `scripts/regression_harness.py`.
- **TDD:**
  1. *Red* — `backend/tests/scripts/test_regression_harness.py` — кейсы: прогон golden-set фиксирует базовые
     метрики (WER/accuracy/F1); при ухудшении против сохранённого baseline харнесс сигналит (нестрого/как warning);
     пустой golden → skip; отчёт diff метрик.
  2. *Green* — связать eval_wer/eval_kpi, хранить baseline, считать diff.
  3. *Refactor* — пороги допустимого дрейфа в конфиг; формат baseline-снапшота.
- **Слой тестов:** eval (некритичный).
- **Definition of Done:** глобальный DoD + некритичный (warning, не блок merge); пороги config-driven.
- **Acceptance / как проверить:** `python scripts/regression_harness.py --dataset datasets/...`.
- **Заметки по портам/конфигу:** харнесс провайдер-агностичен — гоняется на текущем активном конфиге.

---

### M10-T5: Few-shot из размеченного набора → в промпт

- **Цель / зачем:** Использовать разметку как источник few-shot (ТЗ §7), повышая качество без fine-tuning;
  замыкает M4-T2.
- **Зависит от:** M10-T1, M4-T2
- **Затрагивает:** `app/adapters/analyzer/prompt.py` (источник few-shot), `scripts/dataset.py`.
- **TDD:**
  1. *Red* — `backend/tests/adapters/analyzer/test_few_shot.py` — кейсы: при наличии датасета few-shot-примеры
     подмешиваются в промпт (число/отбор из конфига); пустой датасет → промпт без few-shot (как в M4-T2);
     few-shot не содержит ПДн сверх допустимого (обезличивание/флаг).
  2. *Green* — селектор few-shot из датасета → конструктор промпта.
  3. *Refactor* — стратегия отбора (репрезентативность); лимит длины контекста.
- **Слой тестов:** unit.
- **Definition of Done:** глобальный DoD + few-shot config-driven и опционален; пустой датасет не ломает промпт.
- **Acceptance / как проверить:** `pytest backend/tests/adapters/analyzer/test_few_shot.py`.
- **Заметки по портам/конфигу:** few-shot — данные конфига/датасета, не код; провайдер-агностично.

---

### M10-T6: Процедура калибровки (`calibrate.py`)

- **Цель / зачем:** Подбор `initial_prompt`/весов/промпта по метрикам до приемлемой точности (ТЗ §9, `docs/PLAN.md §5 M10`).
- **Зависит от:** M10-T2, M10-T3, M10-T4
- **Затрагивает:** `scripts/calibrate.py`.
- **TDD:**
  1. *Red* — `backend/tests/scripts/test_calibrate.py` — кейсы: на синтетике перебор вариантов
     (веса/`initial_prompt`) выбирает конфиг с лучшей метрикой; результат — кандидаты `weights.yaml`/`providers.yaml`,
     не правки кода; пустой датасет → no-op/skip.
  2. *Green* — цикл оценки вариантов через eval_kpi/eval_wer; вывод лучшего конфига.
  3. *Refactor* — сетка поиска из конфига; сохранение отчёта калибровки.
- **Слой тестов:** eval (некритичный) + unit.
- **Definition of Done:** глобальный DoD + результат калибровки = новые **конфиги** (веса/prompt), без правок кода
  (config-driven инвариант).
- **Acceptance / как проверить:** `python scripts/calibrate.py --dataset datasets/...`.
- **Заметки по портам/конфигу:** калибруются только конфиги (`weights.yaml`/`kpi.yaml`/`providers`), не код.

---

### M10-T7: Некритичная eval-джоба CI

- **Цель / зачем:** Прогонять eval-скрипты в CI как **некритичный** quality-gate (не блокирует merge на пустом датасете).
- **Зависит от:** M10-T2, M10-T3, M10-T4, M0-T6
- **Затрагивает:** `.github/workflows/ci.yml` (eval-джоба).
- **TDD:**
  1. *Red* — `backend/tests/scripts/test_eval_ci_guard.py` — кейсы: при отсутствии `datasets/` eval-скрипты
     завершаются skip/0-кодом (не fail); при наличии — гоняются и печатают метрики; джоба помечена `continue-on-error`.
  2. *Green* — добавить eval-джобу с `continue-on-error: true`, запуск только при наличии датасета.
  3. *Refactor* — кэш моделей/зависимостей eval; артефакты-отчёты.
- **Слой тестов:** eval (некритичный) + конфиг CI.
- **Definition of Done:** глобальный DoD + eval-джоба не блокирует merge; на пустом датасете — skip.
- **Acceptance / как проверить:** прогон CI на PR без датасета (джоба зелёная/skip) и с датасетом (метрики в логах).
- **Заметки по портам/конфигу:** eval гоняется на активном конфиге провайдеров — измеряет текущую связку.
