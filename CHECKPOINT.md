# Текущая контрольная точка

## Завершённая задача

TASK-015 — документальная модель повторных наблюдений и изменений одной source
publication. ADR 0005 и отдельная design-спецификация принимают identity и
порядок observation stream, exact replay и конфликты, версионированный
`ChangeSet`, доказательную недоступность и reappearance без Python-реализации и
без выбора хранилища.

## Состояние основной ветки

- TASK-001…TASK-014 слиты в `main` отдельными merge-коммитами.
- TASK-015 завершена в `task/015-observation-change-model`, готова к отдельному
  review/merge и ещё не слита в `main`.
- Удалённый репозиторий не настроен и не требуется в текущем объёме.

Текущий SHA, активную ветку, факт интеграции и чистоту дерева следует подтверждать
через Git, поскольку документ не дублирует изменяемые идентификаторы истории.

## Что уже существует

- Локальный Git-репозиторий, проектные правила и переносимые документы состояния.
- CPython `>=3.14,<3.15`, `.python-version` для 3.14.7, `uv`, зафиксированный
  `uv.lock`, устанавливаемый `src`-пакет и единая команда `uv run quality`.
- Pydantic 2.x только на недоверенной внешней границе; pytest, Ruff и strict
  mypy; полностью офлайн fixture catalog integrity.
- Публичная строгая граница `load_fixture_source_batch(Path)` для одного
  локального UTF-8 документа `fixture-source-batch@1` со стабильными
  `INPUT_SYNTAX`/`INPUT_SCHEMA` issues.
- Нейтральные immutable-типы структурных locations, provided/missing source
  fields, `ValidatedSourceBatch`, `ContractIssue` и атомарных результатов.
- Чистая операция `adapt_fixture_source_batch(ValidatedSourceBatch)`, которая
  назначает `fixture_portal`, проверяет publication id/URL и возвращает полный
  `SourceBatch` либо упорядоченные `SOURCE_ADAPTER` issues.
- Нейтральные `SourceId`, `PublicationId`, `PublicationRef`, `RawField`,
  `MissingField`, `SourcePublicationSnapshot` и `SourceBatch`.
- Канонические immutable-типы `SourceUrl`, `ObservedAt`, `LocationText`,
  `MoneyAmount`, `Currency`, `Area`, `RoomCount` и версии правил.
- `TracedValue`, отдельные `ValueProvenance`, `MissingProvenance`,
  `UnsupportedProvenance`, закрытые `Present`/`Missing`/`Unsupported` и полный
  `NormalizedListing`.
- Явный неизменяемый `FIXTURE_NORMALIZATION_RULES_V1` с восемью утверждёнными
  версиями правил.
- Чистая публичная операция `normalize_fixture_snapshot(snapshot, rules)` для
  одного snapshot: строгий RFC 3339 → UTC, Unicode whitespace, точные деньги,
  валюта, площадь и комнаты, полное происхождение и атомарный failure.
- Frozen/slots `CollectionSnapshot`, `CollectionBuildSuccess`/
  `CollectionBuildFailure` и чистая операция
  `build_fixture_collection(SourceBatch, rules)`.
- Пакетная операция обходит все snapshots, глобально сортирует
  independently provable `NORMALIZATION` issues и только после полного
  успеха проверяет точную уникальность `PublicationRef`.
- Коллекция хранит полный tuple `NormalizedListing` в порядке входа;
  каждое повторное вхождение после первого даёт устойчивый
  `COLLECTION_CONFLICT/duplicate_publication_ref`.
- Канонические frozen/slots `Money` и `SearchCriteria` с тремя необязательными
  ограничениями; `allowed_rooms` хранится как непустой
  `frozenset[RoomCount]` и не сохраняет входной порядок.
- Публичная граница `load_search_criteria(Path)` для одного UTF-8
  `search-criteria@1`: strict Pydantic structure/types, точные amount/area/rooms
  правила, атомарный immutable success/failure и упорядоченные
  `INPUT_SYNTAX`/`INPUT_SCHEMA` issues без пути и входных значений.
- Frozen/slots `SearchMatch` и `SearchResult`, где совпадение ссылается на
  исходный `NormalizedListing`, а результат хранит использованный immutable
  `SearchCriteria` и tuple совпадений.
- Чистая публичная операция `search_collection(CollectionSnapshot,
  SearchCriteria)`, которая конъюнктивно применяет три стандартных критерия,
  считает `Missing`/`Unsupported` обычным несовпадением только для заданного
  поля и возвращает полный канонически отсортированный результат, включая
  успешный пустой tuple.
- Минимальное frozen/slots document tree `search-result@1`: отдельные
  `PublicationRefDocument`, criteria/match/root, mandatory traced value,
  `PresentDocument`, `MissingDocument`, `UnsupportedDocument` и два структурно
  разных provenance-типа для provided и missing значений.
- Чистая публичная операция `map_search_result(SearchResult)`, которая точно
  переводит wrapper-типы в строки/integer, форматирует площадь в м² с двумя
  знаками без float, сортирует только criteria rooms и сохраняет уже заданный
  tuple matches без повторного поиска или сортировки.
- Отдельный модуль output boundary с приватными frozen strict
  Pydantic-моделями точной формы `search-result@1`, `extra="forbid"` и
  discriminated `present`/`missing`/`unsupported`.
- Публичная операция `serialize_search_result_document(document)` и
  frozen/slots `SearchResultSerializationSuccess`/`Failure`: либо полные
  канонические JSON bytes, либо ровно одна
  `OUTPUT_CONTRACT/invalid_result_document/$` issue без частичных bytes.
- Каноническая serialization с UTF-8 без BOM, sorted compact keys,
  standard escaping, `allow_nan=False`, опущенными absent criteria, без
  `null` и с ровно одним завершающим LF; matches не сортируются.
- Публичный application orchestrator
  `run_local_search(listings_path, criteria_path)` с минимальными frozen/slots
  `LocalSearchSuccess(json_bytes)` и `LocalSearchFailure(issues)`.
- Orchestrator независимо загружает listings и criteria, объединяет content
  issues глобальным ключом listings-before-criteria и прекращает поток до
  адаптации при любой issue; downstream failures также не выдают частичную
  коллекцию или result bytes.
- File access и UTF-8 failures остаются role-aware operational exception, а не
  `INPUT_*`; CLI сообщает только `listings`/`criteria` и безопасную общую
  причину.
- Console script `real-estate-parser` и module entry point
  `python -m real_estate_parser` с единственным subcommand `search` и
  обязательными `--listings`/`--criteria`.
- CLI success пишет готовые canonical bytes через binary stdout без повторной
  serialization; contract failures дают exit `1` и только
  `CATEGORY/CODE/JSON_PATH` в stderr, usage/operational failures — exit `2`.
- Прямые unit-тесты чистых границ, OUT-001, strict output validation,
  детерминизма и immutable result-типов; application composition и subprocess
  CLI E2E байтово совпадают со всеми тремя existing search golden, а
  partial-area сохраняет семантику `currency-004`.
- Негативные application/CLI E2E покрывают SYN-001, MULTI-001, NRM-006,
  COL-001, отдельную criteria issue, глобальный порядок двух независимо
  невалидных документов, usage, missing/non-UTF-8 input и повторный запуск.
- Проект первого локального среза, точные внешние документы, негативная матрица,
  byte-exact golden-файлы и правила детерминизма TASK-002…TASK-004.
- ADR 0005: один observation stream относится строго к одной `PublicationRef`,
  а `ObservationKey` структурно состоит из reference и канонического
  `ObservedAt`; physical property и cross-source dedup не входят в identity.
- Спецификация immutable available/unavailable observations, строго
  возрастающей history, exact replay, equal-timestamp conflict, запрета нового
  out-of-order key и атомарной обработки набора без partial history.
- Версионированная `publication-change-policy@1` со стабильным порядком
  `source_url`, `location_text`, `price_amount`, `currency`, `total_area`,
  `rooms`; canonical change, raw-only change, provenance refresh и успешный
  пустой `ChangeSet` различаются явно.
- Полная таблица `Present`/`Missing`/`Unsupported`, включая reason code,
  canonical before/after и оба provenance; `PublicationRef` и `ObservedAt` не
  объявляются изменениями listing.
- Доказательная модель unavailable только из direct source state либо
  conclusive targeted check конкретной publication по версии правила.
  Отсутствие в batch, timeout, блокировка, network/source failure и incomplete
  scan оставляют исход неизвестным и не меняют history.
- Availability transitions `ConfirmedUnavailable` и `Reappeared`, различие
  unavailable от недоказанных deleted/expired claims, минимальный pure API,
  стабильные conflict codes и consumer contract будущего atomic repository
  port без выбора технологии.

## Что намеренно не реализовано

- Запись output на диск.
- Python-типы и операции нескольких наблюдений, постоянное хранилище,
  repository adapter, фактическая история изменений и дедупликация.
- Физический объект недвижимости, база данных, API, HTTP, HTML и реальные
  площадки.
- Нестандартные сигналы, ИИ, уведомления, UI, OpenClaw и Telegram.
- Docker, CI, развёртывание, удалённый репозиторий и динамический загрузчик
  плагинов.

## Рекомендуемая следующая задача

TASK-016 — реализовать neutral frozen/slots observation/change types и чистую
детерминированную операцию сравнения/добавления одного observation по ADR 0005,
без хранилища, JSON, CLI и изменения первого среза. Это ровно следующий малый
шаг; он не начат.

## Открытые архитектурные вопросы

- Когда и на каких доказательствах вводить сущность или группу физического
  объекта для дедупликации?
- Какое постоянное хранение потребуется и какие измеренные требования определят
  его выбор?
- Понадобится ли отдельный backfill/recompute workflow для доказанных
  out-of-order наблюдений, и как он будет версионировать пересчитанные changes?
- Какие правила законного и бережного получения данных обязательны для первого
  реального источника?
- Когда составному нормализованному значению понадобится происхождение из
  нескольких исходных полей?
- Как измерять качество дедупликации и доказательных сигналов?

Ответы не должны приниматься молча: существенные решения оформляются в
`docs/decisions/` в рамках назначенных задач.
