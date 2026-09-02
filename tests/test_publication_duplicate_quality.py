from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, is_dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

import real_estate_parser
import real_estate_parser.publication_duplicate_quality as quality_module
from real_estate_parser import (
    PUBLICATION_DUPLICATE_POLICY_V1,
    PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
    Area,
    AvailableObservation,
    Currency,
    DirectSourceStateEvidence,
    DuplicateControlContractError,
    DuplicateControlContractErrorCode,
    DuplicateControlLabel,
    DuplicateControlLabelOutcome,
    DuplicatePolicy,
    DuplicatePolicyControlCase,
    DuplicatePolicyControlSet,
    DuplicatePolicyQualityMetrics,
    DuplicatePolicyVersion,
    ExactRatio,
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
    QualityMetricUnavailable,
    QualityMetricUnavailableReason,
    RoomCount,
    SourceId,
    SourceUrl,
    TracedValue,
    UnavailableObservation,
    ValueProvenance,
    assess_publication_pair,
    evaluate_duplicate_policy_quality,
)
from real_estate_parser.publication_observations import AvailabilityRuleVersion

REF_A = PublicationRef(SourceId("alpha_control"), PublicationId("case-a"))
REF_B = PublicationRef(SourceId("beta_control"), PublicationId("case-b"))
REF_C = PublicationRef(SourceId("gamma_control"), PublicationId("case-c"))
REF_D = PublicationRef(SourceId("delta_control"), PublicationId("case-d"))
REF_E = PublicationRef(SourceId("epsilon_control"), PublicationId("case-e"))
REF_F = PublicationRef(SourceId("zeta_control"), PublicationId("case-f"))
REF_SAME_SOURCE = PublicationRef(SourceId("alpha_control"), PublicationId("case-z"))
NORMALIZATION_RULE = NormalizationRuleVersion("fictional-control-field@1")
AVAILABILITY_RULE = AvailabilityRuleVersion("fictional-control-availability@1")


def _observed(minute: int) -> ObservedAt:
    return ObservedAt(datetime(2026, 9, 2, 14, minute, tzinfo=UTC))


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
    area: int = 4_800,
    rooms: int = 2,
    location: str = "Fictional Control Quarter",
) -> AvailableObservation:
    observed_at = _observed(minute)
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
            MoneyAmount(9_900_000), reference, observed_at, "price_amount", "99000.00"
        ),
        currency=_present(Currency("RUB"), reference, observed_at, "currency", "RUB"),
        total_area=_present(Area(area), reference, observed_at, "total_area", str(area)),
        rooms=_present(RoomCount(rooms), reference, observed_at, "rooms", str(rooms)),
    )
    return AvailableObservation(ObservationKey(reference, observed_at), listing)


def _unavailable(reference: PublicationRef, minute: int) -> UnavailableObservation:
    return UnavailableObservation(
        ObservationKey(reference, _observed(minute)),
        DirectSourceStateEvidence(
            raw_source_state="fictionally-unavailable",
            source_field="publication_state",
            adapter_rule_version=AVAILABILITY_RULE,
        ),
    )


def _assessment_result(
    left: PublicationRef,
    right: PublicationRef,
    kind: str,
    *,
    policy: DuplicatePolicy = PUBLICATION_DUPLICATE_POLICY_V1,
) -> PairAssessmentSuccess | PairNotAssessed:
    if kind == "not_assessed":
        result = assess_publication_pair(_available(left, 0), _unavailable(right, 1), policy)
    elif kind == "conflicting":
        result = assess_publication_pair(
            _available(left, 0),
            _available(right, 1, rooms=3),
            policy,
        )
    elif kind == "insufficient":
        result = assess_publication_pair(
            _available(left, 0),
            _available(right, 1, area=5_100),
            policy,
        )
    else:
        assert kind == "candidate"
        result = assess_publication_pair(_available(left, 0), _available(right, 1), policy)
    assert isinstance(result, (PairAssessmentSuccess, PairNotAssessed))
    return result


def _case(
    left: PublicationRef,
    right: PublicationRef,
    kind: str,
    label_outcome: DuplicateControlLabelOutcome,
    *,
    policy: DuplicatePolicy = PUBLICATION_DUPLICATE_POLICY_V1,
) -> DuplicatePolicyControlCase:
    result = _assessment_result(left, right, kind, policy=policy)
    pair = result.pair if isinstance(result, PairNotAssessed) else result.assessment.identity.pair
    return DuplicatePolicyControlCase(
        pair=pair,
        policy_version=policy.version,
        result=result,
        label=DuplicateControlLabel(pair, label_outcome),
    )


def _mixed_control_set() -> DuplicatePolicyControlSet:
    return DuplicatePolicyControlSet(
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        (
            _case(
                REF_A,
                REF_B,
                "candidate",
                DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP,
            ),
            _case(
                REF_A,
                REF_C,
                "conflicting",
                DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP,
            ),
            _case(
                REF_A,
                REF_D,
                "insufficient",
                DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP,
            ),
            _case(
                REF_A,
                REF_E,
                "not_assessed",
                DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP,
            ),
        ),
    )


def test_mixed_population_has_exact_counts_coverage_load_precision_and_recall() -> None:
    metrics = evaluate_duplicate_policy_quality(_mixed_control_set())
    assert metrics == DuplicatePolicyQualityMetrics(
        policy_version=PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        population_count=4,
        assessed_pair_count=3,
        candidate_requires_manual_review_count=1,
        conflicting_evidence_requires_manual_review_count=1,
        insufficient_evidence_no_candidate_count=1,
        not_assessed_count=1,
        review_required_count=2,
        assessment_coverage=ExactRatio(3, 4),
        review_required_population_rate=ExactRatio(2, 4),
        precision=ExactRatio(1, 2),
        recall=ExactRatio(1, 3),
    )
    assert type(metrics.assessment_coverage.numerator) is int
    assert type(metrics.assessment_coverage.denominator) is int
    assert not hasattr(metrics.assessment_coverage, "value")


def test_all_assessed_and_all_not_assessed_have_exact_coverage() -> None:
    assessed = DuplicatePolicyControlSet(
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        (
            _case(REF_A, REF_B, "candidate", DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP),
            _case(REF_C, REF_D, "insufficient", DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP),
        ),
    )
    not_assessed = DuplicatePolicyControlSet(
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        (
            _case(REF_A, REF_B, "not_assessed", DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP),
            _case(REF_C, REF_D, "not_assessed", DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP),
        ),
    )
    assert evaluate_duplicate_policy_quality(assessed).assessment_coverage == ExactRatio(2, 2)
    empty_coverage = evaluate_duplicate_policy_quality(not_assessed)
    assert empty_coverage.assessment_coverage == ExactRatio(0, 2)
    assert empty_coverage.not_assessed_count == 2
    assert empty_coverage.review_required_population_rate == ExactRatio(0, 2)


def test_same_source_and_cross_source_pairs_are_independent_control_cases() -> None:
    same_source = _case(
        REF_A,
        REF_SAME_SOURCE,
        "candidate",
        DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP,
    )
    cross_source = _case(
        REF_A,
        REF_B,
        "candidate",
        DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP,
    )
    control_set = DuplicatePolicyControlSet(
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION, (same_source, cross_source)
    )
    assert len(control_set.cases) == 2
    assert evaluate_duplicate_policy_quality(control_set).review_required_count == 2


def test_control_set_order_is_canonical_and_permutation_invariant() -> None:
    cases = _mixed_control_set().cases
    forward = DuplicatePolicyControlSet(PUBLICATION_DUPLICATE_POLICY_V1_VERSION, cases)
    reverse = DuplicatePolicyControlSet(
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION, tuple(reversed(cases))
    )
    assert forward == reverse
    assert evaluate_duplicate_policy_quality(forward) == evaluate_duplicate_policy_quality(reverse)


def test_control_records_are_frozen_slots_tuple_only_and_exported() -> None:
    control_set = _mixed_control_set()
    record_types = (
        DuplicateControlLabel,
        DuplicatePolicyControlCase,
        DuplicatePolicyControlSet,
        DuplicatePolicyQualityMetrics,
        ExactRatio,
        QualityMetricUnavailable,
    )
    for record_type in record_types:
        assert is_dataclass(record_type)
        assert cast(Any, record_type).__dataclass_params__.frozen
        assert "__slots__" in record_type.__dict__
        assert record_type.__name__ in quality_module.__all__
        assert getattr(real_estate_parser, record_type.__name__) is record_type
    with pytest.raises(FrozenInstanceError):
        control_set.cases = ()  # type: ignore[misc]
    with pytest.raises(DuplicateControlContractError) as raised:
        DuplicatePolicyControlSet(
            PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
            cast(Any, list(control_set.cases)),
        )
    assert raised.value.code is DuplicateControlContractErrorCode.CASES_NOT_TUPLE


def test_empty_and_duplicate_pair_control_sets_are_rejected() -> None:
    with pytest.raises(DuplicateControlContractError) as empty:
        DuplicatePolicyControlSet(PUBLICATION_DUPLICATE_POLICY_V1_VERSION, ())
    assert empty.value.code is DuplicateControlContractErrorCode.EMPTY_CONTROL_SET
    case = _case(REF_A, REF_B, "candidate", DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP)
    with pytest.raises(DuplicateControlContractError) as duplicate:
        DuplicatePolicyControlSet(PUBLICATION_DUPLICATE_POLICY_V1_VERSION, (case, case))
    assert duplicate.value.code is DuplicateControlContractErrorCode.DUPLICATE_PAIR


def test_wrong_pair_result_and_label_bindings_are_rejected() -> None:
    result = _assessment_result(REF_A, REF_B, "candidate")
    other_pair = PublicationPair(REF_A, REF_C)
    with pytest.raises(DuplicateControlContractError) as result_error:
        DuplicatePolicyControlCase(
            other_pair,
            PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
            result,
            DuplicateControlLabel(other_pair, DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP),
        )
    assert result_error.value.code is DuplicateControlContractErrorCode.PAIR_BINDING_MISMATCH
    pair = PublicationPair(REF_A, REF_B)
    with pytest.raises(DuplicateControlContractError) as label_error:
        DuplicatePolicyControlCase(
            pair,
            PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
            result,
            DuplicateControlLabel(other_pair, DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP),
        )
    assert label_error.value.code is DuplicateControlContractErrorCode.LABEL_BINDING_MISMATCH


def test_mixed_policy_versions_and_wrong_success_policy_are_rejected() -> None:
    policy_v2 = DuplicatePolicy(
        DuplicatePolicyVersion("publication-duplicate-policy@2"),
        PUBLICATION_DUPLICATE_POLICY_V1.rules,
    )
    v1_case = _case(REF_A, REF_B, "candidate", DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP)
    v2_case = _case(
        REF_C,
        REF_D,
        "candidate",
        DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP,
        policy=policy_v2,
    )
    with pytest.raises(DuplicateControlContractError) as mixed:
        DuplicatePolicyControlSet(PUBLICATION_DUPLICATE_POLICY_V1_VERSION, (v1_case, v2_case))
    assert mixed.value.code is DuplicateControlContractErrorCode.POLICY_VERSION_MISMATCH
    assert isinstance(v1_case.result, PairAssessmentSuccess)
    with pytest.raises(DuplicateControlContractError) as wrong_case_policy:
        replace(v1_case, policy_version=policy_v2.version)
    assert wrong_case_policy.value.code is DuplicateControlContractErrorCode.POLICY_VERSION_MISMATCH


def test_pair_not_assessed_policy_is_explicit_in_case_and_control_set() -> None:
    case = _case(
        REF_A,
        REF_B,
        "not_assessed",
        DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP,
    )
    assert isinstance(case.result, PairNotAssessed)
    assert not hasattr(case.result, "policy_version")
    assert case.policy_version == PUBLICATION_DUPLICATE_POLICY_V1_VERSION
    control_set = DuplicatePolicyControlSet(case.policy_version, (case,))
    assert control_set.policy_version == case.policy_version


@pytest.mark.parametrize("unsupported", ["failure", "object"])
def test_failure_and_unsupported_results_are_atomic_contract_errors(unsupported: str) -> None:
    result: object
    if unsupported == "failure":
        result = assess_publication_pair(_available(REF_A, 0), _available(REF_A, 1))
        assert isinstance(result, PairAssessmentFailure)
    else:
        result = object()
    pair = PublicationPair(REF_A, REF_B)
    with pytest.raises(DuplicateControlContractError) as raised:
        DuplicatePolicyControlCase(
            pair,
            PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
            cast(Any, result),
            DuplicateControlLabel(pair, DuplicateControlLabelOutcome.INCONCLUSIVE),
        )
    assert raised.value.code is DuplicateControlContractErrorCode.UNSUPPORTED_RESULT
    assert not hasattr(raised.value, "metrics")


def test_invalid_evaluation_input_returns_no_partial_metrics() -> None:
    with pytest.raises(DuplicateControlContractError) as raised:
        evaluate_duplicate_policy_quality(cast(Any, ()))
    assert raised.value.code is DuplicateControlContractErrorCode.INVALID_CONTROL_SET
    assert not hasattr(raised.value, "metrics")


def test_precision_available_and_uses_all_review_required_cases() -> None:
    metrics = evaluate_duplicate_policy_quality(_mixed_control_set())
    assert metrics.precision == ExactRatio(1, 2)


def test_precision_unavailable_when_there_are_no_predicted_positives() -> None:
    control_set = DuplicatePolicyControlSet(
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        (
            _case(
                REF_A,
                REF_B,
                "insufficient",
                DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP,
            ),
            _case(
                REF_C,
                REF_D,
                "not_assessed",
                DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP,
            ),
        ),
    )
    assert evaluate_duplicate_policy_quality(control_set).precision == QualityMetricUnavailable(
        QualityMetricUnavailableReason.NO_PREDICTED_POSITIVE
    )


def test_precision_unavailable_for_inconclusive_predicted_positive_label() -> None:
    control_set = DuplicatePolicyControlSet(
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        (
            _case(
                REF_A,
                REF_B,
                "candidate",
                DuplicateControlLabelOutcome.INCONCLUSIVE,
            ),
            _case(
                REF_C,
                REF_D,
                "conflicting",
                DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP,
            ),
        ),
    )
    assert evaluate_duplicate_policy_quality(control_set).precision == QualityMetricUnavailable(
        QualityMetricUnavailableReason.INCOMPLETE_PREDICTED_POSITIVE_LABELS
    )


def test_recall_available_and_counts_not_assessed_and_insufficient_false_negatives() -> None:
    metrics = evaluate_duplicate_policy_quality(_mixed_control_set())
    assert metrics.recall == ExactRatio(1, 3)


def test_recall_unavailable_when_no_confirmed_relationship_labels_exist() -> None:
    control_set = DuplicatePolicyControlSet(
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        (
            _case(REF_A, REF_B, "candidate", DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP),
            _case(REF_C, REF_D, "insufficient", DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP),
        ),
    )
    assert evaluate_duplicate_policy_quality(control_set).recall == QualityMetricUnavailable(
        QualityMetricUnavailableReason.NO_CONFIRMED_RELATIONSHIP_LABELS
    )


def test_recall_unavailable_when_any_population_label_is_inconclusive() -> None:
    control_set = DuplicatePolicyControlSet(
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        (
            _case(
                REF_A,
                REF_B,
                "candidate",
                DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP,
            ),
            _case(
                REF_C,
                REF_D,
                "not_assessed",
                DuplicateControlLabelOutcome.INCONCLUSIVE,
            ),
        ),
    )
    assert evaluate_duplicate_policy_quality(control_set).recall == QualityMetricUnavailable(
        QualityMetricUnavailableReason.INCOMPLETE_POPULATION_LABELS
    )


def test_labels_are_not_derived_from_outcomes_and_assessments_are_unchanged() -> None:
    result = _assessment_result(REF_A, REF_B, "candidate")
    assert isinstance(result, PairAssessmentSuccess)
    before = result.assessment
    pair = result.assessment.identity.pair
    confirmed = DuplicatePolicyControlCase(
        pair,
        PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
        result,
        DuplicateControlLabel(pair, DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP),
    )
    rejected = replace(
        confirmed,
        label=DuplicateControlLabel(pair, DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP),
    )
    confirmed_metrics = evaluate_duplicate_policy_quality(
        DuplicatePolicyControlSet(PUBLICATION_DUPLICATE_POLICY_V1_VERSION, (confirmed,))
    )
    rejected_metrics = evaluate_duplicate_policy_quality(
        DuplicatePolicyControlSet(PUBLICATION_DUPLICATE_POLICY_V1_VERSION, (rejected,))
    )
    assert confirmed.result == rejected.result
    assert confirmed_metrics.precision == ExactRatio(1, 1)
    assert rejected_metrics.precision == ExactRatio(0, 1)
    assert result.assessment == before
    assert result.assessment.evidence is before.evidence
    assert result.assessment.left_observation is before.left_observation
    assert result.assessment.right_observation is before.right_observation


@pytest.mark.parametrize(
    ("numerator", "denominator"),
    [(-1, 1), (2, 1), (0, 0), (0, -1)],
)
def test_exact_ratio_rejects_invalid_integer_invariants(numerator: int, denominator: int) -> None:
    with pytest.raises(ValueError):
        ExactRatio(numerator, denominator)
    with pytest.raises(TypeError):
        ExactRatio(cast(Any, 0.5), 1)


def test_quality_module_has_no_io_state_scores_or_merge_cluster_api() -> None:
    module_path = Path(real_estate_parser.__file__).with_name("publication_duplicate_quality.py")
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots.isdisjoint(
        {
            "json",
            "os",
            "pathlib",
            "pydantic",
            "sqlite3",
            "time",
            "uuid",
        }
    )
    public_names = set(quality_module.__all__)
    assert not any(
        forbidden in name.lower()
        for name in public_names
        for forbidden in (
            "accuracy",
            "cluster",
            "f1",
            "merge",
            "score",
            "storage",
            "threshold",
        )
    )
    assert not hasattr(real_estate_parser, "merge_control_pairs")
    assert not hasattr(real_estate_parser, "cluster_control_pairs")
