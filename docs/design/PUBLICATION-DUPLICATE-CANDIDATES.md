# Детерминированное формирование duplicate candidate pairs

## Назначение и границы

Документ уточняет [ADR 0008](../decisions/0008-duplicate-candidate-generation.md)
до design-only контракта будущей pure реализации. Он принимает только явно
переданный набор current observations, строит ограниченный multi-pass union
candidate pairs и объясняет неполное участие. Здесь нет Python implementation,
tests, storage/index/database, Pydantic/JSON, filesystem, CLI/API/UI или real
data.

Контракт повторно использует существующие `PublicationRef`, `ObservationKey`,
`AvailableObservation`, `UnavailableObservation`, `Area`, `RoomCount`,
`LocationText` и canonical `PublicationPair`. Он не изменяет
[ADR 0006](../decisions/0006-publication-duplicate-evidence.md),
`publication-duplicate-policy@1`, автоматическую assessment, evidence, manual
review, [ADR 0007](../decisions/0007-reviewed-duplicate-control-metrics.md) или
[quality metrics TASK-020](PUBLICATION-DUPLICATE-QUALITY.md).

Candidate означает только «эта exact pair current observations должна быть
передана в отдельную assessment». Blocking match не является supporting
duplicate evidence, а отсутствие candidate не является contradicting evidence
или доказательством разных объектов.

## Current available input

### Логическая форма

```text
DuplicateCandidateGenerationInput(
  observations: non-empty tuple[AvailableObservation, ...]
)
```

Будущая внешняя pure operation может принять tuple объектов
`PublicationObservation`, но обязана сначала атомарно построить этот validated
input. Инварианты:

- только tuple; mutable collection не принимается;
- tuple непустой;
- каждый элемент — `AvailableObservation` с уже согласованными exact key,
  listing и provenance invariants TASK-016;
- `UnavailableObservation` и иной object — contract failure, не
  non-participation;
- не более одного observation на `PublicationRef`;
- equal `ObservationKey` с разным полным observation content —
  `observation_key_content_conflict`;
- exact repeated observation и два разных keys одной reference —
  `duplicate_publication_ref`;
- после полной проверки observations хранятся по canonical observation order,
  независимо от входной перестановки.

Canonical observation key:

```text
(
  key.reference.source_id.value,
  key.reference.publication_id.value,
  key.observed_at.value
)
```

`ObservedAt.value` уже является canonical UTC datetime. Она участвует в
identity и ordering, но не в blocking key. Поскольку на reference допускается
ровно одно observation, input означает именно caller-selected current context,
а не history lookup.

Валидация конфликтов имеет приоритет:

1. collection shape и непустота;
2. unsupported/unavailable elements;
3. equal key с conflicting full content;
4. repeated `PublicationRef`;
5. policy/configuration.

Все независимо доказуемые conflicts возвращаются одним canonical tuple; ни
candidate, ни bucket outcome при failure не существует.

## Candidate policy v1

### Separate identity

```text
DuplicateCandidatePolicyVersion(value: safe opaque ASCII code)
DuplicateCandidateRuleId(value: safe opaque ASCII code)
DuplicateCandidateRuleVersion(value: safe opaque ASCII code)

DuplicateCandidateRule(
  rule_id: DuplicateCandidateRuleId,
  rule_version: DuplicateCandidateRuleVersion,
  components: non-empty tuple[CandidateBlockingField, ...]
)

DuplicateCandidatePolicy(
  version: DuplicateCandidatePolicyVersion,
  rules: non-empty tuple[DuplicateCandidateRule, ...]
)
```

Первая версия:

```text
DuplicateCandidatePolicyVersion("publication-duplicate-candidate-policy@1")
```

Она не равна и не является alias
`DuplicatePolicyVersion("publication-duplicate-policy@1")`. Candidate policy
выбирает пары; duplicate policy позже оценивает одну выбранную пару.

### Ровно два ordered rules

| Порядок | Rule id | Rule version | Компоненты exact key |
| --- | --- | --- | --- |
| 1 | `area-rooms-exact-block` | `candidate-area-rooms@1` | `total_area`, `rooms` |
| 2 | `area-location-text-exact-block` | `candidate-area-location-text@1` | `total_area`, `location_text` |

Это две ветви candidate gate ADR 0006:

```text
exact total_area AND (exact rooms OR exact location_text)
```

Policy v1 не содержит и не читает:

- price amount или currency;
- source id как часть blocking value;
- `observed_at`;
- source URL, raw representation или provenance;
- tolerance, fuzzy text, locale collation, geocoding или coordinates;
- photo, AI, embedding, LLM или probability;
- персональные или поведенческие признаки.

Source id всё ещё входит в `PublicationRef` и canonical pair identity. Поэтому
same-source и cross-source pairs одинаково допустимы, но key не разделяет
bucket по source.

## Typed blocking keys

```text
AreaRoomsBlockingKey(
  rule_id: area-rooms-exact-block,
  rule_version: candidate-area-rooms@1,
  total_area: Area,
  rooms: RoomCount
)

AreaLocationTextBlockingKey(
  rule_id: area-location-text-exact-block,
  rule_version: candidate-area-location-text@1,
  total_area: Area,
  location_text: LocationText
)

DuplicateBlockingKey =
  AreaRoomsBlockingKey | AreaLocationTextBlockingKey
```

`Area.value` — exact integer hundredths of square metre, `RoomCount.value` —
exact integer canonical count, `LocationText.value` — уже нормализованная
canonical string. Equality всегда структурная по variant, rule id/version и
typed values. Float, decimal formatting, locale-dependent string formatting,
serialized digest и hash value не входят в identity. Internal hash может быть
оптимизацией, но collision всегда разрешается full structural equality и не
может объединить разные keys.

Canonical blocking-key order:

1. rule position в policy;
2. для area/rooms: `Area.value`, затем `RoomCount.value` как integers;
3. для area/location: `Area.value`, затем `LocationText.value` по Unicode code
   points, без locale collation.

## Missing/Unsupported и явное non-participation

Rule создаёт key только если каждый его component имеет `Present` canonical
value ожидаемого типа.

```text
BlockingComponentNonParticipation(
  field: CandidateBlockingField,
  state: MISSING | UNSUPPORTED,
  unsupported_reason_code: safe opaque code | absent
)

BlockingNonParticipation(
  observation_key: ObservationKey,
  rule_id: DuplicateCandidateRuleId,
  rule_version: DuplicateCandidateRuleVersion,
  reasons: non-empty tuple[BlockingComponentNonParticipation, ...]
)
```

Инварианты:

- reasons идут в component order rule;
- `MISSING` не имеет unsupported reason;
- `UNSUPPORTED` сохраняет exact existing reason code, но не raw text;
- запись существует ровно для каждого rule, которому observation не может
  дать key;
- наличие non-participation в одном pass не запрещает участие в другом;
- разные present values не являются non-participation: они просто образуют
  разные exact buckets;
- цена/currency и другие поля вне rules не создают non-participation.

Canonical order: observation key, затем policy rule position, затем component
position. Эти records объясняют отсутствие membership, но не утверждают, какая
конкретная pair была пропущена.

## Caller-supplied bucket limit

```text
BucketPairLimit(value: positive integer)

DuplicateCandidateGenerationConfiguration(
  policy: DuplicateCandidatePolicy,
  bucket_pair_limit: BucketPairLimit
)
```

Limit обязателен и передаётся caller. Ноль, negative value, bool, float и
отсутствие значения — `invalid_bucket_pair_limit`. В policy нет default
константы: выбор числа требует будущих измерений.

Для каждого key строится logical bucket:

```text
BlockingBucket(
  key: DuplicateBlockingKey,
  member_keys: tuple[ObservationKey, ...]  # canonical, unique, size >= 1
)
```

До создания хотя бы одной пары вычисляется exact:

```text
prospective_pair_count = n * (n - 1) / 2
```

где `n = len(member_keys)`. Integer count не округляется и не материализует
all-pairs для подсчёта.

Если count больше limit, bucket целиком не разворачивается:

```text
OversizedBucket(
  key: DuplicateBlockingKey,
  member_keys: tuple[ObservationKey, ...],
  prospective_pair_count: integer,
  reason_code: prospective_pair_count_exceeds_limit
)
```

`prospective_pair_count > bucket_pair_limit.value` обязательно. Нельзя
создать первые `limit` pairs, выбрать pair по arrival order или silently
truncate membership. Bucket с count, равным limit, полностью materialized.
Bucket размера 1 имеет count 0, не создаёт pair и не является oversized.

Oversized records идут по canonical blocking-key order. Member keys идут по
canonical observation-key order.

## Candidate identity и union matches

```text
DuplicateCandidateIdentity(
  pair: PublicationPair,
  left_observation_key: ObservationKey,
  right_observation_key: ObservationKey,
  candidate_policy_version: DuplicateCandidatePolicyVersion
)

DuplicateCandidateBlockingMatch(
  blocking_key: DuplicateBlockingKey
)

DuplicateCandidate(
  identity: DuplicateCandidateIdentity,
  blocking_matches: non-empty tuple[DuplicateCandidateBlockingMatch, ...]
)
```

Keys обязаны соответствовать canonical pair sides. Pair состоит из разных
`PublicationRef`; входной инвариант одного observation на reference не
допускает self-pair.
Новая current observation хотя бы одной стороны меняет exact key и candidate
identity, даже если blocking values прежние.

Каждый non-oversized bucket materializes все canonical unordered pairs его
members. Pair from rule 1 и та же pair from rule 2 объединяются в одну
`DuplicateCandidate`. `blocking_matches`:

- unique по полному structural blocking key;
- непустой;
- содержит все и только keys, чьи non-oversized buckets materialized pair;
- ordered по candidate policy;
- не содержит skipped oversized key, потому что тот pair не materialized;
- не является `DuplicateEvidenceItem` и не предопределяет outcome assessment.

Если пара состоит в oversized area/rooms bucket, но в допустимом
area/location bucket, она появляется через area/location match. Oversized
area/rooms record сохраняется отдельно и не теряется.

Canonical candidate order:

```text
(
  pair.left.source_id.value,
  pair.left.publication_id.value,
  pair.right.source_id.value,
  pair.right.publication_id.value,
  left_observation_key.observed_at.value,
  right_observation_key.observed_at.value,
  candidate_policy_version.value
)
```

## Result и pure generation

```text
DuplicateCandidateGenerationIdentity(
  candidate_policy_version: DuplicateCandidatePolicyVersion,
  bucket_pair_limit: BucketPairLimit,
  canonical_input_keys: non-empty tuple[ObservationKey, ...]
)

DuplicateCandidateGenerationResult(
  identity: DuplicateCandidateGenerationIdentity,
  policy: DuplicateCandidatePolicy,
  candidates: tuple[DuplicateCandidate, ...],
  non_participations: tuple[BlockingNonParticipation, ...],
  oversized_buckets: tuple[OversizedBucket, ...]
)

generate_duplicate_candidates(
  current_observations: non-empty tuple[PublicationObservation, ...],
  configuration: DuplicateCandidateGenerationConfiguration
) -> DuplicateCandidateGenerationSuccess | DuplicateCandidateGenerationFailure
```

Success допускает пустые `candidates`, `non_participations` и
`oversized_buckets` независимо друг от друга. Identity содержит все canonical
input keys; result дополнительно содержит полную поддерживаемую policy
configuration.

Логическая operation:

1. Атомарно валидирует и канонизирует current input.
2. В policy order проецирует максимум два keys либо non-participations на
   observation.
3. Группирует memberships только по full typed key.
4. Для каждого bucket вычисляет prospective count без pair enumeration.
5. Oversized bucket целиком записывает как outcome; допустимый bucket полностью
   materializes.
6. Canonicalizes each pair, union/deduplicates candidates и собирает полный
   ordered match tuple.
7. Возвращает все result collections в объявленном stable order.

Operation не вызывает `assess_publication_pair`, не читает history/storage,
не ищет «соседние» keys и не выполняет fallback scan.

## Верхняя граница работы

Пусть:

- `N` — число input observations;
- `R = 2` — точное максимальное число blocking memberships одного observation;
- `B` — число непустых buckets;
- `L` — caller bucket pair limit;
- `E` — число pair materialization attempts до union.

Тогда:

```text
memberships <= R * N = 2N
B <= 2N
для каждого materialized bucket: pairs <= L
E <= B * L <= 2NL
unique candidates <= E <= 2NL
```

Oversized bucket хранит member keys, но не пары; суммарное число member
occurrences во всех buckets также не больше `2N`. Exact prospective counts
вычисляются constant work на bucket.

Structural grouping и canonical sorting требуют не более
`O(N log N + NL log(NL))` comparisons и `O(N + NL)` bounded materialized
records. При фиксированном `L` это `O(N log N)` work, `O(N)` space и не более
`2NL` pair attempts. Ни одна ветвь не допускает `N(N-1)/2` global scan.

Bound относится к pair generation. Позднейшая assessment каждого returned
candidate является отдельной работой другого контракта.

## Replay, equality и conflicts

Одинаковые full observations, policy configuration и limit всегда дают
структурно равный result независимо от входной перестановки. Equality включает
identity, full policy, ordered candidates/matches, non-participations и
oversized records; object identity, hash, JSON bytes и iteration order
внутреннего map не учитываются.

Будущий consumer обязан:

- exact equal generation result считать replay/no-op;
- equal `DuplicateCandidateIdentity` с иным match tuple/content отклонять как
  `candidate_identity_content_conflict`;
- equal `DuplicateCandidateGenerationIdentity` с иным full result content
  отклонять как `generation_identity_content_conflict`;
- equal observation key с иным full observation content отклонять до
  generation как `observation_key_content_conflict`;
- не выбирать winner и не перезаписывать сохранённый content.

Contract не задаёт repository interface, revision, transaction, database или
append operation.

### Stable generation conflicts

Category: `DUPLICATE_CANDIDATE_GENERATION_CONFLICT`.

| Code | Subject coordinates | Смысл |
| --- | --- | --- |
| `observations_not_tuple` | `generation_input` | вход не immutable tuple |
| `empty_generation_input` | `generation_input` | нет current observations |
| `observation_not_available` | exact `ObservationKey` | передан unavailable observation |
| `unsupported_observation` | zero-based input ordinal | передан иной object |
| `observation_key_content_conflict` | exact `ObservationKey` | equal key имеет разный full content |
| `duplicate_publication_ref` | `PublicationRef` + ordered conflicting keys | reference встречается более одного раза |
| `unsupported_candidate_policy` | candidate policy version | policy/version/rules не равны supported v1 |
| `invalid_bucket_pair_limit` | supplied limit value/type | limit не positive exact integer |
| `candidate_identity_content_conflict` | `DuplicateCandidateIdentity` | equal candidate identity имеет иной content |
| `generation_identity_content_conflict` | `DuplicateCandidateGenerationIdentity` | equal generation identity имеет иной full result |

Input conflicts сортируются по canonical reference/key, затем category/code;
ordinal используется только когда key невозможно получить. Конфликты future
consumer сортируются по generation identity, candidate identity, category и
code. Любой conflict исключает partial candidates/outcomes.

## Blocking coverage на fictional reviewed control set

### Назначение

Метрика измеряет только missed-pair risk конкретных:

- fully fictional cases `DuplicatePolicyControlSet` TASK-020;
- exact generation input/result;
- candidate policy и caller limit.

Она не заменяет precision/recall assessment policy TASK-020. Название
`blocking_coverage` относится к coverage формирования pairs, а не production
duplicate recall.

### Eligibility и disjoint counts

Для каждого control case сначала читается independently supplied label.
Rejected cases не входят в positive denominator. `INCONCLUSIVE` не считается
rejected и делает coverage metric unavailable.

Conclusive `CONFIRMED_RELATIONSHIP` case классифицируется ровно один раз:

1. `PairNotAssessed` → `confirmed_pair_not_assessed_count`;
2. `PairAssessmentSuccess`, но одной или обеих references нет в generation input →
   `confirmed_outside_generation_input_count`;
3. references есть, но assessment left/right keys не равны exact current
   generation keys → `confirmed_stale_or_mismatched_keys_count`;
4. success exact keys представлены как available → eligible confirmed case.

Первые три группы не входят в blocking denominator и не маскируются как miss.
`PairNotAssessed` остаётся отдельным даже если одноимённые references позже
появились в другом generation context.

Для eligible confirmed case:

- covered, если result содержит candidate с exact pair, exact left/right keys
  и generation candidate policy version;
- missed/no-shared-key, если observations не имеют общего exact v1 blocking
  key;
- missed/oversized, если общий key есть, но каждый общий key относится к
  skipped oversized bucket;
- наличие хотя бы одного общего non-oversized key при отсутствии candidate
  означает invalid result, а не измеримый miss.

Если один общий key oversized, а другой materialized pair, case covered.

### Pseudotypes

```text
BlockingCoverageUnavailableReason =
  inconclusive_control_labels
  | no_eligible_confirmed_relationships

BlockingCoverageUnavailable(
  reason: BlockingCoverageUnavailableReason
)

DuplicateCandidateBlockingCoverage(
  candidate_policy_version: DuplicateCandidatePolicyVersion,
  assessment_policy_version: DuplicatePolicyVersion,
  generation_identity: DuplicateCandidateGenerationIdentity,
  control_population_count: positive integer,
  pair_not_assessed_case_count: non-negative integer,
  rejected_label_count: non-negative integer,
  inconclusive_label_count: non-negative integer,
  confirmed_label_count: non-negative integer,
  confirmed_pair_not_assessed_count: non-negative integer,
  confirmed_outside_generation_input_count: non-negative integer,
  confirmed_stale_or_mismatched_keys_count: non-negative integer,
  eligible_confirmed_count: non-negative integer,
  covered_eligible_confirmed_count: non-negative integer,
  missed_no_shared_key_count: non-negative integer,
  missed_oversized_bucket_count: non-negative integer,
  blocking_coverage: ExactRatio | BlockingCoverageUnavailable
)

evaluate_duplicate_candidate_blocking_coverage(
  control_set: DuplicatePolicyControlSet,
  generation_result: DuplicateCandidateGenerationResult
) -> DuplicateCandidateBlockingCoverage | DuplicateCandidateCoverageFailure
```

Count invariants:

```text
population = rejected + inconclusive + confirmed

pair_not_assessed_case_count =
  all control cases whose result is PairNotAssessed

confirmed =
  pair_not_assessed
  + outside_generation_input
  + stale_or_mismatched_keys
  + eligible_confirmed

eligible_confirmed =
  covered
  + missed_no_shared_key
  + missed_oversized_bucket
```

Availability order:

1. Если `inconclusive_label_count > 0`, вернуть
   `inconclusive_control_labels`.
2. Иначе если `eligible_confirmed_count == 0`, вернуть
   `no_eligible_confirmed_relationships`.
3. Иначе:

```text
blocking_coverage =
  ExactRatio(
    covered_eligible_confirmed_count,
    eligible_confirmed_count
  )
```

`ExactRatio` повторно использует exact integer contract TASK-020. Ratio не
сокращается, не форматируется и не преобразуется во float/percent.
Oversized и no-shared-key misses остаются внутри denominator.

Evaluation только читает уже valid control set и generation result. Она не
перезапускает assessment, не изменяет labels/evidence и не создаёт candidates.
`DUPLICATE_CANDIDATE_COVERAGE_CONFLICT/generation_result_inconsistent` с
subject exact `PublicationPair + left/right ObservationKey` возвращается, если
declared result нарушает обязательную связь non-oversized shared key →
candidate. Partial metric при этом нет.

### Ограничение интерпретации

Coverage описывает только supplied fully fictional reviewed population и exact
generation context. Она не доказывает:

- production recall или поведение на реальных площадках;
- representativeness, unbiased sampling или статистическую обобщаемость;
- допустимость сбора, обработки или хранения реальных данных;
- accuracy assessment policy, human labels или identity физического объекта.

## Полностью вымышленная scenario matrix

Все references используют `fixture_portal`/`mirror_fixture` и вымышленные
identifiers; реальные площадки, объекты и люди отсутствуют.

| Сценарий | Input/configuration | Ожидаемый результат |
| --- | --- | --- |
| Оба passes | `A` и `B` имеют exact area, rooms и location | одна candidate с двумя matches в policy order |
| Только rooms pass | area/rooms равны, location различается | candidate с одним area/rooms match |
| Только location pass | area/location равны, rooms различаются | candidate с одним area/location match; assessment позже может сохранить room contradiction |
| Missing rooms | у `B` rooms missing, area/location равны | explicit rooms non-participation для `B` и candidate через location |
| Unsupported location | у `A` location unsupported, area/rooms равны | explicit location non-participation и candidate через rooms |
| Нет общего key | area различается либо corroborating values различаются | successful empty candidates; no contradicting evidence создаётся |
| Same-source | `fixture_portal/a-1` и `fixture_portal/a-2` делят key | допустимая candidate двух разных references |
| Cross-source | `fixture_portal/a-1` и `mirror_fixture/z-9` делят key | допустимая candidate; source id не blocking component |
| Unavailable input | `A` available, `B` unavailable | atomic `observation_not_available`; success отсутствует |
| Repeated reference | два current keys `fixture_portal/a-1` | atomic `duplicate_publication_ref` |
| Same-key conflict | два observations одного exact key с разным listing | atomic `observation_key_content_conflict` |
| Exact limit | bucket 3 members, prospective count 3, limit 3 | все три pairs materialized |
| Oversized atomic skip | bucket 4 members, prospective count 6, limit 3 | zero pairs из bucket; один `OversizedBucket` с четырьмя members и count 6 |
| No first-N | тот же oversized bucket при любой input permutation | ни одна частичная pair не появляется; result одинаков |
| Oversized + alternate key | `A/B` в oversized rooms bucket и в допустимом двух-member location bucket | `A/B` candidate только с location match; oversized rooms outcome сохранён |
| Replay/permutation | одинаковые full observations в другом tuple order | structurally equal generation result |
| New current key | у `B` тот же blocking value, но новый observed_at | новая candidate identity; прежняя различима как stale |
| Coverage 2/4 | 4 eligible confirmed: 2 candidates, 1 no-shared-key, 1 only oversized | exact `2/4`; оба вида miss входят в denominator |
| Confirmed PairNotAssessed | confirmed control case содержит `PairNotAssessed` | отдельный ineligible count; не blocking miss |
| Outside input | confirmed success pair содержит отсутствующую reference | отдельный unrepresented count; не denominator |
| Stale keys | обе references есть, exact assessment key одной стороны старый | отдельный stale/mismatched count; не denominator |
| Inconclusive label | любой case имеет `INCONCLUSIVE` | typed `inconclusive_control_labels`, counts сохранены |
| Zero eligible confirmed | labels conclusive, но confirmed cases только PairNotAssessed/outside/stale либо confirmed нет | typed `no_eligible_confirmed_relationships` |
| Non-transitivity | candidates `A/B` и `B/C` существуют | `A/C` не создаётся без собственного shared key; cluster отсутствует |

## Намеренно отложено

- Python types/functions/exports/tests и фактическая pair generation — TASK-022;
- benchmark и выбор конкретного bucket limit;
- storage, repository/index/database, persistence и concurrency;
- JSON/Pydantic/filesystem boundary, CLI/API/UI;
- assessment batch execution, evidence/manual-review изменения и новые quality
  metrics TASK-020;
- fuzzy/tolerance/geocoding/coordinates/photo/AI/LLM rules;
- physical property, canonical winner, merge/collapse/hide, clustering и
  transitive closure;
- real data, реальные sources, HTTP, OpenClaw, Telegram и notifications.
