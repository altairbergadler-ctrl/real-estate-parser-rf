"""Pure quality metrics for a reviewed duplicate-policy control set."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from real_estate_parser.publication_duplicate_assessments import (
    DuplicateAutomaticOutcome,
    DuplicatePairAssessment,
    DuplicatePolicyVersion,
    PairAssessmentSuccess,
    PairNotAssessed,
    PublicationPair,
)


class DuplicateControlContractErrorCode(StrEnum):
    """Stable reason why a control contract could not be constructed or evaluated."""

    CASES_NOT_TUPLE = "cases_not_tuple"
    EMPTY_CONTROL_SET = "empty_control_set"
    UNSUPPORTED_CASE = "unsupported_case"
    DUPLICATE_PAIR = "duplicate_pair"
    UNSUPPORTED_RESULT = "unsupported_result"
    PAIR_BINDING_MISMATCH = "pair_binding_mismatch"
    POLICY_VERSION_MISMATCH = "policy_version_mismatch"
    LABEL_BINDING_MISMATCH = "label_binding_mismatch"
    UNSUPPORTED_LABEL = "unsupported_label"
    INVALID_CONTROL_SET = "invalid_control_set"


class DuplicateControlContractError(ValueError):
    """Typed atomic contract error; no partial metrics accompany it."""

    __slots__ = ("code",)

    code: DuplicateControlContractErrorCode

    def __init__(self, code: DuplicateControlContractErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class DuplicateControlLabelOutcome(StrEnum):
    """Independent human label for one pair, never an automatic-policy derivation."""

    CONFIRMED_RELATIONSHIP = "CONFIRMED_RELATIONSHIP"
    REJECTED_RELATIONSHIP = "REJECTED_RELATIONSHIP"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True, slots=True)
class DuplicateControlLabel:
    """Caller-supplied assertion bound to one canonical publication pair."""

    pair: PublicationPair
    outcome: DuplicateControlLabelOutcome

    def __post_init__(self) -> None:
        if not isinstance(self.pair, PublicationPair):
            raise DuplicateControlContractError(
                DuplicateControlContractErrorCode.LABEL_BINDING_MISMATCH
            )
        if not isinstance(self.outcome, DuplicateControlLabelOutcome):
            raise DuplicateControlContractError(DuplicateControlContractErrorCode.UNSUPPORTED_LABEL)


type MeasurablePairAssessmentResult = PairAssessmentSuccess | PairNotAssessed


@dataclass(frozen=True, slots=True)
class DuplicatePolicyControlCase:
    """Exact policy result and independently supplied label for one pair."""

    pair: PublicationPair
    policy_version: DuplicatePolicyVersion
    result: MeasurablePairAssessmentResult
    label: DuplicateControlLabel

    def __post_init__(self) -> None:
        if not isinstance(self.pair, PublicationPair):
            raise DuplicateControlContractError(
                DuplicateControlContractErrorCode.PAIR_BINDING_MISMATCH
            )
        if not isinstance(self.policy_version, DuplicatePolicyVersion):
            raise DuplicateControlContractError(
                DuplicateControlContractErrorCode.POLICY_VERSION_MISMATCH
            )
        if not isinstance(self.label, DuplicateControlLabel):
            raise DuplicateControlContractError(DuplicateControlContractErrorCode.UNSUPPORTED_LABEL)
        if self.label.pair != self.pair:
            raise DuplicateControlContractError(
                DuplicateControlContractErrorCode.LABEL_BINDING_MISMATCH
            )
        if isinstance(self.result, PairAssessmentSuccess):
            if not isinstance(self.result.assessment, DuplicatePairAssessment):
                raise DuplicateControlContractError(
                    DuplicateControlContractErrorCode.UNSUPPORTED_RESULT
                )
            if self.result.assessment.identity.pair != self.pair:
                raise DuplicateControlContractError(
                    DuplicateControlContractErrorCode.PAIR_BINDING_MISMATCH
                )
            if self.result.assessment.identity.policy_version != self.policy_version:
                raise DuplicateControlContractError(
                    DuplicateControlContractErrorCode.POLICY_VERSION_MISMATCH
                )
        elif isinstance(self.result, PairNotAssessed):
            if self.result.pair != self.pair:
                raise DuplicateControlContractError(
                    DuplicateControlContractErrorCode.PAIR_BINDING_MISMATCH
                )
        else:
            raise DuplicateControlContractError(
                DuplicateControlContractErrorCode.UNSUPPORTED_RESULT
            )


def _pair_sort_key(pair: PublicationPair) -> tuple[str, str, str, str]:
    return (
        pair.left.source_id.value,
        pair.left.publication_id.value,
        pair.right.source_id.value,
        pair.right.publication_id.value,
    )


@dataclass(frozen=True, slots=True)
class DuplicatePolicyControlSet:
    """Non-empty, one-policy, canonical population of unique pair cases."""

    policy_version: DuplicatePolicyVersion
    cases: tuple[DuplicatePolicyControlCase, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.policy_version, DuplicatePolicyVersion):
            raise DuplicateControlContractError(
                DuplicateControlContractErrorCode.POLICY_VERSION_MISMATCH
            )
        if not isinstance(self.cases, tuple):
            raise DuplicateControlContractError(DuplicateControlContractErrorCode.CASES_NOT_TUPLE)
        if not self.cases:
            raise DuplicateControlContractError(DuplicateControlContractErrorCode.EMPTY_CONTROL_SET)
        if any(not isinstance(case, DuplicatePolicyControlCase) for case in self.cases):
            raise DuplicateControlContractError(DuplicateControlContractErrorCode.UNSUPPORTED_CASE)
        if any(case.policy_version != self.policy_version for case in self.cases):
            raise DuplicateControlContractError(
                DuplicateControlContractErrorCode.POLICY_VERSION_MISMATCH
            )
        pairs = tuple(case.pair for case in self.cases)
        if len(set(pairs)) != len(pairs):
            raise DuplicateControlContractError(DuplicateControlContractErrorCode.DUPLICATE_PAIR)
        object.__setattr__(
            self, "cases", tuple(sorted(self.cases, key=lambda case: _pair_sort_key(case.pair)))
        )


@dataclass(frozen=True, slots=True)
class ExactRatio:
    """Exact bounded integer ratio without float, rounding or display policy."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if type(self.numerator) is not int or type(self.denominator) is not int:
            raise TypeError("exact ratio requires integer values")
        if self.denominator <= 0:
            raise ValueError("exact ratio denominator must be positive")
        if self.numerator < 0 or self.numerator > self.denominator:
            raise ValueError("exact ratio numerator must be within its denominator")


class QualityMetricUnavailableReason(StrEnum):
    """Typed reason why an exact quality ratio cannot be reported."""

    NO_PREDICTED_POSITIVE = "no_predicted_positive"
    INCOMPLETE_PREDICTED_POSITIVE_LABELS = "incomplete_predicted_positive_labels"
    NO_CONFIRMED_RELATIONSHIP_LABELS = "no_confirmed_relationship_labels"
    INCOMPLETE_POPULATION_LABELS = "incomplete_population_labels"


@dataclass(frozen=True, slots=True)
class QualityMetricUnavailable:
    """Unavailable metric result instead of zero, exception or guessed denominator."""

    reason: QualityMetricUnavailableReason

    def __post_init__(self) -> None:
        if not isinstance(self.reason, QualityMetricUnavailableReason):
            raise TypeError("quality metric requires a typed unavailable reason")


type ExactQualityMetric = ExactRatio | QualityMetricUnavailable


@dataclass(frozen=True, slots=True)
class DuplicatePolicyQualityMetrics:
    """Complete deterministic counts and denominator-explicit policy metrics."""

    policy_version: DuplicatePolicyVersion
    population_count: int
    assessed_pair_count: int
    candidate_requires_manual_review_count: int
    conflicting_evidence_requires_manual_review_count: int
    insufficient_evidence_no_candidate_count: int
    not_assessed_count: int
    review_required_count: int
    assessment_coverage: ExactRatio
    review_required_population_rate: ExactRatio
    precision: ExactQualityMetric
    recall: ExactQualityMetric

    def __post_init__(self) -> None:
        if not isinstance(self.policy_version, DuplicatePolicyVersion):
            raise TypeError("quality metrics require a duplicate policy version")
        counts = (
            self.population_count,
            self.assessed_pair_count,
            self.candidate_requires_manual_review_count,
            self.conflicting_evidence_requires_manual_review_count,
            self.insufficient_evidence_no_candidate_count,
            self.not_assessed_count,
            self.review_required_count,
        )
        if any(type(count) is not int or count < 0 for count in counts):
            raise ValueError("quality metric counts must be non-negative integers")
        if self.population_count == 0:
            raise ValueError("quality metrics require a non-empty population")
        assessed_from_outcomes = (
            self.candidate_requires_manual_review_count
            + self.conflicting_evidence_requires_manual_review_count
            + self.insufficient_evidence_no_candidate_count
        )
        if self.assessed_pair_count != assessed_from_outcomes:
            raise ValueError("assessed count must equal automatic outcome counts")
        if self.population_count != self.assessed_pair_count + self.not_assessed_count:
            raise ValueError("population count must equal assessed and not-assessed counts")
        if self.review_required_count != (
            self.candidate_requires_manual_review_count
            + self.conflicting_evidence_requires_manual_review_count
        ):
            raise ValueError("review-required count must equal positive automatic outcomes")
        if self.assessment_coverage != ExactRatio(self.assessed_pair_count, self.population_count):
            raise ValueError("assessment coverage does not match counts")
        if self.review_required_population_rate != ExactRatio(
            self.review_required_count, self.population_count
        ):
            raise ValueError("population review load does not match counts")
        if not isinstance(self.precision, (ExactRatio, QualityMetricUnavailable)) or not isinstance(
            self.recall, (ExactRatio, QualityMetricUnavailable)
        ):
            raise TypeError("precision and recall require exact or unavailable results")


_REVIEW_REQUIRED_OUTCOMES = frozenset(
    {
        DuplicateAutomaticOutcome.CANDIDATE_REQUIRES_MANUAL_REVIEW,
        DuplicateAutomaticOutcome.CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW,
    }
)


def _is_review_required(case: DuplicatePolicyControlCase) -> bool:
    return (
        isinstance(case.result, PairAssessmentSuccess)
        and case.result.assessment.outcome in _REVIEW_REQUIRED_OUTCOMES
    )


def _precision(cases: tuple[DuplicatePolicyControlCase, ...]) -> ExactQualityMetric:
    predicted_positive = tuple(case for case in cases if _is_review_required(case))
    if not predicted_positive:
        return QualityMetricUnavailable(QualityMetricUnavailableReason.NO_PREDICTED_POSITIVE)
    if any(
        case.label.outcome is DuplicateControlLabelOutcome.INCONCLUSIVE
        for case in predicted_positive
    ):
        return QualityMetricUnavailable(
            QualityMetricUnavailableReason.INCOMPLETE_PREDICTED_POSITIVE_LABELS
        )
    confirmed_count = sum(
        case.label.outcome is DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP
        for case in predicted_positive
    )
    return ExactRatio(confirmed_count, len(predicted_positive))


def _recall(cases: tuple[DuplicatePolicyControlCase, ...]) -> ExactQualityMetric:
    if any(case.label.outcome is DuplicateControlLabelOutcome.INCONCLUSIVE for case in cases):
        return QualityMetricUnavailable(QualityMetricUnavailableReason.INCOMPLETE_POPULATION_LABELS)
    confirmed = tuple(
        case
        for case in cases
        if case.label.outcome is DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP
    )
    if not confirmed:
        return QualityMetricUnavailable(
            QualityMetricUnavailableReason.NO_CONFIRMED_RELATIONSHIP_LABELS
        )
    review_required_confirmed_count = sum(_is_review_required(case) for case in confirmed)
    return ExactRatio(review_required_confirmed_count, len(confirmed))


def evaluate_duplicate_policy_quality(
    control_set: DuplicatePolicyControlSet,
) -> DuplicatePolicyQualityMetrics:
    """Evaluate one complete valid control population without partial metrics."""

    if not isinstance(control_set, DuplicatePolicyControlSet):
        raise DuplicateControlContractError(DuplicateControlContractErrorCode.INVALID_CONTROL_SET)
    candidate_count = 0
    conflicting_count = 0
    insufficient_count = 0
    not_assessed_count = 0
    for case in control_set.cases:
        if isinstance(case.result, PairNotAssessed):
            not_assessed_count += 1
        elif (
            case.result.assessment.outcome
            is DuplicateAutomaticOutcome.CANDIDATE_REQUIRES_MANUAL_REVIEW
        ):
            candidate_count += 1
        elif (
            case.result.assessment.outcome
            is DuplicateAutomaticOutcome.CONFLICTING_EVIDENCE_REQUIRES_MANUAL_REVIEW
        ):
            conflicting_count += 1
        else:
            insufficient_count += 1
    population_count = len(control_set.cases)
    assessed_count = population_count - not_assessed_count
    review_required_count = candidate_count + conflicting_count
    return DuplicatePolicyQualityMetrics(
        policy_version=control_set.policy_version,
        population_count=population_count,
        assessed_pair_count=assessed_count,
        candidate_requires_manual_review_count=candidate_count,
        conflicting_evidence_requires_manual_review_count=conflicting_count,
        insufficient_evidence_no_candidate_count=insufficient_count,
        not_assessed_count=not_assessed_count,
        review_required_count=review_required_count,
        assessment_coverage=ExactRatio(assessed_count, population_count),
        review_required_population_rate=ExactRatio(review_required_count, population_count),
        precision=_precision(control_set.cases),
        recall=_recall(control_set.cases),
    )


__all__ = [
    "DuplicateControlContractError",
    "DuplicateControlContractErrorCode",
    "DuplicateControlLabel",
    "DuplicateControlLabelOutcome",
    "DuplicatePolicyControlCase",
    "DuplicatePolicyControlSet",
    "DuplicatePolicyQualityMetrics",
    "ExactQualityMetric",
    "ExactRatio",
    "MeasurablePairAssessmentResult",
    "QualityMetricUnavailable",
    "QualityMetricUnavailableReason",
    "evaluate_duplicate_policy_quality",
]
