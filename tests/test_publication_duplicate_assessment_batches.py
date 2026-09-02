from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, is_dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

import real_estate_parser
import real_estate_parser.publication_duplicate_assessment_batches as batch_module
import real_estate_parser.publication_duplicate_assessments as assessment_module
from real_estate_parser import (
    PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1,
    PUBLICATION_DUPLICATE_POLICY_V1,
    Area,
    AvailabilityRuleVersion,
    AvailableObservation,
    BucketPairLimit,
    CandidateBindingMismatchKind,
    CandidateBindingMismatchSubject,
    DirectSourceStateEvidence,
    DownstreamAssessmentConflictKind,
    DownstreamAssessmentConflictSubject,
    DuplicateAssessmentConflict,
    DuplicateCandidate,
    DuplicateCandidateAssessmentBatch,
    DuplicateCandidateAssessmentBatchConfiguration,
    DuplicateCandidateAssessmentBatchConflict,
    DuplicateCandidateAssessmentBatchFailure,
    DuplicateCandidateAssessmentBatchIdentity,
    DuplicateCandidateAssessmentBatchInput,
    DuplicateCandidateAssessmentBatchSuccess,
    DuplicateCandidateAssessmentItemIdentity,
    DuplicateCandidateAssessmentItemOutcome,
    DuplicateCandidateGenerationConfiguration,
    DuplicateCandidateGenerationIdentity,
    DuplicateCandidateGenerationResult,
    DuplicateCandidateGenerationSuccess,
    DuplicateCandidateIdentity,
    DuplicateCandidatePolicy,
    DuplicateCandidatePolicyVersion,
    DuplicatePolicy,
    DuplicatePolicyVersion,
    GenerationCurrentKeysMismatchKind,
    GenerationCurrentKeysMismatchSubject,
    InputLocation,
    LocationText,
    MoneyAmount,
    NormalizationRuleVersion,
    NormalizedListing,
    ObservationKey,
    ObservedAt,
    PairAssessmentFailure,
    PairAssessmentSuccess,
    PairNotAssessed,
    Present,
    PublicationId,
    PublicationPair,
    PublicationRef,
    RoomCount,
    SourceId,
    SourceUrl,
    TracedValue,
    UnavailableObservation,
    UnexpectedPairNotAssessedSubject,
    UnsupportedAssessmentPolicySubject,
    UnsupportedCandidatePolicySubject,
    ValueProvenance,
    assess_duplicate_candidate_batch,
    assess_publication_pair,
    generate_duplicate_candidates,
)
from real_estate_parser.normalization import Currency

RULE = NormalizationRuleVersion("fictional-assessment-batch-field@1")
AVAILABILITY_RULE = AvailabilityRuleVersion("fictional-assessment-batch-availability@1")
GENERATION_CONFIGURATION = DuplicateCandidateGenerationConfiguration(
    PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1,
    BucketPairLimit(10),
)


def _ref(source: str, publication: str) -> PublicationRef:
    return PublicationRef(SourceId(source), PublicationId(publication))


def _at(minute: int) -> ObservedAt:
    return ObservedAt(datetime(2026, 9, 2, 18, minute, tzinfo=UTC))


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
    location: str = "Fictional Batch Quarter",
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


def _unavailable(reference: PublicationRef, minute: int) -> UnavailableObservation:
    return UnavailableObservation(
        ObservationKey(reference, _at(minute)),
        DirectSourceStateEvidence(
            raw_source_state="fictionally-unavailable",
            source_field="publication_state",
            adapter_rule_version=AVAILABILITY_RULE,
        ),
    )


def _generation(
    observations: tuple[AvailableObservation, ...],
) -> DuplicateCandidateGenerationResult:
    outcome = generate_duplicate_candidates(observations, GENERATION_CONFIGURATION)
    assert isinstance(outcome, DuplicateCandidateGenerationSuccess)
    return outcome.result


def _two_selective_candidates() -> tuple[
    tuple[AvailableObservation, ...], DuplicateCandidateGenerationResult
]:
    observations = (
        _available(_ref("fixture_portal", "a"), 0, rooms=2, location="Fictional North"),
        _available(_ref("fixture_portal", "b"), 1, rooms=2, location="Fictional South"),
        _available(_ref("mirror_fixture", "c"), 2, rooms=3, location="Fictional North"),
    )
    result = _generation(observations)
    assert len(result.candidates) == 2
    return observations, result


def _failure(
    generation_result: object,
    current: object,
    policy: object = PUBLICATION_DUPLICATE_POLICY_V1,
) -> DuplicateCandidateAssessmentBatchFailure:
    outcome = cast(Any, assess_duplicate_candidate_batch)(generation_result, current, policy)
    assert isinstance(outcome, DuplicateCandidateAssessmentBatchFailure)
    return outcome


def _codes(failure: DuplicateCandidateAssessmentBatchFailure) -> tuple[str, ...]:
    return tuple(conflict.code for conflict in failure.conflicts)


def _crafted_result(
    base: DuplicateCandidateGenerationResult,
    *,
    identity: DuplicateCandidateGenerationIdentity | None = None,
    policy: DuplicateCandidatePolicy | None = None,
    candidates: tuple[DuplicateCandidate, ...] | None = None,
) -> DuplicateCandidateGenerationResult:
    result = object.__new__(DuplicateCandidateGenerationResult)
    object.__setattr__(result, "identity", base.identity if identity is None else identity)
    object.__setattr__(result, "policy", base.policy if policy is None else policy)
    object.__setattr__(result, "candidates", base.candidates if candidates is None else candidates)
    object.__setattr__(result, "non_participations", base.non_participations)
    object.__setattr__(result, "oversized_buckets", base.oversized_buckets)
    return result


def test_valid_empty_candidates_are_complete_success_with_zero_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observation = _available(_ref("fixture_portal", "solo"), 0)
    generation = _generation((observation,))
    calls: list[object] = []

    def spy(*args: object, **kwargs: object) -> object:
        calls.append((args, kwargs))
        raise AssertionError("empty candidate batch must not assess a pair")

    monkeypatch.setattr(assessment_module, "assess_publication_pair", spy)
    outcome = assess_duplicate_candidate_batch(
        generation,
        (observation,),
        PUBLICATION_DUPLICATE_POLICY_V1,
    )
    assert isinstance(outcome, DuplicateCandidateAssessmentBatchSuccess)
    assert outcome.batch.item_outcomes == ()
    assert outcome.batch.generation_result == generation
    assert outcome.batch.assessment_policy == PUBLICATION_DUPLICATE_POLICY_V1
    assert calls == []


def test_multiple_same_and_cross_source_candidates_use_exact_canonical_sides_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations, generation = _two_selective_candidates()
    expected_by_reference = {item.key.reference: item for item in observations}
    calls: list[tuple[AvailableObservation, AvailableObservation, DuplicatePolicy]] = []
    original = assess_publication_pair

    def spy(
        first: AvailableObservation,
        second: AvailableObservation,
        policy: DuplicatePolicy,
    ) -> object:
        calls.append((first, second, policy))
        return original(first, second, policy)

    monkeypatch.setattr(assessment_module, "assess_publication_pair", spy)
    outcome = assess_duplicate_candidate_batch(
        generation,
        tuple(reversed(observations)),
        PUBLICATION_DUPLICATE_POLICY_V1,
    )
    assert isinstance(outcome, DuplicateCandidateAssessmentBatchSuccess)
    assert len(outcome.batch.item_outcomes) == 2
    assert tuple(item.candidate for item in outcome.batch.item_outcomes) == generation.candidates
    assert len(calls) == 2
    for call, candidate in zip(calls, generation.candidates, strict=True):
        first, second, policy = call
        assert first == expected_by_reference[candidate.identity.pair.left]
        assert second == expected_by_reference[candidate.identity.pair.right]
        assert policy is PUBLICATION_DUPLICATE_POLICY_V1
        assert candidate.blocking_matches
    pairs = tuple(candidate.identity.pair for candidate in generation.candidates)
    assert any(pair.left.source_id == pair.right.source_id for pair in pairs)
    assert any(pair.left.source_id != pair.right.source_id for pair in pairs)


def test_valid_current_input_permutations_and_replay_are_structurally_equal() -> None:
    observations, generation = _two_selective_candidates()
    first = assess_duplicate_candidate_batch(
        generation, observations, PUBLICATION_DUPLICATE_POLICY_V1
    )
    second = assess_duplicate_candidate_batch(
        generation, tuple(reversed(observations)), PUBLICATION_DUPLICATE_POLICY_V1
    )
    replay = assess_duplicate_candidate_batch(
        generation, observations, PUBLICATION_DUPLICATE_POLICY_V1
    )
    assert first == second == replay


@pytest.mark.parametrize(
    ("current_factory", "expected_codes"),
    [
        (lambda observations: list(observations), ("observations_not_tuple",)),
        (lambda _observations: (), ("empty_current_observations",)),
        (
            lambda observations: (observations[0], _unavailable(observations[1].key.reference, 1)),
            ("observation_not_available",),
        ),
        (
            lambda observations: (observations[0], object()),
            ("unsupported_observation",),
        ),
        (
            lambda observations: (observations[0], observations[0]),
            ("duplicate_publication_ref",),
        ),
        (
            lambda observations: (
                observations[0],
                _available(
                    observations[0].key.reference,
                    0,
                    price=12_000_000,
                ),
            ),
            ("observation_key_content_conflict",),
        ),
    ],
)
def test_current_shape_and_content_conflicts_make_zero_assessment_calls(
    monkeypatch: pytest.MonkeyPatch,
    current_factory: Any,
    expected_codes: tuple[str, ...],
) -> None:
    first = _available(_ref("fixture_portal", "a"), 0)
    second = _available(_ref("mirror_fixture", "b"), 1)
    generation = _generation((first, second))
    calls = 0

    def forbidden(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("preflight failure called assessment")

    monkeypatch.setattr(assessment_module, "assess_publication_pair", forbidden)
    failure = _failure(generation, current_factory((first, second)))
    assert _codes(failure) == expected_codes
    assert calls == 0


def test_same_key_content_conflict_and_another_key_produce_both_independent_codes() -> None:
    observation = _available(_ref("fixture_portal", "a"), 0)
    changed = _available(observation.key.reference, 0, price=12_000_000)
    newer = _available(observation.key.reference, 1)
    generation = _generation((observation,))
    failure = _failure(generation, (observation, changed, newer))
    assert _codes(failure) == (
        "observation_key_content_conflict",
        "duplicate_publication_ref",
    )


def test_missing_extra_and_same_reference_new_key_have_independent_exact_semantics() -> None:
    first = _available(_ref("fixture_portal", "a"), 0)
    second = _available(_ref("mirror_fixture", "b"), 1)
    generation = _generation((first, second))

    missing = _failure(generation, (first,))
    missing_subject = cast(
        GenerationCurrentKeysMismatchSubject,
        missing.conflicts[0].subject,
    )
    assert missing_subject.kind is GenerationCurrentKeysMismatchKind.MISSING_GENERATION_KEY
    assert missing_subject.generation_key == second.key
    assert missing_subject.current_key is None

    extra_observation = _available(_ref("third_fixture", "c"), 2)
    extra = _failure(generation, (first, second, extra_observation))
    extra_subject = cast(GenerationCurrentKeysMismatchSubject, extra.conflicts[0].subject)
    assert extra_subject.kind is GenerationCurrentKeysMismatchKind.EXTRA_CURRENT_KEY
    assert extra_subject.generation_key is None
    assert extra_subject.current_key == extra_observation.key

    newer_second = _available(second.key.reference, 3)
    mismatched = _failure(generation, (first, newer_second))
    assert _codes(mismatched) == ("generation_current_keys_mismatch",)
    mismatch_subject = cast(
        GenerationCurrentKeysMismatchSubject,
        mismatched.conflicts[0].subject,
    )
    assert mismatch_subject.kind is GenerationCurrentKeysMismatchKind.CURRENT_KEY_MISMATCH
    assert mismatch_subject.generation_key == second.key
    assert mismatch_subject.current_key == newer_second.key


def test_missing_and_extra_conflicts_are_canonical_by_reference() -> None:
    first = _available(_ref("fixture_portal", "a"), 0)
    second = _available(_ref("mirror_fixture", "b"), 1)
    generation = _generation((first, second))
    extra = _available(_ref("third_fixture", "c"), 2)
    failure = _failure(generation, (extra,))
    subjects = cast(
        tuple[GenerationCurrentKeysMismatchSubject, ...],
        tuple(conflict.subject for conflict in failure.conflicts),
    )
    assert tuple(subject.kind for subject in subjects) == (
        GenerationCurrentKeysMismatchKind.MISSING_GENERATION_KEY,
        GenerationCurrentKeysMismatchKind.MISSING_GENERATION_KEY,
        GenerationCurrentKeysMismatchKind.EXTRA_CURRENT_KEY,
    )
    assert tuple(subject.reference for subject in subjects) == tuple(
        sorted(
            (first.key.reference, second.key.reference, extra.key.reference),
            key=lambda ref: (ref.source_id.value, ref.publication_id.value),
        )
    )


def test_only_full_supported_candidate_and_assessment_policies_are_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations, generation = _two_selective_candidates()
    changed_candidate_policy = DuplicateCandidatePolicy(
        PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1.version,
        tuple(reversed(PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1.rules)),
    )
    changed_assessment_policy = DuplicatePolicy(
        PUBLICATION_DUPLICATE_POLICY_V1.version,
        tuple(reversed(PUBLICATION_DUPLICATE_POLICY_V1.rules)),
    )
    calls = 0

    def forbidden(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("unsupported policy called assessment")

    monkeypatch.setattr(assessment_module, "assess_publication_pair", forbidden)
    candidate_failure = _failure(
        _crafted_result(generation, policy=changed_candidate_policy),
        observations,
    )
    assessment_failure = _failure(generation, observations, changed_assessment_policy)
    untyped_failure = _failure(generation, observations, object())
    assert _codes(candidate_failure) == ("unsupported_candidate_policy",)
    assert isinstance(candidate_failure.conflicts[0].subject, UnsupportedCandidatePolicySubject)
    assert _codes(assessment_failure) == ("unsupported_assessment_policy",)
    assert isinstance(assessment_failure.conflicts[0].subject, UnsupportedAssessmentPolicySubject)
    assert _codes(untyped_failure) == ("unsupported_assessment_policy",)
    assert calls == 0


def test_unsupported_generation_result_is_typed_and_zero_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observation = _available(_ref("fixture_portal", "a"), 0)

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("unsupported generation result called assessment")

    monkeypatch.setattr(assessment_module, "assess_publication_pair", forbidden)
    failure = _failure(object(), (observation,))
    assert _codes(failure) == ("unsupported_generation_result",)
    assert failure.conflicts[0].subject == "generation_result"


def test_candidate_policy_binding_is_checked_without_regeneration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations, generation = _two_selective_candidates()
    candidate = generation.candidates[0]
    changed_identity = DuplicateCandidateIdentity(
        candidate.identity.pair,
        candidate.identity.left_observation_key,
        candidate.identity.right_observation_key,
        DuplicateCandidatePolicyVersion("fictional-other-candidate-policy@1"),
    )
    changed_candidate = object.__new__(DuplicateCandidate)
    object.__setattr__(changed_candidate, "identity", changed_identity)
    object.__setattr__(changed_candidate, "blocking_matches", candidate.blocking_matches)
    crafted = _crafted_result(
        generation,
        candidates=(changed_candidate, *generation.candidates[1:]),
    )

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("candidate binding failure called assessment")

    monkeypatch.setattr(assessment_module, "assess_publication_pair", forbidden)
    monkeypatch.setattr(
        real_estate_parser,
        "generate_duplicate_candidates",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("regeneration called")),
    )
    failure = _failure(crafted, observations)
    subjects = tuple(
        cast(CandidateBindingMismatchSubject, conflict.subject)
        for conflict in failure.conflicts
        if conflict.code == "candidate_binding_mismatch"
    )
    assert CandidateBindingMismatchKind.CANDIDATE_POLICY_MISMATCH in tuple(
        subject.kind for subject in subjects
    )


def test_duplicate_and_noncanonical_candidate_identities_are_preflight_conflicts() -> None:
    observations, generation = _two_selective_candidates()
    duplicate = _crafted_result(
        generation,
        candidates=(generation.candidates[0], generation.candidates[0]),
    )
    duplicate_failure = _failure(duplicate, observations)
    duplicate_kinds = tuple(
        cast(CandidateBindingMismatchSubject, conflict.subject).kind
        for conflict in duplicate_failure.conflicts
    )
    assert duplicate_kinds == (CandidateBindingMismatchKind.DUPLICATE_CANDIDATE_IDENTITY,)

    reversed_result = _crafted_result(
        generation,
        candidates=tuple(reversed(generation.candidates)),
    )
    order_failure = _failure(reversed_result, observations)
    assert tuple(
        cast(CandidateBindingMismatchSubject, conflict.subject).kind
        for conflict in order_failure.conflicts
    ) == (
        CandidateBindingMismatchKind.NON_CANONICAL_CANDIDATE_ORDER,
        CandidateBindingMismatchKind.NON_CANONICAL_CANDIDATE_ORDER,
    )


def test_unexpected_not_assessed_continues_full_pass_and_is_atomic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations, generation = _two_selective_candidates()
    calls: list[PublicationPair] = []
    original = assess_publication_pair

    def fake(
        first: AvailableObservation,
        second: AvailableObservation,
        policy: DuplicatePolicy,
    ) -> object:
        pair = PublicationPair(first.key.reference, second.key.reference)
        calls.append(pair)
        if len(calls) == 1:
            return PairNotAssessed(
                pair,
                first.key,
                second.key,
                real_estate_parser.DuplicateReasonCode("side_not_available"),
            )
        return original(first, second, policy)

    monkeypatch.setattr(assessment_module, "assess_publication_pair", fake)
    failure = _failure(generation, observations)
    assert len(calls) == len(generation.candidates) == 2
    assert _codes(failure) == ("unexpected_pair_not_assessed",)
    assert isinstance(failure.conflicts[0].subject, UnexpectedPairNotAssessedSubject)
    assert not hasattr(failure, "item_outcomes")
    assert not hasattr(failure, "batch")


def test_pair_failure_and_unsupported_result_are_both_collected_after_full_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations, generation = _two_selective_candidates()
    calls = 0
    nested = DuplicateAssessmentConflict(
        "DUPLICATE_ASSESSMENT_CONFLICT",
        "same_publication_ref",
        observations[0].key.reference,
    )

    def fake(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            return PairAssessmentFailure((nested,))
        return object()

    monkeypatch.setattr(assessment_module, "assess_publication_pair", fake)
    failure = _failure(generation, observations)
    assert calls == 2
    assert _codes(failure) == (
        "downstream_assessment_conflict",
        "downstream_assessment_conflict",
    )
    subjects = tuple(
        cast(DownstreamAssessmentConflictSubject, conflict.subject)
        for conflict in failure.conflicts
    )
    assert tuple(subject.kind for subject in subjects) == (
        DownstreamAssessmentConflictKind.PAIR_ASSESSMENT_FAILURE,
        DownstreamAssessmentConflictKind.UNSUPPORTED_DOWNSTREAM_RESULT,
    )
    assert subjects[0].assessment_conflicts == (nested,)
    assert subjects[1].assessment_conflicts == ()


def test_malformed_success_is_a_typed_downstream_binding_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations, generation = _two_selective_candidates()
    wrong_success = assess_publication_pair(observations[1], observations[2])
    assert isinstance(wrong_success, PairAssessmentSuccess)
    calls = 0

    def fake(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return wrong_success

    monkeypatch.setattr(assessment_module, "assess_publication_pair", fake)
    failure = _failure(generation, observations)
    assert calls == len(generation.candidates)
    assert all(
        cast(DownstreamAssessmentConflictSubject, conflict.subject).kind
        is DownstreamAssessmentConflictKind.SUCCESS_BINDING_MISMATCH
        for conflict in failure.conflicts
    )


def test_batch_and_item_constructor_invariants_reject_partial_or_misbound_content() -> None:
    observations, generation = _two_selective_candidates()
    outcome = assess_duplicate_candidate_batch(
        generation, observations, PUBLICATION_DUPLICATE_POLICY_V1
    )
    assert isinstance(outcome, DuplicateCandidateAssessmentBatchSuccess)
    batch = outcome.batch
    with pytest.raises(ValueError):
        DuplicateCandidateAssessmentBatch(
            batch.identity,
            batch.generation_result,
            batch.assessment_policy,
            batch.item_outcomes[:-1],
        )
    with pytest.raises(TypeError):
        DuplicateCandidateAssessmentBatch(
            batch.identity,
            batch.generation_result,
            batch.assessment_policy,
            cast(Any, list(batch.item_outcomes)),
        )
    with pytest.raises(ValueError):
        DuplicateCandidateAssessmentItemOutcome(
            batch.item_outcomes[1].identity,
            batch.item_outcomes[0].candidate,
            batch.item_outcomes[0].result,
        )
    with pytest.raises(ValueError):
        DuplicateCandidateAssessmentBatchFailure(())


def test_validated_input_and_configuration_require_exact_canonical_bound_content() -> None:
    observations, generation = _two_selective_candidates()
    canonical = tuple(sorted(observations, key=lambda item: item.key.reference.source_id.value))
    validated = DuplicateCandidateAssessmentBatchInput(
        generation,
        canonical,
        PUBLICATION_DUPLICATE_POLICY_V1,
    )
    assert validated.configuration == DuplicateCandidateAssessmentBatchConfiguration(
        generation.configuration,
        PUBLICATION_DUPLICATE_POLICY_V1,
    )
    with pytest.raises(ValueError):
        DuplicateCandidateAssessmentBatchInput(
            generation,
            tuple(reversed(canonical)),
            PUBLICATION_DUPLICATE_POLICY_V1,
        )
    with pytest.raises(TypeError):
        DuplicateCandidateAssessmentBatchInput(
            generation,
            cast(Any, list(canonical)),
            PUBLICATION_DUPLICATE_POLICY_V1,
        )


def test_subject_and_conflict_constructor_invariants_are_exact() -> None:
    observation = _available(_ref("fixture_portal", "a"), 0)
    generation = _generation((observation,))
    identity = DuplicateCandidateAssessmentBatchIdentity(
        generation.identity,
        PUBLICATION_DUPLICATE_POLICY_V1.version,
    )
    with pytest.raises(ValueError):
        GenerationCurrentKeysMismatchSubject(
            GenerationCurrentKeysMismatchKind.MISSING_GENERATION_KEY,
            observation.key.reference,
            observation.key,
            observation.key,
        )
    with pytest.raises(ValueError):
        DuplicateCandidateAssessmentBatchConflict(
            "DUPLICATE_CANDIDATE_ASSESSMENT_BATCH_CONFLICT",
            "batch_identity_content_conflict",
            "generation_result",
        )
    with pytest.raises(TypeError):
        DownstreamAssessmentConflictSubject(
            cast(Any, object()),
            DownstreamAssessmentConflictKind.SUCCESS_BINDING_MISMATCH,
            (),
        )
    conflict = DuplicateCandidateAssessmentBatchConflict(
        "DUPLICATE_CANDIDATE_ASSESSMENT_BATCH_CONFLICT",
        "batch_identity_content_conflict",
        identity,
    )
    assert conflict.subject == identity


def test_records_are_frozen_slots_exported_and_collections_are_tuple_only() -> None:
    record_types = (
        DuplicateCandidateAssessmentBatchConfiguration,
        DuplicateCandidateAssessmentBatchInput,
        DuplicateCandidateAssessmentBatchIdentity,
        DuplicateCandidateAssessmentItemIdentity,
        DuplicateCandidateAssessmentItemOutcome,
        DuplicateCandidateAssessmentBatch,
        DuplicateCandidateAssessmentBatchSuccess,
        GenerationCurrentKeysMismatchSubject,
        CandidateBindingMismatchSubject,
        UnsupportedCandidatePolicySubject,
        UnsupportedAssessmentPolicySubject,
        UnexpectedPairNotAssessedSubject,
        DownstreamAssessmentConflictSubject,
        DuplicateCandidateAssessmentBatchConflict,
        DuplicateCandidateAssessmentBatchFailure,
    )
    for record_type in record_types:
        assert is_dataclass(record_type)
        assert cast(Any, record_type).__dataclass_params__.frozen
        assert "__slots__" in record_type.__dict__
        assert record_type.__name__ in batch_module.__all__

    observation = _available(_ref("fixture_portal", "solo"), 0)
    outcome = assess_duplicate_candidate_batch(
        _generation((observation,)),
        (observation,),
        PUBLICATION_DUPLICATE_POLICY_V1,
    )
    assert isinstance(outcome, DuplicateCandidateAssessmentBatchSuccess)
    with pytest.raises(FrozenInstanceError):
        cast(Any, outcome.batch).assessment_policy = object()
    assert not hasattr(outcome.batch, "__dict__")


def test_public_surface_has_no_storage_external_or_physical_property_api() -> None:
    public_names = set(batch_module.__all__)
    assert "assess_duplicate_candidate_batch" in public_names
    assert public_names <= set(real_estate_parser.__all__)
    forbidden = (
        "storage",
        "repository",
        "database",
        "json",
        "pydantic",
        "filesystem",
        "cli",
        "cluster",
        "merge",
        "winner",
        "property",
        "transitive",
        "generate_duplicate_candidates",
    )
    assert not any(token in name.lower() for name in public_names for token in forbidden)

    source = Path(batch_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(
        token in module.lower()
        for module in imported_modules
        for token in ("json", "pydantic", "sqlite", "sqlalchemy", "requests", "http")
    )


def test_pairwise_batch_does_not_create_missing_transitive_pair() -> None:
    observations, generation = _two_selective_candidates()
    outcome = assess_duplicate_candidate_batch(
        generation, observations, PUBLICATION_DUPLICATE_POLICY_V1
    )
    assert isinstance(outcome, DuplicateCandidateAssessmentBatchSuccess)
    assessed_pairs = {item.result.assessment.identity.pair for item in outcome.batch.item_outcomes}
    all_refs = {observation.key.reference for observation in observations}
    assert len(assessed_pairs) == 2
    assert len(all_refs) == 3
    absent_pair = PublicationPair(observations[1].key.reference, observations[2].key.reference)
    assert absent_pair not in assessed_pairs


def test_future_consumer_conflict_codes_accept_only_exact_item_and_batch_identities() -> None:
    observations, generation = _two_selective_candidates()
    success = assess_duplicate_candidate_batch(
        generation, observations, PUBLICATION_DUPLICATE_POLICY_V1
    )
    assert isinstance(success, DuplicateCandidateAssessmentBatchSuccess)
    item_identity = success.batch.item_outcomes[0].identity
    batch_identity = success.batch.identity
    item_conflict = DuplicateCandidateAssessmentBatchConflict(
        "DUPLICATE_CANDIDATE_ASSESSMENT_BATCH_CONFLICT",
        "item_identity_content_conflict",
        item_identity,
    )
    batch_conflict = DuplicateCandidateAssessmentBatchConflict(
        "DUPLICATE_CANDIDATE_ASSESSMENT_BATCH_CONFLICT",
        "batch_identity_content_conflict",
        batch_identity,
    )
    failure = DuplicateCandidateAssessmentBatchFailure((item_conflict, batch_conflict))
    assert failure.conflicts == (item_conflict, batch_conflict)


def test_candidate_and_assessment_policy_versions_remain_distinct_coordinates() -> None:
    observation = _available(_ref("fixture_portal", "solo"), 0)
    generation = _generation((observation,))
    identity = DuplicateCandidateAssessmentBatchIdentity(
        generation.identity,
        PUBLICATION_DUPLICATE_POLICY_V1.version,
    )
    assert isinstance(
        identity.generation_identity.candidate_policy_version,
        DuplicateCandidatePolicyVersion,
    )
    assert isinstance(identity.assessment_policy_version, DuplicatePolicyVersion)
    assert identity.generation_identity.candidate_policy_version.value != (
        identity.assessment_policy_version.value
    )


def test_invalid_failure_conflict_order_and_duplicates_are_rejected() -> None:
    observations, generation = _two_selective_candidates()
    first_identity = DuplicateCandidateAssessmentItemIdentity(
        DuplicateCandidateAssessmentBatchIdentity(
            generation.identity,
            PUBLICATION_DUPLICATE_POLICY_V1.version,
        ),
        generation.candidates[0].identity,
    )
    first = DuplicateCandidateAssessmentBatchConflict(
        "DUPLICATE_CANDIDATE_ASSESSMENT_BATCH_CONFLICT",
        "item_identity_content_conflict",
        first_identity,
    )
    second = DuplicateCandidateAssessmentBatchConflict(
        "DUPLICATE_CANDIDATE_ASSESSMENT_BATCH_CONFLICT",
        "batch_identity_content_conflict",
        first_identity.batch_identity,
    )
    with pytest.raises(ValueError):
        DuplicateCandidateAssessmentBatchFailure((second, first))
    with pytest.raises(ValueError):
        DuplicateCandidateAssessmentBatchFailure((first, first))


def test_no_implicit_assessment_policy_argument_exists() -> None:
    observation = _available(_ref("fixture_portal", "solo"), 0)
    generation = _generation((observation,))
    with pytest.raises(TypeError):
        cast(Any, assess_duplicate_candidate_batch)(generation, (observation,))


def test_generation_current_mismatch_subject_rejects_cross_reference_keys() -> None:
    first = _available(_ref("fixture_portal", "a"), 0)
    second = _available(_ref("mirror_fixture", "b"), 1)
    with pytest.raises(ValueError):
        GenerationCurrentKeysMismatchSubject(
            GenerationCurrentKeysMismatchKind.MISSING_GENERATION_KEY,
            first.key.reference,
            second.key,
            None,
        )


def test_item_identity_rejects_candidate_policy_from_another_generation() -> None:
    observations, generation = _two_selective_candidates()
    candidate = generation.candidates[0]
    other_identity = DuplicateCandidateIdentity(
        candidate.identity.pair,
        candidate.identity.left_observation_key,
        candidate.identity.right_observation_key,
        DuplicateCandidatePolicyVersion("fictional-other-policy@1"),
    )
    batch_identity = DuplicateCandidateAssessmentBatchIdentity(
        generation.identity,
        PUBLICATION_DUPLICATE_POLICY_V1.version,
    )
    with pytest.raises(ValueError):
        DuplicateCandidateAssessmentItemIdentity(batch_identity, other_identity)


def test_batch_identity_content_is_not_a_hash_or_arrival_order() -> None:
    observations, generation = _two_selective_candidates()
    identity = DuplicateCandidateAssessmentBatchIdentity(
        generation.identity,
        PUBLICATION_DUPLICATE_POLICY_V1.version,
    )
    assert (
        identity.generation_identity.canonical_input_keys
        == generation.identity.canonical_input_keys
    )
    assert not hasattr(identity, "hash")
    assert not hasattr(identity, "arrival_order")
    assert not hasattr(identity, "revision")
    with pytest.raises(ValueError):
        DuplicateCandidateAssessmentBatchIdentity(
            generation.identity,
            DuplicatePolicyVersion("fictional-other-assessment-policy@1"),
        )


def test_replace_cannot_silently_change_complete_batch_content() -> None:
    observations, generation = _two_selective_candidates()
    success = assess_duplicate_candidate_batch(
        generation, observations, PUBLICATION_DUPLICATE_POLICY_V1
    )
    assert isinstance(success, DuplicateCandidateAssessmentBatchSuccess)
    with pytest.raises(ValueError):
        replace(success.batch, item_outcomes=())
