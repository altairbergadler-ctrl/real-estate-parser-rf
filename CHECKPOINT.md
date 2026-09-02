# Текущая контрольная точка

## Завершённая задача

TASK-020 — neutral reviewed control set и pure duplicate-policy quality
metrics. Immutable one-policy population атомарно связывает unique canonical
pairs, exact assessment/not-assessed results и independently supplied
pair-bound labels. Pure evaluation сохраняет categorical counts, exact
coverage и population review load, а precision/recall выдаёт только при
достаточных labels с явными denominators; human label не становится physical
property или безусловной истиной.

## Состояние основной ветки

- TASK-001…TASK-020 слиты в `main` отдельными merge-коммитами.
- Короткоживущая ветка `task/020-reviewed-control-metrics` сохраняет исходный
  атомарный implementation commit после безопасной интеграции.
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
- Нейтральные frozen/slots `ComparisonPolicyVersion`,
  `AvailabilityRuleVersion`, `ObservationKey`, available/unavailable
  observations, два достаточных evidence-типа и строго возрастающая
  `PublicationObservationHistory` одной `PublicationRef` и policy version.
- Immutable `FieldSnapshot`, взаимоисключающие `FieldDeltaKind`, availability
  transitions, `AvailabilityEvidenceDelta`, `ChangeSet`, стабильные
  `ObservationConflict` и атомарные append success/failure без partial
  результатов.
- Явная `PUBLICATION_CHANGE_POLICY_V1` с порядком `source_url`,
  `location_text`, `price_amount`, `currency`, `total_area`, `rooms` и
  канонической проекцией `Present`/`Missing`/`Unsupported(reason_code)`.
- Чистая `compare_consecutive_observations`: available pair сравнивает ровно
  шесть полей с приоритетом substantive, raw-only и provenance refresh;
  timestamp-only даёт пустой `ChangeSet`; availability transitions не
  выполняют field comparison; repeated unavailable сравнивает только evidence.
- Чистая `append_observation`: exact replay любого принятого key возвращает
  исходную history, неизвестный новый key принимается только после tail, а
  reference/timestamp/order/policy conflicts атомарны. Первый append не создаёт
  `ChangeSet`, остальные сравниваются только с непосредственным predecessor.
- Прямые полностью вымышленные exhaustive unit-тесты проверяют конструкторные
  инварианты, все шесть полей, полную матрицу outcome transitions, reason/raw/
  provenance/timestamp semantics, append/replay/conflicts, unavailable,
  reappearance, immutability и отсутствие partial failure state.
- Отдельный frozen/slots `PublicationObservationHistories` принимает только
  tuple histories, обеспечивает не более одного stream на `PublicationRef` и
  канонически хранит их по source/publication id независимо от порядка входа.
- Чистая `append_observation_batch` принимает непустой tuple candidates и
  policy, группирует keys по reference, сворачивает exact duplicates и создаёт
  отсутствующую history с версией переданной policy без repository lookup.
- Каждый уникальный допустимый key обрабатывается готовой
  `append_observation`; success содержит полный набор histories и канонические
  `ObservationBatchItemOutcome` с точными `APPENDED`/`REPLAYED` и `ChangeSet`.
- Batch failure содержит только непустой уникальный tuple всех доказуемых
  conflicts в глобальном порядке reference, наличия/времени subject key,
  category и code; partial histories, dispositions и changes отсутствуют.
- Прямые fully fictional batch unit-тесты доказывают multi-stream creation,
  update/untouched history, tail/non-tail replay, duplicate collapsing,
  same-key content/evidence conflicts, out-of-order нескольких streams, policy
  mismatch, atomic failure, permutation invariance, повторную идемпотентность и
  сохранение availability/reappearance semantics TASK-016.
- ADR 0006: duplicate relation существует только как неупорядоченная pairwise
  assessment двух разных `PublicationRef`; одинаковая reference запрещена, а
  same-source и cross-source pairs разрешены симметрично.
- Structural assessment identity включает canonical pair, точные
  `ObservationKey` обеих available сторон и `publication-duplicate-policy@1`.
  Exact replay является no-op; equal identity с другим содержимым — conflict.
- Новое observation или версия policy создаёт новую assessment. Старая
  сохраняет историческое объяснение, но stale относительно явного current
  context; supersession задаётся отдельной immutable связью и не выводится из
  времени молча.
- Evidence item содержит stable rule id/version, polarity, policy-defined
  categorical strength, поля, полные left/right canonical snapshots,
  provenance обеих publications и safe reason code. Supporting и contradicting
  evidence никогда не стирают друг друга.
- `Missing`/`Unsupported` дают отдельный `RuleNonComparison`; unavailable side,
  batch omission и operational failure assessment не создают. Различие
  свободного location text, цены или времени не является отрицательным
  duplicate evidence; price match остаётся auxiliary и само недостаточно.
- Первая duplicate policy сравнивает в стабильном порядке `total_area`,
  `rooms`, exact `location_text` и полную exact price/currency pair. Candidate
  gate требует exact area и exact rooms либо location; material contradiction
  при выполненном gate даёт отдельный conflicting manual-review outcome.
- Aggregate имеет только `CANDIDATE_REQUIRES_MANUAL_REVIEW`,
  `CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW` и
  `INSUFFICIENT_EVIDENCE_NO_CANDIDATE`; confirmed automatic outcome отсутствует.
- Immutable manual review имеет supplied reviewed time, reviewer/reference
  codes, outcome confirm/reject/inconclusive, rationale/evidence references и
  строгую revision/supersedes semantics. Она не меняет automatic evidence,
  source histories или видимость публикаций.
- Pairwise relation явно нетранзитивна: `A~B` и `B~C` не создают `A~C`.
  Physical property, connected components, automatic merge/collapse и
  canonical winner запрещены текущим контрактом.
- Полностью вымышленные scenarios спецификации покрывают symmetry, replay,
  stale inputs, present provenance, missing/unsupported, mixed evidence,
  insufficient input, same/cross-source, unavailable, все review outcomes,
  supersession conflicts и non-transitivity.
- Нейтральные frozen/slots `PublicationPair`, `DuplicateAssessmentIdentity`,
  `DuplicateFieldSnapshot`, evidence/non-comparison, policy, result/conflict и
  manual-review types с tuple-only collections и safe opaque codes.
- Immutable `PUBLICATION_DUPLICATE_POLICY_V1` с точным порядком rules
  `total_area`, `rooms`, exact `location_text`, `price_amount + currency` и
  categorical strengths без score/probability/tolerance.
- Чистая полностью симметричная `assess_publication_pair`: same reference даёт
  stable conflict, unavailable side — `PairNotAssessed`, две available sides —
  complete assessment с exact decision table ADR 0006.
- Полные canonical field snapshots повторно используют outcome/provenance
  TASK-016; `Missing` не получает raw, `Unsupported` сохраняет reason и raw,
  neutral mismatch не становится contradicting evidence.
- Pure current/stale check, explicit `AssessmentSupersession` и
  `create_manual_review` с supplied identity/time, exact finding references,
  strict revision/supersedes/replay semantics и atomic failures.
- 93 fully fictional прямых unit-теста покрывают rules, symmetry, decision
  table, unavailable, identity/current/supersession, manual reviews,
  immutability, запрещённую merge/cluster поверхность и отсутствие I/O.
- ADR 0007 и согласованная design-спецификация denominator-specific label
  sufficiency для reviewed duplicate-policy control population.
- Узкий independently supplied `DuplicateControlLabel`, atomic
  `DuplicatePolicyControlCase` и непустой one-policy
  `DuplicatePolicyControlSet` с unique pairs и canonical order.
- Typed control contract errors отклоняют unsupported/failure result и
  pair/label/policy conflicts без partial metrics; `PairNotAssessed` получает
  explicit policy binding в case.
- Pure `evaluate_duplicate_policy_quality` возвращает counts каждого automatic
  outcome, not-assessed/assessed/review-required totals, exact assessment
  coverage и population review load.
- Precision и recall имеют только `ExactRatio` либо typed unavailable reason;
  precision требует conclusive review-required denominator, recall — всей
  population и учитывает confirmed insufficient/not-assessed false negatives.
- 24 fully fictional unit-теста покрывают mixed/all assessed/all not-assessed,
  same/cross-source, permutations, bindings/conflicts, immutability, exact
  ratios, label sufficiency/independence и отсутствие I/O/merge/cluster API.

## Что намеренно не реализовано

- Запись output на диск.
- Постоянное хранилище, repository adapter, expected revision implementation,
  batch pair generation, blocking/indexing и сохранение duplicate
  assessments/reviews/control sets.
- Физический объект недвижимости, merge/clustering, база данных, API, HTTP,
  HTML и реальные площадки.
- Нестандартные сигналы, ИИ, уведомления, UI, OpenClaw и Telegram.
- Docker, CI, развёртывание, удалённый репозиторий и динамический загрузчик
  плагинов.

## Рекомендуемая следующая задача

TASK-021 — принять design-only контракт детерминированного формирования ограниченного набора duplicate candidate pairs из available observations с явными blocking keys и измеримым риском пропуска, без реализации, quadratic all-pairs scan, storage, clustering, JSON, CLI или real data

## Открытые архитектурные вопросы

- Понадобится ли когда-либо сущность физического объекта после измерения
  качества independent pair assessments, и какие доказательства разрешат
  отдельный пересмотр ADR 0006?
- Какое постоянное хранение потребуется и какие измеренные требования определят
  его выбор?
- Понадобится ли отдельный backfill/recompute workflow для доказанных
  out-of-order наблюдений, и как он будет версионировать пересчитанные changes?
- Какие правила законного и бережного получения данных обязательны для первого
  реального источника?
- Когда составному нормализованному значению понадобится происхождение из
  нескольких исходных полей?
- Какие blocking keys и coverage evidence позволят ограничить candidate pairs
  без скрытого quadratic scan и измерить риск пропуска?

Ответы не должны приниматься молча: существенные решения оформляются в
`docs/decisions/` в рамках назначенных задач.
