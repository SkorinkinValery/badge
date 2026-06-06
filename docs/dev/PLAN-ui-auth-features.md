# План: фиксы UI/auth + новые фичи MVP «Аудиобейдж»

> Источник: согласованный план из сессии локального запуска MVP (2026-06-07).
> Решения заказчика: токен в `sessionStorage` (гард централизуем); в объём входят
> мультиюзер+роли, retention, датасеты+eval. Bitrix24 и cookie+middleware — вне объёма.

## Статус выполнения (обновлено тимлидом 2026-06-07)
- ✅ **Блок A** — реализован (фоновый агент-фронтендер). 55/55 frontend-тестов, `tsc` без новых ошибок (3 — pre-existing).
- ✅ **Блок B** — реализован (агент-бэкендер) + интегрирован: миграция `user.is_active` накачена, сид admin при старте (`admin_seeded_ok`), DB-backed логин с ролью в JWT, `/api/admin/users` CRUD, UI `/admin/users` + пункт меню. mypy --strict чистый, 42 новых backend-теста зелёные.
- ✅ **Блок C** — реализован: `services/retention.py`, `scripts/purge_retention.py --dry-run` (проверен), конфиг `retention_days`, отображение `retention_until` в детали записи.
- ⏸ **Блок D** — не начат (нужны реальные размеченные звонки от заказчика).
- ⚠️ Известно: 3 pre-existing ошибки `tsc` (ScoreCorrectionForm/ws.ts/record-page.test) и pre-existing backend integration-тесты (jiwer/live-MinIO) — не относятся к этим блокам.

## Context
При локальном запуске MVP обнаружились реальные дефекты фронта и «протекающая» иерархия:
- корневой `layout.tsx`/`page.tsx` были дефолтным шаблоном `create-next-app` (страницы на Mantine падали с 500) — **уже починено** (добавлен `MantineProvider`, временный навигационный хаб на `/`);
- защита маршрутов сделана клиентски и **продублирована в 7 страницах** (`useEffect → getToken → /login`), с «мерцанием» и без единой точки;
- нет навигации внутри приложения (между разделами только через URL), нет кнопки «Выйти» (`clearToken()` есть, но не вызывается), нет глобальной обработки 401;
- информация показывается до авторизации (публичный хаб) — это не устроило заказчика.

В бэкенде есть **недотянутый каркас**: `UserModel` + `seed_admin_if_missing`/`verify_password`/`UserRepo`-протокол существуют, но логин сверяется с `.env`, а не с БД; поле `retention_until` заполняется в `uploads.py`, но джобы удаления нет; скрипты `eval_*`/`calibrate` готовы, но `datasets/` пуст.

**Цель:** правильная иерархия UI с авторизацией как входной точкой + доведение трёх фич до рабочего состояния.

---

## Уже сделано (контекст)
- `Makefile` (`make dev`/`make stop`/`up`/`down`/`migrate`/`test` …).
- `frontend/src/app/layout.tsx` — подключён `@mantine/core/styles.css`, `ColorSchemeScript`, `MantineProvider`.
- `frontend/src/app/page.tsx` — временный навигационный хаб (**будет заменён** в блоке A на redirect).

---

## Блок A — Иерархия UI + auth-рефактор (FIX) ⭐ приоритет
Модель: внутренний инструмент → у неавторизованного только `/login`; всё остальное за единым гардом + общий `AppShell` с меню.

- [ ] **A1. Route-группы.** Создать `(app)/` и перенести в неё `recordings/`, `admin/`. Группа `(auth)/` уже есть (`login/`) — добавить `(auth)/layout.tsx` (минимальный центрированный каркас, без меню).
- [ ] **A2. `(app)/layout.tsx`** (client): единственный гард `if(!getToken()) redirect('/login')` + Mantine `AppShell` (header + navbar). Разделы: **Звонки** → Записи (`/recordings`), Запись с микрофона (`/recordings/record`); **Администрирование** → Менеджеры, Скрипты, Сводка, Настройки.
- [ ] **A3. Убрать дубли гарда** из 7 страниц: `recordings/page.tsx`, `recordings/[id]/page.tsx`, `recordings/record/page.tsx`, `admin/{managers,scripts,summary,settings}/page.tsx`.
- [ ] **A4. `page.tsx` (корень)** — заменить хаб на redirect: есть токен → `/recordings`, иначе → `/login`.
- [ ] **A5. Logout.** Кнопка «Выйти» в header `AppShell` → `clearToken()` + redirect `/login`.
- [ ] **A6. Меню по ролям.** Добавить `getRole()` в `frontend/src/lib/auth.ts` (декод payload JWT либо сохранять роль при логине). Раздел «Администрирование» скрывать для не-admin.
- [ ] **A7. Глобальный 401.** В `apiFetch` (`frontend/src/lib/api.ts`) при `401` → `clearToken()` + redirect `/login`.
- [ ] **A8. Тесты фронта.** Обновить `frontend/src/test/*` под новый layout-гард; добавить тест на redirect/скрытие меню по роли.

**Файлы:** `frontend/src/app/{layout.tsx,page.tsx,(auth)/,(app)/}`, `frontend/src/lib/{auth.ts,api.ts}`.

---

## Блок B — Мультиюзер + роли из БД (FEATURE)
Каркас есть: `backend/app/db/models/user.py`, `backend/app/services/auth.py` (`hash_password`/`verify_password`/`seed_admin_if_missing`/`UserRepo`-протокол, `UserRole={ADMIN,VIEWER}`).

- [ ] **B1. `UserRepo` реализация** — `backend/app/db/repositories/user_repo.py` по образцу `manager_repo.py`.
- [ ] **B2. Логин из БД.** `backend/app/api/auth.py`: `verify_password` против `UserModel`; роль из записи → в JWT.
- [ ] **B3. Сидинг admin при старте.** В `lifespan` (`backend/app/main.py`) вызвать `seed_admin_if_missing`.
- [ ] **B4. Роли.** Подтвердить набор (`admin`/`viewer`; при необходимости `manager`), согласовать с `AdminRequired`/`AnyUserRequired`.
- [ ] **B5. Управление пользователями (API)** `/api/admin/users` CRUD (admin-only) + Alembic-миграция при новых полях.
- [ ] **B6. UI `/admin/users`** (внутри `(app)`, admin-only) по образцу `admin/managers/page.tsx`.
- [ ] **B7. Тесты** — repo, login-из-БД, guard по роли, контракт API.

**Файлы:** `backend/app/db/repositories/user_repo.py`, `backend/app/api/auth.py`, `backend/app/api/admin.py` (или `users.py`), `backend/app/main.py`, `frontend/src/app/(app)/admin/users/`, миграция.

---

## Блок C — Retention / автоудаление (FEATURE)
Каркас есть: `retention_until` на `RecordingModel`, заполняется в `uploads.py` (`_DEFAULT_RETENTION_DAYS = 90`).

- [ ] **C1. Сервис удаления** — `backend/app/services/retention.py`: записи с `retention_until < now` → удаление объектов MinIO + строк БД (recording + transcript/analysis).
- [ ] **C2. Точка запуска** — `scripts/purge_retention.py` (cron), флаг `--dry-run`.
- [ ] **C3. Конфигурируемый срок** — вынести retention-дни в `settings.py`/`providers.yaml`.
- [ ] **C4. UI (мин.)** — `retention_until` в детали записи; (опц.) настройка срока в `/admin/settings`.
- [ ] **C5. Тесты** — отбор по сроку, удаление MinIO+БД, dry-run не удаляет.

**Файлы:** `backend/app/services/retention.py`, `scripts/purge_retention.py`, `backend/app/config/settings.py`, `backend/app/api/uploads.py`, `frontend/src/app/(app)/recordings/[id]/`.

---

## Блок D — Датасеты + eval/калибровка (FEATURE)
Каркас есть: `scripts/dataset.py`, `eval_wer.py`, `eval_kpi.py`, `regression_harness.py`, `calibrate.py`.

- [ ] **D1. Наполнить `datasets/<id>/`** размеченными звонками (`meta/golden_transcript/kpi_labels.json`) — данные от заказчика.
- [ ] **D2. Привязать eval к пайплайну** — `hypothesis_fn` → `FasterWhisperEngine`; `pred` → OpenAI-compatible анализатор.
- [ ] **D3. Прогнать `eval_wer` + `eval_kpi`**, зафиксировать baseline (`wer=0.05`, `kpi_mae=0.50`).
- [ ] **D4. Калибровка промптов** — `calibrate.py` с реальным `eval_fn`.
- [ ] **D5. Документировать** результаты и пороги.

**Файлы:** `datasets/`, `scripts/{eval_wer,eval_kpi,calibrate}.py`, `docs/`.

---

## Вне объёма
- cookie + Next `middleware.ts` (серверная защита) — перед продом.
- Bitrix24 `field_mapping` / боевой `active_crm`.
- vLLM self-host (`--profile self-host`).

---

## Verification
**Фронт (A):** `make dev` → `/` без токена → `/login`; с токеном → `/recordings`; навигация в `AppShell`; «Выйти» чистит токен; меню «Администрирование» скрыто для не-admin; битый токен → редирект на `/login`; `cd frontend && npm test` зелёный.

**Бэкенд (B/C):** `make up && make migrate`; `uv run pytest backend/tests/ -q`, `ruff`, `mypy --strict` зелёные; логин DB-пользователя выдаёт токен с ролью, viewer → 403 на admin-эндпоинтах; `uv run python scripts/purge_retention.py --dry-run` показывает кандидатов.

**Eval (D):** `eval_wer.py`/`eval_kpi.py` на наполненном `datasets/` дают метрики; `regression_harness.py` сохраняет/сравнивает baseline.

**Порядок:** A → B → C → D.
