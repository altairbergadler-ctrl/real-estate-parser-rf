"""Pure evidence-based assessment of one unordered publication pair."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from real_estate_parser.normalization import (
    Area,
    Currency,
    FieldOutcome,
    LocationText,
    Missing,
    MissingProvenance,
    MoneyAmount,
    Present,
    RoomCount,
    Unsupported,
    UnsupportedProvenance,
    ValueProvenance,
)
from real_estate_parser.publication_observations import (
    AvailableObservation,
    CanonicalFieldOutcome,
    FieldSnapshot,
    MissingValue,
    ObservationKey,
    PresentValue,
    PublicationObservation,
    UnavailableObservation,
    UnsupportedValue,
)
from real_estate_parser.source_batch import PublicationRef

type DuplicateComparableFieldName = Literal[
    "total_area",
    "rooms",
    "location_text",
    "price_amount",
    "currency",
]
type DuplicateAssessmentConflictCategory = Literal["DUPLICATE_ASSESSMENT_CONFLICT"]
type DuplicateAssessmentConflictCode = Literal[
    "same_publication_ref",
    "observation_pair_mismatch",
    "assessment_identity_content_conflict",
    "assessment_supersession_conflict",
]
type ManualReviewConflictCategory = Literal["MANUAL_REVIEW_CONFLICT"]
type ManualReviewConflictCode = Literal[
    "review_assessment_mismatch",
    "review_identity_content_conflict",
    "review_revision_mismatch",
    "review_revision_fork",
]
type DuplicateFieldProvenance = ValueProvenance | MissingProvenance | UnsupportedProvenance

_DUPLICATE_FIELDS: tuple[DuplicateComparableFieldName, ...] = (
    "total_area",
    "rooms",
    "location_text",
    "price_amount",
    "currency",
)


def _validate_opaque_code(value: str, label: str) -> None:
    if (
        not 1 <= len(value) <= 128
        or not value.isascii()
        or any(not 0x21 <= ord(character) <= 0x7E for character in value)
    ):
        raise ValueError(f"invalid {label}")


@dataclass(frozen=True, slots=True)
class DuplicatePolicyVersion:
    """Stable opaque identifier for duplicate policy semantics."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "duplicate policy version")


@dataclass(frozen=True, slots=True)
class DuplicateRuleId:
    """Stable opaque identifier for one duplicate rule."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "duplicate rule id")


@dataclass(frozen=True, slots=True)
class DuplicateRuleVersion:
    """Stable opaque identifier for one duplicate rule revision."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "duplicate rule version")


@dataclass(frozen=True, slots=True)
class DuplicateReasonCode:
    """Short safe opaque explanation code, never arbitrary review text."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "duplicate reason code")


@dataclass(frozen=True, slots=True)
class PublicationPair:
    """Canonical unordered pair of two different source publications."""

    left: PublicationRef
    right: PublicationRef

    def __post_init__(self) -> None:
        if not isinstance(self.left, PublicationRef) or not isinstance(self.right, PublicationRef):
            raise TypeError("publication pair requires publication references")
        if self.left == self.right:
            raise ValueError("publication pair requires different references")
        if _reference_sort_key(self.right) < _reference_sort_key(self.left):
            original_left = self.left
            object.__setattr__(self, "left", self.right)
            object.__setattr__(self, "right", original_left)


def _reference_sort_key(reference: PublicationRef) -> tuple[str, str]:
    return reference.source_id.value, reference.publication_id.value


@dataclass(frozen=True, slots=True)
class DuplicateAssessmentIdentity:
    """Structural identity of one exact pair/observations/policy assessment."""

    pair: PublicationPair
    left_observation_key: ObservationKey
    right_observation_key: ObservationKey
    policy_version: DuplicatePolicyVersion

    def __post_init__(self) -> None:
        if self.left_observation_key.reference != self.pair.left:
            raise ValueError("left observation key does not match assessment pair")
        if self.right_observation_key.reference != self.pair.right:
            raise ValueError("right observation key does not match assessment pair")


@dataclass(frozen=True, slots=True)
class DuplicateFieldSnapshot:
    """One duplicate-policy field projection with its complete provenance."""

    field: DuplicateComparableFieldName
    canonical: CanonicalFieldOutcome
    provenance: DuplicateFieldProvenance

    def __post_init__(self) -> None:
        if self.field not in _DUPLICATE_FIELDS:
            raise ValueError("unsupported duplicate comparable field")
        FieldSnapshot(canonical=self.canonical, provenance=self.provenance)
        if isinstance(self.canonical, PresentValue):
            expected_type: type[object]
            if self.field == "total_area":
                expected_type = Area
            elif self.field == "rooms":
                expected_type = RoomCount
            elif self.field == "location_text":
                expected_type = LocationText
            elif self.field == "price_amount":
                expected_type = MoneyAmount
            else:
                expected_type = Currency
            if not isinstance(self.canonical.value, expected_type):
                raise ValueError("canonical value type does not match duplicate field")


class EvidencePolarity(StrEnum):
    """Direction of one comparable duplicate finding."""

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"


class EvidenceStrength(StrEnum):
    """Policy-defined categorical role, not a numeric weight."""

    MATERIAL = "MATERIAL"
    CORROBORATING = "CORROBORATING"
    AUXILIARY = "AUXILIARY"


def _validate_finding_shape(
    compared_fields: tuple[DuplicateComparableFieldName, ...],
    left_snapshots: tuple[DuplicateFieldSnapshot, ...],
    right_snapshots: tuple[DuplicateFieldSnapshot, ...],
) -> None:
    if not isinstance(compared_fields, tuple):
        raise TypeError("compared fields must be a tuple")
    if not isinstance(left_snapshots, tuple) or not isinstance(right_snapshots, tuple):
        raise TypeError("finding snapshots must be tuples")
    if not compared_fields:
        raise ValueError("a duplicate finding must compare at least one field")
    if len(set(compared_fields)) != len(compared_fields):
        raise ValueError("compared fields must be unique")
    if any(field not in _DUPLICATE_FIELDS for field in compared_fields):
        raise ValueError("finding contains an unsupported duplicate field")
    if len(left_snapshots) != len(compared_fields) or len(right_snapshots) != len(compared_fields):
        raise ValueError("finding snapshots must align with compared fields")
    if tuple(snapshot.field for snapshot in left_snapshots) != compared_fields:
        raise ValueError("left snapshots do not align with compared fields")
    if tuple(snapshot.field for snapshot in right_snapshots) != compared_fields:
        raise ValueError("right snapshots do not align with compared fields")


@dataclass(frozen=True, slots=True)
class DuplicateEvidenceItem:
    """One positive or negative comparable finding from a versioned rule."""

    rule_id: DuplicateRuleId
    rule_version: DuplicateRuleVersion
    polarity: EvidencePolarity
    strength: EvidenceStrength
    compared_fields: tuple[DuplicateComparableFieldName, ...]
    left_snapshots: tuple[DuplicateFieldSnapshot, ...]
    right_snapshots: tuple[DuplicateFieldSnapshot, ...]
    reason_code: DuplicateReasonCode

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, DuplicateRuleId) or not isinstance(
            self.rule_version, DuplicateRuleVersion
        ):
            raise TypeError("duplicate evidence requires rule codes")
        if not isinstance(self.polarity, EvidencePolarity) or not isinstance(
            self.strength, EvidenceStrength
        ):
            raise TypeError("duplicate evidence requires categorical polarity and strength")
        _validate_finding_shape(
            self.compared_fields,
            self.left_snapshots,
            self.right_snapshots,
        )


@dataclass(frozen=True, slots=True)
class RuleNonComparison:
    """A rule result with insufficient or intentionally neutral comparison."""

    rule_id: DuplicateRuleId
    rule_version: DuplicateRuleVersion
    compared_fields: tuple[DuplicateComparableFieldName, ...]
    left_snapshots: tuple[DuplicateFieldSnapshot, ...]
    right_snapshots: tuple[DuplicateFieldSnapshot, ...]
    reason_code: DuplicateReasonCode

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, DuplicateRuleId) or not isinstance(
            self.rule_version, DuplicateRuleVersion
        ):
            raise TypeError("rule non-comparison requires rule codes")
        _validate_finding_shape(
            self.compared_fields,
            self.left_snapshots,
            self.right_snapshots,
        )


@dataclass(frozen=True, slots=True)
class DuplicateRule:
    """Immutable identity and field shape of one supported rule."""

    rule_id: DuplicateRuleId
    rule_version: DuplicateRuleVersion
    compared_fields: tuple[DuplicateComparableFieldName, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.compared_fields, tuple):
            raise TypeError("duplicate rule fields must be a tuple")
        if not self.compared_fields:
            raise ValueError("duplicate rule must compare at least one field")
        if len(set(self.compared_fields)) != len(self.compared_fields):
            raise ValueError("duplicate rule fields must be unique")
        if any(field not in _DUPLICATE_FIELDS for field in self.compared_fields):
            raise ValueError("duplicate rule contains an unsupported field")


@dataclass(frozen=True, slots=True)
class DuplicatePolicy:
    """Immutable ordered set of duplicate rules."""

    version: DuplicatePolicyVersion
    rules: tuple[DuplicateRule, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.rules, tuple):
            raise TypeError("duplicate policy rules must be a tuple")
        if not self.rules:
            raise ValueError("duplicate policy must contain a rule")
        if any(not isinstance(rule, DuplicateRule) for rule in self.rules):
            raise TypeError("duplicate policy contains an unsupported rule")
        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("duplicate policy rule ids must be unique")


PUBLICATION_DUPLICATE_POLICY_V1_VERSION = DuplicatePolicyVersion("publication-duplicate-policy@1")
_TOTAL_AREA_RULE = DuplicateRule(
    DuplicateRuleId("total-area-comparison"),
    DuplicateRuleVersion("duplicate-total-area@1"),
    ("total_area",),
)
_ROOMS_RULE = DuplicateRule(
    DuplicateRuleId("rooms-comparison"),
    DuplicateRuleVersion("duplicate-rooms@1"),
    ("rooms",),
)
_LOCATION_RULE = DuplicateRule(
    DuplicateRuleId("location-text-exact"),
    DuplicateRuleVersion("duplicate-location-text@1"),
    ("location_text",),
)
_PRICE_RULE = DuplicateRule(
    DuplicateRuleId("price-exact"),
    DuplicateRuleVersion("duplicate-price@1"),
    ("price_amount", "currency"),
)
PUBLICATION_DUPLICATE_POLICY_V1 = DuplicatePolicy(
    version=PUBLICATION_DUPLICATE_POLICY_V1_VERSION,
    rules=(_TOTAL_AREA_RULE, _ROOMS_RULE, _LOCATION_RULE, _PRICE_RULE),
)


class DuplicateAutomaticOutcome(StrEnum):
    """Conservative categorical outcome that never confirms a property."""

    CANDIDATE_REQUIRES_MANUAL_REVIEW = "CANDIDATE_REQUIRES_MANUAL_REVIEW"
    CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW = "CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW"
    INSUFFICIENT_EVIDENCE_NO_CANDIDATE = "INSUFFICIENT_EVIDENCE_NO_CANDIDATE"


@dataclass(frozen=True, slots=True)
class DuplicatePairAssessment:
    """Complete automatic hypothesis for two exact available observations."""

    identity: DuplicateAssessmentIdentity
    left_observation: AvailableObservation
    right_observation: AvailableObservation
    evidence: tuple[DuplicateEvidenceItem, ...]
    non_comparisons: tuple[RuleNonComparison, ...]
    outcome: DuplicateAutomaticOutcome

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, tuple) or not isinstance(self.non_comparisons, tuple):
            raise TypeError("assessment findings must be tuples")
        if any(not isinstance(item, DuplicateEvidenceItem) for item in self.evidence):
            raise TypeError("assessment contains unsupported evidence")
        if any(not isinstance(item, RuleNonComparison) for item in self.non_comparisons):
            raise TypeError("assessment contains unsupported non-comparison")
        if self.left_observation.key != self.identity.left_observation_key:
            raise ValueError("left observation does not match assessment identity")
        if self.right_observation.key != self.identity.right_observation_key:
            raise ValueError("right observation does not match assessment identity")
        _validate_assessment_finding_bindings(self)
        expected_evidence, expected_non_comparisons = _evaluate_rules(
            self.left_observation,
            self.right_observation,
            PUBLICATION_DUPLICATE_POLICY_V1.rules,
        )
        if self.evidence != expected_evidence or self.non_comparisons != expected_non_comparisons:
            raise ValueError("assessment findings do not match publication duplicate policy")
        if self.outcome is not _automatic_outcome(self.evidence):
            raise ValueError("assessment outcome does not match duplicate evidence")


@dataclass(frozen=True, slots=True)
class CurrentPairContext:
    """Explicit current available keys and policy for one canonical pair."""

    pair: PublicationPair
    left_available_key: ObservationKey | None
    right_available_key: ObservationKey | None
    policy_version: DuplicatePolicyVersion

    def __post_init__(self) -> None:
        if (
            self.left_available_key is not None
            and self.left_available_key.reference != self.pair.left
        ):
            raise ValueError("current left key does not match pair")
        if (
            self.right_available_key is not None
            and self.right_available_key.reference != self.pair.right
        ):
            raise ValueError("current right key does not match pair")


def is_assessment_current(
    assessment: DuplicatePairAssessment,
    context: CurrentPairContext,
) -> bool:
    """Return whether an immutable assessment exactly matches explicit current context."""

    if context.left_available_key is None or context.right_available_key is None:
        return False
    return assessment.identity == DuplicateAssessmentIdentity(
        pair=context.pair,
        left_observation_key=context.left_available_key,
        right_observation_key=context.right_available_key,
        policy_version=context.policy_version,
    )


def is_assessment_stale(
    assessment: DuplicatePairAssessment,
    context: CurrentPairContext,
) -> bool:
    """Return the exact complement of the current check."""

    return not is_assessment_current(assessment, context)


@dataclass(frozen=True, slots=True)
class AssessmentSupersession:
    """Explicit immutable replacement link between assessments of one pair."""

    previous: DuplicateAssessmentIdentity
    replacement: DuplicateAssessmentIdentity

    def __post_init__(self) -> None:
        if self.previous.pair != self.replacement.pair:
            raise ValueError("assessment supersession must stay within one pair")
        if self.previous == self.replacement:
            raise ValueError("assessment supersession requires a different replacement")


@dataclass(frozen=True, slots=True)
class DuplicateAssessmentConflict:
    """Stable duplicate-assessment conflict without partial assessment state."""

    category: DuplicateAssessmentConflictCategory
    code: DuplicateAssessmentConflictCode
    subject: PublicationRef | ObservationKey | DuplicateAssessmentIdentity | AssessmentSupersession

    def __post_init__(self) -> None:
        if self.category != "DUPLICATE_ASSESSMENT_CONFLICT":
            raise ValueError("invalid duplicate assessment conflict category")


@dataclass(frozen=True, slots=True)
class PairAssessmentSuccess:
    """A complete automatic assessment of two available observations."""

    assessment: DuplicatePairAssessment


@dataclass(frozen=True, slots=True)
class PairNotAssessed:
    """Canonical pair and keys that produced no assessment or categorical outcome."""

    pair: PublicationPair
    left_key: ObservationKey
    right_key: ObservationKey
    reason_code: DuplicateReasonCode

    def __post_init__(self) -> None:
        if self.left_key.reference != self.pair.left or self.right_key.reference != self.pair.right:
            raise ValueError("not-assessed keys do not match canonical pair")
        if self.reason_code != DuplicateReasonCode("side_not_available"):
            raise ValueError("unsupported pair-not-assessed reason")


@dataclass(frozen=True, slots=True)
class PairAssessmentFailure:
    """Atomic failure containing conflicts and no partial assessment."""

    conflicts: tuple[DuplicateAssessmentConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple):
            raise TypeError("duplicate assessment conflicts must be a tuple")
        if not self.conflicts:
            raise ValueError("failed pair assessment must contain a conflict")
        if any(
            not isinstance(conflict, DuplicateAssessmentConflict) for conflict in self.conflicts
        ):
            raise TypeError("pair assessment failure contains an unsupported conflict")


type PairAssessmentResult = PairAssessmentSuccess | PairNotAssessed | PairAssessmentFailure


def _field_snapshot(
    observation: AvailableObservation,
    field: DuplicateComparableFieldName,
) -> DuplicateFieldSnapshot:
    outcome: FieldOutcome[object]
    if field == "total_area":
        outcome = observation.listing.total_area
    elif field == "rooms":
        outcome = observation.listing.rooms
    elif field == "location_text":
        outcome = observation.listing.location_text
    elif field == "price_amount":
        outcome = observation.listing.price_amount
    else:
        outcome = observation.listing.currency
    if isinstance(outcome, Present):
        canonical_value = outcome.value.value
        if not isinstance(
            canonical_value,
            (LocationText, MoneyAmount, Currency, Area, RoomCount),
        ):
            raise TypeError("unsupported duplicate canonical value")
        canonical: CanonicalFieldOutcome = PresentValue(canonical_value)
        provenance: DuplicateFieldProvenance = outcome.value.provenance
    elif isinstance(outcome, Missing):
        canonical = MissingValue()
        provenance = outcome.provenance
    else:
        assert isinstance(outcome, Unsupported)
        canonical = UnsupportedValue(outcome.provenance.reason_code)
        provenance = outcome.provenance
    return DuplicateFieldSnapshot(field, canonical, provenance)


def _finding_snapshots(
    left: AvailableObservation,
    right: AvailableObservation,
    rule: DuplicateRule,
) -> tuple[tuple[DuplicateFieldSnapshot, ...], tuple[DuplicateFieldSnapshot, ...]]:
    return (
        tuple(_field_snapshot(left, field) for field in rule.compared_fields),
        tuple(_field_snapshot(right, field) for field in rule.compared_fields),
    )


def _evidence(
    rule: DuplicateRule,
    left_snapshots: tuple[DuplicateFieldSnapshot, ...],
    right_snapshots: tuple[DuplicateFieldSnapshot, ...],
    polarity: EvidencePolarity,
    strength: EvidenceStrength,
    reason: str,
) -> DuplicateEvidenceItem:
    return DuplicateEvidenceItem(
        rule.rule_id,
        rule.rule_version,
        polarity,
        strength,
        rule.compared_fields,
        left_snapshots,
        right_snapshots,
        DuplicateReasonCode(reason),
    )


def _non_comparison(
    rule: DuplicateRule,
    left_snapshots: tuple[DuplicateFieldSnapshot, ...],
    right_snapshots: tuple[DuplicateFieldSnapshot, ...],
    reason: str,
) -> RuleNonComparison:
    return RuleNonComparison(
        rule.rule_id,
        rule.rule_version,
        rule.compared_fields,
        left_snapshots,
        right_snapshots,
        DuplicateReasonCode(reason),
    )


def _evaluate_rule(
    left: AvailableObservation,
    right: AvailableObservation,
    rule: DuplicateRule,
) -> DuplicateEvidenceItem | RuleNonComparison:
    left_snapshots, right_snapshots = _finding_snapshots(left, right, rule)
    left_canonical = tuple(snapshot.canonical for snapshot in left_snapshots)
    right_canonical = tuple(snapshot.canonical for snapshot in right_snapshots)

    if rule == _TOTAL_AREA_RULE:
        if not all(
            isinstance(value, PresentValue) for value in (*left_canonical, *right_canonical)
        ):
            return _non_comparison(
                rule, left_snapshots, right_snapshots, "not_comparable_total_area"
            )
        if left_canonical == right_canonical:
            return _evidence(
                rule,
                left_snapshots,
                right_snapshots,
                EvidencePolarity.SUPPORTS,
                EvidenceStrength.MATERIAL,
                "exact_total_area",
            )
        return _evidence(
            rule,
            left_snapshots,
            right_snapshots,
            EvidencePolarity.CONTRADICTS,
            EvidenceStrength.MATERIAL,
            "different_total_area",
        )

    if rule == _ROOMS_RULE:
        if not all(
            isinstance(value, PresentValue) for value in (*left_canonical, *right_canonical)
        ):
            return _non_comparison(rule, left_snapshots, right_snapshots, "not_comparable_rooms")
        if left_canonical == right_canonical:
            return _evidence(
                rule,
                left_snapshots,
                right_snapshots,
                EvidencePolarity.SUPPORTS,
                EvidenceStrength.CORROBORATING,
                "exact_room_count",
            )
        return _evidence(
            rule,
            left_snapshots,
            right_snapshots,
            EvidencePolarity.CONTRADICTS,
            EvidenceStrength.MATERIAL,
            "different_room_count",
        )

    if rule == _LOCATION_RULE:
        if not all(
            isinstance(value, PresentValue) for value in (*left_canonical, *right_canonical)
        ):
            return _non_comparison(
                rule,
                left_snapshots,
                right_snapshots,
                "not_comparable_location_text",
            )
        if left_canonical == right_canonical:
            return _evidence(
                rule,
                left_snapshots,
                right_snapshots,
                EvidencePolarity.SUPPORTS,
                EvidenceStrength.CORROBORATING,
                "exact_location_text",
            )
        return _non_comparison(
            rule,
            left_snapshots,
            right_snapshots,
            "free_text_mismatch_is_neutral",
        )

    if rule != _PRICE_RULE:
        raise ValueError("unsupported duplicate policy rule")
    if not all(isinstance(value, PresentValue) for value in (*left_canonical, *right_canonical)):
        return _non_comparison(rule, left_snapshots, right_snapshots, "not_comparable_price")
    left_amount, left_currency = left_canonical
    right_amount, right_currency = right_canonical
    if left_currency != right_currency:
        return _non_comparison(
            rule,
            left_snapshots,
            right_snapshots,
            "currency_difference_is_neutral",
        )
    if left_amount == right_amount:
        return _evidence(
            rule,
            left_snapshots,
            right_snapshots,
            EvidencePolarity.SUPPORTS,
            EvidenceStrength.AUXILIARY,
            "exact_price_same_currency",
        )
    return _non_comparison(
        rule,
        left_snapshots,
        right_snapshots,
        "price_difference_is_neutral",
    )


def _evaluate_rules(
    left: AvailableObservation,
    right: AvailableObservation,
    rules: tuple[DuplicateRule, ...],
) -> tuple[tuple[DuplicateEvidenceItem, ...], tuple[RuleNonComparison, ...]]:
    evidence: list[DuplicateEvidenceItem] = []
    non_comparisons: list[RuleNonComparison] = []
    for rule in rules:
        finding = _evaluate_rule(left, right, rule)
        if isinstance(finding, DuplicateEvidenceItem):
            evidence.append(finding)
        else:
            non_comparisons.append(finding)
    return tuple(evidence), tuple(non_comparisons)


def _automatic_outcome(
    evidence: tuple[DuplicateEvidenceItem, ...],
) -> DuplicateAutomaticOutcome:
    qualifying_area = any(
        item.rule_id == _TOTAL_AREA_RULE.rule_id
        and item.polarity is EvidencePolarity.SUPPORTS
        and item.strength is EvidenceStrength.MATERIAL
        for item in evidence
    )
    qualifying_corroboration = any(
        item.rule_id in {_ROOMS_RULE.rule_id, _LOCATION_RULE.rule_id}
        and item.polarity is EvidencePolarity.SUPPORTS
        and item.strength is EvidenceStrength.CORROBORATING
        for item in evidence
    )
    if not (qualifying_area and qualifying_corroboration):
        return DuplicateAutomaticOutcome.INSUFFICIENT_EVIDENCE_NO_CANDIDATE
    material_contradiction = any(
        item.polarity is EvidencePolarity.CONTRADICTS and item.strength is EvidenceStrength.MATERIAL
        for item in evidence
    )
    if material_contradiction:
        return DuplicateAutomaticOutcome.CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW
    return DuplicateAutomaticOutcome.CANDIDATE_REQUIRES_MANUAL_REVIEW


def _validate_assessment_finding_bindings(assessment: DuplicatePairAssessment) -> None:
    policy_positions = {
        rule.rule_id: position
        for position, rule in enumerate(PUBLICATION_DUPLICATE_POLICY_V1.rules)
    }
    all_findings: tuple[DuplicateEvidenceItem | RuleNonComparison, ...] = (
        *assessment.evidence,
        *assessment.non_comparisons,
    )
    if any(item.rule_id not in policy_positions for item in all_findings):
        raise ValueError("assessment contains a rule outside duplicate policy")
    evidence_positions = tuple(policy_positions[item.rule_id] for item in assessment.evidence)
    non_comparison_positions = tuple(
        policy_positions[item.rule_id] for item in assessment.non_comparisons
    )
    if evidence_positions != tuple(sorted(set(evidence_positions))):
        raise ValueError("evidence must be unique and in policy order")
    if non_comparison_positions != tuple(sorted(set(non_comparison_positions))):
        raise ValueError("non-comparisons must be unique and in policy order")
    all_rule_ids = tuple(item.rule_id for item in assessment.evidence) + tuple(
        item.rule_id for item in assessment.non_comparisons
    )
    if set(all_rule_ids) != set(policy_positions) or len(all_rule_ids) != len(policy_positions):
        raise ValueError("assessment must contain exactly one finding per policy rule")
    rule_by_id = {rule.rule_id: rule for rule in PUBLICATION_DUPLICATE_POLICY_V1.rules}
    for item in all_findings:
        rule = rule_by_id[item.rule_id]
        if item.rule_version != rule.rule_version or item.compared_fields != rule.compared_fields:
            raise ValueError("assessment finding does not match policy rule")
        for snapshot in item.left_snapshots:
            _validate_snapshot_binding(
                snapshot,
                assessment.identity.pair.left,
                assessment.identity.left_observation_key,
            )
        for snapshot in item.right_snapshots:
            _validate_snapshot_binding(
                snapshot,
                assessment.identity.pair.right,
                assessment.identity.right_observation_key,
            )


def _validate_snapshot_binding(
    snapshot: DuplicateFieldSnapshot,
    reference: PublicationRef,
    key: ObservationKey,
) -> None:
    if (
        snapshot.provenance.source_id != reference.source_id
        or snapshot.provenance.publication_id != reference.publication_id
        or snapshot.provenance.observed_at != key.observed_at
    ):
        raise ValueError("duplicate snapshot provenance does not match assessment side")


def assess_publication_pair(
    first: PublicationObservation,
    second: PublicationObservation,
    policy: DuplicatePolicy = PUBLICATION_DUPLICATE_POLICY_V1,
) -> PairAssessmentResult:
    """Assess exactly one pair symmetrically without I/O, clocks or hidden state."""

    if not isinstance(first, (AvailableObservation, UnavailableObservation)) or not isinstance(
        second, (AvailableObservation, UnavailableObservation)
    ):
        raise TypeError("pair assessment requires publication observations")
    if policy.rules != PUBLICATION_DUPLICATE_POLICY_V1.rules:
        raise ValueError("unsupported duplicate policy rules")
    first_reference = first.key.reference
    second_reference = second.key.reference
    if first_reference == second_reference:
        return PairAssessmentFailure(
            conflicts=(
                DuplicateAssessmentConflict(
                    "DUPLICATE_ASSESSMENT_CONFLICT",
                    "same_publication_ref",
                    first_reference,
                ),
            )
        )
    pair = PublicationPair(first_reference, second_reference)
    if first_reference == pair.left:
        left, right = first, second
    else:
        left, right = second, first
    if not isinstance(left, AvailableObservation) or not isinstance(right, AvailableObservation):
        return PairNotAssessed(
            pair=pair,
            left_key=left.key,
            right_key=right.key,
            reason_code=DuplicateReasonCode("side_not_available"),
        )
    identity = DuplicateAssessmentIdentity(
        pair=pair,
        left_observation_key=left.key,
        right_observation_key=right.key,
        policy_version=policy.version,
    )
    evidence, non_comparisons = _evaluate_rules(left, right, policy.rules)
    return PairAssessmentSuccess(
        DuplicatePairAssessment(
            identity=identity,
            left_observation=left,
            right_observation=right,
            evidence=evidence,
            non_comparisons=non_comparisons,
            outcome=_automatic_outcome(evidence),
        )
    )


@dataclass(frozen=True, slots=True)
class ReviewReferenceCode:
    """Supplied stable opaque identity of one manual review lineage."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "review reference code")


@dataclass(frozen=True, slots=True)
class ReviewerCode:
    """Supplied pseudonymous reviewer code, never arbitrary personal text."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "reviewer code")


@dataclass(frozen=True, slots=True)
class ReviewRationaleCode:
    """Stable opaque rationale code, never a free-form note."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "review rationale code")


@dataclass(frozen=True, slots=True)
class ReviewedAt:
    """Supplied canonical UTC time of a human review assertion."""

    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is not UTC or self.value.utcoffset() is None:
            raise ValueError("reviewed_at must be canonical UTC")


class ManualReviewOutcome(StrEnum):
    """Human assertion about one exact publication pair."""

    CONFIRMED_RELATIONSHIP = "CONFIRMED_RELATIONSHIP"
    REJECTED_RELATIONSHIP = "REJECTED_RELATIONSHIP"
    INCONCLUSIVE = "INCONCLUSIVE"


class AssessmentFindingKind(StrEnum):
    """Collection in the bound assessment referenced by a review."""

    EVIDENCE = "EVIDENCE"
    NON_COMPARISON = "NON_COMPARISON"


@dataclass(frozen=True, slots=True)
class AssessmentFindingReference:
    """Exact zero-based reference to one immutable automatic finding."""

    assessment_identity: DuplicateAssessmentIdentity
    finding_kind: AssessmentFindingKind
    rule_id: DuplicateRuleId
    rule_version: DuplicateRuleVersion
    polarity: EvidencePolarity | None
    ordinal: int

    def __post_init__(self) -> None:
        if type(self.ordinal) is not int or self.ordinal < 0:
            raise ValueError("finding ordinal must be a non-negative integer")
        if self.finding_kind is AssessmentFindingKind.EVIDENCE:
            if self.polarity is None:
                raise ValueError("evidence reference requires polarity")
        elif self.polarity is not None:
            raise ValueError("non-comparison reference cannot have polarity")


@dataclass(frozen=True, slots=True)
class ManualReviewIdentity:
    """Supplied immutable revision identity within one review lineage."""

    review_reference_code: ReviewReferenceCode
    revision: int

    def __post_init__(self) -> None:
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("manual review revision must be a positive integer")


def _validate_review_collections(
    rationale_codes: tuple[ReviewRationaleCode, ...],
    evidence_references: tuple[AssessmentFindingReference, ...],
) -> None:
    if not isinstance(rationale_codes, tuple):
        raise TypeError("review rationale codes must be a tuple")
    if not isinstance(evidence_references, tuple):
        raise TypeError("review evidence references must be a tuple")
    if not rationale_codes:
        raise ValueError("manual review requires a rationale code")
    if not evidence_references:
        raise ValueError("manual review requires an assessment finding reference")
    if any(not isinstance(code, ReviewRationaleCode) for code in rationale_codes):
        raise TypeError("manual review contains an unsupported rationale code")
    if any(
        not isinstance(reference, AssessmentFindingReference) for reference in evidence_references
    ):
        raise TypeError("manual review contains an unsupported finding reference")


@dataclass(frozen=True, slots=True)
class ManualReviewDraft:
    """Caller-supplied review content awaiting pure binding validation."""

    identity: ManualReviewIdentity
    assessment_identity: DuplicateAssessmentIdentity
    reviewed_at: ReviewedAt
    reviewer_code: ReviewerCode
    outcome: ManualReviewOutcome
    rationale_codes: tuple[ReviewRationaleCode, ...]
    evidence_references: tuple[AssessmentFindingReference, ...]
    supersedes: ManualReviewIdentity | None = None

    def __post_init__(self) -> None:
        _validate_review_collections(self.rationale_codes, self.evidence_references)


@dataclass(frozen=True, slots=True)
class DuplicatePairManualReview:
    """Validated immutable human assertion over one exact assessment."""

    identity: ManualReviewIdentity
    assessment_identity: DuplicateAssessmentIdentity
    reviewed_at: ReviewedAt
    reviewer_code: ReviewerCode
    outcome: ManualReviewOutcome
    rationale_codes: tuple[ReviewRationaleCode, ...]
    evidence_references: tuple[AssessmentFindingReference, ...]
    supersedes: ManualReviewIdentity | None = None

    def __post_init__(self) -> None:
        _validate_review_collections(self.rationale_codes, self.evidence_references)
        if any(
            reference.assessment_identity != self.assessment_identity
            for reference in self.evidence_references
        ):
            raise ValueError("manual review finding reference has another assessment identity")
        if self.identity.revision == 1:
            if self.supersedes is not None:
                raise ValueError("manual review revision 1 cannot supersede another revision")
        elif self.supersedes != ManualReviewIdentity(
            self.identity.review_reference_code,
            self.identity.revision - 1,
        ):
            raise ValueError("manual review must supersede the immediately previous revision")


class ManualReviewDisposition(StrEnum):
    """Successful creation or exact idempotent replay."""

    CREATED = "CREATED"
    REPLAYED = "REPLAYED"


@dataclass(frozen=True, slots=True)
class ManualReviewConflict:
    """Stable manual-review conflict without partial review state."""

    category: ManualReviewConflictCategory
    code: ManualReviewConflictCode
    subject: ManualReviewIdentity

    def __post_init__(self) -> None:
        if self.category != "MANUAL_REVIEW_CONFLICT":
            raise ValueError("invalid manual review conflict category")


@dataclass(frozen=True, slots=True)
class ManualReviewSuccess:
    """A complete created review or exact replay of the previous record."""

    disposition: ManualReviewDisposition
    review: DuplicatePairManualReview


@dataclass(frozen=True, slots=True)
class ManualReviewFailure:
    """Atomic failure containing conflicts and no partial review."""

    conflicts: tuple[ManualReviewConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple):
            raise TypeError("manual review conflicts must be a tuple")
        if not self.conflicts:
            raise ValueError("failed manual review must contain a conflict")
        if any(not isinstance(conflict, ManualReviewConflict) for conflict in self.conflicts):
            raise TypeError("manual review failure contains an unsupported conflict")


type ManualReviewResult = ManualReviewSuccess | ManualReviewFailure


def _review_conflict(
    code: ManualReviewConflictCode,
    subject: ManualReviewIdentity,
) -> ManualReviewFailure:
    return ManualReviewFailure((ManualReviewConflict("MANUAL_REVIEW_CONFLICT", code, subject),))


def _finding_reference_matches(
    reference: AssessmentFindingReference,
    assessment: DuplicatePairAssessment,
) -> bool:
    if reference.assessment_identity != assessment.identity:
        return False
    if reference.finding_kind is AssessmentFindingKind.EVIDENCE:
        if reference.ordinal >= len(assessment.evidence):
            return False
        finding = assessment.evidence[reference.ordinal]
        return (
            reference.rule_id == finding.rule_id
            and reference.rule_version == finding.rule_version
            and reference.polarity is finding.polarity
        )
    if reference.ordinal >= len(assessment.non_comparisons):
        return False
    non_comparison = assessment.non_comparisons[reference.ordinal]
    return (
        reference.rule_id == non_comparison.rule_id
        and reference.rule_version == non_comparison.rule_version
        and reference.polarity is None
    )


def _draft_equals_review(draft: ManualReviewDraft, review: DuplicatePairManualReview) -> bool:
    return (
        draft.identity == review.identity
        and draft.assessment_identity == review.assessment_identity
        and draft.reviewed_at == review.reviewed_at
        and draft.reviewer_code == review.reviewer_code
        and draft.outcome is review.outcome
        and draft.rationale_codes == review.rationale_codes
        and draft.evidence_references == review.evidence_references
        and draft.supersedes == review.supersedes
    )


def create_manual_review(
    assessment: DuplicatePairAssessment,
    draft: ManualReviewDraft,
    previous: DuplicatePairManualReview | None = None,
) -> ManualReviewResult:
    """Validate one supplied immutable review without storage, clocks or UUIDs."""

    if draft.assessment_identity != assessment.identity or any(
        not _finding_reference_matches(reference, assessment)
        for reference in draft.evidence_references
    ):
        return _review_conflict("review_assessment_mismatch", draft.identity)

    if previous is not None and previous.identity == draft.identity:
        if _draft_equals_review(draft, previous):
            return ManualReviewSuccess(ManualReviewDisposition.REPLAYED, previous)
        return _review_conflict("review_identity_content_conflict", draft.identity)

    if draft.identity.revision == 1:
        if draft.supersedes is not None or previous is not None:
            return _review_conflict("review_revision_mismatch", draft.identity)
    else:
        expected_previous_identity = ManualReviewIdentity(
            draft.identity.review_reference_code,
            draft.identity.revision - 1,
        )
        if (
            draft.supersedes != expected_previous_identity
            or previous is None
            or previous.identity != expected_previous_identity
            or draft.reviewed_at.value <= previous.reviewed_at.value
        ):
            return _review_conflict("review_revision_mismatch", draft.identity)
        if previous.assessment_identity.pair != assessment.identity.pair:
            return _review_conflict("review_assessment_mismatch", draft.identity)

    review = DuplicatePairManualReview(
        identity=draft.identity,
        assessment_identity=draft.assessment_identity,
        reviewed_at=draft.reviewed_at,
        reviewer_code=draft.reviewer_code,
        outcome=draft.outcome,
        rationale_codes=draft.rationale_codes,
        evidence_references=draft.evidence_references,
        supersedes=draft.supersedes,
    )
    return ManualReviewSuccess(ManualReviewDisposition.CREATED, review)


__all__ = [
    "AssessmentFindingKind",
    "AssessmentFindingReference",
    "AssessmentSupersession",
    "CurrentPairContext",
    "DuplicateAssessmentConflict",
    "DuplicateAssessmentConflictCategory",
    "DuplicateAssessmentConflictCode",
    "DuplicateAssessmentIdentity",
    "DuplicateAutomaticOutcome",
    "DuplicateComparableFieldName",
    "DuplicateEvidenceItem",
    "DuplicateFieldSnapshot",
    "DuplicatePairAssessment",
    "DuplicatePairManualReview",
    "DuplicatePolicy",
    "DuplicatePolicyVersion",
    "DuplicateReasonCode",
    "DuplicateRule",
    "DuplicateRuleId",
    "DuplicateRuleVersion",
    "EvidencePolarity",
    "EvidenceStrength",
    "ManualReviewConflict",
    "ManualReviewConflictCategory",
    "ManualReviewConflictCode",
    "ManualReviewDisposition",
    "ManualReviewDraft",
    "ManualReviewFailure",
    "ManualReviewIdentity",
    "ManualReviewOutcome",
    "ManualReviewResult",
    "ManualReviewSuccess",
    "PUBLICATION_DUPLICATE_POLICY_V1",
    "PUBLICATION_DUPLICATE_POLICY_V1_VERSION",
    "PairAssessmentFailure",
    "PairAssessmentResult",
    "PairAssessmentSuccess",
    "PairNotAssessed",
    "PublicationPair",
    "ReviewRationaleCode",
    "ReviewReferenceCode",
    "ReviewedAt",
    "ReviewerCode",
    "RuleNonComparison",
    "assess_publication_pair",
    "create_manual_review",
    "is_assessment_current",
    "is_assessment_stale",
]
