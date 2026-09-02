# Контракт ограниченного read-only пилота ЦИАН

## Статус и назначение

- Источник: ЦИАН.
- Дата проверки официальных источников: 2026-09-02.
- Решение: **`CONDITIONAL_GO`**.
- Live access сейчас: **запрещён до снятия всех blockers**.
- Тип документа: design/research contract, не юридическое заключение.

Документ конкретизирует [ADR 0011](../decisions/0011-cian-read-only-pilot-contract.md)
до проверяемого gate будущего минимального пилота. Он не разрешает текущей
задаче получать объявления, не создаёт scraper/source adapter и не изменяет
existing domain contracts.

## Метод исследования и границы доказательства

Проверялись только открытые официальные страницы ЦИАН, опубликованная OpenAPI
schema и официальный текст закона. Не использовались поисковые snippets как
самостоятельное основание решения, неофициальные библиотеки, GitHub, блоги,
reverse-engineered endpoints и чужие пересказы.

В ходе TASK-028:

- не открывались страницы поисковой выдачи или отдельных объявлений;
- не выполнялись запросы к data methods `public-api.cian.ru`;
- не использовались login, cookies, session, browser automation, CAPTCHA,
  proxy или API-key;
- не собирались и не сохранялись listing records, контакты, изображения,
  свободный текст или account data;
- Swagger/OpenAPI читался только как техническая документация.

Отсутствие метода или лимита фиксируется как blocker, а не как подразумеваемое
разрешение. `robots.txt` не является лицензией или договором и рассматривается
только как дополнительный технический constraint.

## Реестр официальных источников

| Проверено | Документ / URL | Применимые части | Проверяемый вывод |
| --- | --- | --- | --- |
| 2026-09-02 | [Правила пользования сайтом ЦИАН](https://www.cian.ru/legal-documents/pravila_polzovaniya_sajtom_cian_0/) | 2.5; 7.1.2; 7.2.3; 7.2.5; 7.2.7 | Действующую редакцию нужно перепроверять; автоматизированные скрипты, доступ вне предоставленных интерфейсов и несогласованное извлечение материалов запрещены. |
| 2026-09-02 | [Лицензионное соглашение ЦИАН](https://www.cian.ru/legal-documents/licenzionnoe_soglashenie_0/) | 3.4–3.5; 4.1.3; 4.1.5; 4.2.1–4.2.4; 8.1.1–8.1.3 | Общее право извлечения не отменяет специальных правил об интерфейсе/автоматизации; использование вне прямо разрешённых способов и копирование базы требуют предварительного разрешения. |
| 2026-09-02 | [Условия использования сервиса API](https://www.cian.ru/legal-documents/usloviya_ispolzovaniya_servisa_api_0) | 1.1–1.2; 2.3–2.8; 3.1–3.6; 4.2–4.5 | Ключ запрашивается у ЦИАН, отдельный функционал может быть ограничен, а автоматизированный сбор через API требует предварительного разрешения. Ключ сам по себе недостаточен. |
| 2026-09-02 | [ЦИАН API docs](https://public-api.cian.ru/docs/latest) и [OpenAPI schema](https://public-api.cian.ru/swagger/latest) | описание авторизации/ограничений; полный список `paths`; tags `offers`, `importOrders`, `statistics` | Опубликованные методы `get-my-offers` и detail относятся к объявлениям агентства; XML относится к входящему импорту; public catalog search/read method не опубликован. Общая рекомендация — не более 10 запросов/с на метод равномерно, но method-specific значения могут отличаться. |
| 2026-09-02 | [robots.txt](https://www.cian.ru/robots.txt) | `User-agent: *`; allow/disallow rules, включая внутренний offers search path и query restrictions | Наличие `Allow` не делает внутренний path публичным API. Любой robots/terms/permission conflict останавливает pilot; undocumented path запрещён. |
| 2026-09-02 | [Федеральный закон № 152-ФЗ на официальном портале](https://ips.pravo.gov.ru/api/ips/legislation/document?baseid=None&hash=98490812b3409e2a8d78a11ca9010f434ea3d9250a11dbbdb78690cd5551bdd6) | статьи 3, 5 и 7 официальной консолидированной версии, доступной при проверке | Персональные данные толкуются широко; цель должна быть заранее определена, объём не должен быть избыточным, раскрытие требует законного основания. Контракт выбирает более узкий режим: не собирать PII вообще. |

Документы ЦИАН допускают односторонние изменения. Перед TASK-029 и перед
каждым будущим live attempt требуется новая проверка тех же canonical URLs,
даты/версии и diff применимых частей.

## Что установлено о способах доступа

### Опубликованный официальный API

Полный published `paths` audit OpenAPI schema на 2026-09-02 показал:

- `GET /v1/get-my-offers` и `GET /v2/get-my-offers` возвращают объявления
  агентства, включая собственные manual/XML-import publications;
- `GET /v1/get-my-offers-detail` возвращает детали объявлений агентства;
- `get-last-order-info`, `get-order` и `get-images-report` описывают отчёты о
  загрузке входящего XML-feed;
- единственный method с `search` в path — устаревшая статистика охвата
  собственного объявления, а не public catalog search;
- метода чтения публичной выдачи/карточек третьих лиц нет.

Следовательно, текущий официальный API не подходит заявленному поисковому
продукту. Использовать его для собственных объявлений означало бы сменить use
case, а не выполнить pilot.

### Партнёрский API или договорной исходящий feed

Это единственный потенциально допустимый route. Он становится разрешённым
только если письмо/договор от уполномоченного представителя ЦИАН однозначно
называет:

- внешнего получателя и поисковый read-only use case;
- публичные объявления третьих лиц как допустимый scope;
- официальный hostname, path/feed и способ авторизации;
- допустимые query dimensions, fields, attribution и downstream use;
- record/request limits, quota window, pagination и retry behavior;
- retention, deletion, incident/termination procedure;
- право хранить provider-supplied synthetic/redacted либо минимальный
  разрешённый sample для offline TASK-029.

Устное подтверждение, обычный account, тариф, API-key или успешный HTTP status
не заменяют это evidence.

### HTML, browser и внутренние endpoints

Запрещены независимо от удобства:

- HTML/search/card scraping;
- XHR/GraphQL/internal endpoint, найденный через DevTools, JavaScript или
  `robots.txt`;
- headless/interactive browser automation;
- cookie/session reuse, account impersonation, proxy rotation;
- CAPTCHA solving, fingerprint/anti-bot evasion;
- RSS/Atom/export path, если он не выдан как разрешённый feed для exact use
  case.

## Blocking conditions

До снятия **всех** пунктов ниже TASK-029 и live pilot не начинаются:

| ID | Blocker | Доказательство снятия |
| --- | --- | --- |
| `B1_PERMISSION` | Нет письменного разрешения на automated public-listings read для внешнего поиска | Сохранённое письмо/договор от уполномоченного ЦИАН с exact purpose/scope |
| `B2_ROUTE` | Нет documented public-listings endpoint/outbound feed | Официальная документация или договорная спецификация hostname/path/feed |
| `B3_USE_RIGHTS` | Не определены поля, transformation, offline reuse, attribution и downstream display | Письменный field/use/attribution schedule |
| `B4_LIMITS` | Нет method/feed-specific rate ceiling, quota window, pagination и retry rule | Документированная квота, действующая для выданного route/account |
| `B5_DATA_SHAPE` | Нельзя доказать исключение контактов, account IDs, text и images | Provider schema/sample и утверждённый allowlist полей |
| `B6_RETENTION` | Не согласованы temporary retention, deletion и sample reuse | Письменный срок/удаление плюс разрешённый synthetic/redacted sample |
| `B7_CURRENT_RULES` | Не выполнена повторная проверка terms/API schema/robots перед работой | Dated audit с URLs, версиями/hashes и отсутствием конфликта |

Если ответ ЦИАН неполон, молчалив, двусмыслен или ограничен собственными
объявлениями, blocker остаётся. Если ЦИАН отказывает, source decision для этого
use case становится `NO_GO`.

## Контракт будущего минимального live pilot

Этот раздел задаёт ceiling, но не разрешает запуск.

### Предварительно фиксированный запрос

До доступа создаётся immutable `PILOT-Q1` receipt с одним сочетанием:

- одна категория сделки;
- один тип объекта;
- одна административная территория в пределах разрешённого ЦИАН scope;
- один фиксированный набор room criteria;
- при необходимости один price interval;
- documented sort и один page/cursor position.

Точные значения утверждаются в будущей задаче до первого request и не
расширяются по результатам ответа. Нельзя обходить соседние территории,
категории, страницы или менять criteria для увеличения выборки.

### Traffic budget

- Ровно один authorized data request за весь pilot run.
- Не более 20 returned/accepted records; server request обязан использовать
  documented page/limit до 20. Если bounded request невозможен — stop до
  уточнения у ЦИАН.
- Никакой второй страницы, cursor continuation, batch expansion или follow-up
  lookup карточек.
- Никакого parallelism, background scheduler, cron, queue или worker pool.
- Никаких automatic retries. Любой non-success response завершает run.
- Локальный one-request budget применяется только **ниже** полученного
  documented provider limit; он не подменяет `B4_LIMITS`.

### Allowlist необходимых полей

Первый pilot принимает только структурированные значения:

1. source code `cian`;
2. publication identifier;
3. canonical public URL, если договор явно разрешает её хранение;
4. source publication/update time, если оно документировано;
5. acquisition timestamp и route/schema version для provenance;
6. object kind и deal kind;
7. region/locality/district без contact/account data;
8. price amount и currency;
9. total area;
10. room count.

Floor, building attributes, coordinates и полный адрес не входят в первый
allowlist. Их отсутствие не разрешает дополнительный запрос. Missing value
остаётся missing и не выводится из текста/изображения.

### Явно запрещённые данные и выводы

- ФИО, телефон, email, chat/message content;
- seller/agent/account/user identifiers и profile URLs;
- документы, платежные и иные account metadata;
- description, notes и любой свободный текст;
- image bytes, thumbnails, image URLs и attachments;
- device/IP/cookie/session identifiers;
- вывод о нахождении владельца за границей, национальности, гражданстве,
  семье, финансовом положении или иной чувствительной характеристике;
- OCR, NLP, AI enrichment, person/entity resolution и contact discovery.

Свободный текст полностью исключён из первого pilot. Его нельзя добавить как
«полезный» без нового ADR, доказанной необходимости, отдельного разрешения и
redaction design.

Если запрещённое поле неожиданно появляется в response, parser не должен его
логировать или сохранять: run немедленно останавливается, transient body
удаляется, а audit содержит только safe stop code и факт удаления.

## Stop conditions

Любое событие ниже означает немедленную остановку без обхода и повторов:

- отсутствует хотя бы одно доказательство `B1`–`B7`;
- CAPTCHA, anti-bot challenge или требование browser/session/cookie;
- HTTP `401`, `403` или `429`;
- robots/terms/permission conflict;
- endpoint отсутствует в договорной/официальной документации;
- redirect на иной hostname/path, не включённый в разрешение;
- schema/version отличается от approved snapshot или поле меняет смысл/type;
- response нельзя ограничить 20 records либо появляются pagination links после
  первой bounded page;
- неожиданные PII, contact, account, text или image fields;
- запрос требует обхода rate limit, защиты, CAPTCHA, geo restriction или
  технического ограничения;
- ключ/секрет оказался в URL, log, exception, fixture или repository;
- provider изменил/отозвал разрешение, terms, quota либо interface;
- любой operational outcome не доказывает полный безопасный success.

Неизвестность не создаёт unavailable observation и не запускает targeted
listing check. Pilot не обращается повторно к конкретной публикации.

## Retention и evidence

### Что можно сохранить

Без listing data:

- canonical URLs официальных документов, title, checked-at и применимые
  clause/section identifiers;
- hash/version approved OpenAPI/partner schema и permission reference;
- approved `PILOT-Q1` criteria receipt, allowlist, caps и route identity;
- request start/end, HTTP status class, accepted/rejected counts и safe stop
  code без raw body и query secret;
- adapter/contract version и deletion receipt;
- доказательство attribution и соблюдения provider quota.

Секрет, полный permission message с персональными контактами и договорные
вложения хранятся вне Git в access-controlled location; в repository
сохраняется только safe reference/status.

### Listing sample

Предпочтителен provider-supplied synthetic/redacted sample без реального
объявления. Минимальный реальный sample можно временно сохранить только если
письменное разрешение явно охватывает offline development/reproducibility:

- только allowlisted structured fields;
- максимум 20 records, фактически для TASK-029 предпочтительно 1 record;
- encrypted/access-controlled workspace, не repository, fixtures, golden,
  logs, backups или chat;
- срок — до завершения TASK-029, но не более 7 календарных дней с момента
  получения; более короткий срок ЦИАН имеет приоритет;
- удаление raw/minimal real sample и всех transient copies с safe deletion
  receipt; committed test fixture после TASK-029 может быть только полностью
  synthetic и не должен позволять восстановить real listing.

Raw HTTP capture по умолчанию запрещён. Он потребует отдельного письменного
разрешения, нового retention/security design и отдельной задачи; TASK-028 его
не разрешает.

## Дешёвый режим

Разрешённый будущий pilot остаётся детерминированным и дешёвым:

- без ИИ, OCR, NLP и внешних enrichment services;
- без browser automation;
- без параллельного обхода;
- без scheduler/background run;
- без retries и backoff loop;
- без изображений и свободного текста;
- одна request, одна bounded response, локальная strict validation и stop.

## Audit checklist будущей задачи

До request:

- все `B1`–`B7` отмечены exact evidence references;
- route, method, query, page size, allowlist и deletion deadline frozen;
- provider limit численно/документально известен, local budget строже;
- terms/license/API/robots rechecked в день запуска;
- secret redaction и no-body logging проверены offline.

После request:

- записаны только safe status/count/timing/schema coordinates;
- доказано `requests=1`, `records<=20`, `pages=1`, `retries=0`, `parallel=0`;
- запрещённые поля/данные отсутствуют либо сработал stop-and-delete;
- сохранён allowed provenance и установлен deletion deadline;
- raw capture, contacts, text, images, account identifiers и secrets
  отсутствуют во workspace/repository/logs;
- deletion receipt закрывает sample не позднее установленного срока.

## Следующий шаг

1. Вне этой задачи пользователь при желании отдельно инициирует обращение к
   ЦИАН за evidence `B1`–`B6`; TASK-028 ничего не отправляет.
2. После получения полного ответа выполняется read-only review `B7` и
   подтверждается, что статус остаётся `CONDITIONAL_GO` с выполненными gates,
   а не `NO_GO`.
3. Только тогда отдельная TASK-029 реализует offline source adapter на
   provider-supplied synthetic/redacted или явно разрешённом сохранённом
   sample. Никакого live access в TASK-029.
4. Controlled live pilot проектируется ещё более поздней отдельной задачей и
   не наследует разрешение автоматически: документы и evidence проверяются
   заново.
