# ADR-001: LLM Provider Strategy — Self-Host vLLM + RU-Cloud Fallback

**Статус:** Принято  
**Дата:** 2026-06-06  
**Автор:** M9 (Self-Host LLM milestone)

---

## Контекст

Система «Аудиобейдж» передаёт транскрипты разговоров на LLM-анализ. Транскрипты содержат
персональные данные (ПДн) — голос + содержание разговора клиента. Трансграничная передача ПДн в
США (OpenAI) без согласия каждого клиента нарушает законодательство РБ (Закон о персональных данных).

На MVP (пилот с обезличенными данными / явным согласием) использовался `gpt-4o-mini` через OpenAI API
(облако, США). Целевое состояние — self-host с сохранением всего пайплайна без изменений кода.

---

## Решение

### 1. Целевой провайдер: vLLM + Qwen2.5 (self-host)

- Транскрипты **никогда не покидают периметр** при использовании self-host.
- Один адаптер (`OpenAICompatibleAnalyzer`) обслуживает и облако, и vLLM — переключение только конфигом.
- vLLM даёт OpenAI-совместимый API; для структурированного вывода используется `guided_json` через
  `extra_body` (поле `structured_output_mode: guided_json` в конфиге).
- Размер модели определяется доступным VRAM: 7B-AWQ (~10 GB), 14B-AWQ (~20 GB).

### 2. Fallback: RU-облако (YandexGPT / GigaChat)

- Российская юрисдикция — допустимый fallback при невозможности self-host.
- Реализованы отдельные адаптеры (`YandexGptAnalyzer`, `GigaChatAnalyzer`) за тем же портом `Analyzer`.
- Выбор активного провайдера — только конфигом, код ядра не меняется.

### 3. STT: аналогичная стратегия

- faster-whisper — self-host (аудио не покидает периметр с M1).
- RU-облако fallback: `YandexSttEngine` (Yandex SpeechKit), `SberSttEngine` (SaluteSpeech).

---

## Переключение провайдеров (инструкция)

### Переход cloud → self-host vLLM

1. Поднять vLLM: `docker compose --profile self-host up -d vllm`
2. В `infra/config/providers.yaml` скопировать блок `llm_profiles.self_host` в `active_llm`:

```yaml
active_llm:
  adapter: openai_compatible
  base_url: http://vllm:8000/v1
  model: Qwen/Qwen2.5-7B-Instruct-AWQ
  structured_output_mode: guided_json
```

3. Убедиться, что `LLM_API_KEY` не требуется (для локального vLLM — пустой).
4. Перезапустить backend: `docker compose restart backend`.
5. Проверить: `curl http://vllm:8000/health`.

### Переход на RU-облако LLM (YandexGPT)

1. Получить IAM-токен или API-ключ Yandex Cloud, установить `folder_id`.
2. Установить env: `LLM_API_KEY=<iam-token>`, `YANDEX_FOLDER_ID=<folder-id>`.
3. В `providers.yaml` скопировать `llm_profiles.ru_cloud` в `active_llm`:

```yaml
active_llm:
  adapter: openai_compatible
  base_url: https://llm.api.cloud.yandex.net/foundationModels/v1/completion
  model: yandexgpt-lite/latest
  structured_output_mode: json_object
```

4. Перезапустить backend.

### Переход на RU-облако STT (Yandex SpeechKit)

1. Установить env: `STT_API_KEY=<api-key>`, `YANDEX_FOLDER_ID=<folder-id>`.
2. В `providers.yaml`:

```yaml
active_stt: yandex
stt:
  yandex:
    api_key: null      # из STT_API_KEY env
    folder_id: null    # из YANDEX_FOLDER_ID env
    language: ru-RU
```

3. Перезапустить backend.

---

## ПДн-обоснование

| Провайдер | Данные покидают периметр? | Соответствие РБ |
|-----------|--------------------------|-----------------|
| vLLM self-host | Нет | ✅ Да |
| YandexGPT / GigaChat | Да, но RU-юрисдикция | ✅ Допустимо |
| OpenAI (облако) | Да, США | ⚠️ Только на пилоте с согласием |

**Self-host (vLLM) — целевое состояние.** OpenAI — только для пилота с явным согласием или
обезличенными данными. RU-облако — промежуточный вариант.

---

## Инвариант архитектуры (доказан M9-T5)

Один пайплайн (LangGraph-граф) работает с любым провайдером STT/LLM без изменения кода ядра.
Доказано тестом `test_provider_swappability.py`: stub / cloud / vLLM / RU-cloud дают
`analysis_result` через один граф.

```
Провайдер меняется только в providers.yaml.
Код ядра (core/pipeline/*) не импортирует адаптеры.
```

---

## Отклонённые альтернативы

- **Разные адаптеры для cloud/vLLM** — отклонено: vLLM совместим с OpenAI API → один адаптер.
- **Стриминг вывода vLLM** — отложено: `guided_json` работает в batch-режиме; стриминг — M10+.
- **Использовать только RU-облако** — отклонено: зависимость от внешней инфраструктуры; self-host надёжнее для ПДн.
