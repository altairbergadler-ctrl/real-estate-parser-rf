# TASK-028 — контракт ограниченного read-only пилота ЦИАН

- Статус: завершено в рабочей ветке, не слито в `main`
- Рабочая ветка: `task/028-cian-read-only-pilot-contract`
- Целевая ветка: `main`
- Стартовый SHA: `d5f1a2ca909b09f2571860baf255b17128038b62`
- Выбранный источник: ЦИАН
- Решение: `CONDITIONAL_GO`

## Цель

На основании актуальных первичных официальных источников принять проверяемый
legal/ethical/technical контракт ограниченного read-only пилота ЦИАН и
однозначно определить, допустим ли будущий live pilot. Неопределённость должна
оставаться blocker, а не разрешением по умолчанию.

Документ не является юридическим заключением.

## Включённый объём

- Официальные правила, лицензионное соглашение и API terms ЦИАН.
- Published `public-api.cian.ru` docs/OpenAPI methods и ограничения.
- Official `robots.txt` только как дополнительный technical constraint.
- Official legal source по принципам обработки персональных данных.
- Различение official API, partner/contract feed, written permission,
  inbound XML и HTML/browser scraping.
- Проверка, существует ли published route для public listings search product.
- Решение о достаточности API-key/terms и наличии rate limits/quotas.
- Минимальный query/traffic/record/field budget, PII rules, retention,
  stop conditions и audit evidence.
- ADR 0011, отдельная design-спецификация и минимальное согласование project
  state documents.

## Исключённый объём

- Любые search/listing/card/internal endpoint requests и real listing data.
- Account, API-key, email/form/support request, login, OAuth, cookies и secret.
- HTML/browser scraping, automation, CAPTCHA, proxy, session и обход защиты.
- Source adapter, scraper, live pilot, saved real fixture, SQL/JSON schema,
  CLI, UI, scheduler и deployment.
- AI, OpenClaw, Telegram и чувствительные сигналы.
- Изменение `src/`, `tests/`, fixtures/golden, `pyproject.toml` или `uv.lock`.
- TASK-029, merge в `main`, push, удаление ветки/worktree.

## Критерии готовности

- [x] Итоговый статус ровно `GO`, `CONDITIONAL_GO` или `NO_GO` и однозначен.
- [x] Каждый разрешающий вывод опирается на открытую official page/schema;
  отсутствие данных не превращено в разрешение.
- [x] Published API проверен на public listings search, own listings и XML
  import scope различены.
- [x] API-key отделён от предварительного разрешения exact use case.
- [x] Published rate guidance зафиксирован без выдуманной квоты; отсутствие
  method-specific limit является blocker.
- [x] Official API/partner access, HTML scraping и external XML/feed сравнены
  в ADR 0011; выбран один conditional route.
- [x] Один predeclared query, one-request budget, максимум 20 records и
  allowlist structured fields определены без live access.
- [x] PII, contacts, account IDs, free text, images и inference о владельце за
  границей запрещены.
- [x] Retention, raw capture prohibition, provenance, version/schema evidence
  и deletion receipt заданы.
- [x] CAPTCHA, `401/403/429`, robots/terms conflict, schema drift, unexpected
  PII, undocumented endpoint и protection bypass являются immediate stop.
- [x] Cheap mode исключает AI, browser, parallelism, retry и scheduler.
- [x] Unknown conditions перечислены как blockers с exact unblock evidence.
- [x] Следующий шаг ограничен возможной отдельной offline TASK-029 после
  выполнения условий; controlled live pilot отложен на более позднюю задачу.
- [x] Existing domain contracts/code/dependencies/fixtures не изменены.
- [x] Все назначенные checks успешны; один documentation commit, чистое дерево,
  без merge в `main`.

## Фактически выполненная работа

- Создан [ADR 0011](../decisions/0011-cian-read-only-pilot-contract.md),
  принявший `CONDITIONAL_GO`: live pilot сейчас запрещён, HTML/internal routes
  отвергнуты, единственный возможный route — written-authorized official
  public-listings API или outbound partner feed.
- Создана
  [детальная design-спецификация](../design/CIAN-READ-ONLY-PILOT-CONTRACT.md)
  с source register, seven blockers, query/data/traffic ceiling, PII/retention,
  stop conditions и audit checklist.
- Published OpenAPI schema проверена как documentation без data-method calls:
  offers methods относятся к объявлениям агентства, XML — к входящему
  импорту, public catalog search method отсутствует.
- Общая рекомендация API `<=10 requests/second/method` зафиксирована только как
  published guidance; с учётом оговорки о method-specific изменениях и
  отсутствия target method она не признаётся достаточной квотой.
- Зафиксировано, что API-key сам по себе не заменяет preliminary permission по
  API terms 3.5 и rules сайта.
- Реальные объявления, contacts, images, text, secrets и source code не
  получались и не сохранялись.
- `PROJECT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHECKPOINT.md` и task registry
  согласованы только с design-only решением.

## Проверки

- `uv sync --frozen` — успешно; CPython 3.14.7 environment собран по frozen
  lock, dependencies/lock не изменены.
- `uv lock --check` — успешно; resolved 18 packages, lock соответствует
  project metadata.
- `uv run quality` — успешно: Ruff format-check (`102 files`), Ruff lint,
  strict mypy (`44 source files`), основной pytest (`618 passed`) и fixture
  catalog integrity (`44 passed`).
- `git diff --check` — успешно.
- Все 62 относительные Markdown links в 8 изменённых документах — успешно;
  broken links отсутствуют.
- Changed-path audit — успешно: ровно 8 назначенных Markdown files; `src/`,
  `tests/`, fixtures/golden, `pyproject.toml` и `uv.lock` не изменены.
- Sensitive/real-data audit — успешно: в изменениях нет listing/card URLs,
  listing IDs, phones, bearer/API secrets или saved listing records; non-doc
  Cian references отсутствуют.
- Official-source audit — успешно: positive/conditional facts traceable к
  source register; отсутствие public method/method-specific quota осталось
  blocker, а internal `robots.txt` path не признан разрешением.
- Проверки выполняются на Windows; Linux не входит в задачу.

## Итог

**`CONDITIONAL_GO`**: controlled live pilot ЦИАН сейчас запрещён. Для снятия
условий требуются written permission именно на public-listings search use case,
official documented endpoint/outbound feed, field/use/attribution rights,
method-specific quota/retry rules, PII-safe schema/sample, retention/deletion
terms и fresh terms/schema/robots audit. Неполный ответ сохраняет запрет;
отказ означает `NO_GO`.

## Итоговый коммит

Один атомарный documentation commit будет создан после полного successful
audit. Точный SHA подтверждается Git после commit и не дублируется внутри его
собственного снимка.

## Следующая рекомендуемая задача

Сначала вне TASK-028 получить все доказательства `B1`–`B6`, не поручая этой
задаче отправку обращений. Только после полного подтверждения отдельная
TASK-029 может реализовать offline adapter на provider-supplied
synthetic/redacted либо явно разрешённом сохранённом примере, без live access.
Controlled live pilot остаётся ещё более поздней отдельной задачей.
