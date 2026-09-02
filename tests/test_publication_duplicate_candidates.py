from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, is_dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

import real_estate_parser
import real_estate_parser.publication_duplicate_candidates as candidate_module
from real_estate_parser import (
    PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1,
    PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION,
    Area,
    AreaLocationTextBlockingKey,
    AreaRoomsBlockingKey,
    AvailabilityRuleVersion,
    AvailableObservation,
    BlockingComponentNonParticipation,
    BlockingComponentState,
    BlockingNonParticipation,
    BucketPairLimit,
    DirectSourceStateEvidence,
    DuplicateCandidate,
    DuplicateCandidateGenerationConfiguration,
    DuplicateCandidateGenerationFailure,
    DuplicateCandidateGenerationIdentity,
    DuplicateCandidateGenerationResult,
    DuplicateCandidateGenerationSuccess,
    DuplicateCandidateIdentity,
    DuplicateCandidatePolicy,
    DuplicateCandidatePolicyVersion,
    DuplicateCandidateReasonCode,
    DuplicateCandidateRule,
    DuplicateCandidateRuleId,
    DuplicateCandidateRuleVersion,
    DuplicatePublicationRefSubject,
    InputLocation,
    LocationText,
    Missing,
    MissingProvenance,
    MoneyAmount,
    NormalizationRuleVersion,
    NormalizedListing,
    ObservationKey,
    ObservedAt,
    OversizedBucket,
    Present,
    PublicationId,
    PublicationPair,
    PublicationRef,
    RoomCount,
    SourceId,
    SourceUrl,
    TracedValue,
    UnavailableObservation,
    Unsupported,
    UnsupportedObservationSubject,
    UnsupportedProvenance,
    ValueProvenance,
    generate_duplicate_candidates,
)
from real_estate_parser.normalization import Currency

RULE = NormalizationRuleVersion("fictional-candidate-field@1")
AVAILABILITY_RULE = AvailabilityRuleVersion("fictional-candidate-availability@1")
CONFIGURATION = DuplicateCandidateGenerationConfiguration(
    PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1,
    BucketPairLimit(10),
)


def _ref(source: str, publication: str) -> PublicationRef:
    return PublicationRef(SourceId(source), PublicationId(publication))


def _at(minute: int) -> ObservedAt:
    return ObservedAt(datetime(2026, 9, 2, 16, minute, tzinfo=UTC))


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


def _missing(reference: PublicationRef, observed_at: ObservedAt, field: str) -> Missing:
    return Missing(
        MissingProvenance(
            source_id=reference.source_id,
            publication_id=reference.publication_id,
            input_path=InputLocation("listings", 0, (field,)),
            source_field=field,
            observed_at=observed_at,
            normalization_rule_version=RULE,
        )
    )


def _unsupported(
    reference: PublicationRef,
    observed_at: ObservedAt,
    field: str,
    reason: str,
) -> Unsupported:
    return Unsupported(
        UnsupportedProvenance(
            source_id=reference.source_id,
            publication_id=reference.publication_id,
            input_path=InputLocation("listings", 0, (field,)),
            source_field=field,
            raw_value="fictional-unsupported",
            observed_at=observed_at,
            normalization_rule_version=RULE,
            reason_code=reason,
        )
    )


def _available(
    reference: PublicationRef,
    minute: int,
    *,
    area: int | None = 4_700,
    rooms: int | None = 2,
    location: str | None = "Fictional Candidate Quarter",
    unsupported_area: str | None = None,
    unsupported_rooms: str | None = None,
    unsupported_location: str | None = None,
) -> AvailableObservation:
    observed_at = _at(minute)
    source_url = f"https://{reference.source_id.value}.example/{reference.publication_id.value}"
    if unsupported_area is not None:
        area_outcome: Present[Area] | Missing | Unsupported = _unsupported(
            reference, observed_at, "total_area", unsupported_area
        )
    elif area is None:
        area_outcome = _missing(reference, observed_at, "total_area")
    else:
        area_outcome = _present(Area(area), reference, observed_at, "total_area", str(area))
    if unsupported_rooms is not None:
        rooms_outcome: Present[RoomCount] | Missing | Unsupported = _unsupported(
            reference, observed_at, "rooms", unsupported_rooms
        )
    elif rooms is None:
        rooms_outcome = _missing(reference, observed_at, "rooms")
    else:
        rooms_outcome = _present(RoomCount(rooms), reference, observed_at, "rooms", str(rooms))
    if unsupported_location is not None:
        location_outcome: Present[LocationText] | Missing | Unsupported = _unsupported(
            reference, observed_at, "location_text", unsupported_location
        )
    elif location is None:
        location_outcome = _missing(reference, observed_at, "location_text")
    else:
        location_outcome = _present(
            LocationText(location), reference, observed_at, "location_text", location
        )
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
        location_text=location_outcome,
        price_amount=_present(
            MoneyAmount(11_000_000), reference, observed_at, "price_amount", "110000.00"
        ),
        currency=_present(Currency("RUB"), reference, observed_at, "currency", "RUB"),
        total_area=area_outcome,
        rooms=rooms_outcome,
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


def _success(
    observations: tuple[AvailableObservation | UnavailableObservation, ...],
    configuration: DuplicateCandidateGenerationConfiguration = CONFIGURATION,
) -> DuplicateCandidateGenerationResult:
    outcome = generate_duplicate_candidates(observations, configuration)
    assert isinstance(outcome, DuplicateCandidateGenerationSuccess)
    return outcome.result


def _failure(
    observations: Any,
    configuration: DuplicateCandidateGenerationConfiguration = CONFIGURATION,
) -> DuplicateCandidateGenerationFailure:
    outcome = generate_duplicate_candidates(observations, configuration)
    assert isinstance(outcome, DuplicateCandidateGenerationFailure)
    return outcome


def _codes(failure: DuplicateCandidateGenerationFailure) -> tuple[str, ...]:
    return tuple(conflict.code for conflict in failure.conflicts)


@pytest.mark.parametrize(
    "code_type",
    [
        DuplicateCandidatePolicyVersion,
        DuplicateCandidateRuleId,
        DuplicateCandidateRuleVersion,
        DuplicateCandidateReasonCode,
    ],
)
@pytest.mark.parametrize("invalid", ["", "has space", "line\nbreak", "é", "x" * 129])
def test_candidate_codes_are_safe_opaque_ascii(code_type: Any, invalid: str) -> None:
    with pytest.raises(ValueError):
        code_type(invalid)


def test_policy_v1_has_exact_separate_version_rules_components_and_order() -> None:
    policy = PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1
    assert policy.version.value == "publication-duplicate-candidate-policy@1"
    assert tuple(rule.rule_id.value for rule in policy.rules) == (
        "area-rooms-exact-block",
        "area-location-text-exact-block",
    )
    assert tuple(rule.rule_version.value for rule in policy.rules) == (
        "candidate-area-rooms@1",
        "candidate-area-location-text@1",
    )
    assert tuple(rule.components for rule in policy.rules) == (
        ("total_area", "rooms"),
        ("total_area", "location_text"),
    )
    assert policy.version.value != "publication-duplicate-policy@1"


@pytest.mark.parametrize("invalid", [True, 0, -1, 1.0])
def test_bucket_pair_limit_accepts_only_positive_exact_int(invalid: object) -> None:
    with pytest.raises(ValueError):
        BucketPairLimit(cast(Any, invalid))
    assert BucketPairLimit(1).value == 1


def test_changed_or_reordered_rules_return_stable_unsupported_policy_failure() -> None:
    changed = DuplicateCandidatePolicy(
        PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION,
        tuple(reversed(PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1.rules)),
    )
    configuration = DuplicateCandidateGenerationConfiguration(changed, BucketPairLimit(3))
    failure = _failure((_available(_ref("alpha_fixture", "a"), 0),), configuration)
    assert _codes(failure) == ("unsupported_candidate_policy",)
    assert failure.conflicts[0].subject == changed.version


def test_generation_defensively_returns_invalid_limit_conflict_without_partial_result() -> None:
    invalid_limit = object.__new__(BucketPairLimit)
    object.__setattr__(invalid_limit, "value", False)
    configuration = object.__new__(DuplicateCandidateGenerationConfiguration)
    object.__setattr__(
        configuration,
        "policy",
        PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1,
    )
    object.__setattr__(configuration, "bucket_pair_limit", invalid_limit)
    failure = _failure(
        (_available(_ref("alpha_fixture", "invalid-limit"), 0),),
        configuration,
    )
    assert _codes(failure) == ("invalid_bucket_pair_limit",)
    assert not hasattr(failure, "result")


def test_blocking_keys_are_structural_typed_and_reject_wrong_rule_binding() -> None:
    area_rooms_rule, area_location_rule = PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1.rules
    first = AreaRoomsBlockingKey(
        area_rooms_rule.rule_id, area_rooms_rule.rule_version, Area(4_700), RoomCount(2)
    )
    same = AreaRoomsBlockingKey(
        area_rooms_rule.rule_id, area_rooms_rule.rule_version, Area(4_700), RoomCount(2)
    )
    location = AreaLocationTextBlockingKey(
        area_location_rule.rule_id,
        area_location_rule.rule_version,
        Area(4_700),
        LocationText("Fictional Candidate Quarter"),
    )
    assert first == same
    assert cast(object, first) != location
    assert not hasattr(first, "float_value")
    assert not hasattr(first, "digest")
    with pytest.raises(ValueError):
        AreaRoomsBlockingKey(
            area_location_rule.rule_id,
            area_location_rule.rule_version,
            Area(4_700),
            RoomCount(2),
        )


def test_input_shape_empty_unavailable_and_unsupported_are_atomic() -> None:
    reference = _ref("alpha_fixture", "a")
    assert _codes(_failure(cast(Any, [_available(reference, 0)]))) == ("observations_not_tuple",)
    assert _codes(_failure(())) == ("empty_generation_input",)
    unavailable_failure = _failure((_unavailable(reference, 0),))
    assert _codes(unavailable_failure) == ("observation_not_available",)
    assert unavailable_failure.conflicts[0].subject == ObservationKey(reference, _at(0))
    unsupported_failure = _failure(cast(Any, (object(),)))
    assert _codes(unsupported_failure) == ("unsupported_observation",)
    assert unsupported_failure.conflicts[0].subject == UnsupportedObservationSubject(0)
    for failure in (unavailable_failure, unsupported_failure):
        assert not hasattr(failure, "result")
        assert not hasattr(failure, "candidates")
        assert not hasattr(failure, "non_participations")
        assert not hasattr(failure, "oversized_buckets")


def test_exact_repeat_same_key_conflict_and_two_keys_same_ref_are_distinct() -> None:
    reference = _ref("alpha_fixture", "a")
    original = _available(reference, 0)
    exact_repeat = _failure((original, original))
    assert _codes(exact_repeat) == ("duplicate_publication_ref",)
    subject = exact_repeat.conflicts[0].subject
    assert isinstance(subject, DuplicatePublicationRefSubject)
    assert subject.observation_keys == (original.key, original.key)

    changed = _available(reference, 0, rooms=3)
    same_key_conflict = _failure((original, changed))
    assert _codes(same_key_conflict) == ("observation_key_content_conflict",)
    assert same_key_conflict.conflicts[0].subject == original.key

    other_key = _available(reference, 1)
    duplicate_reference = _failure((original, other_key))
    assert _codes(duplicate_reference) == ("duplicate_publication_ref",)


def test_multiple_simultaneous_conflicts_are_unique_canonical_and_deterministic() -> None:
    first_ref = _ref("alpha_fixture", "a")
    second_ref = _ref("beta_fixture", "b")
    original = _available(first_ref, 0)
    conflicts = _failure(
        cast(
            Any,
            (
                object(),
                _unavailable(second_ref, 2),
                original,
                _available(first_ref, 0, rooms=3),
                _available(first_ref, 1),
            ),
        )
    )
    assert _codes(conflicts) == (
        "observation_not_available",
        "unsupported_observation",
        "observation_key_content_conflict",
        "duplicate_publication_ref",
    )
    assert len(conflicts.conflicts) == len(set(conflicts.conflicts))
    assert conflicts == _failure(
        cast(
            Any,
            (
                object(),
                _unavailable(second_ref, 2),
                original,
                _available(first_ref, 0, rooms=3),
                _available(first_ref, 1),
            ),
        )
    )


def test_both_passes_union_one_pair_with_policy_ordered_exact_side_matches() -> None:
    left = _available(_ref("alpha_fixture", "a"), 0)
    right = _available(_ref("beta_fixture", "b"), 1)
    result = _success((right, left))
    assert result.identity.canonical_input_keys == (left.key, right.key)
    assert result.configuration == CONFIGURATION
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.identity.pair == PublicationPair(left.key.reference, right.key.reference)
    assert candidate.identity.left_observation_key == left.key
    assert candidate.identity.right_observation_key == right.key
    assert tuple(type(match.blocking_key) for match in candidate.blocking_matches) == (
        AreaRoomsBlockingKey,
        AreaLocationTextBlockingKey,
    )


@pytest.mark.parametrize(
    ("right_rooms", "right_location", "expected_key_type"),
    [
        (2, "Other Fictional Quarter", AreaRoomsBlockingKey),
        (3, "Fictional Candidate Quarter", AreaLocationTextBlockingKey),
    ],
)
def test_each_pass_can_generate_a_candidate_separately(
    right_rooms: int,
    right_location: str,
    expected_key_type: type[object],
) -> None:
    left = _available(_ref("alpha_fixture", "a"), 0)
    right = _available(
        _ref("beta_fixture", "b"),
        1,
        rooms=right_rooms,
        location=right_location,
    )
    result = _success((left, right))
    assert len(result.candidates) == 1
    assert len(result.candidates[0].blocking_matches) == 1
    assert isinstance(result.candidates[0].blocking_matches[0].blocking_key, expected_key_type)


def test_same_source_cross_source_and_no_shared_key_success_are_explicit() -> None:
    left = _available(_ref("alpha_fixture", "a"), 0)
    same_source = _available(_ref("alpha_fixture", "b"), 1)
    cross_source = _available(_ref("beta_fixture", "c"), 2)
    result = _success((cross_source, same_source, left))
    assert len(result.candidates) == 3
    assert PublicationPair(left.key.reference, same_source.key.reference) in {
        candidate.identity.pair for candidate in result.candidates
    }
    empty = _success(
        (
            left,
            _available(
                _ref("gamma_fixture", "d"),
                3,
                area=5_100,
                rooms=4,
                location="Separate Fictional Quarter",
            ),
        )
    )
    assert empty.candidates == ()
    assert empty.oversized_buckets == ()


@pytest.mark.parametrize(
    ("field", "state", "reason"),
    [
        ("area", "missing", None),
        ("area", "unsupported", "area_not_supported"),
        ("rooms", "missing", None),
        ("rooms", "unsupported", "rooms_not_supported"),
        ("location", "missing", None),
        ("location", "unsupported", "location_not_supported"),
    ],
)
def test_missing_unsupported_matrix_preserves_component_order_and_exact_reason(
    field: str, state: str, reason: str | None
) -> None:
    reference = _ref("alpha_fixture", f"{field}-{state}")
    if field == "area":
        observation = _available(
            reference,
            0,
            area=None if state == "missing" else 4_700,
            unsupported_area=reason,
        )
        component_field = "total_area"
    elif field == "rooms":
        observation = _available(
            reference,
            0,
            rooms=None if state == "missing" else 2,
            unsupported_rooms=reason,
        )
        component_field = "rooms"
    else:
        observation = _available(
            reference,
            0,
            location=None if state == "missing" else "Fictional Candidate Quarter",
            unsupported_location=reason,
        )
        component_field = "location_text"
    result = _success((observation,))
    affected = tuple(
        item
        for item in result.non_participations
        if any(component.field == component_field for component in item.reasons)
    )
    expected_count = 2 if field == "area" else 1
    assert len(affected) == expected_count
    for item in affected:
        component = next(
            component for component in item.reasons if component.field == component_field
        )
        expected_state = (
            BlockingComponentState.MISSING
            if state == "missing"
            else BlockingComponentState.UNSUPPORTED
        )
        assert component.state is expected_state
        actual_reason = (
            None
            if component.unsupported_reason_code is None
            else component.unsupported_reason_code.value
        )
        assert actual_reason == reason


def test_multiple_non_participation_reasons_and_alternate_pass() -> None:
    incomplete = _available(
        _ref("alpha_fixture", "a"),
        0,
        area=None,
        rooms=None,
        unsupported_location="location_not_supported",
    )
    result = _success((incomplete,))
    assert tuple(
        tuple(reason.field for reason in item.reasons) for item in result.non_participations
    ) == (("total_area", "rooms"), ("total_area", "location_text"))

    left = _available(_ref("beta_fixture", "b"), 1, rooms=None)
    right = _available(_ref("gamma_fixture", "c"), 2, rooms=None)
    alternate = _success((left, right))
    assert len(alternate.non_participations) == 2
    assert len(alternate.candidates) == 1
    assert isinstance(
        alternate.candidates[0].blocking_matches[0].blocking_key,
        AreaLocationTextBlockingKey,
    )


def test_present_mismatch_is_not_non_participation() -> None:
    result = _success(
        (
            _available(_ref("alpha_fixture", "a"), 0, rooms=1, location="Quarter A"),
            _available(_ref("beta_fixture", "b"), 1, rooms=2, location="Quarter B"),
        )
    )
    assert result.non_participations == ()
    assert result.candidates == ()


def test_bucket_size_one_boundary_and_whole_oversized_skip() -> None:
    one = _available(_ref("alpha_fixture", "a"), 0)
    singleton = _success(
        (one,),
        DuplicateCandidateGenerationConfiguration(
            PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1, BucketPairLimit(1)
        ),
    )
    assert singleton.candidates == ()
    assert singleton.oversized_buckets == ()

    observations = tuple(
        _available(_ref(f"source_{index}", f"item-{index}"), index) for index in range(3)
    )
    exact = _success(
        observations,
        DuplicateCandidateGenerationConfiguration(
            PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1, BucketPairLimit(3)
        ),
    )
    assert len(exact.candidates) == 3
    assert all(len(candidate.blocking_matches) == 2 for candidate in exact.candidates)

    oversized = _success(
        observations,
        DuplicateCandidateGenerationConfiguration(
            PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1, BucketPairLimit(2)
        ),
    )
    assert oversized.candidates == ()
    assert len(oversized.oversized_buckets) == 2
    assert {bucket.prospective_pair_count for bucket in oversized.oversized_buckets} == {3}
    expected_member_keys = tuple(observation.key for observation in observations)
    assert all(bucket.member_keys == expected_member_keys for bucket in oversized.oversized_buckets)
    assert all(
        bucket.reason_code.value == "prospective_pair_count_exceeds_limit"
        for bucket in oversized.oversized_buckets
    )
    assert oversized == _success(
        tuple(reversed(observations)),
        DuplicateCandidateGenerationConfiguration(
            PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1, BucketPairLimit(2)
        ),
    )


def test_oversized_one_rule_allows_alternate_candidate_without_skipped_match() -> None:
    first = _available(_ref("alpha_fixture", "a"), 0, location="Shared Small Bucket")
    second = _available(_ref("beta_fixture", "b"), 1, location="Shared Small Bucket")
    third = _available(_ref("gamma_fixture", "c"), 2, location="Other Location")
    result = _success(
        (third, second, first),
        DuplicateCandidateGenerationConfiguration(
            PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1, BucketPairLimit(2)
        ),
    )
    assert len(result.oversized_buckets) == 1
    oversized = result.oversized_buckets[0]
    assert isinstance(oversized.key, AreaRoomsBlockingKey)
    assert oversized.prospective_pair_count == 3
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.identity.pair == PublicationPair(first.key.reference, second.key.reference)
    assert tuple(type(match.blocking_key) for match in candidate.blocking_matches) == (
        AreaLocationTextBlockingKey,
    )
    assert oversized.key not in {match.blocking_key for match in candidate.blocking_matches}


def test_new_observed_at_changes_candidate_and_generation_identity() -> None:
    left = _available(_ref("alpha_fixture", "a"), 0)
    right = _available(_ref("beta_fixture", "b"), 1)
    current = _success((left, right))
    newer_right = _available(right.key.reference, 2)
    newer = _success((left, newer_right))
    assert current.identity != newer.identity
    assert current.candidates[0].identity != newer.candidates[0].identity


def test_generation_attempts_and_prospective_counts_obey_adr_bound() -> None:
    observations = tuple(
        _available(
            _ref(f"source_{index}", f"item-{index}"),
            index,
            location=f"Location {index % 2}",
        )
        for index in range(6)
    )
    limit = BucketPairLimit(4)
    result = _success(
        observations,
        DuplicateCandidateGenerationConfiguration(PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1, limit),
    )
    materialized_attempts = sum(len(candidate.blocking_matches) for candidate in result.candidates)
    assert materialized_attempts <= 2 * len(observations) * limit.value
    for bucket in result.oversized_buckets:
        member_count = len(bucket.member_keys)
        assert bucket.prospective_pair_count == member_count * (member_count - 1) // 2
        assert bucket.prospective_pair_count > limit.value
        assert all(
            match.blocking_key != bucket.key
            for candidate in result.candidates
            for match in candidate.blocking_matches
        )


def test_public_records_are_frozen_slots_tuple_only_exported_and_strictly_bound() -> None:
    records = (
        AreaRoomsBlockingKey,
        AreaLocationTextBlockingKey,
        BlockingComponentNonParticipation,
        BlockingNonParticipation,
        BucketPairLimit,
        DuplicateCandidate,
        DuplicateCandidateGenerationConfiguration,
        DuplicateCandidateGenerationFailure,
        DuplicateCandidateGenerationIdentity,
        DuplicateCandidateGenerationResult,
        DuplicateCandidateGenerationSuccess,
        DuplicateCandidateIdentity,
        DuplicateCandidatePolicy,
        DuplicateCandidateRule,
        OversizedBucket,
    )
    for record in records:
        assert is_dataclass(record)
        assert cast(Any, record).__dataclass_params__.frozen
        assert "__slots__" in record.__dict__
        assert record.__name__ in candidate_module.__all__
        assert getattr(real_estate_parser, record.__name__) is record
    result = _success((_available(_ref("alpha_fixture", "a"), 0),))
    with pytest.raises(FrozenInstanceError):
        result.candidates = ()  # type: ignore[misc]
    with pytest.raises(TypeError):
        replace(result, candidates=cast(Any, []))
    with pytest.raises(ValueError):
        DuplicateCandidateGenerationFailure(())
    with pytest.raises(ValueError):
        BlockingComponentNonParticipation(
            "rooms", BlockingComponentState.MISSING, DuplicateCandidateReasonCode("wrong")
        )
    pair = PublicationPair(_ref("alpha_fixture", "a"), _ref("beta_fixture", "b"))
    with pytest.raises(ValueError):
        DuplicateCandidateIdentity(
            pair,
            ObservationKey(pair.right, _at(0)),
            ObservationKey(pair.left, _at(1)),
            PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION,
        )


def test_module_has_no_io_storage_clock_uuid_json_assessment_or_coverage_api() -> None:
    module_path = Path(real_estate_parser.__file__).with_name("publication_duplicate_candidates.py")
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots.isdisjoint(
        {"json", "os", "pathlib", "pydantic", "sqlite3", "time", "uuid"}
    )
    assert "assess_publication_pair" not in imported_names
    public_names = set(candidate_module.__all__)
    assert not any(
        forbidden in name.lower()
        for name in public_names
        for forbidden in (
            "assessment",
            "coverage",
            "cluster",
            "merge",
            "repository",
            "storage",
        )
    )
    source = module_path.read_text(encoding="utf-8")
    assert "assess_publication_pair(" not in source
