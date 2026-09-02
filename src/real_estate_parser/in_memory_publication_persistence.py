"""Deterministic in-memory reference adapter for publication persistence ports."""

from dataclasses import dataclass

from real_estate_parser.publication_duplicate_assessment_batches import (
    DuplicateCandidateAssessmentBatch,
    DuplicateCandidateAssessmentBatchIdentity,
)
from real_estate_parser.publication_duplicate_assessments import (
    AssessmentSupersession,
    DuplicateAssessmentIdentity,
    DuplicatePairAssessment,
    DuplicatePairManualReview,
    ManualReviewIdentity,
    ReviewReferenceCode,
)
from real_estate_parser.publication_duplicate_candidates import (
    DuplicateCandidateGenerationIdentity,
    DuplicateCandidateGenerationResult,
)
from real_estate_parser.publication_observation_batches import ObservationBatchAppendSuccess
from real_estate_parser.publication_observations import (
    ObservationAppendDisposition,
    ObservationKey,
    PublicationObservation,
    PublicationObservationHistory,
)
from real_estate_parser.publication_persistence import (
    AssessmentBatchFound,
    AssessmentBatchIdentityContentSubject,
    AssessmentBatchNotFound,
    AssessmentExpectedRevisionSubject,
    AssessmentGenerationDependencySubject,
    AssessmentItemIdentityContentSubject,
    CommitAssessmentSupersessionOutcome,
    CommitAssessmentSupersessionRequest,
    CommitAssessmentSupersessionSuccess,
    CommitDisposition,
    CommitDuplicateAssessmentBatchFailure,
    CommitDuplicateAssessmentBatchOutcome,
    CommitDuplicateAssessmentBatchRequest,
    CommitDuplicateAssessmentBatchSuccess,
    CommitDuplicateGenerationFailure,
    CommitDuplicateGenerationOutcome,
    CommitDuplicateGenerationRequest,
    CommitDuplicateGenerationSuccess,
    CommitDuplicateQualityAuditFailure,
    CommitDuplicateQualityAuditOutcome,
    CommitDuplicateQualityAuditRequest,
    CommitDuplicateQualityAuditSuccess,
    CommitManualReviewRevisionFailure,
    CommitManualReviewRevisionOutcome,
    CommitManualReviewRevisionRequest,
    CommitManualReviewRevisionSuccess,
    CommittedHistoryHead,
    DuplicateAssessmentPersistenceConflict,
    DuplicateAssessmentPersistenceConflictCode,
    DuplicateGenerationPersistenceConflict,
    DuplicateGenerationPersistenceConflictCode,
    DuplicateQualityAuditInput,
    DuplicateQualityPersistenceConflict,
    DuplicateQualityPersistenceConflictCode,
    ExpectAbsent,
    ExpectedRevision,
    ExpectExact,
    GenerationExpectedRevisionSubject,
    GenerationFound,
    GenerationIdentityContentSubject,
    GenerationNotFound,
    LoadDuplicateAssessmentBatchRequest,
    LoadDuplicateGenerationRequest,
    LoadDuplicatePairAssessmentRequest,
    LoadDuplicateQualityAuditRequest,
    LoadedDuplicateAssessmentBatch,
    LoadedDuplicateGeneration,
    LoadedDuplicateQualityAudit,
    LoadedHistoryEntry,
    LoadManualReviewChainRequest,
    LoadManualReviewChainSuccess,
    LoadObservationHistoriesRequest,
    LoadObservationHistoriesSuccess,
    LoadObservationsByKeyRequest,
    LoadObservationsByKeySuccess,
    ManualReviewAssessmentSubject,
    ManualReviewExpectedRevisionSubject,
    ManualReviewPersistenceConflict,
    ManualReviewPersistenceConflictCode,
    ObservationExpectedRevisionSubject,
    ObservationHistoryCommitFailure,
    ObservationHistoryCommitIdentity,
    ObservationHistoryCommitOutcome,
    ObservationHistoryCommitRequest,
    ObservationHistoryCommitSuccess,
    ObservationIdentityContentSubject,
    ObservationPersistenceConflict,
    ObservationPersistenceConflictCode,
    ObservationPreparedHistorySubject,
    PairAssessmentFound,
    PairAssessmentNotFound,
    PersistenceRevision,
    QualityAuditFound,
    QualityAuditIdentity,
    QualityAuditNotFound,
    QualityAuditReferenceCode,
    QualityExpectedRevisionSubject,
    _issue_persistence_revision,
    _persistence_revision_issuer,
)
from real_estate_parser.source_batch import PublicationRef


@dataclass(frozen=True, slots=True)
class _ObservationReceipt:
    candidates: tuple[PublicationObservation, ...]
    prepared_result: ObservationBatchAppendSuccess
    heads: tuple[CommittedHistoryHead, ...]


@dataclass(frozen=True, slots=True)
class _GenerationRecord:
    result: DuplicateCandidateGenerationResult
    revision: PersistenceRevision


@dataclass(frozen=True, slots=True)
class _BatchRecord:
    batch: DuplicateCandidateAssessmentBatch
    revision: PersistenceRevision


@dataclass(frozen=True, slots=True)
class _QualityRecord:
    input: DuplicateQualityAuditInput
    head_revision: PersistenceRevision


def _expectation_matches(
    expected: ExpectedRevision,
    actual: PersistenceRevision | None,
) -> bool:
    if isinstance(expected, ExpectAbsent):
        return actual is None
    return isinstance(expected, ExpectExact) and expected.revision == actual


class InMemoryPublicationPersistence:
    """Reference implementation of all five narrow persistence ports.

    Tokens are deterministic adapter-issued counters.  The counter is only an
    opaque concurrency mechanism: it never enters a domain identity and is not
    derived from a clock, UUID, random value, hash, or domain timestamp.
    """

    def __init__(self) -> None:
        self._next_revision = 1
        self._revision_issuer = _persistence_revision_issuer()
        self._history_heads: dict[
            PublicationRef, tuple[PublicationObservationHistory, PersistenceRevision]
        ] = {}
        self._observations: dict[ObservationKey, PublicationObservation] = {}
        self._observation_receipts: dict[ObservationHistoryCommitIdentity, _ObservationReceipt] = {}
        self._generations: dict[DuplicateCandidateGenerationIdentity, _GenerationRecord] = {}
        self._batches: dict[DuplicateCandidateAssessmentBatchIdentity, _BatchRecord] = {}
        self._assessments: dict[DuplicateAssessmentIdentity, DuplicatePairAssessment] = {}
        self._supersessions: dict[DuplicateAssessmentIdentity, AssessmentSupersession] = {}
        self._reviews: dict[
            ManualReviewIdentity, tuple[DuplicatePairManualReview, PersistenceRevision]
        ] = {}
        self._review_heads: dict[
            ReviewReferenceCode, tuple[DuplicatePairManualReview, PersistenceRevision]
        ] = {}
        self._quality_inputs: dict[QualityAuditIdentity, _QualityRecord] = {}
        self._quality_heads: dict[
            QualityAuditReferenceCode, tuple[QualityAuditIdentity, PersistenceRevision]
        ] = {}

    def _issue_revision(self) -> PersistenceRevision:
        revision = _issue_persistence_revision(
            self._next_revision,
            issuer=self._revision_issuer,
        )
        self._next_revision += 1
        return revision

    def load_histories(
        self,
        request: LoadObservationHistoriesRequest,
    ) -> LoadObservationHistoriesSuccess:
        entries: list[LoadedHistoryEntry] = []
        for reference in request.references:
            record = self._history_heads.get(reference)
            if record is None:
                entries.append(LoadedHistoryEntry(reference, None, None))
            else:
                entries.append(LoadedHistoryEntry(reference, record[0], record[1]))
        return LoadObservationHistoriesSuccess(tuple(entries))

    def load_observations_by_key(
        self,
        request: LoadObservationsByKeyRequest,
    ) -> LoadObservationsByKeySuccess | ObservationHistoryCommitFailure:
        missing = tuple(key for key in request.keys if key not in self._observations)
        if missing:
            return ObservationHistoryCommitFailure(
                tuple(
                    ObservationPersistenceConflict(
                        "OBSERVATION_PERSISTENCE_CONFLICT",
                        ObservationPersistenceConflictCode.OBSERVATION_NOT_FOUND,
                        key,
                    )
                    for key in missing
                )
            )
        return LoadObservationsByKeySuccess(tuple(self._observations[key] for key in request.keys))

    def commit_histories(
        self,
        request: ObservationHistoryCommitRequest,
    ) -> ObservationHistoryCommitOutcome:
        receipt = self._observation_receipts.get(request.identity)
        if receipt is not None:
            if (
                receipt.candidates == request.candidates
                and receipt.prepared_result == request.prepared_result
            ):
                return ObservationHistoryCommitSuccess(
                    CommitDisposition.REPLAYED,
                    receipt.heads,
                )
            return ObservationHistoryCommitFailure(
                (
                    ObservationPersistenceConflict(
                        "OBSERVATION_PERSISTENCE_CONFLICT",
                        ObservationPersistenceConflictCode.COMMIT_IDENTITY_CONTENT_CONFLICT,
                        ObservationIdentityContentSubject(request.identity),
                    ),
                )
            )

        revision_conflicts: list[ObservationPersistenceConflict] = []
        for expected_head in request.expected_heads:
            current = self._history_heads.get(expected_head.reference)
            actual = None if current is None else current[1]
            if not _expectation_matches(expected_head.expected_revision, actual):
                revision_conflicts.append(
                    ObservationPersistenceConflict(
                        "OBSERVATION_PERSISTENCE_CONFLICT",
                        ObservationPersistenceConflictCode.EXPECTED_REVISION_MISMATCH,
                        ObservationExpectedRevisionSubject(
                            expected_head.reference,
                            expected_head.expected_revision,
                            actual,
                        ),
                    )
                )
        if revision_conflicts:
            return ObservationHistoryCommitFailure(tuple(revision_conflicts))

        prepared_by_reference = {
            history.reference: history for history in request.prepared_result.histories.histories
        }
        outcomes_by_key = {outcome.key: outcome for outcome in request.prepared_result.outcomes}
        candidates_by_reference: dict[PublicationRef, list[PublicationObservation]] = {}
        for candidate in request.candidates:
            candidates_by_reference.setdefault(candidate.key.reference, []).append(candidate)

        lineage_conflicts: list[ObservationPersistenceConflict] = []
        for expected_head in request.expected_heads:
            reference = expected_head.reference
            current_record = self._history_heads.get(reference)
            current_history = None if current_record is None else current_record[0]
            current_observations = () if current_history is None else current_history.observations
            if (
                current_history is not None
                and current_history.comparison_policy_version
                != request.identity.comparison_policy_version
            ):
                lineage_conflicts.append(self._prepared_mismatch(request, reference))
                continue

            observations = list(current_observations)
            by_key = {observation.key: observation for observation in observations}
            invalid = False
            for candidate in candidates_by_reference[reference]:
                existing = by_key.get(candidate.key)
                outcome = outcomes_by_key[candidate.key]
                if existing is not None:
                    if (
                        existing != candidate
                        or outcome.disposition is not ObservationAppendDisposition.REPLAYED
                    ):
                        invalid = True
                    continue
                if observations and (
                    candidate.key.observed_at.value <= observations[-1].key.observed_at.value
                ):
                    lineage_conflicts.append(
                        ObservationPersistenceConflict(
                            "OBSERVATION_PERSISTENCE_CONFLICT",
                            ObservationPersistenceConflictCode.UNSUPPORTED_OUT_OF_ORDER_COMMIT,
                            candidate.key,
                        )
                    )
                    invalid = True
                    continue
                if outcome.disposition is not ObservationAppendDisposition.APPENDED:
                    invalid = True
                observations.append(candidate)
                by_key[candidate.key] = candidate
            prepared = prepared_by_reference[reference]
            expected_history = PublicationObservationHistory(
                reference,
                request.identity.comparison_policy_version,
                tuple(observations),
            )
            if invalid or prepared != expected_history:
                lineage_conflicts.append(self._prepared_mismatch(request, reference))
        if lineage_conflicts:
            return ObservationHistoryCommitFailure(tuple(lineage_conflicts))

        heads = tuple(
            CommittedHistoryHead(
                expected.reference,
                prepared_by_reference[expected.reference],
                self._issue_revision(),
            )
            for expected in request.expected_heads
        )
        for head in heads:
            self._history_heads[head.reference] = (head.history, head.revision)
        for candidate in request.candidates:
            self._observations[candidate.key] = candidate
        self._observation_receipts[request.identity] = _ObservationReceipt(
            request.candidates,
            request.prepared_result,
            heads,
        )
        return ObservationHistoryCommitSuccess(CommitDisposition.COMMITTED, heads)

    @staticmethod
    def _prepared_mismatch(
        request: ObservationHistoryCommitRequest,
        reference: PublicationRef,
    ) -> ObservationPersistenceConflict:
        return ObservationPersistenceConflict(
            "OBSERVATION_PERSISTENCE_CONFLICT",
            ObservationPersistenceConflictCode.PREPARED_HISTORY_MISMATCH,
            ObservationPreparedHistorySubject(request.identity, reference),
        )

    def load_generation(
        self,
        request: LoadDuplicateGenerationRequest,
    ) -> LoadedDuplicateGeneration:
        record = self._generations.get(request.identity)
        if record is None:
            return GenerationNotFound()
        return GenerationFound(record.result, record.revision)

    def commit_generation(
        self,
        request: CommitDuplicateGenerationRequest,
    ) -> CommitDuplicateGenerationOutcome:
        identity = request.result.identity
        record = self._generations.get(identity)
        if record is not None:
            if record.result == request.result:
                return CommitDuplicateGenerationSuccess(
                    CommitDisposition.REPLAYED,
                    record.result,
                    record.revision,
                )
            return CommitDuplicateGenerationFailure(
                (
                    DuplicateGenerationPersistenceConflict(
                        "DUPLICATE_GENERATION_PERSISTENCE_CONFLICT",
                        DuplicateGenerationPersistenceConflictCode.GENERATION_IDENTITY_CONTENT_CONFLICT,
                        GenerationIdentityContentSubject(identity),
                    ),
                )
            )
        if not _expectation_matches(request.expected_revision, None):
            return CommitDuplicateGenerationFailure(
                (
                    DuplicateGenerationPersistenceConflict(
                        "DUPLICATE_GENERATION_PERSISTENCE_CONFLICT",
                        DuplicateGenerationPersistenceConflictCode.EXPECTED_REVISION_MISMATCH,
                        GenerationExpectedRevisionSubject(
                            identity,
                            request.expected_revision,
                            None,
                        ),
                    ),
                )
            )
        revision = self._issue_revision()
        self._generations[identity] = _GenerationRecord(request.result, revision)
        return CommitDuplicateGenerationSuccess(
            CommitDisposition.COMMITTED,
            request.result,
            revision,
        )

    def load_assessment_batch(
        self,
        request: LoadDuplicateAssessmentBatchRequest,
    ) -> LoadedDuplicateAssessmentBatch:
        record = self._batches.get(request.identity)
        if record is None:
            return AssessmentBatchNotFound()
        return AssessmentBatchFound(record.batch, record.revision)

    def load_pair_assessment(
        self,
        request: LoadDuplicatePairAssessmentRequest,
    ) -> PairAssessmentFound | PairAssessmentNotFound:
        assessment = self._assessments.get(request.identity)
        if assessment is None:
            return PairAssessmentNotFound()
        return PairAssessmentFound(assessment)

    def commit_assessment_batch(
        self,
        request: CommitDuplicateAssessmentBatchRequest,
    ) -> CommitDuplicateAssessmentBatchOutcome:
        batch = request.batch
        generation = batch.generation_result
        generation_record = self._generations.get(generation.identity)
        batch_record = self._batches.get(batch.identity)

        if batch_record is not None and batch_record.batch == batch:
            if generation_record is not None and generation_record.result == generation:
                return CommitDuplicateAssessmentBatchSuccess(
                    CommitDisposition.REPLAYED,
                    generation_record.revision,
                    batch_record.revision,
                    batch_record.batch,
                )

        content_conflicts: list[DuplicateAssessmentPersistenceConflict] = []
        if generation_record is not None and generation_record.result != generation:
            content_conflicts.append(
                DuplicateAssessmentPersistenceConflict(
                    "DUPLICATE_ASSESSMENT_PERSISTENCE_CONFLICT",
                    DuplicateAssessmentPersistenceConflictCode.GENERATION_DEPENDENCY_CONTENT_CONFLICT,
                    AssessmentGenerationDependencySubject(generation.identity),
                )
            )
        if batch_record is not None and batch_record.batch != batch:
            content_conflicts.append(
                DuplicateAssessmentPersistenceConflict(
                    "DUPLICATE_ASSESSMENT_PERSISTENCE_CONFLICT",
                    DuplicateAssessmentPersistenceConflictCode.BATCH_IDENTITY_CONTENT_CONFLICT,
                    AssessmentBatchIdentityContentSubject(batch.identity),
                )
            )
        incoming_assessments = tuple(item.result.assessment for item in batch.item_outcomes)
        for assessment in incoming_assessments:
            existing = self._assessments.get(assessment.identity)
            if existing is not None and existing != assessment:
                content_conflicts.append(
                    DuplicateAssessmentPersistenceConflict(
                        "DUPLICATE_ASSESSMENT_PERSISTENCE_CONFLICT",
                        DuplicateAssessmentPersistenceConflictCode.ITEM_IDENTITY_CONTENT_CONFLICT,
                        AssessmentItemIdentityContentSubject(assessment.identity),
                    )
                )
        if content_conflicts:
            return CommitDuplicateAssessmentBatchFailure(tuple(content_conflicts))

        actual_generation = None if generation_record is None else generation_record.revision
        actual_batch = None if batch_record is None else batch_record.revision
        revision_conflicts: list[DuplicateAssessmentPersistenceConflict] = []
        if not _expectation_matches(
            request.expected_generation_revision,
            actual_generation,
        ):
            revision_conflicts.append(
                DuplicateAssessmentPersistenceConflict(
                    "DUPLICATE_ASSESSMENT_PERSISTENCE_CONFLICT",
                    DuplicateAssessmentPersistenceConflictCode.EXPECTED_REVISION_MISMATCH,
                    AssessmentExpectedRevisionSubject(
                        "generation",
                        generation.identity,
                        request.expected_generation_revision,
                        actual_generation,
                    ),
                )
            )
        if not _expectation_matches(request.expected_batch_revision, actual_batch):
            revision_conflicts.append(
                DuplicateAssessmentPersistenceConflict(
                    "DUPLICATE_ASSESSMENT_PERSISTENCE_CONFLICT",
                    DuplicateAssessmentPersistenceConflictCode.EXPECTED_REVISION_MISMATCH,
                    AssessmentExpectedRevisionSubject(
                        "batch",
                        batch.identity,
                        request.expected_batch_revision,
                        actual_batch,
                    ),
                )
            )
        if revision_conflicts:
            return CommitDuplicateAssessmentBatchFailure(tuple(revision_conflicts))

        generation_revision = (
            self._issue_revision() if generation_record is None else generation_record.revision
        )
        batch_revision = self._issue_revision()
        if generation_record is None:
            self._generations[generation.identity] = _GenerationRecord(
                generation,
                generation_revision,
            )
        self._batches[batch.identity] = _BatchRecord(batch, batch_revision)
        for assessment in incoming_assessments:
            self._assessments[assessment.identity] = assessment
        return CommitDuplicateAssessmentBatchSuccess(
            CommitDisposition.COMMITTED,
            generation_revision,
            batch_revision,
            batch,
        )

    def commit_assessment_supersession(
        self,
        request: CommitAssessmentSupersessionRequest,
    ) -> CommitAssessmentSupersessionOutcome:
        link = request.link
        existing = self._supersessions.get(link.previous)
        if existing == link:
            return CommitAssessmentSupersessionSuccess(CommitDisposition.REPLAYED, link)
        conflicts: list[DuplicateAssessmentPersistenceConflict] = []
        if existing is not None:
            conflicts.append(
                DuplicateAssessmentPersistenceConflict(
                    "DUPLICATE_ASSESSMENT_PERSISTENCE_CONFLICT",
                    DuplicateAssessmentPersistenceConflictCode.ASSESSMENT_SUPERSESSION_CONFLICT,
                    link,
                )
            )
        for identity in (link.previous, link.replacement):
            if identity not in self._assessments:
                conflicts.append(
                    DuplicateAssessmentPersistenceConflict(
                        "DUPLICATE_ASSESSMENT_PERSISTENCE_CONFLICT",
                        DuplicateAssessmentPersistenceConflictCode.ASSESSMENT_DEPENDENCY_NOT_FOUND,
                        identity,
                    )
                )
        if conflicts:
            return CommitDuplicateAssessmentBatchFailure(tuple(conflicts))
        self._supersessions[link.previous] = link
        return CommitAssessmentSupersessionSuccess(CommitDisposition.COMMITTED, link)

    def load_manual_review_chain(
        self,
        request: LoadManualReviewChainRequest,
    ) -> LoadManualReviewChainSuccess:
        revisions = tuple(
            record[0]
            for identity, record in sorted(
                self._reviews.items(),
                key=lambda item: (
                    item[0].review_reference_code.value,
                    item[0].revision,
                ),
            )
            if identity.review_reference_code == request.review_reference_code
        )
        head_record = self._review_heads.get(request.review_reference_code)
        if head_record is None:
            return LoadManualReviewChainSuccess(revisions, None, None)
        return LoadManualReviewChainSuccess(revisions, head_record[0], head_record[1])

    def commit_manual_review(
        self,
        request: CommitManualReviewRevisionRequest,
    ) -> CommitManualReviewRevisionOutcome:
        review = request.review
        stored_assessment = self._assessments.get(review.assessment_identity)
        if (
            request.bound_assessment.identity != review.assessment_identity
            or stored_assessment != request.bound_assessment
        ):
            return CommitManualReviewRevisionFailure(
                (
                    ManualReviewPersistenceConflict(
                        "MANUAL_REVIEW_PERSISTENCE_CONFLICT",
                        ManualReviewPersistenceConflictCode.REVIEW_ASSESSMENT_MISMATCH,
                        ManualReviewAssessmentSubject(
                            review.identity,
                            request.bound_assessment.identity,
                        ),
                    ),
                )
            )

        existing_record = self._reviews.get(review.identity)
        if existing_record is not None:
            if existing_record[0] == review:
                return CommitManualReviewRevisionSuccess(
                    CommitDisposition.REPLAYED,
                    review,
                    existing_record[1],
                )
            return CommitManualReviewRevisionFailure(
                (
                    ManualReviewPersistenceConflict(
                        "MANUAL_REVIEW_PERSISTENCE_CONFLICT",
                        ManualReviewPersistenceConflictCode.REVIEW_IDENTITY_CONTENT_CONFLICT,
                        review.identity,
                    ),
                    ManualReviewPersistenceConflict(
                        "MANUAL_REVIEW_PERSISTENCE_CONFLICT",
                        ManualReviewPersistenceConflictCode.REVIEW_REVISION_FORK,
                        review.identity,
                    ),
                )
            )
        conflicts: list[ManualReviewPersistenceConflict] = []
        reference_code = review.identity.review_reference_code
        head_record = self._review_heads.get(reference_code)
        actual_revision = None if head_record is None else head_record[1]
        if not _expectation_matches(request.expected_head_revision, actual_revision):
            conflicts.append(
                ManualReviewPersistenceConflict(
                    "MANUAL_REVIEW_PERSISTENCE_CONFLICT",
                    ManualReviewPersistenceConflictCode.EXPECTED_REVISION_MISMATCH,
                    ManualReviewExpectedRevisionSubject(
                        reference_code,
                        request.expected_head_revision,
                        actual_revision,
                    ),
                )
            )
        expected_revision = 1 if head_record is None else head_record[0].identity.revision + 1
        expected_previous = None if head_record is None else head_record[0].identity
        if review.identity.revision != expected_revision or review.supersedes != expected_previous:
            code = (
                ManualReviewPersistenceConflictCode.REVIEW_REVISION_FORK
                if review.supersedes is not None and review.supersedes in self._reviews
                else ManualReviewPersistenceConflictCode.REVIEW_REVISION_MISMATCH
            )
            conflicts.append(
                ManualReviewPersistenceConflict(
                    "MANUAL_REVIEW_PERSISTENCE_CONFLICT",
                    code,
                    review.identity,
                )
            )
        if conflicts:
            return CommitManualReviewRevisionFailure(tuple(conflicts))

        head_revision = self._issue_revision()
        self._reviews[review.identity] = (review, head_revision)
        self._review_heads[reference_code] = (review, head_revision)
        return CommitManualReviewRevisionSuccess(
            CommitDisposition.COMMITTED,
            review,
            head_revision,
        )

    def load_quality_audit(
        self,
        request: LoadDuplicateQualityAuditRequest,
    ) -> LoadedDuplicateQualityAudit:
        record = self._quality_inputs.get(request.identity)
        if record is None:
            return QualityAuditNotFound()
        return QualityAuditFound(record.input, record.head_revision)

    def commit_quality_audit(
        self,
        request: CommitDuplicateQualityAuditRequest,
    ) -> CommitDuplicateQualityAuditOutcome:
        audit_input = request.input
        identity = audit_input.identity
        existing = self._quality_inputs.get(identity)
        if existing is not None:
            if existing.input == audit_input:
                return CommitDuplicateQualityAuditSuccess(
                    CommitDisposition.REPLAYED,
                    audit_input,
                    existing.head_revision,
                )
            return CommitDuplicateQualityAuditFailure(
                (
                    DuplicateQualityPersistenceConflict(
                        "DUPLICATE_QUALITY_PERSISTENCE_CONFLICT",
                        DuplicateQualityPersistenceConflictCode.AUDIT_IDENTITY_CONTENT_CONFLICT,
                        identity,
                    ),
                    DuplicateQualityPersistenceConflict(
                        "DUPLICATE_QUALITY_PERSISTENCE_CONFLICT",
                        DuplicateQualityPersistenceConflictCode.AUDIT_REVISION_FORK,
                        identity,
                    ),
                )
            )

        head = self._quality_heads.get(identity.reference_code)
        actual = None if head is None else head[1]
        conflicts: list[DuplicateQualityPersistenceConflict] = []
        if not _expectation_matches(request.expected_head_revision, actual):
            conflicts.append(
                DuplicateQualityPersistenceConflict(
                    "DUPLICATE_QUALITY_PERSISTENCE_CONFLICT",
                    DuplicateQualityPersistenceConflictCode.EXPECTED_REVISION_MISMATCH,
                    QualityExpectedRevisionSubject(
                        identity.reference_code,
                        request.expected_head_revision,
                        actual,
                    ),
                )
            )
        expected_domain_revision = 1 if head is None else head[0].revision + 1
        if identity.revision != expected_domain_revision:
            conflicts.append(
                DuplicateQualityPersistenceConflict(
                    "DUPLICATE_QUALITY_PERSISTENCE_CONFLICT",
                    DuplicateQualityPersistenceConflictCode.AUDIT_REVISION_FORK,
                    identity,
                )
            )
        if conflicts:
            return CommitDuplicateQualityAuditFailure(tuple(conflicts))

        head_revision = self._issue_revision()
        self._quality_inputs[identity] = _QualityRecord(audit_input, head_revision)
        self._quality_heads[identity.reference_code] = (identity, head_revision)
        return CommitDuplicateQualityAuditSuccess(
            CommitDisposition.COMMITTED,
            audit_input,
            head_revision,
        )
