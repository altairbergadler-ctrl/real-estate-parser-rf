# Атомарная assessment-композиция готовых duplicate candidates

## Назначение и границы

Документ уточняет [ADR 0009](../decisions/0009-duplicate-candidate-assessment-batch.md)
до переносимого design-only контракта будущей pure реализации TASK-025.
Композиция принимает готовый `DuplicateCandidateGenerationResult`, полный
caller-supplied current context и явно выбранную assessment policy. Она
проверяет exact structural binding и оценивает все и только materialized
candidates существующей `assess_publication_pair`.

Повторно используются public contracts:

- `AvailableObservation`, `ObservationKey`, `PublicationRef` из observation
  model;
- `PublicationPair`, `DuplicatePolicy`, `DuplicatePolicyVersion`,
  `PairAssessmentSuccess`, `PairNotAssessed`, `PairAssessmentFailure` и
  `assess_publication_pair` из
  [duplicate evidence](PUBLICATION-DUPLICATE-EVIDENCE.md);
- `DuplicateCandidate`, `DuplicateCandidateIdentity`,
  `DuplicateCandidateGenerationIdentity` и
  `DuplicateCandidateGenerationResult` из
  [candidate generation](PUBLICATION-DUPLICATE-CANDIDATES.md).

Ни один из этих contracts и policies не меняется. Здесь нет Python
implementation/tests, storage, repository/index/database, Pydantic/JSON,
filesystem, CLI/API/UI, concurrency/revision, real data, HTTP, AI, physical
property, merge или cluster.

## Термины и обязательные различия

- **Generation context** — exact
  `DuplicateCandidateGenerationIdentity`, включая candidate policy, bucket
  limit и полный canonical tuple input keys.
- **Current context** — полный validated canonical tuple caller-supplied
  `AvailableObservation`; только он содержит listing и provenance для вызова
  assessment.
- **Candidate policy** выбирает pairs и имеет identity
  `publication-duplicate-candidate-policy@1`.
- **Assessment policy** оценивает одну pair и имеет независимую identity
  `publication-duplicate-policy@1`.
- **Batch identity** связывает один generation context с одной assessment
  policy version. Она не является identity generation или assessment одной
  pair.
- **Atomicity** означает: success содержит outcomes всех candidates, failure
  не содержит ни одного item outcome.

Candidate blocking matches — только объяснение route, которым generation
materialized pair. Они не являются `DuplicateEvidenceItem`, не подменяют
полные observations и не влияют напрямую на assessment outcome.

## Логические pseudotypes

### Validated input и configuration

Внешняя pure operation принимает raw tuple, но после preflight conceptually
строит следующий validated input:

```text
DuplicateCandidateAssessmentBatchInput(
  generation_result: DuplicateCandidateGenerationResult,
  current_observations: non-empty canonical tuple[AvailableObservation, ...],
  assessment_policy: DuplicatePolicy
)
```

Отдельная configuration не смешивает policies:

```text
DuplicateCandidateAssessmentBatchConfiguration(
  generation_configuration: DuplicateCandidateGenerationConfiguration,
  assessment_policy: DuplicatePolicy
)
```

`generation_configuration` получается только из exact supplied
`generation_result.configuration`; composition не принимает новый bucket
limit и не строит новый candidate policy.

### Batch и item identity

```text
DuplicateCandidateAssessmentBatchIdentity(
  generation_identity: DuplicateCandidateGenerationIdentity,
  assessment_policy_version: DuplicatePolicyVersion
)

DuplicateCandidateAssessmentItemIdentity(
  batch_identity: DuplicateCandidateAssessmentBatchIdentity,
  candidate_identity: DuplicateCandidateIdentity
)
```

Batch identity содержит две разные policy coordinates через вложенную
generation identity и assessment version. Assessment version никогда не
выводится из candidate policy version и не обязана иметь сходную строку.

Item identity уникальна внутри batch по candidate identity. Новая current key,
новый bucket limit, candidate policy или assessment policy создают новую
identity через соответствующую structural coordinate.

### Item outcome, success и failure

```text
DuplicateCandidateAssessmentItemOutcome(
  identity: DuplicateCandidateAssessmentItemIdentity,
  candidate: DuplicateCandidate,
  result: PairAssessmentSuccess
)

DuplicateCandidateAssessmentBatch(
  identity: DuplicateCandidateAssessmentBatchIdentity,
  generation_result: DuplicateCandidateGenerationResult,
  assessment_policy: DuplicatePolicy,
  item_outcomes: tuple[DuplicateCandidateAssessmentItemOutcome, ...]
)

DuplicateCandidateAssessmentBatchSuccess(
  batch: DuplicateCandidateAssessmentBatch
)

DuplicateCandidateAssessmentBatchFailure(
  conflicts: non-empty unique canonical
             tuple[DuplicateCandidateAssessmentBatchConflict, ...]
)

DuplicateCandidateAssessmentBatchOutcome =
  DuplicateCandidateAssessmentBatchSuccess
  | DuplicateCandidateAssessmentBatchFailure
```

Success stores the full generation result rather than only its identity. This
binds configuration, candidates, blocking matches, non-participations and
oversized outcomes to the batch content without copying any of them into
assessment evidence.

Future pure operation:

```text
assess_duplicate_candidate_batch(
  generation_result: DuplicateCandidateGenerationResult,
  current_observations: tuple[object, ...],
  assessment_policy: DuplicatePolicy
) -> DuplicateCandidateAssessmentBatchOutcome
```

Default policies are not implicit in this API. Caller passes assessment policy
explicitly; generation policy and limit come from the result.

## Constructor invariants

### Batch input

- `generation_result` is an actual `DuplicateCandidateGenerationResult`;
- current observations are a tuple, not list/iterator/mutable collection;
- tuple is non-empty;
- every item is an actual `AvailableObservation` with valid key/listing/
  provenance invariants;
- no `UnavailableObservation` and no unsupported object;
- no equal `ObservationKey` with different full observation content;
- no more than one item per `PublicationRef`, including exact repeats;
- canonical stored order is
  `(source_id.value, publication_id.value, observed_at.value)`;
- input permutations that contain the same full observations construct the
  same validated input.

Same-key handling is exact:

1. One key with two unequal full observations produces only
   `observation_key_content_conflict` for that key.
2. Exact repeated full observation produces `duplicate_publication_ref`.
3. Two different keys of one reference produce `duplicate_publication_ref`.
4. If one reference has both a same-key content conflict and another key, both
   independently provable codes may exist; neither chooses a winning item.

### Batch identity

- `generation_identity` is exact supplied result identity;
- `assessment_policy_version` is exact supplied policy version;
- candidate and assessment policy versions retain their different types;
- identity contains no hash, JSON bytes, clock, UUID, repository revision or
  arrival order.

### Item identity and outcome

- `item.identity.batch_identity == batch.identity`;
- `item.identity.candidate_identity == item.candidate.identity`;
- candidate is exactly one member of `batch.generation_result.candidates`;
- candidate identity policy equals generation identity candidate policy;
- candidate pair is canonical and contains two different references;
- candidate left/right keys equal current keys for exact pair sides;
- result is an actual `PairAssessmentSuccess`;
- result assessment identity pair and keys equal candidate identity pair and
  keys;
- result assessment policy version equals batch assessment policy version;
- result assessment left/right observations equal exact current observations,
  including full listing and provenance content;
- item contains no `PairNotAssessed` or `PairAssessmentFailure`.

### Batch success

- full generation result is exact supplied object by structural equality;
- full assessment policy equals supported supplied policy;
- identity equals generation identity plus assessment policy version;
- item outcomes are tuple-only, unique and in the exact canonical order of
  `generation_result.candidates`;
- there is exactly one item outcome per candidate and no outcome for any other
  pair;
- `len(item_outcomes) == len(generation_result.candidates)`;
- empty candidate tuple requires empty item tuple and is a valid success;
- success and batch records are frozen/slots in the future implementation.

### Failure

- conflicts are tuple-only, non-empty, unique and canonical;
- failure has no `batch`, `item_outcomes`, partial assessments or successful
  prefix;
- a constructor rejects unsorted, duplicate or empty conflict tuples.

## Supported policies

Preflight accepts exactly:

```text
generation_result.policy == PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1
generation_result.identity.candidate_policy_version
  == PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1.version
assessment_policy == PUBLICATION_DUPLICATE_POLICY_V1
```

Full structural equality is required, not only equality of version strings.
This matters because existing `assess_publication_pair` can evaluate a caller
constructed policy with v1 rules and a different version. Batch v1
intentionally forbids that: future assessment policy versions require a new
batch contract decision or explicit support.

`unsupported_candidate_policy` and `unsupported_assessment_policy` are
different codes and subjects. One cannot be inferred from the other.

## Exact binding current context к generation result

Let `G` be `generation_result.identity.canonical_input_keys` and `K` be the
canonical keys of validated current observations. Binding requires `K == G`
as an ordered tuple after canonicalization.

The mismatch is classified by reference, not by an undifferentiated set diff:

```text
GenerationCurrentKeysMismatchKind =
  MISSING_GENERATION_KEY
  | EXTRA_CURRENT_KEY
  | CURRENT_KEY_MISMATCH

GenerationCurrentKeysMismatchSubject(
  kind: GenerationCurrentKeysMismatchKind,
  reference: PublicationRef,
  generation_key: ObservationKey | absent,
  current_key: ObservationKey | absent
)
```

Exact forms:

- `MISSING_GENERATION_KEY`: reference/key exists in `G`, reference absent from
  current context; generation key present, current key absent.
- `EXTRA_CURRENT_KEY`: reference/key exists in current context, reference
  absent from `G`; current key present, generation key absent.
- `CURRENT_KEY_MISMATCH`: same reference exists once in both contexts, but
  exact keys differ; both keys present. A newer `observed_at` is this kind, not
  one missing plus one extra conflict.

Order of mismatch subjects is canonical reference order, then kind position
`MISSING_GENERATION_KEY`, `EXTRA_CURRENT_KEY`, `CURRENT_KEY_MISMATCH`, then
generation/current key coordinates. Exact equality yields no mismatch.

Generation result intentionally contains no full observations. Therefore:

- composition cannot reconstruct listing or provenance from keys;
- blocking matches, non-participations, oversized buckets and assessment
  snapshots cannot supply current content;
- same-key content conflict is detectable within current input and later by a
  consumer comparing full batch content, not by generation identity alone;
- exact current observation objects are passed to assessment unchanged.

## Candidate structural binding

For every `candidate` in the supplied result, preflight constructs the only
expected identity from existing coordinates:

```text
expected_pair = PublicationPair(
  candidate.identity.left_observation_key.reference,
  candidate.identity.right_observation_key.reference
)

expected_identity = DuplicateCandidateIdentity(
  pair=expected_pair,
  left_observation_key=current_by_ref[expected_pair.left].key,
  right_observation_key=current_by_ref[expected_pair.right].key,
  candidate_policy_version=generation_result.identity.candidate_policy_version
)
```

Exact `candidate.identity == expected_identity` is mandatory. Additionally,
both keys must occur in generation identity, candidate identities must be
unique and candidates must retain the result's canonical order. Any violation
is `candidate_binding_mismatch` with a typed kind:

```text
CandidateBindingMismatchKind =
  CANDIDATE_POLICY_MISMATCH
  | CANDIDATE_PAIR_KEY_MISMATCH
  | CANDIDATE_KEY_OUTSIDE_GENERATION
  | CANDIDATE_KEY_OUTSIDE_CURRENT
  | DUPLICATE_CANDIDATE_IDENTITY
  | NON_CANONICAL_CANDIDATE_ORDER

CandidateBindingMismatchSubject(
  kind: CandidateBindingMismatchKind,
  candidate_identity: DuplicateCandidateIdentity
)
```

Existing constructors already prevent these states under normal construction;
batch preflight repeats the boundary checks defensively because it promises no
assessment call for a structurally inconsistent supplied result.

The composition does **not** project fields, rebuild buckets, recompute
prospective counts or prove that blocking matches could have materialized the
pair. That would repeat candidate generation. It accepts the exact candidate
set as the selection contract after identity/context binding. Full candidate
and matches remain preserved in success solely as generation routing metadata.

## Conflict contract

### Category and codes

```text
DuplicateCandidateAssessmentBatchConflictCategory =
  DUPLICATE_CANDIDATE_ASSESSMENT_BATCH_CONFLICT

DuplicateCandidateAssessmentBatchConflictCode =
  observations_not_tuple
  | empty_current_observations
  | observation_not_available
  | unsupported_observation
  | observation_key_content_conflict
  | duplicate_publication_ref
  | unsupported_generation_result
  | unsupported_candidate_policy
  | unsupported_assessment_policy
  | generation_current_keys_mismatch
  | candidate_binding_mismatch
  | unexpected_pair_not_assessed
  | downstream_assessment_conflict
  | item_identity_content_conflict
  | batch_identity_content_conflict
```

### Structural subjects

```text
BatchInputSubject = current_observations | generation_result | assessment_policy

UnsupportedObservationSubject(input_ordinal: non-negative integer)

DuplicatePublicationRefSubject(
  reference: PublicationRef,
  observation_keys: canonical tuple[ObservationKey, ...]  # size >= 2
)

UnsupportedCandidatePolicySubject(
  candidate_policy_version: DuplicateCandidatePolicyVersion
)

UnsupportedAssessmentPolicySubject(
  assessment_policy_version: DuplicatePolicyVersion | absent
)

UnexpectedPairNotAssessedSubject(
  item_identity: DuplicateCandidateAssessmentItemIdentity,
  result: PairNotAssessed
)

DownstreamAssessmentConflictKind =
  PAIR_ASSESSMENT_FAILURE
  | SUCCESS_BINDING_MISMATCH
  | UNSUPPORTED_DOWNSTREAM_RESULT

DownstreamAssessmentConflictSubject(
  item_identity: DuplicateCandidateAssessmentItemIdentity,
  kind: DownstreamAssessmentConflictKind,
  assessment_conflicts: tuple[DuplicateAssessmentConflict, ...]
)

DuplicateCandidateAssessmentBatchConflict(
  category: DuplicateCandidateAssessmentBatchConflictCategory,
  code: DuplicateCandidateAssessmentBatchConflictCode,
  subject:
    BatchInputSubject
    | ObservationKey
    | UnsupportedObservationSubject
    | DuplicatePublicationRefSubject
    | UnsupportedCandidatePolicySubject
    | UnsupportedAssessmentPolicySubject
    | GenerationCurrentKeysMismatchSubject
    | CandidateBindingMismatchSubject
    | UnexpectedPairNotAssessedSubject
    | DownstreamAssessmentConflictSubject
    | DuplicateCandidateAssessmentItemIdentity
    | DuplicateCandidateAssessmentBatchIdentity
)
```

Absent assessment policy version is permitted only when the supplied object is
not a typed `DuplicatePolicy` and its version cannot be read safely.

`assessment_conflicts` is non-empty only for
`PAIR_ASSESSMENT_FAILURE`; it preserves the exact typed downstream conflicts
in their already canonical order. Other kinds use an empty tuple. Free-form
exception text, input values, repr and stack traces are absent.

### Code-to-subject binding

| Code | Required subject | Phase |
| --- | --- | --- |
| `observations_not_tuple` | `current_observations` | preflight |
| `empty_current_observations` | `current_observations` | preflight |
| `observation_not_available` | exact `ObservationKey` | preflight |
| `unsupported_observation` | input ordinal | preflight |
| `observation_key_content_conflict` | exact `ObservationKey` | preflight |
| `duplicate_publication_ref` | reference + conflicting keys | preflight |
| `unsupported_generation_result` | `generation_result` | preflight |
| `unsupported_candidate_policy` | typed candidate policy subject | preflight |
| `unsupported_assessment_policy` | typed assessment policy subject | preflight |
| `generation_current_keys_mismatch` | typed missing/extra/key mismatch | preflight |
| `candidate_binding_mismatch` | candidate identity + typed kind | preflight |
| `unexpected_pair_not_assessed` | item identity + exact result | downstream |
| `downstream_assessment_conflict` | item identity + typed kind/details | downstream |
| `item_identity_content_conflict` | item identity | future consumer |
| `batch_identity_content_conflict` | batch identity | future consumer |

### Canonical ordering and uniqueness

Conflict phase/code position is exactly the order in the code union above.
Within one code:

- observation keys use canonical observation-key order;
- unsupported observations use input ordinal;
- duplicate references use reference order, then their canonical key tuple;
- key mismatches use the subject order defined earlier;
- candidate subjects use canonical candidate order, then mismatch kind order;
- downstream subjects use canonical item/candidate order, then downstream kind,
  then exact nested conflict order;
- item conflicts use item identity order;
- batch conflicts use generation identity coordinates followed by assessment
  policy version.

Final sort key is `(code_position, subject_sort_key, category, code)`. Exact
duplicate conflict records collapse to one. Constructor validation requires
the resulting tuple already have this order.

## Preflight validation and zero-call guarantee

Validation is phase-gated to avoid cascading guesses while still collecting
all conflicts independently provable inside each reachable phase:

1. **Top-level shape.** Validate generation result type, current tuple shape
   and assessment policy type. Independent supported-policy checks may run for
   valid typed objects. If current is not tuple, no item/context/candidate
   checks depending on it run.
2. **Current items.** Scan the full tuple and collect every unavailable item,
   unsupported ordinal, same-key content conflict and duplicate reference.
   No item is silently dropped or selected as winner.
3. **Canonical current context.** Construct it only if phase 2 has no current
   conflicts. Empty tuple remains `empty_current_observations` and does not
   produce derivative per-key missing conflicts.
4. **Policy/result support.** Validate full candidate policy/result binding
   and full assessment policy. These checks are independent of candidate
   count.
5. **Generation/current binding.** Run only with valid canonical current
   context and valid generation identity. Collect all missing/extra/key
   mismatches.
6. **Candidate binding.** Check generation-only coordinates whenever valid;
   check current-specific coordinates only after exact context equality.
   Collect all candidate violations.
7. Canonicalize/deduplicate the accumulated preflight conflicts.

If this tuple is non-empty, return `DuplicateCandidateAssessmentBatchFailure`
immediately. `assess_publication_pair` has been called exactly zero times.

No later conflict is guessed when a prerequisite structural object cannot be
constructed. For example, an unsupported object with no key produces only its
ordinal conflict, not a fabricated key mismatch.

## Assessment call order and downstream handling

After conflict-free preflight:

1. Build an `O(N)` lookup `current_by_reference` from the canonical current
   tuple.
2. Iterate `generation_result.candidates` in their existing canonical order.
3. For each candidate, obtain exact left and right observations by pair side.
4. Call exactly:

```text
assess_publication_pair(
  first=left_current_observation,
  second=right_current_observation,
  policy=assessment_policy
)
```

5. Do not pass blocking matches, snapshots or candidate policy into the
   assessment operation.
6. Classify the returned union:
   - exact bound `PairAssessmentSuccess` → retain provisional item outcome;
   - `PairNotAssessed` → `unexpected_pair_not_assessed`;
   - `PairAssessmentFailure` → `downstream_assessment_conflict` with exact
     nested conflicts;
   - success with wrong pair/keys/policy/full sides →
     `downstream_assessment_conflict/SUCCESS_BINDING_MISMATCH`;
   - any other returned object →
     `downstream_assessment_conflict/UNSUPPORTED_DOWNSTREAM_RESULT`.
7. Continue through every remaining candidate after any downstream conflict.
   The operation is pure and side-effect free; no retry is performed and no
   candidate is called twice.
8. If downstream conflicts exist, discard all provisional successful items,
   canonicalize conflicts and return atomic failure.
9. Otherwise construct the complete ordered success.

`PairNotAssessed` and `PairAssessmentFailure` are values, not exceptions. This
contract converts them to typed batch conflicts. It does not catch arbitrary
programming exceptions or attach their text; correct preflight and the public
v1 constructors make such exceptions outside the domain outcome contract.

### Exact call counts

| State | Assessment calls |
| --- | --- |
| Any preflight conflict | `0` |
| Valid input, `C = 0` candidates | `0` |
| Valid input, `C > 0`, all success | exactly `C` |
| Valid input, downstream conflict at any position | exactly `C` |

There is no short-circuit after downstream failure because the chosen contract
returns the complete pure conflict set.

## Atomicity

Atomicity is structural rather than a database transaction:

- preflight failure exposes no calls/results;
- downstream failure exposes typed conflicts only;
- provisional successes are local implementation details and absent from the
  failure contract;
- success proves one exact item per supplied candidate;
- no assessment, candidate, generation result, observation or policy is
  mutated;
- no persistence or expected revision is implied.

A future side-effecting adapter cannot reuse the continue-after-failure rule
without a new decision: it would need transaction/idempotency semantics. This
design applies only because every operation here is pure.

## Determinism, replay and future consumer conflicts

Structural equality includes:

- full generation result, not only generation identity;
- canonical full current observations and provenance;
- full assessment policy;
- batch/item identities;
- exact ordered pair assessments and findings.

For any permutation of the same valid full current observations:

```text
assess_duplicate_candidate_batch(G, permutation(O), P)
  == assess_duplicate_candidate_batch(G, O, P)
```

Future consumer rules:

- equal full batch → exact replay/no-op;
- equal item identity and equal full item → replay/no-op;
- equal item identity with different candidate or assessment content →
  `item_identity_content_conflict`;
- equal batch identity with different generation result, policy or item tuple
  → `batch_identity_content_conflict`;
- when both item and batch conflicts are independently observable, collect
  both in canonical order;
- never overwrite, merge, select newest, compare timestamps as winner or
  silently recompute stored content.

A new observation key changes generation identity and batch identity. A new
assessment policy version changes batch/item identity while preserving the
generation identity. Same keys with changed full observation content retain
batch identity but change batch content, so a future consumer reports stable
content conflict rather than overwrite.

## Complexity proof

Let:

- `N = len(current_observations)`;
- `C = len(generation_result.candidates)`.

Preflight performs:

- one pass over `N` observations to validate and build key/reference maps;
- one linear merge/comparison of canonical current keys and generation keys;
- one pass over `C` already canonical candidates for structural binding.

Composition performs `C` map lookups per side and exactly `C` calls to
`assess_publication_pair`. Therefore:

```text
batch lookup/composition work = O(N + C)
total work = O(N + C) + sum(cost(assess_publication_pair(candidate_i)))
assessment call count = C
space = O(N + C) for lookups, provisional items and conflicts
```

Canonical conflict/output order does not require a new all-pairs or candidate
sort: inputs are canonical by their validated contracts and conflicts are
emitted into fixed code/subject order. An implementation may stable-sort the
at-most-linear conflict list defensively; that does not alter the prohibited
pair-generation boundary, but the target algorithm should use ordered passes
to retain the stated `O(N + C)` composition bound.

Forbidden work:

- `N * (N - 1) / 2` scan;
- calling `generate_duplicate_candidates`;
- projecting or regrouping blocking keys;
- adding candidates for missing pairs;
- transitive closure or connected components;
- retry, fallback policy or hidden assessment version selection.

## Полностью вымышленная scenario matrix

Все examples используют только `fixture_portal`, `mirror_fixture` и `.example`.
Они не описывают реальные объекты или людей.

| Сценарий | Input | Ожидаемый result/calls |
| --- | --- | --- |
| Empty candidates | valid non-empty current context и generation result с `candidates=()` | success, empty item tuple, `0` calls |
| One pair | одна exact candidate `A/B` | один bound item outcome, ровно `1` call |
| Multiple pairs с общей publication | canonical candidates `A/B`, `A/C` | два независимых items, `A` передаётся в два calls, ровно `2` calls |
| Same-source | `fixture_portal/a-1` и `fixture_portal/a-2` | допустимая assessment, identities сохраняются |
| Cross-source | `fixture_portal/a-1` и `mirror_fixture/z-9` | допустимая assessment, source не routing evidence |
| Input permutation | те же full observations в обратном tuple order | тот же canonical input и structurally equal batch |
| Missing observation | generation содержит key `B`, current reference `B` отсутствует | `generation_current_keys_mismatch/MISSING_GENERATION_KEY`, `0` calls |
| Extra observation | current содержит reference `C`, которой нет в generation | `generation_current_keys_mismatch/EXTRA_CURRENT_KEY`, `0` calls |
| Newer key same reference | generation `B@t1`, current `B@t2` | один `CURRENT_KEY_MISMATCH`, не missing+extra, `0` calls |
| Unavailable item | current tuple содержит `UnavailableObservation` | `observation_not_available`, `0` calls |
| Unsupported item | current tuple содержит иной object | `unsupported_observation` с ordinal, `0` calls |
| Same-key content conflict | два `B@t1` с разным full listing/provenance | `observation_key_content_conflict`, no winner, `0` calls |
| Duplicate ref | exact repeat либо `B@t1` и `B@t2` | `duplicate_publication_ref`, `0` calls |
| Candidate policy mismatch | result policy/version не full supported v1 | `unsupported_candidate_policy`, `0` calls |
| Assessment policy mismatch | explicit policy не full supported v1 | `unsupported_assessment_policy`, `0` calls |
| Crafted candidate binding mismatch | candidate left key относится к иной current side или outside generation | `candidate_binding_mismatch` с exact kind, `0` calls |
| Blocking metadata | valid candidate имеет один или два blocking matches | matches сохраняются только в generation result; assessment получает только full sides |
| Unexpected `PairNotAssessed` | downstream возвращает not-assessed для valid available sides | typed `unexpected_pair_not_assessed`; оставшиеся candidates всё равно called once; atomic failure |
| Downstream assessment failure | downstream возвращает `PairAssessmentFailure` | nested typed conflicts сохранены; полный pure pass; no item outcomes |
| Multiple downstream failures | разные candidates дают not-assessed/failure | unique canonical conflict tuple независимо от positions; exactly `C` calls |
| Replay | identical full generation result/current/policy | structurally equal batch; future consumer no-op |
| Same batch identity, changed content | generation result или current full content изменён при тех же identity keys | `batch_identity_content_conflict`, без overwrite |
| Same item identity, changed content | exact item identity имеет другую assessment | `item_identity_content_conflict`, без winner |
| New generation identity | `B@t2` проходит новую generation и batch | новая batch/item identity; old batch сохраняется отдельно |
| Non-transitivity | candidates `A/B` и `B/C`, но `A/C` отсутствует | только два supplied items; `A/C` не создаётся, cluster отсутствует |

## Намеренно отсутствует

- implementation, exports и tests — TASK-025;
- изменение `assess_publication_pair`, `generate_duplicate_candidates`, ADR
  0006/0008 либо candidate/assessment policies;
- storage, repository, index, database, ORM, migrations и persistence;
- concurrency, transaction, expected revision, locking и retry;
- JSON, Pydantic, filesystem, serialization и external schemas;
- CLI, API, UI, dashboard и notifications;
- real data, реальные sources, HTTP, scraping и legal collection policy;
- AI, embeddings, LLM, fuzzy matching, tolerance и hidden fallback;
- physical property, canonical winner, history merge, collapse/hide,
  clustering, connected components и transitive closure.

## Следующая рекомендуемая задача

TASK-025 — реализовать neutral frozen/slots batch-assessment contracts и pure deterministic composition по ADR 0009 для exact DuplicateCandidateGenerationResult/current AvailableObservation binding, без storage, JSON, CLI, real data или изменения candidate/assessment policies
