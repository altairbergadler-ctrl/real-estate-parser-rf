"""Pure exact blocking coverage for one fictional reviewed control population."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from real_estate_parser.normalization import Area, LocationText, RoomCount
from real_estate_parser.publication_duplicate_assessments import (
    DuplicateEvidenceItem,
    DuplicatePairAssessment,
    DuplicatePolicyVersion,
    PairAssessmentSuccess,
    PairNotAssessed,
    PublicationPair,
    RuleNonComparison,
)
from real_estate_parser.publication_duplicate_candidates import (
    AreaLocationTextBlockingKey,
    AreaRoomsBlockingKey,
    DuplicateBlockingKey,
    DuplicateCandidateGenerationIdentity,
    DuplicateCandidateGenerationResult,
    DuplicateCandidateIdentity,
    DuplicateCandidatePolicy,
    DuplicateCandidatePolicyVersion,
    OversizedBucket,
)
from real_estate_parser.publication_duplicate_quality import (
    DuplicateControlLabelOutcome,
    DuplicatePolicyControlSet,
    ExactRatio,
)
from real_estate_parser.publication_observations import ObservationKey, PresentValue
from real_estate_parser.source_batch import PublicationRef

type DuplicateCandidateCoverageConflictCategory = Literal["DUPLICATE_CANDIDATE_COVERAGE_CONFLICT"]
type DuplicateCandidateCoverageConflictCode = Literal["generation_result_inconsistent"]


class BlockingCoverageUnavailableReason(StrEnum):
    """Typed reason why exact blocking coverage cannot be reported."""

    INCONCLUSIVE_CONTROL_LABELS = "inconclusive_control_labels"
    NO_ELIGIBLE_CONFIRMED_RELATIONSHIPS = "no_eligible_confirmed_relationships"


@dataclass(frozen=True, slots=True)
class BlockingCoverageUnavailable:
    """Unavailable coverage instead of zero or a changed denominator."""

    reason: BlockingCoverageUnavailableReason

    def __post_init__(self) -> None:
        if not isinstance(self.reason, BlockingCoverageUnavailableReason):
            raise TypeError("blocking coverage requires a typed unavailable reason")


type ExactBlockingCoverage = ExactRatio | BlockingCoverageUnavailable


@dataclass(frozen=True, slots=True)
class DuplicateCandidateBlockingCoverage:
    """Complete disjoint counts bound to exact assessment and generation contexts."""

    candidate_policy_version: DuplicateCandidatePolicyVersion
    assessment_policy_version: DuplicatePolicyVersion
    generation_identity: DuplicateCandidateGenerationIdentity
    control_population_count: int
    pair_not_assessed_case_count: int
    rejected_label_count: int
    inconclusive_label_count: int
    confirmed_label_count: int
    confirmed_pair_not_assessed_count: int
    confirmed_outside_generation_input_count: int
    confirmed_stale_or_mismatched_keys_count: int
    eligible_confirmed_count: int
    covered_eligible_confirmed_count: int
    missed_no_shared_key_count: int
    missed_oversized_bucket_count: int
    blocking_coverage: ExactBlockingCoverage

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_policy_version, DuplicateCandidatePolicyVersion):
            raise TypeError("coverage requires a candidate policy version")
        if not isinstance(self.assessment_policy_version, DuplicatePolicyVersion):
            raise TypeError("coverage requires an assessment policy version")
        if not isinstance(self.generation_identity, DuplicateCandidateGenerationIdentity):
            raise TypeError("coverage requires an exact generation identity")
        if self.candidate_policy_version != self.generation_identity.candidate_policy_version:
            raise ValueError("candidate policy version must match generation identity")

        counts = (
            self.control_population_count,
            self.pair_not_assessed_case_count,
            self.rejected_label_count,
            self.inconclusive_label_count,
            self.confirmed_label_count,
            self.confirmed_pair_not_assessed_count,
            self.confirmed_outside_generation_input_count,
            self.confirmed_stale_or_mismatched_keys_count,
            self.eligible_confirmed_count,
            self.covered_eligible_confirmed_count,
            self.missed_no_shared_key_count,
            self.missed_oversized_bucket_count,
        )
        if any(type(count) is not int or count < 0 for count in counts):
            raise ValueError("blocking coverage counts must be non-negative exact integers")
        if self.control_population_count == 0:
            raise ValueError("blocking coverage requires a non-empty control population")
        if self.pair_not_assessed_case_count > self.control_population_count:
            raise ValueError("not-assessed count cannot exceed the control population")
        if self.confirmed_pair_not_assessed_count > self.pair_not_assessed_case_count:
            raise ValueError("confirmed not-assessed count cannot exceed all not-assessed cases")
        if self.control_population_count != (
            self.rejected_label_count + self.inconclusive_label_count + self.confirmed_label_count
        ):
            raise ValueError("control population must equal all label counts")
        if self.confirmed_label_count != (
            self.confirmed_pair_not_assessed_count
            + self.confirmed_outside_generation_input_count
            + self.confirmed_stale_or_mismatched_keys_count
            + self.eligible_confirmed_count
        ):
            raise ValueError("confirmed count must equal its disjoint classifications")
        if self.eligible_confirmed_count != (
            self.covered_eligible_confirmed_count
            + self.missed_no_shared_key_count
            + self.missed_oversized_bucket_count
        ):
            raise ValueError("eligible confirmed count must equal covered and missed counts")

        expected_metric: ExactBlockingCoverage
        if self.inconclusive_label_count > 0:
            expected_metric = BlockingCoverageUnavailable(
                BlockingCoverageUnavailableReason.INCONCLUSIVE_CONTROL_LABELS
            )
        elif self.eligible_confirmed_count == 0:
            expected_metric = BlockingCoverageUnavailable(
                BlockingCoverageUnavailableReason.NO_ELIGIBLE_CONFIRMED_RELATIONSHIPS
            )
        else:
            expected_metric = ExactRatio(
                self.covered_eligible_confirmed_count,
                self.eligible_confirmed_count,
            )
        if not isinstance(self.blocking_coverage, (ExactRatio, BlockingCoverageUnavailable)):
            raise TypeError("blocking coverage must be exact or explicitly unavailable")
        if self.blocking_coverage != expected_metric:
            raise ValueError("blocking coverage metric does not match counts and precedence")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateCoverageConflictSubject:
    """Exact canonical pair and current side keys for one inconsistent result."""

    pair: PublicationPair
    left_observation_key: ObservationKey
    right_observation_key: ObservationKey

    def __post_init__(self) -> None:
        if not isinstance(self.pair, PublicationPair):
            raise TypeError("coverage conflict subject requires a publication pair")
        if not isinstance(self.left_observation_key, ObservationKey) or not isinstance(
            self.right_observation_key, ObservationKey
        ):
            raise TypeError("coverage conflict subject requires exact observation keys")
        if self.left_observation_key.reference != self.pair.left:
            raise ValueError("coverage conflict left key does not match its pair")
        if self.right_observation_key.reference != self.pair.right:
            raise ValueError("coverage conflict right key does not match its pair")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateCoverageConflict:
    """Stable evidence that a declared generation result is inconsistent."""

    category: DuplicateCandidateCoverageConflictCategory
    code: DuplicateCandidateCoverageConflictCode
    subject: DuplicateCandidateCoverageConflictSubject

    def __post_init__(self) -> None:
        if self.category != "DUPLICATE_CANDIDATE_COVERAGE_CONFLICT":
            raise ValueError("invalid duplicate candidate coverage conflict category")
        if self.code != "generation_result_inconsistent":
            raise ValueError("invalid duplicate candidate coverage conflict code")
        if not isinstance(self.subject, DuplicateCandidateCoverageConflictSubject):
            raise TypeError("coverage conflict requires a structural subject")


def _conflict_sort_key(conflict: DuplicateCandidateCoverageConflict) -> tuple[object, ...]:
    subject = conflict.subject
    return (
        subject.pair.left.source_id.value,
        subject.pair.left.publication_id.value,
        subject.pair.right.source_id.value,
        subject.pair.right.publication_id.value,
        subject.left_observation_key.observed_at.value,
        subject.right_observation_key.observed_at.value,
        conflict.category,
        conflict.code,
    )


def _canonical_conflicts(
    conflicts: tuple[DuplicateCandidateCoverageConflict, ...],
) -> tuple[DuplicateCandidateCoverageConflict, ...]:
    ordered = sorted(conflicts, key=_conflict_sort_key)
    unique: list[DuplicateCandidateCoverageConflict] = []
    for conflict in ordered:
        if conflict not in unique:
            unique.append(conflict)
    return tuple(unique)


@dataclass(frozen=True, slots=True)
class DuplicateCandidateCoverageSuccess:
    """One complete exact coverage result."""

    coverage: DuplicateCandidateBlockingCoverage

    def __post_init__(self) -> None:
        if not isinstance(self.coverage, DuplicateCandidateBlockingCoverage):
            raise TypeError("coverage success requires complete blocking coverage")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateCoverageFailure:
    """Canonical atomic conflicts without any partial metrics."""

    conflicts: tuple[DuplicateCandidateCoverageConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple):
            raise TypeError("coverage conflicts must be a tuple")
        if not self.conflicts:
            raise ValueError("coverage failure must contain a conflict")
        if any(
            not isinstance(conflict, DuplicateCandidateCoverageConflict)
            for conflict in self.conflicts
        ):
            raise TypeError("coverage failure contains an unsupported conflict")
        if self.conflicts != _canonical_conflicts(self.conflicts):
            raise ValueError("coverage conflicts must be unique and canonical")


type DuplicateCandidateCoverageOutcome = (
    DuplicateCandidateCoverageSuccess | DuplicateCandidateCoverageFailure
)


def _assessment_snapshots(
    assessment: DuplicatePairAssessment,
) -> dict[str, tuple[object, object]]:
    snapshots: dict[str, tuple[object, object]] = {}
    findings: tuple[DuplicateEvidenceItem | RuleNonComparison, ...] = (
        *assessment.evidence,
        *assessment.non_comparisons,
    )
    for finding in findings:
        for field, left, right in zip(
            finding.compared_fields,
            finding.left_snapshots,
            finding.right_snapshots,
            strict=True,
        ):
            snapshots[field] = (left.canonical, right.canonical)
    return snapshots


def _equal_present_values[T](
    snapshots: dict[str, tuple[object, object]],
    field: str,
    expected_type: type[T],
) -> T | None:
    left, right = snapshots[field]
    if (
        isinstance(left, PresentValue)
        and isinstance(right, PresentValue)
        and isinstance(left.value, expected_type)
        and isinstance(right.value, expected_type)
        and left.value == right.value
    ):
        return left.value
    return None


def _shared_blocking_keys(
    assessment: DuplicatePairAssessment,
    policy: DuplicateCandidatePolicy,
) -> tuple[DuplicateBlockingKey, ...]:
    snapshots = _assessment_snapshots(assessment)
    area = _equal_present_values(snapshots, "total_area", Area)
    rooms = _equal_present_values(snapshots, "rooms", RoomCount)
    location = _equal_present_values(snapshots, "location_text", LocationText)
    shared: list[DuplicateBlockingKey] = []
    area_rooms_rule, area_location_rule = policy.rules
    if area is not None and rooms is not None:
        shared.append(
            AreaRoomsBlockingKey(
                area_rooms_rule.rule_id,
                area_rooms_rule.rule_version,
                area,
                rooms,
            )
        )
    if area is not None and location is not None:
        shared.append(
            AreaLocationTextBlockingKey(
                area_location_rule.rule_id,
                area_location_rule.rule_version,
                area,
                location,
            )
        )
    return tuple(shared)


def _is_wholly_skipped_for_pair(
    key: DuplicateBlockingKey,
    left_key: ObservationKey,
    right_key: ObservationKey,
    oversized_buckets: tuple[OversizedBucket, ...],
) -> bool:
    return any(
        bucket.key == key and left_key in bucket.member_keys and right_key in bucket.member_keys
        for bucket in oversized_buckets
    )


def _current_keys_by_reference(
    identity: DuplicateCandidateGenerationIdentity,
) -> dict[PublicationRef, ObservationKey]:
    return {key.reference: key for key in identity.canonical_input_keys}


def evaluate_duplicate_candidate_blocking_coverage(
    control_set: DuplicatePolicyControlSet,
    generation_result: DuplicateCandidateGenerationResult,
) -> DuplicateCandidateCoverageOutcome:
    """Measure exact candidate coverage without generation, assessment, I/O or state."""

    if not isinstance(control_set, DuplicatePolicyControlSet):
        raise TypeError("coverage evaluation requires a duplicate policy control set")
    if not isinstance(generation_result, DuplicateCandidateGenerationResult):
        raise TypeError("coverage evaluation requires a candidate generation result")

    rejected_count = sum(
        case.label.outcome is DuplicateControlLabelOutcome.REJECTED_RELATIONSHIP
        for case in control_set.cases
    )
    inconclusive_count = sum(
        case.label.outcome is DuplicateControlLabelOutcome.INCONCLUSIVE
        for case in control_set.cases
    )
    confirmed_cases = tuple(
        case
        for case in control_set.cases
        if case.label.outcome is DuplicateControlLabelOutcome.CONFIRMED_RELATIONSHIP
    )
    pair_not_assessed_count = sum(
        isinstance(case.result, PairNotAssessed) for case in control_set.cases
    )

    current_keys = _current_keys_by_reference(generation_result.identity)
    candidate_identities = {candidate.identity for candidate in generation_result.candidates}
    confirmed_pair_not_assessed_count = 0
    confirmed_outside_count = 0
    confirmed_stale_count = 0
    eligible_count = 0
    covered_count = 0
    no_shared_count = 0
    oversized_count = 0
    conflicts: list[DuplicateCandidateCoverageConflict] = []

    for case in confirmed_cases:
        if isinstance(case.result, PairNotAssessed):
            confirmed_pair_not_assessed_count += 1
            continue

        result = case.result
        if not isinstance(result, PairAssessmentSuccess):
            raise TypeError("valid control case has an unsupported assessment result")
        assessment = result.assessment
        pair = case.pair
        left_current = current_keys.get(pair.left)
        right_current = current_keys.get(pair.right)
        if left_current is None or right_current is None:
            confirmed_outside_count += 1
            continue
        if (
            assessment.identity.left_observation_key != left_current
            or assessment.identity.right_observation_key != right_current
        ):
            confirmed_stale_count += 1
            continue

        eligible_count += 1
        candidate_identity = DuplicateCandidateIdentity(
            pair,
            left_current,
            right_current,
            generation_result.identity.candidate_policy_version,
        )
        if candidate_identity in candidate_identities:
            covered_count += 1
            continue

        shared_keys = _shared_blocking_keys(assessment, generation_result.policy)
        if not shared_keys:
            no_shared_count += 1
            continue
        if all(
            _is_wholly_skipped_for_pair(
                key,
                left_current,
                right_current,
                generation_result.oversized_buckets,
            )
            for key in shared_keys
        ):
            oversized_count += 1
            continue
        conflicts.append(
            DuplicateCandidateCoverageConflict(
                "DUPLICATE_CANDIDATE_COVERAGE_CONFLICT",
                "generation_result_inconsistent",
                DuplicateCandidateCoverageConflictSubject(
                    pair,
                    left_current,
                    right_current,
                ),
            )
        )

    if conflicts:
        return DuplicateCandidateCoverageFailure(_canonical_conflicts(tuple(conflicts)))

    metric: ExactBlockingCoverage
    if inconclusive_count > 0:
        metric = BlockingCoverageUnavailable(
            BlockingCoverageUnavailableReason.INCONCLUSIVE_CONTROL_LABELS
        )
    elif eligible_count == 0:
        metric = BlockingCoverageUnavailable(
            BlockingCoverageUnavailableReason.NO_ELIGIBLE_CONFIRMED_RELATIONSHIPS
        )
    else:
        metric = ExactRatio(covered_count, eligible_count)

    return DuplicateCandidateCoverageSuccess(
        DuplicateCandidateBlockingCoverage(
            candidate_policy_version=generation_result.identity.candidate_policy_version,
            assessment_policy_version=control_set.policy_version,
            generation_identity=generation_result.identity,
            control_population_count=len(control_set.cases),
            pair_not_assessed_case_count=pair_not_assessed_count,
            rejected_label_count=rejected_count,
            inconclusive_label_count=inconclusive_count,
            confirmed_label_count=len(confirmed_cases),
            confirmed_pair_not_assessed_count=confirmed_pair_not_assessed_count,
            confirmed_outside_generation_input_count=confirmed_outside_count,
            confirmed_stale_or_mismatched_keys_count=confirmed_stale_count,
            eligible_confirmed_count=eligible_count,
            covered_eligible_confirmed_count=covered_count,
            missed_no_shared_key_count=no_shared_count,
            missed_oversized_bucket_count=oversized_count,
            blocking_coverage=metric,
        )
    )


__all__ = [
    "BlockingCoverageUnavailable",
    "BlockingCoverageUnavailableReason",
    "DuplicateCandidateBlockingCoverage",
    "DuplicateCandidateCoverageConflict",
    "DuplicateCandidateCoverageConflictCategory",
    "DuplicateCandidateCoverageConflictCode",
    "DuplicateCandidateCoverageConflictSubject",
    "DuplicateCandidateCoverageFailure",
    "DuplicateCandidateCoverageOutcome",
    "DuplicateCandidateCoverageSuccess",
    "ExactBlockingCoverage",
    "evaluate_duplicate_candidate_blocking_coverage",
]
