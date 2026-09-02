# Consumer-owned persistence и replay публикаций

## Назначение и границы

Документ уточняет [ADR 0010](../decisions/0010-publication-persistence-and-replay.md)
до design-only контракта будущих neutral ports и reference adapter. Он
определяет authority, lineage, structural identity, optimistic revision,
atomic commit, replay, conflict и retention для уже существующих publication
observation и duplicate artifacts.

Повторно используются без изменений:

- `AvailableObservation`, `UnavailableObservation`, `ObservationKey`,
  `PublicationObservationHistory`, `PublicationObservationHistories`,
  `ChangeSet` и atomic batch outcome из
  [observation model](PUBLICATION-OBSERVATIONS-AND-CHANGES.md);
- `DuplicatePairAssessment`, `DuplicateAssessmentIdentity`,
  `AssessmentSupersession`, `DuplicatePairManualReview` и
  `ManualReviewIdentity` из
  [duplicate evidence](PUBLICATION-DUPLICATE-EVIDENCE.md);
- `DuplicateCandidateGenerationIdentity`,
  `DuplicateCandidateGenerationResult` и полный candidate content из
  [candidate generation](PUBLICATION-DUPLICATE-CANDIDATES.md);
- `DuplicateCandidateAssessmentBatchIdentity` и полный batch из
  [assessment batch](PUBLICATION-DUPLICATE-ASSESSMENT-BATCH.md);
- `DuplicatePolicyControlSet`, `DuplicatePolicyQualityMetrics` и
  `DuplicateCandidateBlockingCoverage` из
  [quality contracts](PUBLICATION-DUPLICATE-QUALITY.md).

Здесь нет Python implementation, storage technology, schema, ORM, migration,
serialization, filesystem layout, transaction manager, executor, scheduler,
queue, cache, distributed lock, API, CLI, UI или real data. `SQLite`,
`PostgreSQL`, event store и иной backend не выбираются.

## Два независимых измерения классификации

`Authoritative`, `derived`, `audit` и `projection` не являются одной шкалой.
Первые два термина отвечают, откуда взялось утверждение; вторые два — можно ли
удалить конкретное сохранённое представление без потери доказательства.

### Authority

- **Authoritative state** — принятый исходный observation либо явно supplied
  human assertion. Он не вычисляется из duplicate policy и не заменяется её
  новым результатом.
- **Derived state** — deterministic результат pure operation над exact inputs
  и explicit policy/configuration. Он объясним и воспроизводим, но не является
  новым источником истины о публикации или физическом объекте.

### Retention role

- **Immutable audit record** — committed record, который доказывает, какой
  exact input, policy, output или human assertion реально участвовал в
  workflow. Его можно архивировать по отдельно принятой policy, но routine
  retry/recompute не изменяет и не удаляет его.
- **Disposable/rebuildable projection** — ускоряющее чтение представление,
  полностью восстанавливаемое из retained authoritative и audit records. Его
  потеря не удаляет evidence и не меняет identity.

Один record может быть authoritative и immutable audit одновременно.
Derived artifact также становится immutable audit record, если был committed
как фактически использованный результат. Слово `derived` не разрешает его
перезапись.

## Классификация public artifacts

| Artifact | Authority | Retention role | Обоснование и правило |
| --- | --- | --- | --- |
| `ValidatedSourceBatch`, `SourceBatch`, `SourcePublicationSnapshot` | upstream input, не authoritative publication state этой границы | transient; optional upstream immutable audit по отдельной policy | Они предшествуют normalized observation. Текущие ports не вводят raw archive. Если будущая legal/audit policy требует capture, сохраняются exact source/reference/observed-at/adapter coordinates отдельным consumer contract. |
| `AvailableObservation` | authoritative evidentiary observation | immutable audit | Содержит exact `NormalizedListing`, raw representation внутри provenance и точный `ObservationKey`. После commit не редактируется. |
| `UnavailableObservation` | authoritative evidentiary observation | immutable audit | Содержит только доказанную недоступность по ADR 0005. Operational failure и batch omission не превращаются в запись. |
| `PublicationObservationHistory` | canonical snapshot authoritative sequence на одной revision | immutable snapshot; head является projection | Последовательность observations authoritative. Новый append создаёт новую revision/snapshot, но не изменяет принятые observations. |
| `PublicationObservationHistories` | атомарный multi-stream view над загруженным набором histories | rebuildable projection; commit receipt audit | Контейнер можно перестроить из streams. Receipt конкретного multi-history commit сохраняется для crash/retry и аудита. |
| `ChangeSet`, `ObservationBatchItemOutcome` | derived по exact adjacent observations и comparison policy | immutable audit, если committed; иначе rebuildable | Они не меняют observations. Equal inputs/policy обязаны дать equal content. Новая policy не переписывает старый result. |
| `DuplicateCandidateGenerationResult` | derived routing artifact | immutable audit после commit; до side effect rebuildable | Exact input keys, full policy, limit, candidates, non-participations и oversized outcomes объясняют selection. Он не duplicate evidence. |
| `DuplicatePairAssessment` | derived evidence artifact | immutable audit после commit или review reference | Exact observations и duplicate policy объясняют findings. Он не human decision и не physical-property fact. |
| `DuplicateCandidateAssessmentBatch` | derived complete batch artifact | immutable audit после commit | Сохраняет full generation result, assessment policy и все exact pair outcomes. Failure никогда не сохраняет partial batch. |
| `AssessmentSupersession` | explicit relational assertion | immutable audit | Не выводится из времени. Link добавляется, но previous assessment не удаляется. |
| `DuplicatePairManualReview` revision | authoritative supplied human assertion exact pair | immutable audit | Revision/supersedes chain append-only. Даже confirm не создаёт physical property или merge. |
| `DuplicateControlLabel` | authoritative supplied label только для exact control population | immutable audit при использовании в evaluation | Не выводится из automatic result и не становится общим production truth. |
| `DuplicatePolicyControlSet` | version-bound audit input | immutable audit snapshot при зафиксированной evaluation | Сохраняет exact cases/results/labels, если на его основе опубликовано или принято решение о качестве. |
| `DuplicatePolicyQualityMetrics`, `DuplicateCandidateBlockingCoverage` | derived evaluation | disposable/rebuildable projection | Пересчитываются из retained exact control input, assessment/generation artifacts и contract version. Cached copy не authoritative. |
| `CURRENT`/`STALE`, current review head, latest artifact lookup, indexes/counts | derived current view | disposable/rebuildable projection | Статус зависит от явно переданного current context или retained chain. Head/index не заменяет immutable revisions. |
| Operational attempt/error | не domain state | operational telemetry вне текущих ports | Timeout или crash не создаёт observation, duplicate artifact или review. Unknown commit outcome разрешается read/replay protocol. |

## Выбранная модель authority

Authoritative source publication state — это полный retained tuple observations
каждой `PublicationRef`. Текущее состояние является последним observation
только как projection; старые observations не теряют силу исторического
evidence.

Manual review authoritative только как assertion указанного reviewer code о
точной pair/assessment. Control label authoritative только как supplied label
в указанной control population. Ни одно из них не доказывает существование
`PhysicalProperty`, не объединяет histories и не делает pairwise relation
транзитивной.

Candidate, assessment и metrics не становятся authoritative из-за сохранения.
Immutable committed copy доказывает фактически использованный computation, а
не истинность его вывода.

## Общие concurrency pseudotypes

Общие building blocks допустимы, но они не образуют `Repository[T]`:

```text
PersistenceRevision(value: opaque adapter-issued token)

ExpectedRevision =
  ExpectAbsent
  | ExpectExact(revision: PersistenceRevision)

CommitDisposition = COMMITTED | REPLAYED

PersistenceOperationFailureCode =
  temporarily_unavailable
  | integrity_violation
  | outcome_unknown

PersistenceOperationFailure(
  code: PersistenceOperationFailureCode,
  subject: typed port-specific operation subject
)
```

`PersistenceRevision`:

- принадлежит одному exact stream, artifact slot или review head;
- не входит в observation/candidate/assessment/review identity;
- не является временем, sequence number предметной модели или ETag format;
- не сравнивается через `<`, `>`, newest или lexical order;
- меняется только после нового successful content commit;
- не меняется при exact replay.

`ExpectAbsent` означает «при load этот slot/head отсутствовал».
`ExpectExact(r)` означает «commit основан на exact loaded revision `r`».
Отсутствующее или неявное ожидание запрещено: нет unconditional write и
last-write-wins.

Operational `outcome_unknown` не является domain conflict и не утверждает,
что commit применён или отклонён. Consumer должен выполнить reconciliation по
structural identity; повтор с новым content запрещён до reconciliation.

## Structural equality и порядок решения commit

Full content equality использует equality существующих immutable contracts.
Object identity, memory address, serialized bytes, digest/hash, arrival order,
adapter timestamp и revision не определяют equality.

Каждая commit operation conceptually выполняет один и тот же порядок:

1. Проверить форму request, domain invariants и full lineage.
2. Найти существующий immutable record/receipt по structural identity.
3. Если identity существует и full content равен — вернуть `REPLAYED`, даже
   если request несёт revision, которая стала stale после первого commit.
4. Если identity существует и full content различается — вернуть typed
   identity/content conflict; winner не выбирать.
5. Если identity ещё не существует — проверить все expected revisions.
6. При любом mismatch вернуть atomic conflict без writes.
7. Иначе записать всю заявленную atomic unit и выдать новые revisions.

Replay-before-revision нужен для lost-response retry: первый commit мог
полностью завершиться, но caller не получил success. Это не позволяет stale
writer добавить новый content, потому что no-op доступен только при exact
identity и exact full content.

## Port ownership и направление зависимостей

Каждый port объявляется consuming application boundary рядом с use case, а не
storage module. Pure core types ничего не знают о ports. Infrastructure adapter
зависит от contracts и реализует их снаружи.

```text
source/application composition
  -> observation append application -> ObservationHistoryPort

candidate-generation application
  -> DuplicateGenerationArtifactPort

assessment-batch application
  -> DuplicateGenerationArtifactPort (read)
  -> DuplicateAssessmentArtifactPort

manual-review application
  -> DuplicateAssessmentArtifactPort (read)
  -> ManualReviewRevisionPort

quality evaluation application
  -> DuplicateQualityAuditPort
  -> pure quality operations

infrastructure adapter
  -> implements one or several ports
  -> never owns domain identity or policy
```

Один backend может реализовать все contracts и использовать одну физическую
transaction. Это implementation detail. Нельзя переносить generic
`save(entity)`, backend query model, session/transaction object или storage
schema внутрь application/core.

## ObservationHistoryPort

### Owner и reads

Port принадлежит application use case, который consumer-ом выполняет
multi-history observation append. Он загружает только явно указанные
`PublicationRef`; scan всех histories не требуется.

```text
LoadObservationHistoriesRequest(
  references: non-empty unique canonical tuple[PublicationRef, ...]
)

LoadedHistoryEntry(
  reference: PublicationRef,
  history: PublicationObservationHistory | absent,
  revision: PersistenceRevision | absent
)

LoadObservationHistoriesSuccess(
  entries: exact request-ordered tuple[LoadedHistoryEntry, ...]
)

LoadObservationHistoriesOutcome =
  LoadObservationHistoriesSuccess
  | PersistenceOperationFailure
```

Absent history имеет absent revision и позже требует `ExpectAbsent`. Existing
history сохраняет exact `comparison_policy_version`; port не выбирает policy и
не создаёт пустую history за consumer.

Для duplicate recompute отдельный exact read не выбирает current молча:

```text
LoadObservationsByKeyRequest(
  keys: non-empty unique canonical tuple[ObservationKey, ...]
)

LoadObservationsByKeySuccess(
  observations: exact key-ordered tuple[PublicationObservation, ...]
)
```

Отсутствующий key является typed read failure/integrity conflict, а не
`Missing` field и не `UnavailableObservation`.

### Commit identity и content

```text
ObservationHistoryCommitIdentity(
  comparison_policy_version: ComparisonPolicyVersion,
  candidate_keys: non-empty unique canonical tuple[ObservationKey, ...]
)

ExpectedHistoryHead(
  reference: PublicationRef,
  expected_revision: ExpectedRevision
)

ObservationHistoryCommitRequest(
  identity: ObservationHistoryCommitIdentity,
  expected_heads: non-empty reference-ordered tuple[ExpectedHistoryHead, ...],
  candidates: non-empty canonical tuple[PublicationObservation, ...],
  prepared_result: ObservationBatchAppendSuccess
)

CommittedHistoryHead(
  reference: PublicationRef,
  history: PublicationObservationHistory,
  revision: PersistenceRevision
)

ObservationHistoryCommitSuccess(
  disposition: CommitDisposition,
  heads: non-empty reference-ordered tuple[CommittedHistoryHead, ...]
)

ObservationHistoryCommitOutcome =
  ObservationHistoryCommitSuccess
  | ObservationHistoryCommitFailure
  | PersistenceOperationFailure

ObservationHistoryCommitFailure(
  conflicts: non-empty unique canonical
             tuple[ObservationPersistenceConflict, ...]
)
```

Identity использует canonical unique candidate keys после exact duplicate
collapse pure batch semantics. Full content включает exact full candidates,
prepared histories, dispositions и `ChangeSet`; same keys с иным content дают
content conflict.

`expected_heads` содержит ровно streams, которые pure result намерен изменить
или подтвердить replay-ом. Каждый reference обязан встречаться в candidates и
prepared result. Consumer сначала строит initial
`PublicationObservationHistories` из load, вызывает existing
`append_observation_batch`, а затем передаёт только complete success. Port не
сравнивает observations скрытой policy и не принимает pure failure.

### Atomic unit

Одна unit содержит:

- все новые immutable observations всех затронутых references;
- новые complete history snapshots/head revisions;
- все prepared item outcomes и `ChangeSet`, если они сохраняются как audit;
- immutable `ObservationHistoryCommitReceipt` по commit identity и full
  content, включая post-revisions.

Все streams и receipt становятся видимы вместе либо не меняется ничего.
Нельзя применить conflict-free prefix, один stream, один `ChangeSet` или только
receipt. Exact replay читает receipt и возвращает сохранённые heads без новой
revision.

Normal port не поддерживает out-of-order backfill. `out_of_order_observation`
из pure operation не достигает commit. Изменить authoritative timeline через
редактирование history snapshot или прямую вставку запрещено.

## DuplicateGenerationArtifactPort

Port принадлежит candidate-generation application. Identity уже определена
ADR 0008 и не расширяется storage revision.

```text
LoadDuplicateGenerationRequest(
  identity: DuplicateCandidateGenerationIdentity
)

LoadedDuplicateGeneration =
  GenerationFound(
    result: DuplicateCandidateGenerationResult,
    revision: PersistenceRevision
  )
  | GenerationNotFound
  | PersistenceOperationFailure

CommitDuplicateGenerationRequest(
  expected_revision: ExpectedRevision,
  result: DuplicateCandidateGenerationResult
)

CommitDuplicateGenerationSuccess(
  disposition: CommitDisposition,
  result: DuplicateCandidateGenerationResult,
  revision: PersistenceRevision
)

CommitDuplicateGenerationFailure(
  conflicts: non-empty unique canonical
             tuple[DuplicateGenerationPersistenceConflict, ...]
)

CommitDuplicateGenerationOutcome =
  CommitDuplicateGenerationSuccess
  | CommitDuplicateGenerationFailure
  | PersistenceOperationFailure
```

Atomic unit — один полный result: identity, full candidate policy, bucket
limit, canonical input keys, candidates/matches, non-participations и
oversized buckets. Partial candidates или отдельные buckets не сохраняются.

First commit обычно использует `ExpectAbsent`. Equal generation identity с
exact equal result — replay. Equal identity с иным full result —
`generation_identity_content_conflict`, независимо от revision.

Generation result не содержит full input observations. Для exact recompute
consumer загружает их из `ObservationHistoryPort` по
`identity.canonical_input_keys`; adapter не восстанавливает content из keys,
blocking matches или snapshots.

## DuplicateAssessmentArtifactPort

Port принадлежит assessment-batch application. Он предоставляет exact batch
read и exact pair-assessment read для manual-review consumer; он не выполняет
assessment.

```text
LoadDuplicateAssessmentBatchRequest(
  identity: DuplicateCandidateAssessmentBatchIdentity
)

LoadedDuplicateAssessmentBatch =
  AssessmentBatchFound(
    batch: DuplicateCandidateAssessmentBatch,
    revision: PersistenceRevision
  )
  | AssessmentBatchNotFound
  | PersistenceOperationFailure

LoadDuplicatePairAssessmentRequest(
  identity: DuplicateAssessmentIdentity
)

LoadedDuplicatePairAssessment =
  PairAssessmentFound(assessment: DuplicatePairAssessment)
  | PairAssessmentNotFound
  | PersistenceOperationFailure
```

Pair read обязан вернуть ровно один structurally equal assessment. Два разных
contents одной identity являются integrity violation, а не arbitrary winner.

```text
CommitDuplicateAssessmentBatchRequest(
  expected_generation_revision: ExpectedRevision,
  expected_batch_revision: ExpectedRevision,
  batch: DuplicateCandidateAssessmentBatch
)

CommitDuplicateAssessmentBatchSuccess(
  disposition: CommitDisposition,
  generation_revision: PersistenceRevision,
  batch_revision: PersistenceRevision,
  batch: DuplicateCandidateAssessmentBatch
)

CommitDuplicateAssessmentBatchFailure(
  conflicts: non-empty unique canonical
             tuple[DuplicateAssessmentPersistenceConflict, ...]
)

CommitDuplicateAssessmentBatchOutcome =
  CommitDuplicateAssessmentBatchSuccess
  | CommitDuplicateAssessmentBatchFailure
  | PersistenceOperationFailure
```

Atomic unit включает:

- exact embedded `batch.generation_result`, который должен быть equal уже
  сохранённому generation artifact либо сохраняется вместе с batch;
- полный batch identity, assessment policy и все item outcomes;
- все exact pair assessments/evidence, доступные по их identities;
- batch receipt/revisions.

Generation artifact может существовать без assessment batch. Assessment batch
не может стать видимым без exact generation artifact. Если generation slot
имеет equal identity/different content, весь commit отклоняется. Если batch
conflict возникает после проверки generation, generation также не изменяется.
Failure не сохраняет successful pair prefix.

Explicit `AssessmentSupersession` сохраняется отдельной immutable link unit
этого порта только после проверки существования обеих exact assessment
identities. Replay equal link — no-op; competing replacement — conflict.
Link не меняет и не удаляет assessments.

## ManualReviewRevisionPort

Port принадлежит manual-review application, которое до commit загружает exact
assessment и текущую chain. Review code не является именем человека и не
создаётся adapter-ом.

```text
LoadManualReviewChainRequest(
  review_reference_code: ReviewReferenceCode
)

LoadManualReviewChainSuccess(
  revisions: canonical tuple[DuplicatePairManualReview, ...],
  head: DuplicatePairManualReview | absent,
  head_revision: PersistenceRevision | absent
)

CommitManualReviewRevisionRequest(
  expected_head_revision: ExpectedRevision,
  review: DuplicatePairManualReview,
  bound_assessment: DuplicatePairAssessment
)

CommitManualReviewRevisionSuccess(
  disposition: CommitDisposition,
  review: DuplicatePairManualReview,
  head_revision: PersistenceRevision
)

CommitManualReviewRevisionFailure(
  conflicts: non-empty unique canonical
             tuple[ManualReviewPersistenceConflict, ...]
)

CommitManualReviewRevisionOutcome =
  CommitManualReviewRevisionSuccess
  | CommitManualReviewRevisionFailure
  | PersistenceOperationFailure
```

Atomic unit — новая immutable review revision, её exact assessment/finding
binding, `supersedes` edge и обновление head projection. Revision `1` требует
`ExpectAbsent`; следующая revision требует exact loaded head token и existing
previous review. Port повторяет structural invariants existing pure
`create_manual_review`, но не создаёт timestamps, codes или outcome.

Equal `ManualReviewIdentity`/equal full content — replay. Equal identity с иным
content — `review_identity_content_conflict`. Две different revisions,
superseding одну previous, дают `review_revision_fork`; arrival time и
`reviewed_at` не выбирают winner. При failure previous chain и head неизменны.

## DuplicateQualityAuditPort

Port принадлежит quality-evaluation application. Он нужен только когда
evaluation используется как durable audit evidence. Online executor
candidate/assessment не зависит от него.

Existing control contracts не имеют revision identity для relabeling, поэтому
persistence envelope требует supplied stable audit coordinates, не изменяя
сам `DuplicatePolicyControlSet`:

```text
QualityAuditReferenceCode(value: supplied stable safe opaque ASCII code)

QualityAuditIdentity(
  reference_code: QualityAuditReferenceCode,
  revision: positive integer
)

DuplicateQualityAuditInput(
  identity: QualityAuditIdentity,
  control_set: DuplicatePolicyControlSet,
  generation_result: DuplicateCandidateGenerationResult | absent
)

CommitDuplicateQualityAuditRequest(
  expected_head_revision: ExpectedRevision,
  input: DuplicateQualityAuditInput
)

CommitDuplicateQualityAuditSuccess(
  disposition: CommitDisposition,
  input: DuplicateQualityAuditInput,
  head_revision: PersistenceRevision
)

CommitDuplicateQualityAuditFailure(
  conflicts: non-empty unique canonical
             tuple[DuplicateQualityPersistenceConflict, ...]
)

CommitDuplicateQualityAuditOutcome =
  CommitDuplicateQualityAuditSuccess
  | CommitDuplicateQualityAuditFailure
  | PersistenceOperationFailure
```

Atomic immutable audit input сохраняет full cases, supplied labels, exact pair
results, policy version и, для blocking coverage, full generation result.
Metrics/coverage не являются required persisted records: они пересчитываются
pure operations. Cached output имеет projection status и никогда не
заменяет audit input.

Revision `n` supersedes только `n-1` того же audit reference через explicit
envelope lineage. Relabel или новая population получают новую audit revision;
старый input не переписывается. TASK-027 может реализовать этот narrow port,
не добавляя новые core quality policies или external schemas.

## Lineage, policy и version coordinates

Чтобы exact recompute и аудит были возможны, retained record содержит не
только «результат», но все уже существующие structural coordinates:

| Record | Обязательные coordinates |
| --- | --- |
| Observation | `PublicationRef`, canonical `ObservedAt`, full listing или unavailable evidence, все provenance/rule versions |
| History commit | comparison policy version, canonical candidate keys и full observations, expected subjects, complete batch result, post-revisions |
| Change audit | `from_key`, `to_key`, comparison policy version, full deltas/evidence |
| Generation | candidate policy full configuration/version, bucket limit, canonical input keys, full result |
| Assessment batch | exact generation identity/result, assessment policy full configuration/version, batch/item identities, full observations/evidence |
| Assessment supersession | previous/replacement assessment identities |
| Manual review | review identity/revision, exact assessment identity/content, supplied reviewed time/reviewer/rationale/finding references, supersedes |
| Quality audit input | supplied audit identity/revision, full control set/policy/results/labels, exact generation result when coverage is evaluated |

Adapter metadata may record its own format version, но оно не заменяет domain
policy/version и не входит в structural replay equality, если application
contract явно этого не требует.

## Minimal read requirements будущего side-effecting executor

Документ не проектирует executor, но ports обязаны позволить ему выполнить
следующий bounded набор reads:

1. Загрузить exact set histories по references candidates, получив history или
   absence и per-stream revisions одним consistent read result.
2. Загрузить full observations по exact keys для generation recompute и
   assessment binding; «latest» без caller-selected keys недостаточно.
3. Загрузить generation artifact по exact generation identity, включая full
   configuration/content и revision либо unambiguous absence.
4. Загрузить assessment batch по exact batch identity и отдельную pair
   assessment по exact identity для review binding.
5. Загрузить full manual-review chain/head по supplied review reference и exact
   head revision.
6. Для quality workflow загрузить exact immutable audit input revision; metrics
   могут быть пересчитаны и не требуют authoritative cache read.

Ни один read не должен выбирать newest artifact across policy versions,
скрывать stale status, возвращать partial multi-history snapshot или
подменять absent record пустым success object.

## Stable persistence conflict taxonomy

### Categories

```text
OBSERVATION_PERSISTENCE_CONFLICT
DUPLICATE_GENERATION_PERSISTENCE_CONFLICT
DUPLICATE_ASSESSMENT_PERSISTENCE_CONFLICT
MANUAL_REVIEW_PERSISTENCE_CONFLICT
DUPLICATE_QUALITY_PERSISTENCE_CONFLICT
```

### Common structural subjects

```text
ExpectedRevisionSubject(
  slot: port-specific structural slot identity,
  expected: ExpectedRevision,
  actual: PersistenceRevision | absent
)

IdentityContentSubject(
  identity: port-specific structural identity
)

DependencyArtifactSubject(
  required_identity: generation | assessment identity
)

AtomicUnitSubject(
  identity: commit | batch | review | quality audit identity
)
```

Revision tokens могут быть возвращены как opaque values для следующего
compare-and-commit; они не интерпретируются и не сортируются по содержимому.

### Codes и required subjects

| Category | Code | Subject | Смысл |
| --- | --- | --- | --- |
| Observation | `commit_identity_content_conflict` | `ObservationHistoryCommitIdentity` | equal commit identity имеет иной candidates/result content |
| Observation | `expected_revision_mismatch` | expected subject каждого conflicting stream | хотя бы один history head изменился либо absence больше не верна |
| Observation | `prepared_history_mismatch` | atomic unit + `PublicationRef` | prepared result не является exact complete transform loaded subjects |
| Observation | `unsupported_out_of_order_commit` | exact `ObservationKey` | normal port не принимает backfill/correction bypass |
| Generation | `generation_identity_content_conflict` | generation identity | equal identity имеет иной full result |
| Generation | `expected_revision_mismatch` | generation slot expected subject | slot state отличается от loaded state |
| Assessment | `batch_identity_content_conflict` | batch identity | equal batch identity имеет иной full content |
| Assessment | `item_identity_content_conflict` | item identity | equal item identity имеет иной candidate/assessment content |
| Assessment | `generation_dependency_content_conflict` | generation identity | stored generation под equal identity отличается |
| Assessment | `expected_revision_mismatch` | generation или batch slot expected subject | один из atomic subjects stale |
| Assessment | `assessment_supersession_conflict` | exact supersession link | previous имеет competing replacement либо pair mismatch |
| Manual review | `review_identity_content_conflict` | manual review identity | equal identity имеет иной full review |
| Manual review | `review_revision_mismatch` | review identity/expected head | revision не является exact следующим шагом |
| Manual review | `review_revision_fork` | previous review identity | competing children одной previous revision |
| Manual review | `review_assessment_mismatch` | review identity + assessment identity | assessment/findings binding не exact |
| Manual review | `expected_revision_mismatch` | review-head expected subject | head изменился после load |
| Quality | `audit_identity_content_conflict` | quality audit identity | equal audit identity имеет иной control/generation content |
| Quality | `audit_revision_fork` | previous quality audit identity | competing next revisions |
| Quality | `expected_revision_mismatch` | quality-head expected subject | audit head изменился после load |

Domain conflicts из ADR 0005/0006/0008/0009 сохраняют свои исходные category,
code и subject и возникают до persistence commit. Port не переименовывает
`timestamp_content_conflict`, `out_of_order_observation`,
`candidate_identity_content_conflict` или batch preflight failures в
operational error.

### Canonical ordering

Внутри одного failure exact duplicate conflicts сворачиваются. Порядок:

1. category position: observation, generation, assessment, manual review,
   quality;
2. code position в таблице каждой category;
3. existing subject order соответствующего domain contract:
   `PublicationRef`/`ObservationKey`, generation identity/candidate identity,
   batch/item identity, canonical pair/assessment identity, review reference и
   positive revision, quality reference и positive revision;
4. для нескольких expected-revision subjects — exact port slot order;
5. category и code как финальный deterministic tie-breaker.

`PublicationRef` и `ObservationKey` используют existing source/publication/time
order. Pair, candidate, generation, batch, item и review coordinates используют
порядок ADR 0006/0008/0009; locale, hash, backend row id и arrival order не
добавляются.

Один conflict в atomic unit исключает весь success. Failure не содержит
provisional histories, candidates, pair results, review head или metrics.

## Retry, crash и concurrent writers

### Обычный повторный запуск

Consumer повторяет full deterministic command с теми же exact inputs и policy.
Если artifact уже committed exact, port возвращает `REPLAYED`; повторный pure
calculation допустим, но не обязателен после exact load.

### Crash до commit

Ни одна часть atomic unit не видима. Load по identity возвращает absence и
прежние revisions; тот же request может быть повторён.

### Crash во время или после commit

Port гарантирует только два observable состояния: вся unit отсутствует либо
вся unit присутствует с receipt/revisions. Если caller получил
`outcome_unknown` или был прерван без ответа, он загружает exact identity:

- exact content найден — считать replay, не писать повторно;
- identity найдена с другим content — content conflict;
- identity отсутствует и expected subjects всё ещё равны — повторить exact
  request;
- identity отсутствует, но revisions stale — reload и recompute.

### Stale read

Новая identity/content на основании stale history/artifact state не
записывается. `expected_revision_mismatch` возвращает все independently known
conflicting subjects. Consumer не заменяет expected token текущим без нового
load и повторного pure computation.

### Concurrent writers

- Same identity + same content: один writer commit, остальные `REPLAYED`.
- Same identity + different content: один content может быть уже committed;
  остальные получают content conflict, не overwrite.
- Different observation commit identities, одна expected stream revision:
  максимум одна atomic unit commits; другая получает revision mismatch по всей
  своей unit и пересчитывается после reload.
- Две next manual-review revisions от одного head: максимум одна commits;
  другая получает fork/revision conflict. `reviewed_at` не выбирает winner.
- Независимые slots могут commit независимо, если port unit не связывает их;
  adapter не создаёт скрытую global ordering guarantee.

## Recompute, backfill и supersession

### Same identity recompute

Full inputs и full policy/configuration той же identity должны дать exact equal
content. Equal result — no-op. Different result — integrity/content conflict,
который требует расследования версии кода или нарушенного input, а не
автоматического исправления stored artifact.

### New policy/configuration

Новая candidate policy, bucket limit, observation key либо assessment policy
создаёт новую structural generation/batch identity. Старый artifact остаётся
audit record. Новая assessment не делает старую superseded автоматически;
`AssessmentSupersession` записывается явно.

Новая comparison policy не переписывает existing observation history и
`ChangeSet`. Existing normal append contract хранит одну policy version в
history. Separate multi-policy change projection или migration требует нового
ADR; authoritative observations уже retained и дают для него input.

### Derived backfill

Можно materialize ранее отсутствующий generation/assessment/quality artifact
для исторических exact keys, если все full observations и policy/configuration
доступны. Он получает обычную structural identity и проходит те же
replay/content checks. «Backfill» не разрешает изменить старый artifact.

### Observation correction/backfill

Новый неизвестный observation key раньше tail остаётся
`out_of_order_observation`. Port не имеет bypass operation. Исправление
accepted authoritative observation, импорт старой записи или recompute всей
timeline требуют отдельной correction identity, lineage, audit и ADR. До этого
они не выполняются.

## Retention

Routine code никогда автоматически не удаляет и не переписывает:

- committed available/unavailable observations и их provenance/evidence;
- immutable history commit receipts и retained historical snapshots;
- committed generation results, assessment batches, pair evidence и explicit
  supersession links;
- manual-review revisions и их chain edges;
- quality audit inputs/labels, если по ним был сохранён или опубликован вывод;
- policy/configuration/version coordinates, exact input identities и binding.

Можно удалить и построить снова:

- history head/current-state index из retained observations/receipts;
- `CURRENT`/`STALE` views и latest-by-policy indexes;
- quality metrics и blocking coverage из exact audit inputs;
- search/cache indexes и cached serialized/materialized views;
- transient generated artifacts, которые никогда не были committed и не
  участвовали в side effect.

Rebuild обязан проверять equality retained audit artifact. Projection может
заменить собственную предыдущую projection, но не immutable audit record.
Автоматическая garbage collection committed evidence запрещена. Сроки,
архивный tier, legal hold, user deletion и physical erasure остаются отдельной
retention/security задачей.

## Полностью вымышленная scenario matrix

Все examples используют только `fixture_portal`, `mirror_fixture`, `.example`
и synthetic codes. Они не описывают реальные объекты или людей.

| Сценарий | Вход и сохранённое состояние | Ожидаемый результат |
| --- | --- | --- |
| First history write | `fixture_portal/demo-a@10:00`, history отсутствует, `ExpectAbsent` | одна multi-history unit `COMMITTED`; observation, history head и receipt видимы вместе |
| Exact history retry | тот же commit identity, full observation/result и старый `ExpectAbsent` после lost response | `REPLAYED`; revision не меняется, duplicate observation отсутствует |
| Stale revision | writer загрузил history revision `r1`, другой writer уже committed новый key и получил `r2` | `expected_revision_mismatch(actual=r2)`; ни один stream request не меняется |
| Concurrent equal writers | два writers посылают exact equal generation result с `ExpectAbsent` | один `COMMITTED`, второй `REPLAYED`; один immutable artifact |
| Concurrent different writers | два history commits используют одну expected revision, но разные новые keys | максимум один full commit; второй atomic revision conflict, без partial history |
| History append conflict | batch содержит `demo-a@11:00` с content, отличным от уже принятого exact key | pure `timestamp_content_conflict`; port commit не вызывается, state неизменно |
| Multi-history atomic failure | `demo-a` expected revision верна, `demo-b` stale | весь A/B commit отклонён; `demo-a` также не получает observation или receipt |
| Generation identity/content conflict | stored generation `G` и recompute имеют equal identity, но иной candidate tuple | `generation_identity_content_conflict`; stored `G` не переписан |
| Assessment batch identity/content conflict | equal batch identity, но assessment evidence/item content различается | `batch_identity_content_conflict` и при необходимости item conflict в canonical order; no overwrite |
| Generation/assessment atomicity | embedded generation отсутствует, batch valid, attempt прерывается | после recovery видимы либо generation+full batch, либо ничего; generation-only partial от этой unit невозможна |
| Manual-review first revision | supplied review `review-demo/1`, exact assessment, no head, `ExpectAbsent` | review, chain edge absence и new head committed одной unit |
| Manual-review exact retry | exact revision 1 повторена после lost response | `REPLAYED`; новая head revision не создаётся |
| Manual-review revision conflict | writers создают разные revision 2, обе supersede revision 1 | одна commits; другая получает `review_revision_fork`/revision mismatch; revision 1 сохранена |
| Recompute новой policy version | те же observation keys, candidate policy `@2` либо assessment policy `@2` | новая generation/batch identity и новый immutable artifact; `@1` сохранён, supersession только explicit |
| Derived historical backfill | old exact keys retained, generation artifact отсутствует, full old policy доступна | artifact может быть committed под своей exact identity; histories не меняются |
| Forbidden observation backfill | tail `12:00`, неизвестный observation `11:00` | `out_of_order_observation`; persistence bypass отсутствует |
| Interrupted before commit | process остановлен до atomic boundary | identity absent, revisions прежние, state полностью прежнее |
| Interrupted after commit before response | full unit committed, response потерян | load находит exact receipt/content; retry возвращает `REPLAYED` |
| Interrupted indeterminate | adapter возвращает `outcome_unknown` | caller не предполагает rollback; exact read/reconcile обязателен до нового content |
| No partial assessment state | третий pair outcome invalid в batch | pure batch failure либо commit failure не сохраняет первые два pair outcomes |
| Quality rebuild | cached `2/4` coverage удалена, exact control audit input и generation retained | pure evaluation строит exact equal `2/4`; audit input не меняется |
| Projection rebuild conflict | rebuild metrics отличается при тех же exact inputs/contract | integrity incident; cached value не становится authoritative winner |
| Explicit assessment supersession | new assessment identity той же pair committed, supplied link указывает old → new | обе assessments и immutable link сохранены; old не удалена |
| Stale without supersession | current key изменился, old assessment retained, link отсутствует | old assessment вычисляется как `STALE`; supersession не изобретается |

## Намеренно отсутствует

- Python protocols/classes, implementation, exports и tests — TASK-027;
- SQL/JSON/filesystem schema, ORM, migrations и durable adapter;
- database transaction API, cache, queue, scheduler, distributed lock и
  retry/backoff policy;
- side-effecting executor/orchestrator и end-to-end ingestion run;
- изменение observation/candidate/assessment/manual-review contracts или
  policies;
- raw/source capture port и legal retention/deletion policy;
- correction/out-of-order observation workflow и multi-policy history
  migration;
- real data, HTTP, scraping, source adapter и юридические решения;
- API, CLI, UI, AI, OpenClaw, Telegram и notifications;
- physical property, merge/collapse/hide, clustering и transitive semantics.

## Следующая рекомендуемая задача

TASK-027 — реализовать neutral Python port contracts и deterministic in-memory
reference adapter по ADR 0010 с exact replay, optimistic revision и atomic
failures, без SQL/JSON/filesystem/CLI/real data и без side-effecting production
executor.
