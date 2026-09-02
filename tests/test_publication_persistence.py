from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, is_dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

import real_estate_parser
import real_estate_parser.publication_persistence as contracts
from real_estate_parser.in_memory_publication_persistence import (
    InMemoryPublicationPersistence,
)
from real_estate_parser.normalization import (
    Area,
    Currency,
    LocationText,
    MoneyAmount,
    NormalizationRuleVersion,
    NormalizedListing,
    ObservedAt,
    Present,
    RoomCount,
    SourceUrl,
    TracedValue,
    ValueProvenance,
)
from real_estate_parser.publication_duplicate_assessment_batches import (
    DuplicateCandidateAssessmentBatchSuccess,
    assess_duplicate_candidate_batch,
)
from real_estate_parser.publication_duplicate_assessments import (
    PUBLICATION_DUPLICATE_POLICY_V1,
    AssessmentFindingKind,
    AssessmentFindingReference,
    AssessmentSupersession,
    DuplicatePairAssessment,
    ManualReviewDraft,
    ManualReviewIdentity,
    ManualReviewOutcome,
    ManualReviewSuccess,
    ReviewedAt,
    ReviewerCode,
    ReviewRationaleCode,
    ReviewReferenceCode,
    create_manual_review,
)
from real_estate_parser.publication_duplicate_candidates import (
    PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1,
    BucketPairLimit,
    DuplicateCandidateGenerationConfiguration,
    DuplicateCandidateGenerationResult,
    DuplicateCandidateGenerationSuccess,
    generate_duplicate_candidates,
)
from real_estate_parser.publication_duplicate_quality import (
    DuplicateControlLabel,
    DuplicateControlLabelOutcome,
    DuplicatePolicyControlCase,
    DuplicatePolicyControlSet,
)
from real_estate_parser.publication_observation_batches import (
    ObservationBatchAppendSuccess,
    PublicationObservationHistories,
    append_observation_batch,
)
from real_estate_parser.publication_observations import (
    PUBLICATION_CHANGE_POLICY_V1,
    AvailableObservation,
    ObservationKey,
    PublicationObservation,
    PublicationObservationHistory,
)
from real_estate_parser.source_batch import (
    InputLocation,
    PublicationId,
    PublicationRef,
    SourceId,
)

RULE = NormalizationRuleVersion("fictional-persistence-field@1")
GENERATION_CONFIGURATION = DuplicateCandidateGenerationConfiguration(
    PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1,
    BucketPairLimit(10),
)


def _ref(source: str, publication: str) -> PublicationRef:
    return PublicationRef(SourceId(source), PublicationId(publication))


def _at(minute: int) -> ObservedAt:
    return ObservedAt(datetime(2026, 9, 2, 19, minute, tzinfo=UTC))


def _provenance(
    reference: PublicationRef,
    observed_at: ObservedAt,
    field: str,
    raw: str,
) -> ValueProvenance:
    return ValueProvenance(
        source_id=reference.source_id,
        publication_id=reference.publication_id,
        input_path=InputLocation("listings", 0, (field,)),
        source_field=field,
        raw_value=raw,
        observed_at=observed_at,
        normalization_rule_version=RULE,
    )


def _present[T](
    value: T,
    reference: PublicationRef,
    observed_at: ObservedAt,
    field: str,
    raw: str,
) -> Present[T]:
    return Present(TracedValue(value, _provenance(reference, observed_at, field, raw)))


def _available(
    reference: PublicationRef,
    minute: int,
    *,
    area: int = 4_700,
    rooms: int = 2,
    location: str = "Fictional Persistence Quarter",
    price: int = 11_000_000,
) -> AvailableObservation:
    observed_at = _at(minute)
    source_url = f"https://{reference.source_id.value}.example/{reference.publication_id.value}"
    listing = NormalizedListing(
        reference=TracedValue(
            reference,
            _provenance(reference, observed_at, "publication_id", reference.publication_id.value),
        ),
        source_url=TracedValue(
            SourceUrl(source_url),
            _provenance(reference, observed_at, "source_url", source_url),
        ),
        observed_at=TracedValue(
            observed_at,
            _provenance(reference, observed_at, "observed_at", observed_at.to_rfc3339()),
        ),
        location_text=_present(
            LocationText(location), reference, observed_at, "location_text", location
        ),
        price_amount=_present(
            MoneyAmount(price), reference, observed_at, "price_amount", str(price)
        ),
        currency=_present(Currency("RUB"), reference, observed_at, "currency", "RUB"),
        total_area=_present(Area(area), reference, observed_at, "total_area", str(area)),
        rooms=_present(RoomCount(rooms), reference, observed_at, "rooms", str(rooms)),
    )
    return AvailableObservation(ObservationKey(reference, observed_at), listing)


def _history_request(
    candidates: tuple[PublicationObservation, ...],
    loaded: contracts.LoadObservationHistoriesSuccess,
) -> contracts.ObservationHistoryCommitRequest:
    histories = PublicationObservationHistories(
        tuple(entry.history for entry in loaded.entries if entry.history is not None)
    )
    prepared = append_observation_batch(histories, candidates, PUBLICATION_CHANGE_POLICY_V1)
    assert isinstance(prepared, ObservationBatchAppendSuccess)
    expected = tuple(
        contracts.ExpectedHistoryHead(
            entry.reference,
            contracts.ExpectAbsent()
            if entry.revision is None
            else contracts.ExpectExact(entry.revision),
        )
        for entry in loaded.entries
    )
    keys = tuple(sorted((candidate.key for candidate in candidates), key=_key_sort))
    return contracts.ObservationHistoryCommitRequest(
        contracts.ObservationHistoryCommitIdentity(
            PUBLICATION_CHANGE_POLICY_V1.version,
            keys,
        ),
        expected,
        tuple(sorted(candidates, key=lambda candidate: _key_sort(candidate.key))),
        prepared,
    )


def _key_sort(key: ObservationKey) -> tuple[str, str, object]:
    return (
        key.reference.source_id.value,
        key.reference.publication_id.value,
        key.observed_at.value,
    )


def _load(
    adapter: InMemoryPublicationPersistence,
    *references: PublicationRef,
) -> contracts.LoadObservationHistoriesSuccess:
    outcome = adapter.load_histories(
        contracts.LoadObservationHistoriesRequest(tuple(sorted(references, key=_ref_sort)))
    )
    assert isinstance(outcome, contracts.LoadObservationHistoriesSuccess)
    return outcome


def _ref_sort(reference: PublicationRef) -> tuple[str, str]:
    return reference.source_id.value, reference.publication_id.value


def _generation(
    observations: tuple[AvailableObservation, ...],
) -> DuplicateCandidateGenerationResult:
    outcome = generate_duplicate_candidates(observations, GENERATION_CONFIGURATION)
    assert isinstance(outcome, DuplicateCandidateGenerationSuccess)
    return outcome.result


def _batch(
    observations: tuple[AvailableObservation, ...],
    generation: DuplicateCandidateGenerationResult | None = None,
) -> Any:
    selected_generation = generation or _generation(observations)
    outcome = assess_duplicate_candidate_batch(
        selected_generation,
        observations,
        PUBLICATION_DUPLICATE_POLICY_V1,
    )
    assert isinstance(outcome, DuplicateCandidateAssessmentBatchSuccess)
    return outcome.batch


def _finding_reference(assessment: DuplicatePairAssessment) -> AssessmentFindingReference:
    finding = assessment.evidence[0]
    return AssessmentFindingReference(
        assessment.identity,
        AssessmentFindingKind.EVIDENCE,
        finding.rule_id,
        finding.rule_version,
        finding.polarity,
        0,
    )


def _review(
    assessment: DuplicatePairAssessment,
    revision: int,
    previous: Any = None,
    *,
    outcome: ManualReviewOutcome = ManualReviewOutcome.CONFIRMED_RELATIONSHIP,
) -> Any:
    reference_code = ReviewReferenceCode("review-persistence-demo")
    draft = ManualReviewDraft(
        ManualReviewIdentity(reference_code, revision),
        assessment.identity,
        ReviewedAt(datetime(2026, 9, 2, 20, revision, tzinfo=UTC)),
        ReviewerCode("reviewer-fixture"),
        outcome,
        (ReviewRationaleCode("visible-fields-reviewed"),),
        (_finding_reference(assessment),),
        None if revision == 1 else ManualReviewIdentity(reference_code, revision - 1),
    )
    result = create_manual_review(assessment, draft, previous)
    assert isinstance(result, ManualReviewSuccess)
    return result.review


def _stored_batch(
    adapter: InMemoryPublicationPersistence,
    *,
    minute_offset: int = 0,
) -> tuple[tuple[AvailableObservation, ...], Any, contracts.CommitDuplicateAssessmentBatchSuccess]:
    observations = (
        _available(_ref("fixture_portal", "a"), minute_offset),
        _available(_ref("mirror_fixture", "b"), minute_offset + 1),
    )
    batch = _batch(observations)
    outcome = adapter.commit_assessment_batch(
        contracts.CommitDuplicateAssessmentBatchRequest(
            contracts.ExpectAbsent(),
            contracts.ExpectAbsent(),
            batch,
        )
    )
    assert isinstance(outcome, contracts.CommitDuplicateAssessmentBatchSuccess)
    return observations, batch, outcome


def test_public_protocols_are_narrow_and_reference_adapter_implements_all() -> None:
    adapter = InMemoryPublicationPersistence()
    assert isinstance(adapter, contracts.ObservationHistoryPort)
    assert isinstance(adapter, contracts.DuplicateGenerationArtifactPort)
    assert isinstance(adapter, contracts.DuplicateAssessmentArtifactPort)
    assert isinstance(adapter, contracts.ManualReviewRevisionPort)
    assert isinstance(adapter, contracts.DuplicateQualityAuditPort)
    assert not hasattr(contracts, "Repository")
    assert not hasattr(adapter, "save")
    assert not hasattr(adapter, "execute")
    for public_name in (
        "ObservationHistoryPort",
        "DuplicateGenerationArtifactPort",
        "DuplicateAssessmentArtifactPort",
        "ManualReviewRevisionPort",
        "DuplicateQualityAuditPort",
        "InMemoryPublicationPersistence",
        "PersistenceRevision",
        "ExpectAbsent",
        "ExpectExact",
    ):
        assert public_name in real_estate_parser.__all__
        assert hasattr(real_estate_parser, public_name)


def test_public_records_are_frozen_slotted_and_revision_is_adapter_issued() -> None:
    records = (
        contracts.ExpectAbsent(),
        contracts.QualityAuditReferenceCode("quality-demo"),
        contracts.QualityAuditIdentity(contracts.QualityAuditReferenceCode("quality-demo"), 1),
        contracts.GenerationNotFound(),
    )
    assert all(is_dataclass(record) for record in records)
    assert all(hasattr(type(record), "__slots__") for record in records)
    with pytest.raises(FrozenInstanceError):
        cast(Any, records[1]).value = "changed"
    with pytest.raises(TypeError, match="issued only by adapters"):
        contracts.PersistenceRevision(1, _issuer=object())

    public_dataclasses = (
        value
        for value in vars(contracts).values()
        if isinstance(value, type)
        and value.__module__ == contracts.__name__
        and is_dataclass(value)
    )
    for record_type in public_dataclasses:
        parameters = cast(Any, record_type).__dataclass_params__
        assert parameters.frozen is True
        assert hasattr(record_type, "__slots__")


def test_constructor_invariants_reject_non_tuple_and_noncanonical_requests() -> None:
    reference_a = _ref("fixture_portal", "a")
    reference_b = _ref("mirror_fixture", "b")
    with pytest.raises(TypeError, match="tuple"):
        cast(Any, contracts.LoadObservationHistoriesRequest)([reference_a])
    with pytest.raises(ValueError, match="canonical"):
        contracts.LoadObservationHistoriesRequest((reference_b, reference_a))
    with pytest.raises(ValueError, match="positive"):
        contracts.QualityAuditIdentity(contracts.QualityAuditReferenceCode("quality-demo"), 0)


def test_typed_operational_failure_contains_no_partial_success_state() -> None:
    failure = contracts.PersistenceOperationFailure(
        contracts.PersistenceOperationFailureCode.OUTCOME_UNKNOWN,
        contracts.PersistenceOperationSubject(
            contracts.PersistencePortName.OBSERVATION_HISTORY,
            contracts.PersistenceOperationName.COMMIT_HISTORIES,
            _ref("fixture_portal", "operation-subject"),
        ),
    )
    assert failure.code is contracts.PersistenceOperationFailureCode.OUTCOME_UNKNOWN
    assert not hasattr(failure, "heads")
    assert not hasattr(failure, "result")


def test_history_first_write_exact_retry_and_exact_reads_are_stable() -> None:
    adapter = InMemoryPublicationPersistence()
    reference = _ref("fixture_portal", "history-a")
    observation = _available(reference, 0)
    request = _history_request((observation,), _load(adapter, reference))

    first = adapter.commit_histories(request)
    retry = adapter.commit_histories(request)
    assert isinstance(first, contracts.ObservationHistoryCommitSuccess)
    assert isinstance(retry, contracts.ObservationHistoryCommitSuccess)
    assert first.disposition is contracts.CommitDisposition.COMMITTED
    assert retry.disposition is contracts.CommitDisposition.REPLAYED
    assert retry.heads == first.heads

    histories = _load(adapter, reference)
    assert histories.entries[0].history == first.heads[0].history
    exact = adapter.load_observations_by_key(
        contracts.LoadObservationsByKeyRequest((observation.key,))
    )
    assert exact == contracts.LoadObservationsByKeySuccess((observation,))
    missing = adapter.load_observations_by_key(
        contracts.LoadObservationsByKeyRequest((_available(reference, 1).key,))
    )
    assert isinstance(missing, contracts.ObservationHistoryCommitFailure)
    assert (
        missing.conflicts[0].code
        is contracts.ObservationPersistenceConflictCode.OBSERVATION_NOT_FOUND
    )


def test_history_equal_identity_different_content_is_conflict_before_revision() -> None:
    adapter = InMemoryPublicationPersistence()
    reference = _ref("fixture_portal", "history-content")
    original = _available(reference, 0, location="Fictional North")
    loaded = _load(adapter, reference)
    original_request = _history_request((original,), loaded)
    assert isinstance(
        adapter.commit_histories(original_request),
        contracts.ObservationHistoryCommitSuccess,
    )

    changed = _available(reference, 0, location="Fictional South")
    conflicting_request = _history_request((changed,), loaded)
    outcome = adapter.commit_histories(conflicting_request)
    assert isinstance(outcome, contracts.ObservationHistoryCommitFailure)
    assert tuple(conflict.code for conflict in outcome.conflicts) == (
        contracts.ObservationPersistenceConflictCode.COMMIT_IDENTITY_CONTENT_CONFLICT,
    )
    assert (
        _load(adapter, reference).entries[0].history
        == original_request.prepared_result.histories.histories[0]
    )


def test_competing_history_writers_roll_back_all_streams_on_one_stale_head() -> None:
    adapter = InMemoryPublicationPersistence()
    reference_a = _ref("fixture_portal", "atomic-a")
    reference_b = _ref("mirror_fixture", "atomic-b")
    initial = (_available(reference_a, 0), _available(reference_b, 0))
    initial_request = _history_request(initial, _load(adapter, reference_a, reference_b))
    assert isinstance(
        adapter.commit_histories(initial_request),
        contracts.ObservationHistoryCommitSuccess,
    )

    shared_load = _load(adapter, reference_a, reference_b)
    b_update = _available(reference_b, 1)
    b_only_load = contracts.LoadObservationHistoriesSuccess((shared_load.entries[1],))
    assert isinstance(
        adapter.commit_histories(_history_request((b_update,), b_only_load)),
        contracts.ObservationHistoryCommitSuccess,
    )

    stale_request = _history_request(
        (_available(reference_a, 2), _available(reference_b, 2)),
        shared_load,
    )
    stale = adapter.commit_histories(stale_request)
    assert isinstance(stale, contracts.ObservationHistoryCommitFailure)
    assert tuple(conflict.code for conflict in stale.conflicts) == (
        contracts.ObservationPersistenceConflictCode.EXPECTED_REVISION_MISMATCH,
    )
    after = _load(adapter, reference_a, reference_b)
    assert len(cast(PublicationObservationHistory, after.entries[0].history).observations) == 1
    assert cast(PublicationObservationHistory, after.entries[1].history).observations == (
        initial[1],
        b_update,
    )


def test_generation_commit_replay_content_conflict_and_competing_writer_revision() -> None:
    adapter = InMemoryPublicationPersistence()
    observations = (
        _available(_ref("fixture_portal", "generation-a"), 0),
        _available(_ref("mirror_fixture", "generation-b"), 1),
    )
    generation = _generation(observations)
    request = contracts.CommitDuplicateGenerationRequest(contracts.ExpectAbsent(), generation)
    first = adapter.commit_generation(request)
    retry = adapter.commit_generation(request)
    assert isinstance(first, contracts.CommitDuplicateGenerationSuccess)
    assert isinstance(retry, contracts.CommitDuplicateGenerationSuccess)
    assert retry.disposition is contracts.CommitDisposition.REPLAYED
    assert retry.revision == first.revision

    changed_content = replace(generation, candidates=())
    conflict = adapter.commit_generation(
        contracts.CommitDuplicateGenerationRequest(contracts.ExpectAbsent(), changed_content)
    )
    assert isinstance(conflict, contracts.CommitDuplicateGenerationFailure)
    assert conflict.conflicts[0].code is (
        contracts.DuplicateGenerationPersistenceConflictCode.GENERATION_IDENTITY_CONTENT_CONFLICT
    )
    loaded = adapter.load_generation(contracts.LoadDuplicateGenerationRequest(generation.identity))
    assert loaded == contracts.GenerationFound(generation, first.revision)

    other = _generation((_available(_ref("fixture_portal", "generation-solo"), 2),))
    stale = adapter.commit_generation(
        contracts.CommitDuplicateGenerationRequest(contracts.ExpectExact(first.revision), other)
    )
    assert isinstance(stale, contracts.CommitDuplicateGenerationFailure)
    assert stale.conflicts[0].code is (
        contracts.DuplicateGenerationPersistenceConflictCode.EXPECTED_REVISION_MISMATCH
    )


def test_assessment_commit_atomically_saves_generation_batch_and_pair() -> None:
    adapter = InMemoryPublicationPersistence()
    _, batch, first = _stored_batch(adapter)
    assert first.disposition is contracts.CommitDisposition.COMMITTED
    assert adapter.load_generation(
        contracts.LoadDuplicateGenerationRequest(batch.generation_result.identity)
    ) == contracts.GenerationFound(batch.generation_result, first.generation_revision)
    assert adapter.load_assessment_batch(
        contracts.LoadDuplicateAssessmentBatchRequest(batch.identity)
    ) == contracts.AssessmentBatchFound(batch, first.batch_revision)
    assessment = batch.item_outcomes[0].result.assessment
    assert adapter.load_pair_assessment(
        contracts.LoadDuplicatePairAssessmentRequest(assessment.identity)
    ) == contracts.PairAssessmentFound(assessment)

    retry = adapter.commit_assessment_batch(
        contracts.CommitDuplicateAssessmentBatchRequest(
            contracts.ExpectAbsent(),
            contracts.ExpectAbsent(),
            batch,
        )
    )
    assert isinstance(retry, contracts.CommitDuplicateAssessmentBatchSuccess)
    assert retry.disposition is contracts.CommitDisposition.REPLAYED
    assert retry.generation_revision == first.generation_revision
    assert retry.batch_revision == first.batch_revision


def test_assessment_stale_generation_expectation_has_no_batch_or_pair_prefix() -> None:
    adapter = InMemoryPublicationPersistence()
    observations = (
        _available(_ref("fixture_portal", "assessment-a"), 0),
        _available(_ref("mirror_fixture", "assessment-b"), 1),
    )
    generation = _generation(observations)
    generation_commit = adapter.commit_generation(
        contracts.CommitDuplicateGenerationRequest(contracts.ExpectAbsent(), generation)
    )
    assert isinstance(generation_commit, contracts.CommitDuplicateGenerationSuccess)
    batch = _batch(observations, generation)

    failed = adapter.commit_assessment_batch(
        contracts.CommitDuplicateAssessmentBatchRequest(
            contracts.ExpectAbsent(),
            contracts.ExpectAbsent(),
            batch,
        )
    )
    assert isinstance(failed, contracts.CommitDuplicateAssessmentBatchFailure)
    assert failed.conflicts[0].code is (
        contracts.DuplicateAssessmentPersistenceConflictCode.EXPECTED_REVISION_MISMATCH
    )
    assert isinstance(
        adapter.load_assessment_batch(
            contracts.LoadDuplicateAssessmentBatchRequest(batch.identity)
        ),
        contracts.AssessmentBatchNotFound,
    )
    assessment_identity = batch.item_outcomes[0].result.assessment.identity
    assert isinstance(
        adapter.load_pair_assessment(
            contracts.LoadDuplicatePairAssessmentRequest(assessment_identity)
        ),
        contracts.PairAssessmentNotFound,
    )
    assert adapter.load_generation(
        contracts.LoadDuplicateGenerationRequest(generation.identity)
    ) == contracts.GenerationFound(generation, generation_commit.revision)


def test_assessment_equal_identity_different_content_is_atomic_conflict() -> None:
    adapter = InMemoryPublicationPersistence()
    _, batch, committed = _stored_batch(adapter)
    changed_generation = replace(batch.generation_result, candidates=())
    changed_batch = type(batch)(
        batch.identity,
        changed_generation,
        batch.assessment_policy,
        (),
    )
    conflict = adapter.commit_assessment_batch(
        contracts.CommitDuplicateAssessmentBatchRequest(
            contracts.ExpectExact(committed.generation_revision),
            contracts.ExpectExact(committed.batch_revision),
            changed_batch,
        )
    )
    assert isinstance(conflict, contracts.CommitDuplicateAssessmentBatchFailure)
    assert tuple(item.code for item in conflict.conflicts) == (
        contracts.DuplicateAssessmentPersistenceConflictCode.BATCH_IDENTITY_CONTENT_CONFLICT,
        contracts.DuplicateAssessmentPersistenceConflictCode.GENERATION_DEPENDENCY_CONTENT_CONFLICT,
    )
    assert adapter.load_assessment_batch(
        contracts.LoadDuplicateAssessmentBatchRequest(batch.identity)
    ) == contracts.AssessmentBatchFound(batch, committed.batch_revision)


def test_manual_review_atomic_chain_replay_and_fork_do_not_choose_winner() -> None:
    adapter = InMemoryPublicationPersistence()
    _, batch, _ = _stored_batch(adapter)
    assessment = batch.item_outcomes[0].result.assessment
    review_one = _review(assessment, 1)
    request_one = contracts.CommitManualReviewRevisionRequest(
        contracts.ExpectAbsent(),
        review_one,
        assessment,
    )
    first = adapter.commit_manual_review(request_one)
    retry = adapter.commit_manual_review(request_one)
    assert isinstance(first, contracts.CommitManualReviewRevisionSuccess)
    assert isinstance(retry, contracts.CommitManualReviewRevisionSuccess)
    assert retry.disposition is contracts.CommitDisposition.REPLAYED
    assert retry.head_revision == first.head_revision

    winning_review = _review(assessment, 2, review_one)
    winning = adapter.commit_manual_review(
        contracts.CommitManualReviewRevisionRequest(
            contracts.ExpectExact(first.head_revision),
            winning_review,
            assessment,
        )
    )
    assert isinstance(winning, contracts.CommitManualReviewRevisionSuccess)
    old_retry_after_new_head = adapter.commit_manual_review(request_one)
    assert isinstance(
        old_retry_after_new_head,
        contracts.CommitManualReviewRevisionSuccess,
    )
    assert old_retry_after_new_head.head_revision == first.head_revision
    competing_review = _review(
        assessment,
        2,
        review_one,
        outcome=ManualReviewOutcome.REJECTED_RELATIONSHIP,
    )
    fork = adapter.commit_manual_review(
        contracts.CommitManualReviewRevisionRequest(
            contracts.ExpectExact(first.head_revision),
            competing_review,
            assessment,
        )
    )
    assert isinstance(fork, contracts.CommitManualReviewRevisionFailure)
    assert tuple(conflict.code for conflict in fork.conflicts) == (
        contracts.ManualReviewPersistenceConflictCode.REVIEW_IDENTITY_CONTENT_CONFLICT,
        contracts.ManualReviewPersistenceConflictCode.REVIEW_REVISION_FORK,
    )
    chain = adapter.load_manual_review_chain(
        contracts.LoadManualReviewChainRequest(review_one.identity.review_reference_code)
    )
    assert isinstance(chain, contracts.LoadManualReviewChainSuccess)
    assert chain.revisions == (review_one, winning_review)
    assert chain.head == winning_review


def test_quality_audit_keeps_supplied_revision_and_replays_without_metrics() -> None:
    adapter = InMemoryPublicationPersistence()
    _, batch, _ = _stored_batch(adapter)
    result = batch.item_outcomes[0].result
    pair = result.assessment.identity.pair
    control_set = DuplicatePolicyControlSet(
        PUBLICATION_DUPLICATE_POLICY_V1.version,
        (
            DuplicatePolicyControlCase(
                pair,
                PUBLICATION_DUPLICATE_POLICY_V1.version,
                result,
                DuplicateControlLabel(
                    pair,
                    DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP,
                ),
            ),
        ),
    )
    audit_input = contracts.DuplicateQualityAuditInput(
        contracts.QualityAuditIdentity(contracts.QualityAuditReferenceCode("quality-demo"), 1),
        control_set,
        batch.generation_result,
    )
    request = contracts.CommitDuplicateQualityAuditRequest(
        contracts.ExpectAbsent(),
        audit_input,
    )
    first = adapter.commit_quality_audit(request)
    retry = adapter.commit_quality_audit(request)
    assert isinstance(first, contracts.CommitDuplicateQualityAuditSuccess)
    assert isinstance(retry, contracts.CommitDuplicateQualityAuditSuccess)
    assert retry.disposition is contracts.CommitDisposition.REPLAYED
    assert retry.head_revision == first.head_revision
    assert not hasattr(audit_input, "metrics")
    assert not hasattr(audit_input, "coverage")
    assert adapter.load_quality_audit(
        contracts.LoadDuplicateQualityAuditRequest(audit_input.identity)
    ) == contracts.QualityAuditFound(audit_input, first.head_revision)

    stale_second = replace(
        audit_input,
        identity=contracts.QualityAuditIdentity(audit_input.identity.reference_code, 2),
    )
    failed = adapter.commit_quality_audit(
        contracts.CommitDuplicateQualityAuditRequest(
            contracts.ExpectAbsent(),
            stale_second,
        )
    )
    assert isinstance(failed, contracts.CommitDuplicateQualityAuditFailure)
    assert tuple(conflict.code for conflict in failed.conflicts) == (
        contracts.DuplicateQualityPersistenceConflictCode.EXPECTED_REVISION_MISMATCH,
    )
    assert isinstance(
        adapter.load_quality_audit(
            contracts.LoadDuplicateQualityAuditRequest(stale_second.identity)
        ),
        contracts.QualityAuditNotFound,
    )

    second = adapter.commit_quality_audit(
        contracts.CommitDuplicateQualityAuditRequest(
            contracts.ExpectExact(first.head_revision),
            stale_second,
        )
    )
    assert isinstance(second, contracts.CommitDuplicateQualityAuditSuccess)
    assert second.input.identity.revision == 2
    old_retry = adapter.commit_quality_audit(request)
    assert isinstance(old_retry, contracts.CommitDuplicateQualityAuditSuccess)
    assert old_retry.head_revision == first.head_revision


def test_assessment_supersession_requires_exact_assessments_and_replays() -> None:
    adapter = InMemoryPublicationPersistence()
    _, first_batch, _ = _stored_batch(adapter)
    _, second_batch, _ = _stored_batch(adapter, minute_offset=2)
    first_assessment = first_batch.item_outcomes[0].result.assessment
    second_assessment = second_batch.item_outcomes[0].result.assessment
    link = AssessmentSupersession(first_assessment.identity, second_assessment.identity)
    missing = InMemoryPublicationPersistence().commit_assessment_supersession(
        contracts.CommitAssessmentSupersessionRequest(link)
    )
    assert isinstance(missing, contracts.CommitDuplicateAssessmentBatchFailure)
    assert tuple(conflict.subject for conflict in missing.conflicts) == (
        first_assessment.identity,
        second_assessment.identity,
    )
    request = contracts.CommitAssessmentSupersessionRequest(link)
    first = adapter.commit_assessment_supersession(request)
    retry = adapter.commit_assessment_supersession(request)
    assert first == contracts.CommitAssessmentSupersessionSuccess(
        contracts.CommitDisposition.COMMITTED,
        link,
    )
    assert retry == contracts.CommitAssessmentSupersessionSuccess(
        contracts.CommitDisposition.REPLAYED,
        link,
    )
    assert adapter.load_pair_assessment(
        contracts.LoadDuplicatePairAssessmentRequest(first_assessment.identity)
    ) == contracts.PairAssessmentFound(first_assessment)
    assert adapter.load_pair_assessment(
        contracts.LoadDuplicatePairAssessmentRequest(second_assessment.identity)
    ) == contracts.PairAssessmentFound(second_assessment)


def test_forbidden_persistence_surface_has_no_io_or_production_executor() -> None:
    root = Path(__file__).parents[1]
    files = (
        root / "src/real_estate_parser/publication_persistence.py",
        root / "src/real_estate_parser/in_memory_publication_persistence.py",
    )
    forbidden_import_roots = {
        "asyncio",
        "http",
        "json",
        "pathlib",
        "pickle",
        "requests",
        "socket",
        "sqlite3",
        "sqlalchemy",
        "subprocess",
        "urllib",
        "uuid",
    }
    forbidden_public_names = {
        "Repository",
        "Executor",
        "Orchestrator",
        "Scheduler",
        "TransactionManager",
    }
    for file in files:
        tree = ast.parse(file.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        assert imports.isdisjoint(forbidden_import_roots)
        public_classes = {
            node.name
            for node in tree.body
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
        }
        assert public_classes.isdisjoint(forbidden_public_names)
