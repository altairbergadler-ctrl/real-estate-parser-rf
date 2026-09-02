# Текущая контрольная точка

## Завершённая задача

TASK-028 — design/research контракт ограниченного read-only пилота ЦИАН.
Принят [ADR 0011](docs/decisions/0011-cian-read-only-pilot-contract.md) со
статусом `CONDITIONAL_GO`: controlled live pilot сейчас запрещён. Published
API относится к объявлениям самого агентства и входящему XML-импорту, а не к
public catalog search. Единственный потенциальный route — письменное
разрешение ЦИАН на exact public-listings use case и официальный documented
API/outbound feed с method-specific quota, PII-safe fields и retention terms.

## Состояние основной ветки

- TASK-001…TASK-028 слиты в `main` отдельными merge-коммитами.
- Короткоживущая ветка `task/023-duplicate-blocking-coverage` сохраняет
  исходный атомарный implementation commit после безопасной интеграции.
- Короткоживущая ветка `task/024-duplicate-assessment-batch-design` сохраняет
  исходный атомарный documentation commit после безопасной интеграции.
- Короткоживущая ветка `task/025-duplicate-assessment-batch-core` сохраняет
  исходный атомарный implementation commit после безопасной интеграции.
- Короткоживущая ветка `task/026-persistence-replay-boundary-design` сохраняет
  исходный атомарный documentation commit после безопасной интеграции.
- Короткоживущая ветка `task/027-persistence-ports-in-memory` сохраняет
  исходный атомарный implementation commit после безопасной интеграции.
- Короткоживущая ветка `task/028-cian-read-only-pilot-contract` сохраняет
  исходный атомарный documentation commit после безопасной интеграции.
- Приватный удалённый репозиторий GitHub настроен:
  `altairbergadler-ctrl/real-estate-parser-rf`. `main`, завершённые task-ветки
  и теги публикуются как переносимый резерв истории проекта.

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
- ADR 0008 и design-спецификация отдельной
  `publication-duplicate-candidate-policy@1` с двумя exact rules
  `total_area + rooms` и `total_area + location_text`, совпадающими с
  candidate gate ADR 0006.
- Непустой canonical current available input contract с one-observation per
  `PublicationRef`, exact keys и atomic failures для unavailable, duplicate
  reference и same-key conflicting content.
- Typed exact blocking keys без float/hash/locale identity, explicit
  Missing/Unsupported non-participations и unique candidates с canonical pair,
  exact left/right observation keys и полным ordered tuple materialized
  matches.
- Caller-supplied positive bucket pair limit, exact prospective
  `n * (n - 1) / 2`, whole-bucket `OversizedBucket` и запрет partial first-N.
  Pair attempts ограничены `2NL`; global quadratic scan/fallback отсутствует.
- Design exact blocking coverage для fully fictional reviewed control set:
  eligible confirmed denominator, no-shared/oversized misses, отдельные
  PairNotAssessed/outside/stale counts и typed unavailable reasons для
  inconclusive labels/нулевого denominator.
- Neutral frozen/slots candidate-generation types: отдельные safe policy/rule/
  reason codes, exact `AreaRoomsBlockingKey` и
  `AreaLocationTextBlockingKey`, component/rule non-participation,
  `BucketPairLimit`, whole `OversizedBucket`, candidate/generation identities,
  full result и atomic success/failure conflicts.
- Immutable `PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1` с exact version
  `publication-duplicate-candidate-policy@1` и ровно двумя rules ADR 0008 в
  фиксированном порядке.
- Pure `generate_duplicate_candidates` атомарно проверяет tuple current
  observations, availability, full-key content и one-reference invariant,
  затем канонизирует input и создаёт максимум две exact memberships на
  observation.
- Каждый bucket сначала получает integer `n * (n - 1) // 2`; count выше
  caller limit целиком создаёт oversized outcome и zero pairs, count на
  границе полностью materializes. Multi-pass union сохраняет только
  materialized blocking matches и допускает successful empty candidates.
- 49 fully fictional direct tests покрывают policy/contracts, atomic conflicts,
  both/single passes, same/cross-source, Missing/Unsupported, exact boundary,
  no-first-N oversized skip, alternate route, permutation/new-key identity,
  immutability, exact bound и отсутствие assessment/I/O/storage surface.
- Neutral frozen/slots `BlockingCoverageUnavailable`,
  `DuplicateCandidateBlockingCoverage`, structural coverage conflict subject,
  canonical atomic success/failure и ровно две unavailable reasons ADR 0008.
- Pure `evaluate_duplicate_candidate_blocking_coverage` классифицирует
  conclusively confirmed cases в строгом порядке PairNotAssessed, outside
  generation input, stale/mismatched exact keys и eligible, сохраняя assessment
  policy, candidate policy и полную generation identity раздельно.
- Eligible exact-key case считается covered по exact candidate identity,
  no-shared-key miss либо whole-oversized-bucket miss. Общий non-oversized key
  без candidate даёт только
  `DUPLICATE_CANDIDATE_COVERAGE_CONFLICT/generation_result_inconsistent`.
- 18 fully fictional direct tests покрывают exact `2/4`, оба routes,
  oversized alternate route, same/cross-source, eligibility order, label и
  PairNotAssessed counts, unavailable precedence, exact ratio, bindings,
  invariants, canonical conflicts, immutability и запрещённую surface.
- ADR 0009 и design-спецификация отдельной pure atomic composition от exact
  `DuplicateCandidateGenerationResult` и полного caller-supplied current
  `AvailableObservation` context к existing `assess_publication_pair`.
- Batch identity сохраняет exact generation identity и отдельную explicit
  `DuplicatePolicyVersion`; full supported candidate policy v1 и assessment
  policy v1 проверяются независимо и не выводятся друг из друга.
- Current tuple-only non-empty available context канонизируется и exact
  связывается с generation keys; missing generation key, extra current key и
  new key той же reference имеют разные structural mismatch kinds.
- Все preflight conflicts собираются до первого call и гарантируют zero calls;
  valid empty candidates дают success с empty outcomes, а каждый non-empty
  candidate вызывает single-pair assessment ровно один раз в canonical order.
- Unexpected PairNotAssessed, downstream failure и malformed success дают
  typed atomic batch conflicts. Pure pass продолжается для полного conflict
  set, но failure никогда не содержит provisional successful item outcomes.
- Success сохраняет full generation result binding, assessment policy и exact
  ordered candidate/item assessments. Replay и equal-identity/different-
  content conflicts не выбирают winner; blocking matches не становятся
  evidence.
- Composition bound равен `O(N + C)` lookup/binding плюс стоимость ровно `C`
  pair assessments; regeneration, all-pairs fallback, physical property,
  merge, cluster и transitive closure запрещены.
- Neutral frozen/slots `DuplicateCandidateAssessmentBatchInput`, двух-policy
  configuration, batch/item identities, exact item outcome, complete batch,
  atomic success/failure и typed conflict subjects ADR 0009.
- Pure `assess_duplicate_candidate_batch` принимает full generation result,
  raw current tuple и explicit assessment policy; поддерживает только exact
  full candidate policy v1 и assessment policy v1.
- Phase-gated preflight различает unavailable/unsupported, same-key unequal
  content, duplicate reference, missing generation key, extra current key и
  same-reference current-key mismatch, затем defensive проверяет candidate
  policy/pair/keys/uniqueness/order до первого assessment call.
- Valid empty candidates дают complete success и zero calls. Каждый non-empty
  supplied candidate получает ровно один existing pair call в canonical order
  с exact full current sides; blocking matches не становятся evidence.
- PairNotAssessed, pair failure, malformed success и unsupported downstream
  result преобразуются в typed batch conflicts. Pure pass продолжается до
  конца, но failure не содержит provisional items; success сохраняет full
  generation result, full assessment policy и ordered exact assessments.
- 33 fully fictional direct tests покрывают constructors, all preflight
  conflicts, exact binding, call counts/order, empty/multiple/same/cross-source,
  permutations, downstream full pass, replay/immutability, non-transitivity и
  forbidden public surface.
- Финальный TASK-025 quality gate успешен: targeted `33 passed`, Ruff,
  strict mypy (`41 source files`), основной pytest `603 passed`, fixture catalog
  `44 passed`, frozen sync/lock, `git diff --check`, 47 relative Markdown links
  и changed-path/public-surface audits.
- ADR 0010 однозначно принимает hybrid persistence model после сравнения с
  history-only recompute и all-records-authoritative вариантами по
  доказательности, воспроизводимости, стоимости, модульности, идемпотентности и
  эксплуатации.
- Authoritative publication state — immutable available/unavailable
  observations; supplied manual-review revisions и control labels authoritative
  только как human assertions в exact assessment/control context.
- `ChangeSet`, generation results, pair/batch assessments, explicit
  supersessions и committed control inputs остаются derived/version-bound, но
  сохраняются immutable как audit, если участвовали в side effect. Quality
  metrics, blocking coverage, current/stale, heads и indexes rebuildable.
- `SourcePublicationSnapshot`/boundary batches не становятся автоматически
  authoritative этой границы. Optional raw capture требует отдельного
  legal/audit consumer contract.
- Пять consumer-owned contracts разделяют observation histories, candidate
  generation artifacts, assessment batch artifacts, manual-review revisions и
  quality audit inputs; общий `Repository[T]` и storage-owned domain API
  запрещены.
- Common opaque `PersistenceRevision` относится только к exact stream/artifact
  slot/head. Explicit `ExpectAbsent | ExpectExact` исключает unconditional
  write и hidden last-write-wins; token не является временем или identity.
- Commit protocol сначала проверяет structural identity/full content: exact
  equal даёт `REPLAYED` без новой revision даже после lost response, equal
  identity/different content даёт conflict, и только новая identity проходит
  expected-revision check.
- Multi-history append сохраняет все affected streams и immutable receipt одной
  unit. Generation сохраняется только complete result; assessment batch
  атомарно утверждает/сохраняет exact embedded generation и все pair outcomes.
  Manual review атомарно сохраняет revision, supersedes edge и head.
- `outcome_unknown` требует exact identity read/reconciliation. Observable
  recovery state — вся unit либо ничего; stale revision ведёт к reload и
  повторному pure computation, не к замене token без recompute.
- Same-policy recompute обязан быть structurally equal. Новые observation keys,
  limit или policy создают новую identity; старые audit records сохраняются,
  supersession только explicit.
- Derived historical backfill разрешён только как materialization отсутствующей
  exact identity. Normal observation out-of-order/correction bypass отсутствует
  и требует нового ADR.
- Retention запрещает routine overwrite/delete observations, reviews,
  committed audit artifacts, receipts, supersession links и lineage. Только
  rebuildable projections можно безопасно пересоздавать.
- Design задаёт stable port-specific conflict categories/subjects и canonical
  order, minimal exact reads будущего executor и fully fictional matrix first
  write/retry/stale/concurrency/conflict/recompute/interruption/no-partial cases.
- Финальный TASK-026 quality gate успешен: Ruff format-check (`95 files`),
  Ruff lint, strict mypy (`41 source files`), основной pytest (`603 passed`),
  fixture catalog `44 passed`, frozen sync/lock, `git diff --check`, 59
  relative Markdown links и changed-path audit.
- Common frozen/slots persistence primitives: adapter-issued opaque
  `PersistenceRevision`, explicit `ExpectAbsent | ExpectExact`,
  `CommitDisposition`, typed operational failures и канонические
  port-specific structural conflicts.
- Пять публичных consumer-owned Protocol ports без generic repository:
  histories/observations, generation artifacts, assessment batch/pair/link,
  manual-review chain/head и quality audit inputs.
- Deterministic `InMemoryPublicationPersistence`, который реализует все
  пять ports, выдаёт revisions без clock/UUID/random/hash/domain
  timestamp и сохраняет их при replay.
- Exact reads не выбирают newest across policies и не подменяют
  absence пустым domain object.
- Observation commit атомарно фиксирует все affected histories,
  outcomes/changes и immutable receipt; stale stream отклоняет всю
  unit.
- Generation сохраняется только complete; assessment commit атомарно
  связывает exact generation, full batch и все pair assessments без
  partial prefix.
- Assessment supersession сохраняется отдельным immutable link;
  manual review атомарно фиксирует revision, assessment/finding
  binding, supersedes edge и head без winner при fork.
- Quality audit хранит supplied audit identity/revision, full control set и
  optional exact generation; metrics/coverage не становятся authoritative
  state.
- 15 fully fictional direct tests покрывают public constructors/ports,
  first writes, exact retry, content/stale conflicts, competing writers, atomic
  rollback, exact reads, manual fork, quality revision, supersession,
  immutability и forbidden surface.
- Финальный TASK-027 quality gate успешен: targeted `15 passed`, Ruff
  format-check (`99 files`), Ruff lint, strict mypy (`44 source files`),
  основной pytest `618 passed`, fixture catalog `44 passed`, frozen sync/lock,
  `git diff --check`, relative Markdown links и changed-path/public-surface
  audits.
- ADR 0011 сравнивает official/partner access, HTML/browser scraping и
  разрешённый outbound XML/feed и принимает только conditional official route.
- Official site/API terms, license, OpenAPI schema и robots checked
  2026-09-02 без обращения к search/listing/card/data endpoints.
- Published `get-my-offers`/detail относятся к объявлениям агентства;
  XML methods — к входящему импорту. Documented public-listings search/read
  method для внешнего продукта отсутствует.
- API-key не заменяет preliminary permission exact use case. Общая
  рекомендация `<=10 requests/s/method` с оговоркой о method-specific
  значениях не является достаточной квотой отсутствующего target route.
- Статус `CONDITIONAL_GO` означает текущий запрет live access. HTML, browser
  automation, internal/undocumented endpoint, CAPTCHA/proxy/cookie/session и
  protection bypass имеют `NO_GO`.
- Семь blockers требуют written public-listings permission, documented route,
  field/use/attribution rights, method-specific limits, PII-safe shape,
  retention/sample terms и fresh rules/schema/robots audit.
- Future pilot ceiling: один заранее frozen query, одна request, одна page,
  максимум 20 records, strict structured allowlist, zero retry/parallel/
  scheduler/AI/browser. Free text, images, contacts, account identifiers и
  inference о владельце за границей запрещены.
- Raw capture по умолчанию запрещён. Provider-supplied synthetic/redacted
  sample предпочтителен; явно разрешённый minimal real sample хранится вне Git
  не более 7 дней/до TASK-029 и удаляется с safe receipt.
- Реальные объявления, contacts, images, text, keys/secrets, source code,
  dependencies, fixtures и domain contracts TASK-028 не изменяла.
- Финальный TASK-028 quality gate успешен: frozen sync/lock, Ruff
  format-check (`102 files`), Ruff lint, strict mypy (`44 source files`),
  основной pytest `618 passed`, fixture catalog `44 passed`,
  `git diff --check`, 62 relative Markdown links, exact 8-file changed-path и
  sensitive/real-data/source-evidence audits.

## Что намеренно не реализовано

- Запись output на диск.
- Durable persistence adapter и storage schema/technology.
- SQL/JSON/filesystem schema, ORM, migrations, transaction manager, cache,
  queue, scheduler, distributed lock и выбор storage technology.
- Side-effecting production executor/orchestrator, ingestion run и retry/backoff
  implementation.
- Raw source capture, legal retention/deletion, observation correction/backfill
  и multi-policy history migration.
- Аккаунт/API-key/письменное разрешение ЦИАН, public-listings API/outbound feed,
  saved sample и любое обращение в поддержку/продажи.
- Offline source adapter TASK-029 и controlled live pilot ЦИАН.
- Физический объект недвижимости, merge/clustering, база данных, API, HTTP,
  HTML и реальные площадки.
- Нестандартные сигналы, ИИ, уведомления, UI, OpenClaw и Telegram.
- Docker, CI, развёртывание и динамический загрузчик плагинов.

## Рекомендуемая следующая задача

Не начинать implementation, пока пользователь отдельно не получит от ЦИАН
полный evidence package `B1`–`B6` из
[pilot contract](docs/design/CIAN-READ-ONLY-PILOT-CONTRACT.md). После полного
подтверждения и fresh `B7` отдельная TASK-029 может реализовать только offline
adapter на provider-supplied synthetic/redacted либо явно разрешённом
сохранённом примере, без live access. Controlled live pilot остаётся более
поздней отдельной задачей.

## Открытые архитектурные вопросы

- Понадобится ли когда-либо сущность физического объекта после измерения
  качества independent pair assessments, и какие доказательства разрешат
  отдельный пересмотр ADR 0006?
- Какое durable хранение потребуется после reference adapter и какие измеренные
  объём, read patterns, retention и concurrency определят его выбор?
- Понадобится ли отдельный backfill/recompute workflow для доказанных
  out-of-order наблюдений, и как он будет версионировать пересчитанные changes?
- Предоставит ли ЦИАН письменное разрешение на external public-listings search,
  documented route/feed, field rights, exact quota и retention/sample terms,
  достаточные для снятия blockers TASK-028?
- Когда составному нормализованному значению понадобится происхождение из
  нескольких исходных полей?
- Какой bucket pair limit оправдают будущие fully fictional benchmarks и
  reviewed blocking coverage без превращения числа в универсальную константу?
- Какой отдельный side-effecting execution contract потребуется
  и какие operational retry/backoff/observability правила не должны проникать
  в consumer-owned persistence ports?
- Потребуется ли legal/audit raw source capture, и какие retention/deletion
  требования разрешат отдельный upstream port?

Ответы не должны приниматься молча: существенные решения оформляются в
`docs/decisions/` в рамках назначенных задач.
