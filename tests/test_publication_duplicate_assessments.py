from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

import real_estate_parser
import real_estate_parser.publication_duplicate_assessments as duplicate_module
from real_estate_parser import (
    PUBLICATION_DUPLICATE_POLICY_V1,
    PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
    Area,
    AssessmentFindingKind,
    AssessmentFindingReference,
    AssessmentSupersession,
    AvailableObservation,
    Currency,
    CurrentPairContext,
    DuplicateAssessmentIdentity,
    DuplicateAutomaticOutcome,
    DuplicateEvidenceItem,
    DuplicateFieldSnapshot,
    DuplicatePairAssessment,
    DuplicatePairManualReview,
    DuplicatePolicy,
    DuplicatePolicyVersion,
    DuplicateReasonCode,
    DuplicateRuleId,
    DuplicateRuleVersion,
    EvidencePolarity,
    EvidenceStrength,
    InputLocation,
    LocationText,
    ManualReviewDisposition,
    ManualReviewDraft,
    ManualReviewFailure,
    ManualReviewIdentity,
    ManualReviewOutcome,
    ManualReviewSuccess,
    Missing,
    MissingProvenance,
    MissingValue,
    MoneyAmount,
    NormalizationRuleVersion,
    NormalizedListing,
    ObservationKey,
    ObservedAt,
    PairAssessmentFailure,
    PairAssessmentSuccess,
    PairNotAssessed,
    Present,
    PresentValue,
    PublicationId,
    PublicationPair,
    PublicationRef,
    ReviewedAt,
    ReviewerCode,
    ReviewRationaleCode,
    ReviewReferenceCode,
    RoomCount,
    RuleNonComparison,
    SourceId,
    SourceUrl,
    TracedValue,
    UnavailableObservation,
    Unsupported,
    UnsupportedProvenance,
    UnsupportedValue,
    ValueProvenance,
    assess_publication_pair,
    create_manual_review,
    is_assessment_current,
    is_assessment_stale,
)
from real_estate_parser.publication_observations import (
    AvailabilityRuleVersion,
    DirectSourceStateEvidence,
)

LEFT_REF = PublicationPair(
    PublicationRef(SourceId("zeta_fixture"), PublicationId("z-019")),
    PublicationRef(SourceId("alpha_fixture"), PublicationId("a-019")),
).left
RIGHT_REF = PublicationRef(SourceId("zeta_fixture"), PublicationId("z-019"))
SAME_SOURCE_REF = PublicationRef(SourceId("alpha_fixture"), PublicationId("b-019"))
THIRD_REF = PublicationRef(SourceId("omega_fixture"), PublicationId("c-019"))
RULE = NormalizationRuleVersion("fictional-field@1")
AVAILABILITY_RULE = AvailabilityRuleVersion("fictional-availability@1")


def _at(minute: int, *, day: int = 2) -> ObservedAt:
    return ObservedAt(datetime(2026, 9, day, 10, minute, tzinfo=UTC))


def _reviewed(minute: int) -> ReviewedAt:
    return ReviewedAt(datetime(2026, 9, 2, 12, minute, tzinfo=UTC))


def _path(field: str, index: int) -> InputLocation:
    return InputLocation("listings", index, (field,))


def _value_provenance(
    reference: PublicationRef,
    observed_at: ObservedAt,
    field: str,
    raw: str,
) -> ValueProvenance:
    return ValueProvenance(
        source_id=reference.source_id,
        publication_id=reference.publication_id,
        input_path=_path(field, 0 if reference == LEFT_REF else 1),
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
    return Present(TracedValue(value, _value_provenance(reference, observed_at, field, raw)))


def _missing(
    reference: PublicationRef,
    observed_at: ObservedAt,
    field: str,
) -> Missing:
    return Missing(
        MissingProvenance(
            source_id=reference.source_id,
            publication_id=reference.publication_id,
            input_path=_path(field, 0 if reference == LEFT_REF else 1),
            source_field=field,
            observed_at=observed_at,
            normalization_rule_version=RULE,
        )
    )


def _unsupported(
    reference: PublicationRef,
    observed_at: ObservedAt,
    field: str,
    raw: str = "future-code",
    reason: str = "unsupported_fictional_value",
) -> Unsupported:
    return Unsupported(
        UnsupportedProvenance(
            source_id=reference.source_id,
            publication_id=reference.publication_id,
            input_path=_path(field, 0 if reference == LEFT_REF else 1),
            source_field=field,
            raw_value=raw,
            observed_at=observed_at,
            normalization_rule_version=RULE,
            reason_code=reason,
        )
    )


def _listing(
    reference: PublicationRef,
    observed_at: ObservedAt,
    *,
    location_text: Present[LocationText] | Missing | Unsupported | None = None,
    price_amount: Present[MoneyAmount] | Missing | Unsupported | None = None,
    currency: Present[Currency] | Missing | Unsupported | None = None,
    total_area: Present[Area] | Missing | Unsupported | None = None,
    rooms: Present[RoomCount] | Missing | Unsupported | None = None,
) -> NormalizedListing:
    source_url = f"https://{reference.source_id.value}.example/{reference.publication_id.value}"
    return NormalizedListing(
        reference=TracedValue(
            reference,
            _value_provenance(
                reference,
                observed_at,
                "publication_id",
                reference.publication_id.value,
            ),
        ),
        source_url=TracedValue(
            SourceUrl(source_url),
            _value_provenance(reference, observed_at, "source_url", source_url),
        ),
        observed_at=TracedValue(
            observed_at,
            _value_provenance(reference, observed_at, "observed_at", observed_at.to_rfc3339()),
        ),
        location_text=location_text
        if location_text is not None
        else _present(
            LocationText("Fictional Quarter"),
            reference,
            observed_at,
            "location_text",
            "Fictional Quarter",
        ),
        price_amount=price_amount
        if price_amount is not None
        else _present(
            MoneyAmount(12_300_000),
            reference,
            observed_at,
            "price_amount",
            "123000.00",
        ),
        currency=currency
        if currency is not None
        else _present(Currency("RUB"), reference, observed_at, "currency", "RUB"),
        total_area=total_area
        if total_area is not None
        else _present(Area(4_700), reference, observed_at, "total_area", "47.00"),
        rooms=rooms
        if rooms is not None
        else _present(RoomCount(2), reference, observed_at, "rooms", "2"),
    )


def _available(
    reference: PublicationRef,
    minute: int,
    **changes: Any,
) -> AvailableObservation:
    observed_at = _at(minute)
    return AvailableObservation(
        ObservationKey(reference, observed_at),
        _listing(reference, observed_at, **changes),
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


def _assessment(
    left: AvailableObservation | None = None,
    right: AvailableObservation | None = None,
) -> DuplicatePairAssessment:
    result = assess_publication_pair(
        left or _available(LEFT_REF, 0),
        right or _available(RIGHT_REF, 1),
    )
    assert isinstance(result, PairAssessmentSuccess)
    return result.assessment


def _finding(
    assessment: DuplicatePairAssessment,
    rule_id: str,
) -> DuplicateEvidenceItem | RuleNonComparison:
    for finding in assessment.evidence:
        if finding.rule_id.value == rule_id:
            return finding
    for non_comparison in assessment.non_comparisons:
        if non_comparison.rule_id.value == rule_id:
            return non_comparison
    raise AssertionError(f"missing finding for {rule_id}")


def _finding_reference(
    assessment: DuplicatePairAssessment,
    kind: AssessmentFindingKind = AssessmentFindingKind.EVIDENCE,
    ordinal: int = 0,
) -> AssessmentFindingReference:
    if kind is AssessmentFindingKind.EVIDENCE:
        evidence = assessment.evidence[ordinal]
        return AssessmentFindingReference(
            assessment.identity,
            kind,
            evidence.rule_id,
            evidence.rule_version,
            evidence.polarity,
            ordinal,
        )
    non_comparison = assessment.non_comparisons[ordinal]
    return AssessmentFindingReference(
        assessment.identity,
        kind,
        non_comparison.rule_id,
        non_comparison.rule_version,
        None,
        ordinal,
    )


def _draft(
    assessment: DuplicatePairAssessment,
    *,
    revision: int = 1,
    outcome: ManualReviewOutcome = ManualReviewOutcome.CONFIRMED_RELATIONSHIP,
    reviewed_at: ReviewedAt | None = None,
    evidence_references: tuple[AssessmentFindingReference, ...] | None = None,
    assessment_identity: DuplicateAssessmentIdentity | None = None,
    supersedes: ManualReviewIdentity | None = None,
) -> ManualReviewDraft:
    return ManualReviewDraft(
        identity=ManualReviewIdentity(ReviewReferenceCode("review-demo-019"), revision),
        assessment_identity=assessment_identity or assessment.identity,
        reviewed_at=reviewed_at or _reviewed(revision),
        reviewer_code=ReviewerCode("reviewer-fixture-01"),
        outcome=outcome,
        rationale_codes=(ReviewRationaleCode("reviewed-visible-fields"),),
        evidence_references=evidence_references or (_finding_reference(assessment),),
        supersedes=supersedes,
    )


@pytest.mark.parametrize(
    "code_type",
    [
        DuplicatePolicyVersion,
        DuplicateRuleId,
        DuplicateRuleVersion,
        DuplicateReasonCode,
        ReviewReferenceCode,
        ReviewerCode,
        ReviewRationaleCode,
    ],
)
@pytest.mark.parametrize("invalid", ["", "has space", "line\nbreak", "é", "x" * 129])
def test_opaque_codes_reject_non_code_text(
    code_type: Callable[[str], object],
    invalid: str,
) -> None:
    with pytest.raises(ValueError):
        code_type(invalid)


def test_policy_v1_has_exact_version_rules_and_order() -> None:
    assert PUBLICATION_DUPLICATE_POLICY_V1_VERSION.value == "publication-duplicate-policy@1"
    assert tuple(rule.rule_id.value for rule in PUBLICATION_DUPLICATE_POLICY_V1.rules) == (
        "total-area-comparison",
        "rooms-comparison",
        "location-text-exact",
        "price-exact",
    )
    assert tuple(rule.rule_version.value for rule in PUBLICATION_DUPLICATE_POLICY_V1.rules) == (
        "duplicate-total-area@1",
        "duplicate-rooms@1",
        "duplicate-location-text@1",
        "duplicate-price@1",
    )
    assert tuple(rule.compared_fields for rule in PUBLICATION_DUPLICATE_POLICY_V1.rules) == (
        ("total_area",),
        ("rooms",),
        ("location_text",),
        ("price_amount", "currency"),
    )


def test_publication_pair_is_canonical_for_same_and_cross_source_pairs() -> None:
    cross = PublicationPair(RIGHT_REF, LEFT_REF)
    same_source = PublicationPair(SAME_SOURCE_REF, LEFT_REF)
    assert cross == PublicationPair(LEFT_REF, RIGHT_REF)
    assert (cross.left, cross.right) == (LEFT_REF, RIGHT_REF)
    assert (same_source.left, same_source.right) == (LEFT_REF, SAME_SOURCE_REF)
    with pytest.raises(ValueError):
        PublicationPair(LEFT_REF, LEFT_REF)


def test_same_reference_returns_stable_failure_without_pair() -> None:
    result = assess_publication_pair(_available(LEFT_REF, 0), _available(LEFT_REF, 1))
    assert isinstance(result, PairAssessmentFailure)
    assert len(result.conflicts) == 1
    assert result.conflicts[0].category == "DUPLICATE_ASSESSMENT_CONFLICT"
    assert result.conflicts[0].code == "same_publication_ref"
    assert result.conflicts[0].subject == LEFT_REF
    assert not hasattr(result, "assessment")


def test_same_source_and_cross_source_pairs_are_assessed_without_merging() -> None:
    same_source = assess_publication_pair(
        _available(LEFT_REF, 0),
        _available(SAME_SOURCE_REF, 1),
    )
    cross_source = assess_publication_pair(
        _available(LEFT_REF, 0),
        _available(RIGHT_REF, 1),
    )
    assert isinstance(same_source, PairAssessmentSuccess)
    assert isinstance(cross_source, PairAssessmentSuccess)
    assert same_source.assessment.identity.pair.right == SAME_SOURCE_REF
    assert cross_source.assessment.identity.pair.right == RIGHT_REF
    assert not hasattr(same_source.assessment, "physical_property")


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (_unavailable(LEFT_REF, 0), _available(RIGHT_REF, 1)),
        (_available(LEFT_REF, 0), _unavailable(RIGHT_REF, 1)),
        (_unavailable(LEFT_REF, 0), _unavailable(RIGHT_REF, 1)),
    ],
)
def test_unavailable_input_is_not_assessed_and_has_no_evidence_or_outcome(
    first: AvailableObservation | UnavailableObservation,
    second: AvailableObservation | UnavailableObservation,
) -> None:
    result = assess_publication_pair(first, second)
    reverse = assess_publication_pair(second, first)
    assert isinstance(result, PairNotAssessed)
    assert result == reverse
    assert result.pair == PublicationPair(LEFT_REF, RIGHT_REF)
    assert result.reason_code.value == "side_not_available"
    assert not hasattr(result, "evidence")
    assert not hasattr(result, "outcome")


@pytest.mark.parametrize(
    ("right_changes", "expected_outcome"),
    [
        (
            {},
            DuplicateAutomaticOutcome.CANDIDATE_REQUIRES_MANUAL_REVIEW,
        ),
        (
            {"rooms": _present(RoomCount(3), RIGHT_REF, _at(1), "rooms", "3")},
            DuplicateAutomaticOutcome.CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW,
        ),
        (
            {
                "total_area": _missing(RIGHT_REF, _at(1), "total_area"),
                "location_text": _present(
                    LocationText("Another Fictional Quarter"),
                    RIGHT_REF,
                    _at(1),
                    "location_text",
                    "Another Fictional Quarter",
                ),
            },
            DuplicateAutomaticOutcome.INSUFFICIENT_EVIDENCE_NO_CANDIDATE,
        ),
        (
            {"total_area": _present(Area(5_100), RIGHT_REF, _at(1), "total_area", "51")},
            DuplicateAutomaticOutcome.INSUFFICIENT_EVIDENCE_NO_CANDIDATE,
        ),
    ],
)
def test_full_structural_symmetry_for_every_automatic_outcome(
    right_changes: dict[str, object],
    expected_outcome: DuplicateAutomaticOutcome,
) -> None:
    left = _available(LEFT_REF, 0)
    right = _available(RIGHT_REF, 1, **right_changes)
    forward = assess_publication_pair(left, right)
    reverse = assess_publication_pair(right, left)
    assert forward == reverse
    assert isinstance(forward, PairAssessmentSuccess)
    assert forward.assessment.outcome is expected_outcome
    assert forward.assessment.left_observation == left
    assert forward.assessment.right_observation == right


@pytest.mark.parametrize(
    ("right_outcome", "reason", "polarity", "strength"),
    [
        ("equal", "exact_total_area", EvidencePolarity.SUPPORTS, EvidenceStrength.MATERIAL),
        (
            "different",
            "different_total_area",
            EvidencePolarity.CONTRADICTS,
            EvidenceStrength.MATERIAL,
        ),
        ("missing", "not_comparable_total_area", None, None),
        ("unsupported", "not_comparable_total_area", None, None),
    ],
)
def test_total_area_rule_exact_matrix(
    right_outcome: str,
    reason: str,
    polarity: EvidencePolarity | None,
    strength: EvidenceStrength | None,
) -> None:
    observed_at = _at(1)
    variants: dict[str, Present[Area] | Missing | Unsupported] = {
        "equal": _present(Area(4_700), RIGHT_REF, observed_at, "total_area", "47.0"),
        "different": _present(Area(4_701), RIGHT_REF, observed_at, "total_area", "47.01"),
        "missing": _missing(RIGHT_REF, observed_at, "total_area"),
        "unsupported": _unsupported(RIGHT_REF, observed_at, "total_area"),
    }
    assessment = _assessment(right=_available(RIGHT_REF, 1, total_area=variants[right_outcome]))
    finding = _finding(assessment, "total-area-comparison")
    assert finding.reason_code.value == reason
    assert finding.compared_fields == ("total_area",)
    if polarity is None:
        assert isinstance(finding, RuleNonComparison)
    else:
        assert isinstance(finding, DuplicateEvidenceItem)
        assert (finding.polarity, finding.strength) == (polarity, strength)


@pytest.mark.parametrize(
    ("right_outcome", "reason", "polarity", "strength"),
    [
        ("equal", "exact_room_count", EvidencePolarity.SUPPORTS, EvidenceStrength.CORROBORATING),
        (
            "different",
            "different_room_count",
            EvidencePolarity.CONTRADICTS,
            EvidenceStrength.MATERIAL,
        ),
        ("missing", "not_comparable_rooms", None, None),
        ("unsupported", "not_comparable_rooms", None, None),
    ],
)
def test_rooms_rule_exact_matrix(
    right_outcome: str,
    reason: str,
    polarity: EvidencePolarity | None,
    strength: EvidenceStrength | None,
) -> None:
    observed_at = _at(1)
    variants: dict[str, Present[RoomCount] | Missing | Unsupported] = {
        "equal": _present(RoomCount(2), RIGHT_REF, observed_at, "rooms", "two"),
        "different": _present(RoomCount(3), RIGHT_REF, observed_at, "rooms", "3"),
        "missing": _missing(RIGHT_REF, observed_at, "rooms"),
        "unsupported": _unsupported(RIGHT_REF, observed_at, "rooms"),
    }
    assessment = _assessment(right=_available(RIGHT_REF, 1, rooms=variants[right_outcome]))
    finding = _finding(assessment, "rooms-comparison")
    assert finding.reason_code.value == reason
    if polarity is None:
        assert isinstance(finding, RuleNonComparison)
    else:
        assert isinstance(finding, DuplicateEvidenceItem)
        assert (finding.polarity, finding.strength) == (polarity, strength)


@pytest.mark.parametrize(
    ("right_outcome", "reason", "is_evidence"),
    [
        ("equal", "exact_location_text", True),
        ("different", "free_text_mismatch_is_neutral", False),
        ("missing", "not_comparable_location_text", False),
        ("unsupported", "not_comparable_location_text", False),
    ],
)
def test_location_rule_treats_only_exact_present_match_as_support(
    right_outcome: str,
    reason: str,
    is_evidence: bool,
) -> None:
    observed_at = _at(1)
    variants: dict[str, Present[LocationText] | Missing | Unsupported] = {
        "equal": _present(
            LocationText("Fictional Quarter"),
            RIGHT_REF,
            observed_at,
            "location_text",
            "Fictional Quarter",
        ),
        "different": _present(
            LocationText("Other Fictional Quarter"),
            RIGHT_REF,
            observed_at,
            "location_text",
            "Other Fictional Quarter",
        ),
        "missing": _missing(RIGHT_REF, observed_at, "location_text"),
        "unsupported": _unsupported(RIGHT_REF, observed_at, "location_text"),
    }
    assessment = _assessment(right=_available(RIGHT_REF, 1, location_text=variants[right_outcome]))
    finding = _finding(assessment, "location-text-exact")
    assert finding.reason_code.value == reason
    if is_evidence:
        assert isinstance(finding, DuplicateEvidenceItem)
        assert finding.polarity is EvidencePolarity.SUPPORTS
        assert finding.strength is EvidenceStrength.CORROBORATING
    else:
        assert isinstance(finding, RuleNonComparison)


def _future_currency(value: str) -> Currency:
    currency = object.__new__(Currency)
    object.__setattr__(currency, "value", value)
    return currency


@pytest.mark.parametrize(
    ("amount_kind", "currency_kind", "reason", "is_evidence"),
    [
        ("equal", "equal", "exact_price_same_currency", True),
        ("different", "equal", "price_difference_is_neutral", False),
        ("equal", "different", "currency_difference_is_neutral", False),
        ("missing", "equal", "not_comparable_price", False),
        ("unsupported", "equal", "not_comparable_price", False),
        ("equal", "missing", "not_comparable_price", False),
        ("equal", "unsupported", "not_comparable_price", False),
    ],
)
def test_price_rule_exact_matrix_and_neutral_differences(
    amount_kind: str,
    currency_kind: str,
    reason: str,
    is_evidence: bool,
) -> None:
    observed_at = _at(1)
    amounts: dict[str, Present[MoneyAmount] | Missing | Unsupported] = {
        "equal": _present(
            MoneyAmount(12_300_000), RIGHT_REF, observed_at, "price_amount", "123000"
        ),
        "different": _present(
            MoneyAmount(12_400_000), RIGHT_REF, observed_at, "price_amount", "124000"
        ),
        "missing": _missing(RIGHT_REF, observed_at, "price_amount"),
        "unsupported": _unsupported(RIGHT_REF, observed_at, "price_amount"),
    }
    currencies: dict[str, Present[Currency] | Missing | Unsupported] = {
        "equal": _present(Currency("RUB"), RIGHT_REF, observed_at, "currency", "RUB"),
        # Current normalization supports only RUB. A constructor-bypassed future canonical
        # currency exercises the policy's defensive cross-currency branch without changing it.
        "different": _present(_future_currency("USD"), RIGHT_REF, observed_at, "currency", "USD"),
        "missing": _missing(RIGHT_REF, observed_at, "currency"),
        "unsupported": _unsupported(RIGHT_REF, observed_at, "currency", "XYZ"),
    }
    assessment = _assessment(
        right=_available(
            RIGHT_REF,
            1,
            price_amount=amounts[amount_kind],
            currency=currencies[currency_kind],
        )
    )
    finding = _finding(assessment, "price-exact")
    assert finding.reason_code.value == reason
    assert finding.compared_fields == ("price_amount", "currency")
    assert tuple(snapshot.field for snapshot in finding.left_snapshots) == finding.compared_fields
    assert tuple(snapshot.field for snapshot in finding.right_snapshots) == finding.compared_fields
    if is_evidence:
        assert isinstance(finding, DuplicateEvidenceItem)
        assert finding.polarity is EvidencePolarity.SUPPORTS
        assert finding.strength is EvidenceStrength.AUXILIARY
    else:
        assert isinstance(finding, RuleNonComparison)


def test_snapshots_preserve_side_provenance_missing_and_unsupported_semantics() -> None:
    right_at = _at(1)
    assessment = _assessment(
        right=_available(
            RIGHT_REF,
            1,
            total_area=_missing(RIGHT_REF, right_at, "total_area"),
            rooms=_unsupported(RIGHT_REF, right_at, "rooms", "many", "rooms_not_supported"),
        )
    )
    area = cast(RuleNonComparison, _finding(assessment, "total-area-comparison"))
    rooms = cast(RuleNonComparison, _finding(assessment, "rooms-comparison"))
    area_right = area.right_snapshots[0]
    rooms_right = rooms.right_snapshots[0]
    assert isinstance(area_right.canonical, MissingValue)
    assert isinstance(area_right.provenance, MissingProvenance)
    assert not hasattr(area_right.provenance, "raw_value")
    assert isinstance(rooms_right.canonical, UnsupportedValue)
    assert rooms_right.canonical.reason_code == "rooms_not_supported"
    assert isinstance(rooms_right.provenance, UnsupportedProvenance)
    assert rooms_right.provenance.raw_value == "many"
    findings: tuple[DuplicateEvidenceItem | RuleNonComparison, ...] = (
        *assessment.evidence,
        *assessment.non_comparisons,
    )
    for finding in findings:
        for snapshot in finding.left_snapshots:
            assert snapshot.provenance.source_id == LEFT_REF.source_id
            assert snapshot.provenance.publication_id == LEFT_REF.publication_id
        for snapshot in finding.right_snapshots:
            assert snapshot.provenance.source_id == RIGHT_REF.source_id
            assert snapshot.provenance.publication_id == RIGHT_REF.publication_id


def test_findings_are_strictly_policy_ordered_in_separate_tuples() -> None:
    right_at = _at(1)
    assessment = _assessment(
        right=_available(
            RIGHT_REF,
            1,
            rooms=_present(RoomCount(3), RIGHT_REF, right_at, "rooms", "3"),
            location_text=_missing(RIGHT_REF, right_at, "location_text"),
            price_amount=_missing(RIGHT_REF, right_at, "price_amount"),
            currency=_missing(RIGHT_REF, right_at, "currency"),
        )
    )
    assert tuple(item.rule_id.value for item in assessment.evidence) == (
        "total-area-comparison",
        "rooms-comparison",
    )
    assert tuple(item.rule_id.value for item in assessment.non_comparisons) == (
        "location-text-exact",
        "price-exact",
    )
    with pytest.raises(ValueError):
        replace(assessment, evidence=tuple(reversed(assessment.evidence)))


def test_decision_table_preserves_support_and_contradiction_together() -> None:
    right_at = _at(1)
    assessment = _assessment(
        right=_available(
            RIGHT_REF,
            1,
            rooms=_present(RoomCount(3), RIGHT_REF, right_at, "rooms", "3"),
        )
    )
    assert (
        assessment.outcome is DuplicateAutomaticOutcome.CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW
    )
    assert [item.polarity for item in assessment.evidence] == [
        EvidencePolarity.SUPPORTS,
        EvidencePolarity.CONTRADICTS,
        EvidencePolarity.SUPPORTS,
        EvidencePolarity.SUPPORTS,
    ]


def test_exact_price_alone_is_insufficient_and_no_numeric_result_exists() -> None:
    right_at = _at(1)
    assessment = _assessment(
        left=_available(
            LEFT_REF,
            0,
            total_area=_missing(LEFT_REF, _at(0), "total_area"),
            rooms=_missing(LEFT_REF, _at(0), "rooms"),
            location_text=_missing(LEFT_REF, _at(0), "location_text"),
        ),
        right=_available(
            RIGHT_REF,
            1,
            total_area=_missing(RIGHT_REF, right_at, "total_area"),
            rooms=_missing(RIGHT_REF, right_at, "rooms"),
            location_text=_missing(RIGHT_REF, right_at, "location_text"),
        ),
    )
    assert assessment.outcome is DuplicateAutomaticOutcome.INSUFFICIENT_EVIDENCE_NO_CANDIDATE
    assert tuple(item.reason_code.value for item in assessment.evidence) == (
        "exact_price_same_currency",
    )
    assessment_fields = {field.name for field in fields(DuplicatePairAssessment)}
    assert {"score", "probability", "tolerance"}.isdisjoint(assessment_fields)


def test_identity_binding_new_observation_and_policy_are_structural() -> None:
    assessment = _assessment()
    with pytest.raises(ValueError):
        DuplicateAssessmentIdentity(
            assessment.identity.pair,
            assessment.identity.right_observation_key,
            assessment.identity.left_observation_key,
            assessment.identity.policy_version,
        )
    new_observation_assessment = _assessment(right=_available(RIGHT_REF, 2))
    policy_v2 = DuplicatePolicy(
        DuplicatePolicyVersion("publication-duplicate-policy@2"),
        PUBLICATION_DUPLICATE_POLICY_V1.rules,
    )
    policy_result = assess_publication_pair(
        assessment.left_observation,
        assessment.right_observation,
        policy_v2,
    )
    assert isinstance(policy_result, PairAssessmentSuccess)
    assert new_observation_assessment.identity != assessment.identity
    assert policy_result.assessment.identity != assessment.identity
    assert policy_result.assessment.identity.policy_version == policy_v2.version


def test_current_stale_and_supersession_are_explicit_and_immutable() -> None:
    assessment = _assessment()
    current = CurrentPairContext(
        assessment.identity.pair,
        assessment.identity.left_observation_key,
        assessment.identity.right_observation_key,
        assessment.identity.policy_version,
    )
    missing_current = replace(current, right_available_key=None)
    newer = _assessment(right=_available(RIGHT_REF, 2))
    stale = replace(current, right_available_key=newer.identity.right_observation_key)
    assert is_assessment_current(assessment, current)
    assert not is_assessment_stale(assessment, current)
    assert is_assessment_stale(assessment, stale)
    assert is_assessment_stale(assessment, missing_current)
    link = AssessmentSupersession(assessment.identity, newer.identity)
    assert link.previous == assessment.identity
    with pytest.raises(ValueError):
        AssessmentSupersession(assessment.identity, assessment.identity)
    other_pair = _assessment(
        left=_available(LEFT_REF, 0),
        right=_available(THIRD_REF, 1),
    )
    with pytest.raises(ValueError):
        AssessmentSupersession(assessment.identity, other_pair.identity)


@pytest.mark.parametrize("outcome", list(ManualReviewOutcome))
def test_manual_review_all_outcomes_remain_separate_from_assessment(
    outcome: ManualReviewOutcome,
) -> None:
    assessment = _assessment()
    before = assessment
    result = create_manual_review(assessment, _draft(assessment, outcome=outcome))
    assert isinstance(result, ManualReviewSuccess)
    assert isinstance(result.review, DuplicatePairManualReview)
    assert result.disposition is ManualReviewDisposition.CREATED
    assert result.review.outcome is outcome
    assert result.review.assessment_identity == assessment.identity
    assert assessment == before
    assert result.review.evidence_references[0].assessment_identity == assessment.identity
    assert not hasattr(result.review, "merged_listing")
    assert not hasattr(result.review, "physical_property")
    assert not hasattr(result.review, "cluster")


def test_manual_review_can_reference_evidence_and_non_comparison_exactly() -> None:
    right_at = _at(1)
    assessment = _assessment(
        right=_available(
            RIGHT_REF,
            1,
            location_text=_missing(RIGHT_REF, right_at, "location_text"),
        )
    )
    references = (
        _finding_reference(assessment, AssessmentFindingKind.EVIDENCE, 0),
        _finding_reference(assessment, AssessmentFindingKind.NON_COMPARISON, 0),
    )
    result = create_manual_review(
        assessment,
        _draft(
            assessment,
            outcome=ManualReviewOutcome.INCONCLUSIVE,
            evidence_references=references,
        ),
    )
    assert isinstance(result, ManualReviewSuccess)
    assert result.review.evidence_references == references


@pytest.mark.parametrize("change", ["ordinal", "rule_id", "rule_version", "polarity"])
def test_manual_review_rejects_inexact_finding_references(change: str) -> None:
    assessment = _assessment()
    reference = _finding_reference(assessment)
    if change == "ordinal":
        invalid = replace(reference, ordinal=99)
    elif change == "rule_id":
        invalid = replace(reference, rule_id=DuplicateRuleId("another-rule"))
    elif change == "rule_version":
        invalid = replace(reference, rule_version=DuplicateRuleVersion("another-rule@1"))
    else:
        invalid = replace(reference, polarity=EvidencePolarity.CONTRADICTS)
    result = create_manual_review(
        assessment,
        _draft(assessment, evidence_references=(invalid,)),
    )
    assert isinstance(result, ManualReviewFailure)
    assert result.conflicts[0].code == "review_assessment_mismatch"
    assert not hasattr(result, "review")


def test_manual_review_rejects_wrong_assessment_binding() -> None:
    assessment = _assessment()
    other = _assessment(right=_available(RIGHT_REF, 2))
    result = create_manual_review(
        assessment,
        _draft(
            assessment,
            assessment_identity=other.identity,
            evidence_references=(_finding_reference(other),),
        ),
    )
    assert isinstance(result, ManualReviewFailure)
    assert result.conflicts[0].code == "review_assessment_mismatch"


def test_manual_review_revision_two_same_assessment_and_exact_replay() -> None:
    assessment = _assessment()
    first_result = create_manual_review(assessment, _draft(assessment))
    assert isinstance(first_result, ManualReviewSuccess)
    first = first_result.review
    second_draft = _draft(
        assessment,
        revision=2,
        reviewed_at=_reviewed(2),
        supersedes=first.identity,
        outcome=ManualReviewOutcome.REJECTED_RELATIONSHIP,
    )
    second_result = create_manual_review(assessment, second_draft, previous=first)
    assert isinstance(second_result, ManualReviewSuccess)
    assert second_result.disposition is ManualReviewDisposition.CREATED
    replay = create_manual_review(assessment, second_draft, previous=second_result.review)
    assert isinstance(replay, ManualReviewSuccess)
    assert replay.disposition is ManualReviewDisposition.REPLAYED
    assert replay.review is second_result.review


def test_manual_review_revision_two_can_bind_new_assessment_of_same_pair() -> None:
    assessment = _assessment()
    first_result = create_manual_review(assessment, _draft(assessment))
    assert isinstance(first_result, ManualReviewSuccess)
    newer = _assessment(right=_available(RIGHT_REF, 2))
    second = create_manual_review(
        newer,
        _draft(
            newer,
            revision=2,
            reviewed_at=_reviewed(2),
            supersedes=first_result.review.identity,
        ),
        previous=first_result.review,
    )
    assert isinstance(second, ManualReviewSuccess)
    assert second.review.assessment_identity == newer.identity
    assert first_result.review.assessment_identity == assessment.identity


def test_equal_manual_review_identity_with_other_content_is_conflict() -> None:
    assessment = _assessment()
    created = create_manual_review(assessment, _draft(assessment))
    assert isinstance(created, ManualReviewSuccess)
    conflicting = _draft(
        assessment,
        outcome=ManualReviewOutcome.REJECTED_RELATIONSHIP,
    )
    result = create_manual_review(assessment, conflicting, previous=created.review)
    assert isinstance(result, ManualReviewFailure)
    assert result.conflicts[0].code == "review_identity_content_conflict"


@pytest.mark.parametrize(
    "case", ["missing_previous", "bad_supersedes", "not_later", "revision1_previous"]
)
def test_manual_review_revision_and_timestamp_mismatches_are_atomic(case: str) -> None:
    assessment = _assessment()
    created = create_manual_review(assessment, _draft(assessment))
    assert isinstance(created, ManualReviewSuccess)
    previous = created.review
    if case == "missing_previous":
        draft = _draft(assessment, revision=2, supersedes=previous.identity)
        supplied_previous = None
    elif case == "bad_supersedes":
        draft = _draft(
            assessment,
            revision=2,
            supersedes=ManualReviewIdentity(ReviewReferenceCode("other-review"), 1),
        )
        supplied_previous = previous
    elif case == "not_later":
        draft = _draft(
            assessment,
            revision=2,
            reviewed_at=previous.reviewed_at,
            supersedes=previous.identity,
        )
        supplied_previous = previous
    else:
        draft = replace(
            _draft(assessment),
            identity=ManualReviewIdentity(ReviewReferenceCode("other-review"), 1),
        )
        supplied_previous = previous
    result = create_manual_review(assessment, draft, previous=supplied_previous)
    assert isinstance(result, ManualReviewFailure)
    assert result.conflicts[0].code == "review_revision_mismatch"
    assert not hasattr(result, "review")


def test_manual_review_revision_cannot_cross_pair() -> None:
    assessment = _assessment()
    created = create_manual_review(assessment, _draft(assessment))
    assert isinstance(created, ManualReviewSuccess)
    other = _assessment(
        left=_available(LEFT_REF, 0),
        right=_available(THIRD_REF, 1),
    )
    draft = _draft(
        other,
        revision=2,
        reviewed_at=_reviewed(2),
        supersedes=created.review.identity,
    )
    result = create_manual_review(other, draft, previous=created.review)
    assert isinstance(result, ManualReviewFailure)
    assert result.conflicts[0].code == "review_assessment_mismatch"


def test_frozen_slots_tuple_only_and_failure_invariants() -> None:
    assessment = _assessment()
    assert not hasattr(assessment, "__dict__")
    with pytest.raises(FrozenInstanceError):
        assessment.outcome = DuplicateAutomaticOutcome.INSUFFICIENT_EVIDENCE_NO_CANDIDATE  # type: ignore[misc]
    with pytest.raises(TypeError):
        replace(assessment, evidence=list(assessment.evidence))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        ManualReviewDraft(
            identity=ManualReviewIdentity(ReviewReferenceCode("review-shape"), 1),
            assessment_identity=assessment.identity,
            reviewed_at=_reviewed(0),
            reviewer_code=ReviewerCode("reviewer-shape"),
            outcome=ManualReviewOutcome.INCONCLUSIVE,
            rationale_codes=cast(Any, [ReviewRationaleCode("shape-check")]),
            evidence_references=(_finding_reference(assessment),),
        )
    with pytest.raises(ValueError):
        PairAssessmentFailure(())
    with pytest.raises(ValueError):
        ManualReviewFailure(())
    with pytest.raises(ValueError):
        replace(assessment.evidence[0], compared_fields=())
    with pytest.raises(ValueError):
        ManualReviewDraft(
            identity=ManualReviewIdentity(ReviewReferenceCode("review-empty"), 1),
            assessment_identity=assessment.identity,
            reviewed_at=_reviewed(0),
            reviewer_code=ReviewerCode("reviewer-empty"),
            outcome=ManualReviewOutcome.INCONCLUSIVE,
            rationale_codes=(),
            evidence_references=(_finding_reference(assessment),),
        )


def test_public_duplicate_records_are_frozen_slots_and_consciously_exported() -> None:
    record_types = (
        DuplicateAssessmentIdentity,
        DuplicateEvidenceItem,
        DuplicateFieldSnapshot,
        DuplicatePairAssessment,
        DuplicatePairManualReview,
        DuplicatePolicy,
        ManualReviewDraft,
        ManualReviewIdentity,
        PairAssessmentFailure,
        PairAssessmentSuccess,
        PairNotAssessed,
        PublicationPair,
        RuleNonComparison,
    )
    for record_type in record_types:
        assert is_dataclass(record_type)
        assert cast(Any, record_type).__dataclass_params__.frozen
        assert "__slots__" in record_type.__dict__
        assert record_type.__name__ in duplicate_module.__all__
        assert getattr(real_estate_parser, record_type.__name__) is record_type


def test_duplicate_snapshot_reuses_canonical_outcome_invariants() -> None:
    provenance = _value_provenance(LEFT_REF, _at(0), "total_area", "47")
    snapshot = DuplicateFieldSnapshot("total_area", PresentValue(Area(4_700)), provenance)
    assert snapshot.canonical == PresentValue(Area(4_700))
    with pytest.raises(ValueError):
        DuplicateFieldSnapshot("rooms", PresentValue(Area(4_700)), provenance)
    with pytest.raises(ValueError):
        DuplicateFieldSnapshot(
            "total_area",
            MissingValue(),
            provenance,
        )


def test_non_transitivity_creates_no_third_relation_or_cluster_api() -> None:
    ab = _assessment(
        left=_available(LEFT_REF, 0),
        right=_available(RIGHT_REF, 1),
    )
    bc_result = assess_publication_pair(
        _available(RIGHT_REF, 1),
        _available(THIRD_REF, 2),
    )
    assert isinstance(bc_result, PairAssessmentSuccess)
    assert ab.identity.pair != bc_result.assessment.identity.pair
    assert not hasattr(real_estate_parser, "cluster_publications")
    assert not hasattr(real_estate_parser, "PhysicalProperty")
    assert not hasattr(ab, "related_pairs")


def test_module_has_no_io_boundary_clock_uuid_score_or_storage_imports() -> None:
    module_path = Path(real_estate_parser.__file__).with_name(
        "publication_duplicate_assessments.py"
    )
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
        {"json", "pydantic", "pathlib", "sqlite3", "time", "uuid", "os"}
    )
    public_names = set(real_estate_parser.publication_duplicate_assessments.__all__)
    assert not any(
        forbidden in name.lower()
        for name in public_names
        for forbidden in ("score", "probability", "cluster", "merge", "storage")
    )
