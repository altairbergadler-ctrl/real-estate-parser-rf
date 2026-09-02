from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, is_dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

import real_estate_parser
import real_estate_parser.publication_duplicate_candidate_coverage as coverage_module
from real_estate_parser import (
    PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1,
    PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION,
    PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
    Area,
    BlockingCoverageUnavailable,
    BlockingCoverageUnavailableReason,
    BucketPairLimit,
    Currency,
    DirectSourceStateEvidence,
    DuplicateCandidateBlockingCoverage,
    DuplicateCandidateCoverageConflict,
    DuplicateCandidateCoverageConflictSubject,
    DuplicateCandidateCoverageFailure,
    DuplicateCandidateCoverageSuccess,
    DuplicateCandidateGenerationConfiguration,
    DuplicateCandidateGenerationResult,
    DuplicateControlLabel,
    DuplicateControlLabelOutcome,
    DuplicatePolicyControlCase,
    DuplicatePolicyControlSet,
    ExactRatio,
    InputLocation,
    LocationText,
    MoneyAmount,
    NormalizationRuleVersion,
    NormalizedListing,
    ObservationKey,
    ObservedAt,
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
    ValueProvenance,
    assess_publication_pair,
    evaluate_duplicate_candidate_blocking_coverage,
    generate_duplicate_candidates,
)
from real_estate_parser.publication_duplicate_candidates import (
    DuplicateCandidateGenerationSuccess,
)
from real_estate_parser.publication_observations import AvailabilityRuleVersion

NORMALIZATION_RULE = NormalizationRuleVersion("fictional-coverage-field@1")
AVAILABILITY_RULE = AvailabilityRuleVersion("fictional-coverage-availability@1")


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
        normalization_rule_version=NORMALIZATION_RULE,
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
    area: int,
    rooms: int,
    location: str,
) -> real_estate_parser.AvailableObservation:
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
            MoneyAmount(10_000_000), reference, observed_at, "price_amount", "100000.00"
        ),
        currency=_present(Currency("RUB"), reference, observed_at, "currency", "RUB"),
        total_area=_present(Area(area), reference, observed_at, "total_area", str(area)),
        rooms=_present(RoomCount(rooms), reference, observed_at, "rooms", str(rooms)),
    )
    return real_estate_parser.AvailableObservation(
        ObservationKey(reference, observed_at),
        listing,
    )


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
    observations: tuple[real_estate_parser.AvailableObservation, ...],
    *,
    limit: int = 10,
) -> DuplicateCandidateGenerationResult:
    outcome = generate_duplicate_candidates(
        observations,
        DuplicateCandidateGenerationConfiguration(
            PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1,
            BucketPairLimit(limit),
        ),
    )
    assert isinstance(outcome, DuplicateCandidateGenerationSuccess)
    return outcome.result


def _assessed_case(
    left: real_estate_parser.AvailableObservation,
    right: real_estate_parser.AvailableObservation,
    label: DuplicateControlLabelOutcome = DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP,
) -> DuplicatePolicyControlCase:
    result = assess_publication_pair(left, right)
    assert isinstance(result, PairAssessmentSuccess)
    pair = result.assessment.identity.pair
    return DuplicatePolicyControlCase(
        pair,
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        result,
        DuplicateControlLabel(pair, label),
    )


def _not_assessed_case(
    left: real_estate_parser.AvailableObservation,
    right: UnavailableObservation,
    label: DuplicateControlLabelOutcome,
) -> DuplicatePolicyControlCase:
    result = assess_publication_pair(left, right)
    assert isinstance(result, PairNotAssessed)
    return DuplicatePolicyControlCase(
        result.pair,
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        result,
        DuplicateControlLabel(result.pair, label),
    )


def _control_set(*cases: DuplicatePolicyControlCase) -> DuplicatePolicyControlSet:
    return DuplicatePolicyControlSet(PUBLICATION_DUPLICATE_POLICY_V1_VERSION, cases)


def _coverage(
    control_set: DuplicatePolicyControlSet,
    generation: DuplicateCandidateGenerationResult,
) -> DuplicateCandidateBlockingCoverage:
    outcome = evaluate_duplicate_candidate_blocking_coverage(control_set, generation)
    assert isinstance(outcome, DuplicateCandidateCoverageSuccess)
    return outcome.coverage


def _mixed_example() -> tuple[
    DuplicatePolicyControlSet,
    DuplicateCandidateGenerationResult,
]:
    covered_rooms_left = _available(
        _ref("same_fixture", "rooms-a"), 0, area=4_700, rooms=1, location="Rooms A"
    )
    covered_rooms_right = _available(
        _ref("same_fixture", "rooms-b"), 1, area=4_700, rooms=1, location="Rooms B"
    )
    covered_location_left = _available(
        _ref("alpha_fixture", "location-a"),
        2,
        area=4_800,
        rooms=2,
        location="Shared Location",
    )
    covered_location_right = _available(
        _ref("beta_fixture", "location-b"),
        3,
        area=4_800,
        rooms=3,
        location="Shared Location",
    )
    no_shared_left = _available(
        _ref("gamma_fixture", "miss-a"), 4, area=4_900, rooms=4, location="Miss A"
    )
    no_shared_right = _available(
        _ref("delta_fixture", "miss-b"), 5, area=5_000, rooms=5, location="Miss B"
    )
    oversized_left = _available(
        _ref("epsilon_fixture", "large-a"), 6, area=5_100, rooms=6, location="Large A"
    )
    oversized_right = _available(
        _ref("zeta_fixture", "large-b"), 7, area=5_100, rooms=6, location="Large B"
    )
    oversized_third = _available(
        _ref("eta_fixture", "large-c"), 8, area=5_100, rooms=6, location="Large C"
    )
    observations = (
        covered_rooms_left,
        covered_rooms_right,
        covered_location_left,
        covered_location_right,
        no_shared_left,
        no_shared_right,
        oversized_left,
        oversized_right,
        oversized_third,
    )
    return (
        _control_set(
            _assessed_case(covered_rooms_left, covered_rooms_right),
            _assessed_case(covered_location_left, covered_location_right),
            _assessed_case(no_shared_left, no_shared_right),
            _assessed_case(oversized_left, oversized_right),
        ),
        _generation(observations, limit=2),
    )


def test_mixed_fictional_population_has_exact_unsimplified_two_of_four_coverage() -> None:
    control_set, generation = _mixed_example()
    coverage = _coverage(control_set, generation)
    assert coverage.control_population_count == 4
    assert coverage.confirmed_label_count == 4
    assert coverage.eligible_confirmed_count == 4
    assert coverage.covered_eligible_confirmed_count == 2
    assert coverage.missed_no_shared_key_count == 1
    assert coverage.missed_oversized_bucket_count == 1
    assert coverage.blocking_coverage == ExactRatio(2, 4)
    assert isinstance(coverage.blocking_coverage, ExactRatio)
    assert type(coverage.blocking_coverage.numerator) is int
    assert not hasattr(coverage.blocking_coverage, "value")


def test_both_routes_and_oversized_alternate_route_are_covered_for_same_and_cross_source() -> None:
    both_left = _available(_ref("same_fixture", "both-a"), 0, area=4_700, rooms=2, location="Both")
    both_right = _available(_ref("same_fixture", "both-b"), 1, area=4_700, rooms=2, location="Both")
    alternate_left = _available(
        _ref("alpha_fixture", "alternate-a"),
        2,
        area=5_200,
        rooms=3,
        location="Alternate Shared",
    )
    alternate_right = _available(
        _ref("beta_fixture", "alternate-b"),
        3,
        area=5_200,
        rooms=3,
        location="Alternate Shared",
    )
    oversized_third = _available(
        _ref("gamma_fixture", "alternate-c"),
        4,
        area=5_200,
        rooms=3,
        location="Other",
    )
    generation = _generation(
        (both_left, both_right, alternate_left, alternate_right, oversized_third),
        limit=2,
    )
    coverage = _coverage(
        _control_set(
            _assessed_case(both_left, both_right),
            _assessed_case(alternate_left, alternate_right),
        ),
        generation,
    )
    assert coverage.blocking_coverage == ExactRatio(2, 2)
    both_candidate = next(
        candidate
        for candidate in generation.candidates
        if candidate.identity.pair
        == PublicationPair(both_left.key.reference, both_right.key.reference)
    )
    assert len(both_candidate.blocking_matches) == 2
    alternate_candidate = next(
        candidate
        for candidate in generation.candidates
        if candidate.identity.pair
        == PublicationPair(alternate_left.key.reference, alternate_right.key.reference)
    )
    assert len(alternate_candidate.blocking_matches) == 1
    assert coverage.missed_oversized_bucket_count == 0


def test_confirmed_eligibility_order_and_all_label_counts_are_disjoint() -> None:
    eligible_left = _available(
        _ref("alpha_fixture", "eligible-a"), 0, area=4_700, rooms=2, location="Eligible"
    )
    eligible_right = _available(
        _ref("beta_fixture", "eligible-b"), 1, area=4_700, rooms=2, location="Eligible"
    )
    stale_left = _available(
        _ref("gamma_fixture", "stale-a"), 2, area=4_800, rooms=3, location="Stale"
    )
    stale_assessed_right = _available(
        _ref("delta_fixture", "stale-b"), 3, area=4_800, rooms=3, location="Stale"
    )
    stale_current_right = _available(
        stale_assessed_right.key.reference, 4, area=4_800, rooms=3, location="Stale"
    )
    outside_left = _available(
        _ref("epsilon_fixture", "outside-a"), 5, area=4_900, rooms=4, location="Outside"
    )
    outside_right = _available(
        _ref("zeta_fixture", "outside-b"), 6, area=4_900, rooms=4, location="Outside"
    )
    not_assessed_left = _available(
        _ref("eta_fixture", "not-a"), 7, area=5_000, rooms=5, location="Not"
    )
    not_assessed_right = _unavailable(_ref("theta_fixture", "not-b"), 8)
    rejected_not_left = _available(
        _ref("iota_fixture", "rejected-a"), 9, area=5_100, rooms=6, location="Rejected"
    )
    rejected_not_right = _unavailable(_ref("kappa_fixture", "rejected-b"), 10)
    inconclusive_left = _available(
        _ref("lambda_fixture", "inc-a"), 11, area=5_200, rooms=7, location="Inc A"
    )
    inconclusive_right = _available(
        _ref("mu_fixture", "inc-b"), 12, area=5_300, rooms=8, location="Inc B"
    )
    control_set = _control_set(
        _assessed_case(eligible_left, eligible_right),
        _assessed_case(stale_left, stale_assessed_right),
        _assessed_case(outside_left, outside_right),
        _not_assessed_case(
            not_assessed_left,
            not_assessed_right,
            DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP,
        ),
        _not_assessed_case(
            rejected_not_left,
            rejected_not_right,
            DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP,
        ),
        _assessed_case(
            inconclusive_left,
            inconclusive_right,
            DuplicateControlLabelOutcome.INCONCLUSIVE,
        ),
    )
    generation = _generation(
        (eligible_left, eligible_right, stale_left, stale_current_right),
        limit=10,
    )
    coverage = _coverage(control_set, generation)
    assert coverage.control_population_count == 6
    assert coverage.pair_not_assessed_case_count == 2
    assert coverage.rejected_label_count == 1
    assert coverage.inconclusive_label_count == 1
    assert coverage.confirmed_label_count == 4
    assert coverage.confirmed_pair_not_assessed_count == 1
    assert coverage.confirmed_outside_generation_input_count == 1
    assert coverage.confirmed_stale_or_mismatched_keys_count == 1
    assert coverage.eligible_confirmed_count == 1
    assert coverage.covered_eligible_confirmed_count == 1
    assert coverage.blocking_coverage == BlockingCoverageUnavailable(
        BlockingCoverageUnavailableReason.INCONCLUSIVE_CONTROL_LABELS
    )
    with pytest.raises(ValueError):
        replace(coverage, pair_not_assessed_case_count=0)


def test_unavailable_reason_precedence_and_zero_eligible_denominator() -> None:
    left = _available(_ref("alpha_fixture", "a"), 0, area=4_700, rooms=2, location="A")
    right = _available(_ref("beta_fixture", "b"), 1, area=4_800, rooms=3, location="B")
    generation = _generation((left, right))
    inconclusive = _coverage(
        _control_set(_assessed_case(left, right, DuplicateControlLabelOutcome.INCONCLUSIVE)),
        generation,
    )
    assert inconclusive.blocking_coverage == BlockingCoverageUnavailable(
        BlockingCoverageUnavailableReason.INCONCLUSIVE_CONTROL_LABELS
    )

    rejected = _coverage(
        _control_set(
            _assessed_case(left, right, DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP)
        ),
        generation,
    )
    assert rejected.eligible_confirmed_count == 0
    assert rejected.blocking_coverage == BlockingCoverageUnavailable(
        BlockingCoverageUnavailableReason.NO_ELIGIBLE_CONFIRMED_RELATIONSHIPS
    )


def test_policy_and_exact_generation_identity_are_preserved_separately() -> None:
    control_set, generation = _mixed_example()
    coverage = _coverage(control_set, generation)
    assert coverage.candidate_policy_version == PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION
    assert coverage.assessment_policy_version == PUBLICATION_DUPLICATE_POLICY_V1_VERSION
    assert coverage.generation_identity is generation.identity
    assert coverage.candidate_policy_version.value != coverage.assessment_policy_version.value


def test_structurally_accepted_missing_candidate_is_one_atomic_conflict() -> None:
    left = _available(_ref("alpha_fixture", "missing-a"), 0, area=4_700, rooms=2, location="Shared")
    right = _available(_ref("beta_fixture", "missing-b"), 1, area=4_700, rooms=2, location="Shared")
    generated = _generation((left, right))
    crafted = replace(generated, candidates=())
    outcome = evaluate_duplicate_candidate_blocking_coverage(
        _control_set(_assessed_case(left, right)),
        crafted,
    )
    assert isinstance(outcome, DuplicateCandidateCoverageFailure)
    assert outcome.conflicts == (
        DuplicateCandidateCoverageConflict(
            "DUPLICATE_CANDIDATE_COVERAGE_CONFLICT",
            "generation_result_inconsistent",
            DuplicateCandidateCoverageConflictSubject(
                PublicationPair(left.key.reference, right.key.reference),
                left.key,
                right.key,
            ),
        ),
    )
    assert not hasattr(outcome, "coverage")
    assert not hasattr(outcome, "metrics")


def test_multiple_inconsistencies_are_canonical_and_failure_rejects_other_order() -> None:
    a = _available(_ref("zeta_fixture", "a"), 0, area=4_700, rooms=1, location="A")
    b = _available(_ref("zeta_fixture", "b"), 1, area=4_700, rooms=1, location="B")
    c = _available(_ref("alpha_fixture", "c"), 2, area=4_800, rooms=2, location="C")
    d = _available(_ref("beta_fixture", "d"), 3, area=4_800, rooms=2, location="D")
    generated = _generation((a, b, c, d))
    crafted = replace(generated, candidates=())
    outcome = evaluate_duplicate_candidate_blocking_coverage(
        _control_set(_assessed_case(a, b), _assessed_case(c, d)),
        crafted,
    )
    assert isinstance(outcome, DuplicateCandidateCoverageFailure)
    assert tuple(conflict.subject.pair for conflict in outcome.conflicts) == (
        PublicationPair(c.key.reference, d.key.reference),
        PublicationPair(a.key.reference, b.key.reference),
    )
    with pytest.raises(ValueError):
        DuplicateCandidateCoverageFailure(tuple(reversed(outcome.conflicts)))


def test_coverage_contracts_are_frozen_slots_tuple_only_and_exported() -> None:
    control_set, generation = _mixed_example()
    outcome = evaluate_duplicate_candidate_blocking_coverage(control_set, generation)
    assert isinstance(outcome, DuplicateCandidateCoverageSuccess)
    record_types = (
        BlockingCoverageUnavailable,
        DuplicateCandidateBlockingCoverage,
        DuplicateCandidateCoverageConflict,
        DuplicateCandidateCoverageConflictSubject,
        DuplicateCandidateCoverageFailure,
        DuplicateCandidateCoverageSuccess,
    )
    for record_type in record_types:
        assert is_dataclass(record_type)
        assert cast(Any, record_type).__dataclass_params__.frozen
        assert "__slots__" in record_type.__dict__
        assert record_type.__name__ in coverage_module.__all__
        assert getattr(real_estate_parser, record_type.__name__) is record_type
    with pytest.raises(FrozenInstanceError):
        outcome.coverage.eligible_confirmed_count = 0  # type: ignore[misc]
    with pytest.raises(TypeError):
        DuplicateCandidateCoverageFailure(cast(Any, []))
    with pytest.raises(ValueError):
        DuplicateCandidateCoverageFailure(())


@pytest.mark.parametrize(
    "change",
    [
        {"control_population_count": 0},
        {"rejected_label_count": 1},
        {"confirmed_label_count": 3},
        {"eligible_confirmed_count": 3},
        {"covered_eligible_confirmed_count": 3},
        {"pair_not_assessed_case_count": 5},
        {"blocking_coverage": ExactRatio(1, 4)},
    ],
)
def test_negative_coverage_constructor_invariants(change: dict[str, object]) -> None:
    control_set, generation = _mixed_example()
    valid = _coverage(control_set, generation)
    with pytest.raises(ValueError):
        replace(valid, **cast(Any, change))
    with pytest.raises(ValueError):
        replace(valid, eligible_confirmed_count=cast(Any, 4.0))


def test_unavailable_reason_enum_has_exactly_two_reasons_and_is_strict() -> None:
    assert tuple(reason.value for reason in BlockingCoverageUnavailableReason) == (
        "inconclusive_control_labels",
        "no_eligible_confirmed_relationships",
    )
    with pytest.raises(TypeError):
        BlockingCoverageUnavailable(cast(Any, "inconclusive_control_labels"))


def test_permutations_are_deterministic_and_evaluation_does_not_mutate_inputs() -> None:
    a = _available(_ref("alpha_fixture", "a"), 0, area=4_700, rooms=1, location="A")
    b = _available(_ref("beta_fixture", "b"), 1, area=4_700, rooms=1, location="B")
    c = _available(_ref("gamma_fixture", "c"), 2, area=4_800, rooms=2, location="Shared")
    d = _available(_ref("delta_fixture", "d"), 3, area=4_800, rooms=3, location="Shared")
    cases = (_assessed_case(a, b), _assessed_case(c, d))
    control_set = _control_set(*cases)
    generation = _generation((a, b, c, d))
    before_control = control_set
    before_generation = generation
    permuted_generation = _generation((d, c, b, a))
    permuted_control = DuplicatePolicyControlSet(
        control_set.policy_version,
        tuple(reversed(cases)),
    )
    assert generation == permuted_generation
    assert control_set == permuted_control
    assert _coverage(control_set, generation) == _coverage(
        permuted_control,
        permuted_generation,
    )
    assert control_set == before_control
    assert generation == before_generation


def test_evaluation_has_no_assessment_generation_io_or_state_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control_set, generation = _mixed_example()

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("forbidden operation called")

    monkeypatch.setattr(real_estate_parser, "assess_publication_pair", forbidden)
    monkeypatch.setattr(real_estate_parser, "generate_duplicate_candidates", forbidden)
    assert isinstance(
        evaluate_duplicate_candidate_blocking_coverage(control_set, generation),
        DuplicateCandidateCoverageSuccess,
    )

    module_path = Path(real_estate_parser.__file__).with_name(
        "publication_duplicate_candidate_coverage.py"
    )
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
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
        {"json", "os", "pathlib", "pydantic", "random", "sqlite3", "time", "uuid"}
    )
    assert "assess_publication_pair" not in imported_names
    assert "generate_duplicate_candidates" not in imported_names
    assert "assess_publication_pair(" not in source
    assert "generate_duplicate_candidates(" not in source
    public_names = set(coverage_module.__all__)
    assert not any(
        forbidden_name in name.lower()
        for name in public_names
        for forbidden_name in (
            "cluster",
            "merge",
            "repository",
            "storage",
            "score",
            "probability",
        )
    )
