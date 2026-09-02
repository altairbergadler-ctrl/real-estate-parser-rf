"""Pure atomic assessment composition for materialized duplicate candidates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

import real_estate_parser.publication_duplicate_assessments as assessment_module
from real_estate_parser.publication_duplicate_assessments import (
    PUBLICATION_DUPLICATE_POLICY_V1,
    DuplicateAssessmentConflict,
    DuplicateAssessmentIdentity,
    DuplicatePolicy,
    DuplicatePolicyVersion,
    PairAssessmentFailure,
    PairAssessmentSuccess,
    PairNotAssessed,
    PublicationPair,
)
from real_estate_parser.publication_duplicate_candidates import (
    PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1,
    DuplicateCandidate,
    DuplicateCandidateGenerationConfiguration,
    DuplicateCandidateGenerationIdentity,
    DuplicateCandidateGenerationResult,
    DuplicateCandidateIdentity,
    DuplicateCandidatePolicyVersion,
    DuplicatePublicationRefSubject,
    UnsupportedObservationSubject,
)
from real_estate_parser.publication_observations import (
    AvailableObservation,
    ObservationKey,
    UnavailableObservation,
)
from real_estate_parser.source_batch import PublicationRef

type DuplicateCandidateAssessmentBatchConflictCategory = Literal[
    "DUPLICATE_CANDIDATE_ASSESSMENT_BATCH_CONFLICT"
]
type DuplicateCandidateAssessmentBatchConflictCode = Literal[
    "observations_not_tuple",
    "empty_current_observations",
    "observation_not_available",
    "unsupported_observation",
    "observation_key_content_conflict",
    "duplicate_publication_ref",
    "unsupported_generation_result",
    "unsupported_candidate_policy",
    "unsupported_assessment_policy",
    "generation_current_keys_mismatch",
    "candidate_binding_mismatch",
    "unexpected_pair_not_assessed",
    "downstream_assessment_conflict",
    "item_identity_content_conflict",
    "batch_identity_content_conflict",
]
type BatchInputSubject = Literal["current_observations", "generation_result", "assessment_policy"]


def _observation_key_sort_key(key: ObservationKey) -> tuple[str, str, object]:
    return (
        key.reference.source_id.value,
        key.reference.publication_id.value,
        key.observed_at.value,
    )


def _reference_sort_key(reference: PublicationRef) -> tuple[str, str]:
    return reference.source_id.value, reference.publication_id.value


def _candidate_identity_sort_key(identity: DuplicateCandidateIdentity) -> tuple[object, ...]:
    return (
        identity.pair.left.source_id.value,
        identity.pair.left.publication_id.value,
        identity.pair.right.source_id.value,
        identity.pair.right.publication_id.value,
        identity.left_observation_key.observed_at.value,
        identity.right_observation_key.observed_at.value,
        identity.candidate_policy_version.value,
    )


def _generation_identity_sort_key(
    identity: DuplicateCandidateGenerationIdentity,
) -> tuple[object, ...]:
    return (
        identity.candidate_policy_version.value,
        identity.bucket_pair_limit.value,
        tuple(_observation_key_sort_key(key) for key in identity.canonical_input_keys),
    )


@dataclass(frozen=True, slots=True)
class DuplicateCandidateAssessmentBatchConfiguration:
    """Exact generation configuration plus an independent assessment policy."""

    generation_configuration: DuplicateCandidateGenerationConfiguration
    assessment_policy: DuplicatePolicy

    def __post_init__(self) -> None:
        if not isinstance(self.generation_configuration, DuplicateCandidateGenerationConfiguration):
            raise TypeError("batch configuration requires a generation configuration")
        if not isinstance(self.assessment_policy, DuplicatePolicy):
            raise TypeError("batch configuration requires an assessment policy")
        if self.generation_configuration.policy != PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1:
            raise ValueError("batch configuration requires the supported candidate policy")
        if self.assessment_policy != PUBLICATION_DUPLICATE_POLICY_V1:
            raise ValueError("batch configuration requires the supported assessment policy")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateAssessmentBatchInput:
    """Validated canonical input created only after conflict-free preflight."""

    generation_result: DuplicateCandidateGenerationResult
    current_observations: tuple[AvailableObservation, ...]
    assessment_policy: DuplicatePolicy

    def __post_init__(self) -> None:
        if not isinstance(self.generation_result, DuplicateCandidateGenerationResult):
            raise TypeError("batch input requires a generation result")
        if not isinstance(self.current_observations, tuple):
            raise TypeError("batch current observations must be a tuple")
        if not self.current_observations:
            raise ValueError("batch current observations must be non-empty")
        if any(
            not isinstance(observation, AvailableObservation)
            for observation in self.current_observations
        ):
            raise TypeError("batch input requires available observations")
        keys = tuple(observation.key for observation in self.current_observations)
        if len(set(keys)) != len(keys):
            raise ValueError("batch current observation keys must be unique")
        if len({key.reference for key in keys}) != len(keys):
            raise ValueError("batch current references must be unique")
        if keys != self.generation_result.identity.canonical_input_keys:
            raise ValueError("batch current observations do not match generation identity")
        if self.generation_result.policy != PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1:
            raise ValueError("batch input requires the supported candidate policy")
        if self.assessment_policy != PUBLICATION_DUPLICATE_POLICY_V1:
            raise ValueError("batch input requires the supported assessment policy")
        if _candidate_binding_conflicts(self.generation_result, self.current_observations):
            raise ValueError("batch input contains an invalid candidate binding")

    @property
    def configuration(self) -> DuplicateCandidateAssessmentBatchConfiguration:
        """Return the exact two-policy configuration represented by this input."""

        return DuplicateCandidateAssessmentBatchConfiguration(
            self.generation_result.configuration,
            self.assessment_policy,
        )


@dataclass(frozen=True, slots=True)
class DuplicateCandidateAssessmentBatchIdentity:
    """Generation identity and independent assessment-policy coordinate."""

    generation_identity: DuplicateCandidateGenerationIdentity
    assessment_policy_version: DuplicatePolicyVersion

    def __post_init__(self) -> None:
        if not isinstance(self.generation_identity, DuplicateCandidateGenerationIdentity):
            raise TypeError("batch identity requires a generation identity")
        if not isinstance(self.assessment_policy_version, DuplicatePolicyVersion):
            raise TypeError("batch identity requires an assessment policy version")
        if self.assessment_policy_version != PUBLICATION_DUPLICATE_POLICY_V1.version:
            raise ValueError("batch identity requires the supported assessment policy version")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateAssessmentItemIdentity:
    """One candidate identity within an exact assessment batch."""

    batch_identity: DuplicateCandidateAssessmentBatchIdentity
    candidate_identity: DuplicateCandidateIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.batch_identity, DuplicateCandidateAssessmentBatchIdentity):
            raise TypeError("item identity requires a batch identity")
        if not isinstance(self.candidate_identity, DuplicateCandidateIdentity):
            raise TypeError("item identity requires a candidate identity")
        if (
            self.candidate_identity.candidate_policy_version
            != self.batch_identity.generation_identity.candidate_policy_version
        ):
            raise ValueError("item candidate policy does not match batch generation policy")


def _success_matches_candidate(
    result: PairAssessmentSuccess,
    candidate: DuplicateCandidate,
    assessment_policy_version: DuplicatePolicyVersion,
    left_observation: AvailableObservation | None = None,
    right_observation: AvailableObservation | None = None,
) -> bool:
    try:
        assessment = result.assessment
        expected_identity = DuplicateAssessmentIdentity(
            pair=candidate.identity.pair,
            left_observation_key=candidate.identity.left_observation_key,
            right_observation_key=candidate.identity.right_observation_key,
            policy_version=assessment_policy_version,
        )
        if assessment.identity != expected_identity:
            return False
        if assessment.left_observation.key != candidate.identity.left_observation_key:
            return False
        if assessment.right_observation.key != candidate.identity.right_observation_key:
            return False
        if left_observation is not None and assessment.left_observation != left_observation:
            return False
        if right_observation is not None and assessment.right_observation != right_observation:
            return False
    except AttributeError, TypeError, ValueError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class DuplicateCandidateAssessmentItemOutcome:
    """Exact candidate and its complete bound pair-assessment success."""

    identity: DuplicateCandidateAssessmentItemIdentity
    candidate: DuplicateCandidate
    result: PairAssessmentSuccess

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateCandidateAssessmentItemIdentity):
            raise TypeError("item outcome requires an item identity")
        if not isinstance(self.candidate, DuplicateCandidate):
            raise TypeError("item outcome requires a duplicate candidate")
        if not isinstance(self.result, PairAssessmentSuccess):
            raise TypeError("item outcome requires a successful pair assessment")
        if self.identity.candidate_identity != self.candidate.identity:
            raise ValueError("item identity does not match candidate")
        if not _success_matches_candidate(
            self.result,
            self.candidate,
            self.identity.batch_identity.assessment_policy_version,
        ):
            raise ValueError("item assessment does not match candidate and batch identity")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateAssessmentBatch:
    """Complete atomic assessment of all candidates in one generation result."""

    identity: DuplicateCandidateAssessmentBatchIdentity
    generation_result: DuplicateCandidateGenerationResult
    assessment_policy: DuplicatePolicy
    item_outcomes: tuple[DuplicateCandidateAssessmentItemOutcome, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateCandidateAssessmentBatchIdentity):
            raise TypeError("batch requires a batch identity")
        if not isinstance(self.generation_result, DuplicateCandidateGenerationResult):
            raise TypeError("batch requires a generation result")
        if self.generation_result.policy != PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1:
            raise ValueError("batch requires the full supported candidate policy")
        if self.identity.generation_identity != self.generation_result.identity:
            raise ValueError("batch identity does not match generation result")
        if self.assessment_policy != PUBLICATION_DUPLICATE_POLICY_V1:
            raise ValueError("batch requires the full supported assessment policy")
        if self.identity.assessment_policy_version != self.assessment_policy.version:
            raise ValueError("batch identity does not match assessment policy")
        if not isinstance(self.item_outcomes, tuple):
            raise TypeError("batch item outcomes must be a tuple")
        if any(
            not isinstance(item, DuplicateCandidateAssessmentItemOutcome)
            for item in self.item_outcomes
        ):
            raise TypeError("batch contains an unsupported item outcome")
        if len(self.item_outcomes) != len(self.generation_result.candidates):
            raise ValueError("batch requires exactly one outcome per candidate")
        if (
            tuple(item.candidate for item in self.item_outcomes)
            != self.generation_result.candidates
        ):
            raise ValueError("batch item outcomes must follow exact candidate order")
        if any(item.identity.batch_identity != self.identity for item in self.item_outcomes):
            raise ValueError("batch item identity does not match batch identity")
        identities = tuple(item.identity for item in self.item_outcomes)
        if len(set(identities)) != len(identities):
            raise ValueError("batch item identities must be unique")

    @property
    def configuration(self) -> DuplicateCandidateAssessmentBatchConfiguration:
        """Return the exact generation and assessment configuration."""

        return DuplicateCandidateAssessmentBatchConfiguration(
            self.generation_result.configuration,
            self.assessment_policy,
        )


@dataclass(frozen=True, slots=True)
class DuplicateCandidateAssessmentBatchSuccess:
    """A complete successful atomic batch."""

    batch: DuplicateCandidateAssessmentBatch

    def __post_init__(self) -> None:
        if not isinstance(self.batch, DuplicateCandidateAssessmentBatch):
            raise TypeError("batch success requires a complete batch")


class GenerationCurrentKeysMismatchKind(StrEnum):
    """Exact structural relation between generation and current keys."""

    MISSING_GENERATION_KEY = "MISSING_GENERATION_KEY"
    EXTRA_CURRENT_KEY = "EXTRA_CURRENT_KEY"
    CURRENT_KEY_MISMATCH = "CURRENT_KEY_MISMATCH"


@dataclass(frozen=True, slots=True)
class GenerationCurrentKeysMismatchSubject:
    """One reference-level exact generation/current key mismatch."""

    kind: GenerationCurrentKeysMismatchKind
    reference: PublicationRef
    generation_key: ObservationKey | None
    current_key: ObservationKey | None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, GenerationCurrentKeysMismatchKind):
            raise TypeError("generation/current mismatch requires a typed kind")
        if not isinstance(self.reference, PublicationRef):
            raise TypeError("generation/current mismatch requires a publication reference")
        if self.generation_key is not None and self.generation_key.reference != self.reference:
            raise ValueError("generation mismatch key does not match reference")
        if self.current_key is not None and self.current_key.reference != self.reference:
            raise ValueError("current mismatch key does not match reference")
        expected_presence = {
            GenerationCurrentKeysMismatchKind.MISSING_GENERATION_KEY: (True, False),
            GenerationCurrentKeysMismatchKind.EXTRA_CURRENT_KEY: (False, True),
            GenerationCurrentKeysMismatchKind.CURRENT_KEY_MISMATCH: (True, True),
        }[self.kind]
        if (
            self.generation_key is not None,
            self.current_key is not None,
        ) != expected_presence:
            raise ValueError("generation/current mismatch keys do not match kind")
        if self.kind is GenerationCurrentKeysMismatchKind.CURRENT_KEY_MISMATCH and (
            self.generation_key == self.current_key
        ):
            raise ValueError("current-key mismatch requires unequal keys")


class CandidateBindingMismatchKind(StrEnum):
    """Defensive candidate-to-generation/current binding failure."""

    CANDIDATE_POLICY_MISMATCH = "CANDIDATE_POLICY_MISMATCH"
    CANDIDATE_PAIR_KEY_MISMATCH = "CANDIDATE_PAIR_KEY_MISMATCH"
    CANDIDATE_KEY_OUTSIDE_GENERATION = "CANDIDATE_KEY_OUTSIDE_GENERATION"
    CANDIDATE_KEY_OUTSIDE_CURRENT = "CANDIDATE_KEY_OUTSIDE_CURRENT"
    DUPLICATE_CANDIDATE_IDENTITY = "DUPLICATE_CANDIDATE_IDENTITY"
    NON_CANONICAL_CANDIDATE_ORDER = "NON_CANONICAL_CANDIDATE_ORDER"


@dataclass(frozen=True, slots=True)
class CandidateBindingMismatchSubject:
    """One exact candidate identity and its structural mismatch kind."""

    kind: CandidateBindingMismatchKind
    candidate_identity: DuplicateCandidateIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CandidateBindingMismatchKind):
            raise TypeError("candidate mismatch requires a typed kind")
        if not isinstance(self.candidate_identity, DuplicateCandidateIdentity):
            raise TypeError("candidate mismatch requires a candidate identity")


@dataclass(frozen=True, slots=True)
class UnsupportedCandidatePolicySubject:
    """Typed unsupported candidate-policy coordinate."""

    candidate_policy_version: DuplicateCandidatePolicyVersion

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_policy_version, DuplicateCandidatePolicyVersion):
            raise TypeError("unsupported candidate policy requires a typed version")


@dataclass(frozen=True, slots=True)
class UnsupportedAssessmentPolicySubject:
    """Typed assessment coordinate, absent only for an unsupported object."""

    assessment_policy_version: DuplicatePolicyVersion | None

    def __post_init__(self) -> None:
        if self.assessment_policy_version is not None and not isinstance(
            self.assessment_policy_version, DuplicatePolicyVersion
        ):
            raise TypeError("unsupported assessment policy version must be typed or absent")


@dataclass(frozen=True, slots=True)
class UnexpectedPairNotAssessedSubject:
    """A downstream not-assessed value for two preflight-validated available sides."""

    item_identity: DuplicateCandidateAssessmentItemIdentity
    result: PairNotAssessed

    def __post_init__(self) -> None:
        if not isinstance(self.item_identity, DuplicateCandidateAssessmentItemIdentity):
            raise TypeError("not-assessed subject requires an item identity")
        if not isinstance(self.result, PairNotAssessed):
            raise TypeError("not-assessed subject requires a pair-not-assessed result")


class DownstreamAssessmentConflictKind(StrEnum):
    """Stable classification of an unusable downstream result."""

    PAIR_ASSESSMENT_FAILURE = "PAIR_ASSESSMENT_FAILURE"
    SUCCESS_BINDING_MISMATCH = "SUCCESS_BINDING_MISMATCH"
    UNSUPPORTED_DOWNSTREAM_RESULT = "UNSUPPORTED_DOWNSTREAM_RESULT"


@dataclass(frozen=True, slots=True)
class DownstreamAssessmentConflictSubject:
    """One downstream item conflict without exception text or partial success."""

    item_identity: DuplicateCandidateAssessmentItemIdentity
    kind: DownstreamAssessmentConflictKind
    assessment_conflicts: tuple[DuplicateAssessmentConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.item_identity, DuplicateCandidateAssessmentItemIdentity):
            raise TypeError("downstream subject requires an item identity")
        if not isinstance(self.kind, DownstreamAssessmentConflictKind):
            raise TypeError("downstream subject requires a typed kind")
        if not isinstance(self.assessment_conflicts, tuple):
            raise TypeError("downstream assessment conflicts must be a tuple")
        if any(
            not isinstance(conflict, DuplicateAssessmentConflict)
            for conflict in self.assessment_conflicts
        ):
            raise TypeError("downstream subject contains an unsupported assessment conflict")
        if self.kind is DownstreamAssessmentConflictKind.PAIR_ASSESSMENT_FAILURE:
            if not self.assessment_conflicts:
                raise ValueError("pair assessment failure requires nested conflicts")
        elif self.assessment_conflicts:
            raise ValueError("only pair assessment failure may contain nested conflicts")


type DuplicateCandidateAssessmentBatchConflictSubject = (
    BatchInputSubject
    | ObservationKey
    | UnsupportedObservationSubject
    | DuplicatePublicationRefSubject
    | UnsupportedCandidatePolicySubject
    | UnsupportedAssessmentPolicySubject
    | GenerationCurrentKeysMismatchSubject
    | CandidateBindingMismatchSubject
    | UnexpectedPairNotAssessedSubject
    | DownstreamAssessmentConflictSubject
    | DuplicateCandidateAssessmentItemIdentity
    | DuplicateCandidateAssessmentBatchIdentity
)


@dataclass(frozen=True, slots=True)
class DuplicateCandidateAssessmentBatchConflict:
    """Stable typed batch conflict with no partial item outcomes."""

    category: DuplicateCandidateAssessmentBatchConflictCategory
    code: DuplicateCandidateAssessmentBatchConflictCode
    subject: DuplicateCandidateAssessmentBatchConflictSubject

    def __post_init__(self) -> None:
        if self.category != "DUPLICATE_CANDIDATE_ASSESSMENT_BATCH_CONFLICT":
            raise ValueError("invalid duplicate candidate assessment batch category")
        if self.code not in _CONFLICT_CODE_POSITION:
            raise ValueError("invalid duplicate candidate assessment batch conflict code")
        if self.code in {"observations_not_tuple", "empty_current_observations"}:
            valid = self.subject == "current_observations"
        elif self.code == "unsupported_generation_result":
            valid = self.subject == "generation_result"
        elif self.code in {"observation_not_available", "observation_key_content_conflict"}:
            valid = isinstance(self.subject, ObservationKey)
        elif self.code == "unsupported_observation":
            valid = isinstance(self.subject, UnsupportedObservationSubject)
        elif self.code == "duplicate_publication_ref":
            valid = isinstance(self.subject, DuplicatePublicationRefSubject)
        elif self.code == "unsupported_candidate_policy":
            valid = isinstance(self.subject, UnsupportedCandidatePolicySubject)
        elif self.code == "unsupported_assessment_policy":
            valid = isinstance(self.subject, UnsupportedAssessmentPolicySubject)
        elif self.code == "generation_current_keys_mismatch":
            valid = isinstance(self.subject, GenerationCurrentKeysMismatchSubject)
        elif self.code == "candidate_binding_mismatch":
            valid = isinstance(self.subject, CandidateBindingMismatchSubject)
        elif self.code == "unexpected_pair_not_assessed":
            valid = isinstance(self.subject, UnexpectedPairNotAssessedSubject)
        elif self.code == "downstream_assessment_conflict":
            valid = isinstance(self.subject, DownstreamAssessmentConflictSubject)
        elif self.code == "item_identity_content_conflict":
            valid = isinstance(self.subject, DuplicateCandidateAssessmentItemIdentity)
        else:
            valid = isinstance(self.subject, DuplicateCandidateAssessmentBatchIdentity)
        if not valid:
            raise ValueError("batch conflict subject does not match its code")


_CONFLICT_CODE_POSITION: dict[DuplicateCandidateAssessmentBatchConflictCode, int] = {
    "observations_not_tuple": 0,
    "empty_current_observations": 1,
    "observation_not_available": 2,
    "unsupported_observation": 3,
    "observation_key_content_conflict": 4,
    "duplicate_publication_ref": 5,
    "unsupported_generation_result": 6,
    "unsupported_candidate_policy": 7,
    "unsupported_assessment_policy": 8,
    "generation_current_keys_mismatch": 9,
    "candidate_binding_mismatch": 10,
    "unexpected_pair_not_assessed": 11,
    "downstream_assessment_conflict": 12,
    "item_identity_content_conflict": 13,
    "batch_identity_content_conflict": 14,
}
_KEY_MISMATCH_POSITION = {
    GenerationCurrentKeysMismatchKind.MISSING_GENERATION_KEY: 0,
    GenerationCurrentKeysMismatchKind.EXTRA_CURRENT_KEY: 1,
    GenerationCurrentKeysMismatchKind.CURRENT_KEY_MISMATCH: 2,
}
_CANDIDATE_MISMATCH_POSITION = {
    kind: position for position, kind in enumerate(CandidateBindingMismatchKind)
}
_DOWNSTREAM_KIND_POSITION = {
    kind: position for position, kind in enumerate(DownstreamAssessmentConflictKind)
}


def _item_identity_sort_key(
    identity: DuplicateCandidateAssessmentItemIdentity,
) -> tuple[object, ...]:
    return (
        *_candidate_identity_sort_key(identity.candidate_identity),
        *_generation_identity_sort_key(identity.batch_identity.generation_identity),
        identity.batch_identity.assessment_policy_version.value,
    )


def _subject_sort_key(
    subject: DuplicateCandidateAssessmentBatchConflictSubject,
) -> tuple[object, ...]:
    if isinstance(subject, str):
        return (subject,)
    if isinstance(subject, ObservationKey):
        return _observation_key_sort_key(subject)
    if isinstance(subject, UnsupportedObservationSubject):
        return (subject.input_ordinal,)
    if isinstance(subject, DuplicatePublicationRefSubject):
        return (
            *_reference_sort_key(subject.reference),
            tuple(_observation_key_sort_key(key) for key in subject.observation_keys),
        )
    if isinstance(subject, UnsupportedCandidatePolicySubject):
        return (subject.candidate_policy_version.value,)
    if isinstance(subject, UnsupportedAssessmentPolicySubject):
        return (
            ""
            if subject.assessment_policy_version is None
            else subject.assessment_policy_version.value,
        )
    if isinstance(subject, GenerationCurrentKeysMismatchSubject):
        return (
            *_reference_sort_key(subject.reference),
            _KEY_MISMATCH_POSITION[subject.kind],
            ()
            if subject.generation_key is None
            else _observation_key_sort_key(subject.generation_key),
            () if subject.current_key is None else _observation_key_sort_key(subject.current_key),
        )
    if isinstance(subject, CandidateBindingMismatchSubject):
        return (
            *_candidate_identity_sort_key(subject.candidate_identity),
            _CANDIDATE_MISMATCH_POSITION[subject.kind],
        )
    if isinstance(subject, UnexpectedPairNotAssessedSubject):
        return _item_identity_sort_key(subject.item_identity)
    if isinstance(subject, DownstreamAssessmentConflictSubject):
        return (
            *_item_identity_sort_key(subject.item_identity),
            _DOWNSTREAM_KIND_POSITION[subject.kind],
            tuple(
                (conflict.category, conflict.code, repr(conflict.subject))
                for conflict in subject.assessment_conflicts
            ),
        )
    if isinstance(subject, DuplicateCandidateAssessmentItemIdentity):
        return _item_identity_sort_key(subject)
    return (
        *_generation_identity_sort_key(subject.generation_identity),
        subject.assessment_policy_version.value,
    )


def _conflict_sort_key(
    conflict: DuplicateCandidateAssessmentBatchConflict,
) -> tuple[object, ...]:
    return (
        _CONFLICT_CODE_POSITION[conflict.code],
        _subject_sort_key(conflict.subject),
        conflict.category,
        conflict.code,
    )


def _canonical_conflicts(
    conflicts: list[DuplicateCandidateAssessmentBatchConflict],
) -> tuple[DuplicateCandidateAssessmentBatchConflict, ...]:
    ordered = sorted(conflicts, key=_conflict_sort_key)
    unique: list[DuplicateCandidateAssessmentBatchConflict] = []
    seen: set[DuplicateCandidateAssessmentBatchConflict] = set()
    for conflict in ordered:
        if conflict not in seen:
            unique.append(conflict)
            seen.add(conflict)
    return tuple(unique)


@dataclass(frozen=True, slots=True)
class DuplicateCandidateAssessmentBatchFailure:
    """Canonical non-empty conflicts and no partial batch or item outcomes."""

    conflicts: tuple[DuplicateCandidateAssessmentBatchConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple):
            raise TypeError("batch conflicts must be a tuple")
        if not self.conflicts:
            raise ValueError("batch failure requires a conflict")
        if any(
            not isinstance(conflict, DuplicateCandidateAssessmentBatchConflict)
            for conflict in self.conflicts
        ):
            raise TypeError("batch failure contains an unsupported conflict")
        if _canonical_conflicts(list(self.conflicts)) != self.conflicts:
            raise ValueError("batch conflicts must be unique and canonical")


type DuplicateCandidateAssessmentBatchOutcome = (
    DuplicateCandidateAssessmentBatchSuccess | DuplicateCandidateAssessmentBatchFailure
)


def _conflict(
    code: DuplicateCandidateAssessmentBatchConflictCode,
    subject: DuplicateCandidateAssessmentBatchConflictSubject,
) -> DuplicateCandidateAssessmentBatchConflict:
    return DuplicateCandidateAssessmentBatchConflict(
        "DUPLICATE_CANDIDATE_ASSESSMENT_BATCH_CONFLICT",
        code,
        subject,
    )


def _validated_current_and_conflicts(
    current_observations: object,
) -> tuple[tuple[AvailableObservation, ...], list[DuplicateCandidateAssessmentBatchConflict]]:
    if not isinstance(current_observations, tuple):
        return (), [_conflict("observations_not_tuple", "current_observations")]
    if not current_observations:
        return (), [_conflict("empty_current_observations", "current_observations")]

    conflicts: list[DuplicateCandidateAssessmentBatchConflict] = []
    available: list[AvailableObservation] = []
    for ordinal, observation in enumerate(current_observations):
        if isinstance(observation, UnavailableObservation):
            conflicts.append(_conflict("observation_not_available", observation.key))
        elif isinstance(observation, AvailableObservation):
            available.append(observation)
        else:
            conflicts.append(
                _conflict("unsupported_observation", UnsupportedObservationSubject(ordinal))
            )

    by_key: dict[ObservationKey, list[AvailableObservation]] = {}
    by_reference: dict[PublicationRef, list[AvailableObservation]] = {}
    for observation in available:
        by_key.setdefault(observation.key, []).append(observation)
        by_reference.setdefault(observation.key.reference, []).append(observation)

    conflicting_keys: list[ObservationKey] = []
    for key, group in by_key.items():
        if any(observation != group[0] for observation in group[1:]):
            conflicting_keys.append(key)
    conflicting_key_set = set(conflicting_keys)
    for key in sorted(conflicting_keys, key=_observation_key_sort_key):
        conflicts.append(_conflict("observation_key_content_conflict", key))

    duplicate_subjects: list[DuplicatePublicationRefSubject] = []
    for reference, group in by_reference.items():
        if len(group) < 2:
            continue
        keys = tuple(sorted((item.key for item in group), key=_observation_key_sort_key))
        only_conflicting_same_key = len(set(keys)) == 1 and keys[0] in conflicting_key_set
        if not only_conflicting_same_key:
            duplicate_subjects.append(DuplicatePublicationRefSubject(reference, keys))
    for subject in sorted(duplicate_subjects, key=lambda item: _reference_sort_key(item.reference)):
        conflicts.append(
            _conflict(
                "duplicate_publication_ref",
                subject,
            )
        )

    return tuple(available), conflicts


def _unsupported_candidate_policy_subject(
    generation_result: DuplicateCandidateGenerationResult,
) -> UnsupportedCandidatePolicySubject:
    identity = getattr(generation_result, "identity", None)
    version = getattr(identity, "candidate_policy_version", None)
    if not isinstance(version, DuplicateCandidatePolicyVersion):
        policy = getattr(generation_result, "policy", None)
        version = getattr(policy, "version", None)
    if not isinstance(version, DuplicateCandidatePolicyVersion):
        version = DuplicateCandidatePolicyVersion("unsupported-candidate-policy")
    return UnsupportedCandidatePolicySubject(version)


def _policy_and_result_conflicts(
    generation_result: object,
    assessment_policy: object,
) -> list[DuplicateCandidateAssessmentBatchConflict]:
    conflicts: list[DuplicateCandidateAssessmentBatchConflict] = []
    if not isinstance(generation_result, DuplicateCandidateGenerationResult):
        conflicts.append(_conflict("unsupported_generation_result", "generation_result"))
    else:
        identity = getattr(generation_result, "identity", None)
        policy = getattr(generation_result, "policy", None)
        if (
            policy != PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1
            or not isinstance(identity, DuplicateCandidateGenerationIdentity)
            or identity.candidate_policy_version
            != PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1.version
        ):
            conflicts.append(
                _conflict(
                    "unsupported_candidate_policy",
                    _unsupported_candidate_policy_subject(generation_result),
                )
            )
    if not isinstance(assessment_policy, DuplicatePolicy):
        conflicts.append(
            _conflict(
                "unsupported_assessment_policy",
                UnsupportedAssessmentPolicySubject(None),
            )
        )
    elif assessment_policy != PUBLICATION_DUPLICATE_POLICY_V1:
        conflicts.append(
            _conflict(
                "unsupported_assessment_policy",
                UnsupportedAssessmentPolicySubject(assessment_policy.version),
            )
        )
    return conflicts


def _generation_current_conflicts(
    generation_result: DuplicateCandidateGenerationResult,
    current_observations: tuple[AvailableObservation, ...],
) -> list[DuplicateCandidateAssessmentBatchConflict]:
    current_by_reference = {item.key.reference: item.key for item in current_observations}
    unmatched_current = dict(current_by_reference)
    conflicts: list[DuplicateCandidateAssessmentBatchConflict] = []
    for generation_key in generation_result.identity.canonical_input_keys:
        reference = generation_key.reference
        current_key = unmatched_current.pop(reference, None)
        if current_key is None:
            kind = GenerationCurrentKeysMismatchKind.MISSING_GENERATION_KEY
        elif generation_key != current_key:
            kind = GenerationCurrentKeysMismatchKind.CURRENT_KEY_MISMATCH
        else:
            continue
        conflicts.append(
            _conflict(
                "generation_current_keys_mismatch",
                GenerationCurrentKeysMismatchSubject(
                    kind,
                    reference,
                    generation_key,
                    current_key,
                ),
            )
        )
    for reference in sorted(unmatched_current, key=_reference_sort_key):
        conflicts.append(
            _conflict(
                "generation_current_keys_mismatch",
                GenerationCurrentKeysMismatchSubject(
                    GenerationCurrentKeysMismatchKind.EXTRA_CURRENT_KEY,
                    reference,
                    None,
                    unmatched_current[reference],
                ),
            )
        )
    return conflicts


def _candidate_binding_conflicts(
    generation_result: DuplicateCandidateGenerationResult,
    current_observations: tuple[AvailableObservation, ...] | None,
) -> list[DuplicateCandidateAssessmentBatchConflict]:
    candidates = getattr(generation_result, "candidates", ())
    if not isinstance(candidates, tuple) or any(
        not isinstance(candidate, DuplicateCandidate) for candidate in candidates
    ):
        return [_conflict("unsupported_generation_result", "generation_result")]
    generation_keys = set(generation_result.identity.canonical_input_keys)
    current_by_reference = (
        None
        if current_observations is None
        else {observation.key.reference: observation.key for observation in current_observations}
    )
    conflicts: list[DuplicateCandidateAssessmentBatchConflict] = []
    identities = tuple(candidate.identity for candidate in candidates)
    identity_counts: dict[DuplicateCandidateIdentity, int] = {}
    for identity in identities:
        identity_counts[identity] = identity_counts.get(identity, 0) + 1
    noncanonical_identities: set[DuplicateCandidateIdentity] = set()
    for previous, current in zip(identities, identities[1:], strict=False):
        if _candidate_identity_sort_key(current) < _candidate_identity_sort_key(previous):
            noncanonical_identities.update((previous, current))
    for candidate in candidates:
        identity = candidate.identity
        kinds: list[CandidateBindingMismatchKind] = []
        if identity.candidate_policy_version != generation_result.identity.candidate_policy_version:
            kinds.append(CandidateBindingMismatchKind.CANDIDATE_POLICY_MISMATCH)
        try:
            expected_pair = PublicationPair(
                identity.left_observation_key.reference,
                identity.right_observation_key.reference,
            )
            if identity.pair != expected_pair:
                kinds.append(CandidateBindingMismatchKind.CANDIDATE_PAIR_KEY_MISMATCH)
            if current_by_reference is not None:
                expected_left = current_by_reference.get(identity.pair.left)
                expected_right = current_by_reference.get(identity.pair.right)
                if (
                    expected_left is not None
                    and expected_right is not None
                    and (
                        identity.left_observation_key != expected_left
                        or identity.right_observation_key != expected_right
                    )
                ):
                    kinds.append(CandidateBindingMismatchKind.CANDIDATE_PAIR_KEY_MISMATCH)
        except AttributeError, TypeError, ValueError:
            kinds.append(CandidateBindingMismatchKind.CANDIDATE_PAIR_KEY_MISMATCH)
        if {
            identity.left_observation_key,
            identity.right_observation_key,
        } - generation_keys:
            kinds.append(CandidateBindingMismatchKind.CANDIDATE_KEY_OUTSIDE_GENERATION)
        if current_by_reference is not None and (
            current_by_reference.get(identity.pair.left) != identity.left_observation_key
            or current_by_reference.get(identity.pair.right) != identity.right_observation_key
        ):
            kinds.append(CandidateBindingMismatchKind.CANDIDATE_KEY_OUTSIDE_CURRENT)
        if identity_counts[identity] > 1:
            kinds.append(CandidateBindingMismatchKind.DUPLICATE_CANDIDATE_IDENTITY)
        if identity in noncanonical_identities:
            kinds.append(CandidateBindingMismatchKind.NON_CANONICAL_CANDIDATE_ORDER)
        for kind in dict.fromkeys(kinds):
            conflicts.append(
                _conflict(
                    "candidate_binding_mismatch",
                    CandidateBindingMismatchSubject(kind, identity),
                )
            )
    return conflicts


def _batch_identity(
    generation_result: DuplicateCandidateGenerationResult,
    assessment_policy: DuplicatePolicy,
) -> DuplicateCandidateAssessmentBatchIdentity:
    return DuplicateCandidateAssessmentBatchIdentity(
        generation_result.identity,
        assessment_policy.version,
    )


def assess_duplicate_candidate_batch(
    generation_result: DuplicateCandidateGenerationResult,
    current_observations: tuple[object, ...],
    assessment_policy: DuplicatePolicy,
) -> DuplicateCandidateAssessmentBatchOutcome:
    """Assess all and only supplied candidates after exact zero-call preflight."""

    current, current_conflicts = _validated_current_and_conflicts(current_observations)
    preflight_conflicts = [
        *current_conflicts,
        *_policy_and_result_conflicts(generation_result, assessment_policy),
    ]
    typed_generation = (
        generation_result
        if isinstance(generation_result, DuplicateCandidateGenerationResult)
        else None
    )
    typed_generation_policy = getattr(typed_generation, "policy", None)
    typed_generation_identity = getattr(typed_generation, "identity", None)
    supported_generation = (
        typed_generation is not None
        and typed_generation_policy == PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1
        and isinstance(typed_generation_identity, DuplicateCandidateGenerationIdentity)
        and typed_generation_identity.candidate_policy_version
        == PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1.version
    )
    supported_assessment = (
        assessment_policy
        if isinstance(assessment_policy, DuplicatePolicy)
        and assessment_policy == PUBLICATION_DUPLICATE_POLICY_V1
        else None
    )
    current_valid = (
        isinstance(current_observations, tuple)
        and bool(current_observations)
        and not (current_conflicts)
    )
    exact_current_binding = False
    canonical_current: tuple[AvailableObservation, ...] = ()
    if supported_generation and current_valid:
        assert typed_generation is not None
        binding_conflicts = _generation_current_conflicts(typed_generation, current)
        preflight_conflicts.extend(binding_conflicts)
        exact_current_binding = not binding_conflicts
        if exact_current_binding:
            current_by_reference = {
                observation.key.reference: observation for observation in current
            }
            canonical_current = tuple(
                current_by_reference[key.reference]
                for key in typed_generation.identity.canonical_input_keys
            )
        preflight_conflicts.extend(
            _candidate_binding_conflicts(
                typed_generation,
                canonical_current if exact_current_binding else None,
            )
        )
    elif supported_generation:
        assert typed_generation is not None
        preflight_conflicts.extend(_candidate_binding_conflicts(typed_generation, None))

    if preflight_conflicts:
        return DuplicateCandidateAssessmentBatchFailure(_canonical_conflicts(preflight_conflicts))

    assert typed_generation is not None
    assert supported_assessment is not None
    assert exact_current_binding
    validated_input = DuplicateCandidateAssessmentBatchInput(
        typed_generation,
        canonical_current,
        supported_assessment,
    )
    identity = _batch_identity(typed_generation, supported_assessment)
    current_by_reference = {
        observation.key.reference: observation
        for observation in validated_input.current_observations
    }
    provisional_items: list[DuplicateCandidateAssessmentItemOutcome] = []
    downstream_conflicts: list[DuplicateCandidateAssessmentBatchConflict] = []
    for candidate in typed_generation.candidates:
        item_identity = DuplicateCandidateAssessmentItemIdentity(identity, candidate.identity)
        left = current_by_reference[candidate.identity.pair.left]
        right = current_by_reference[candidate.identity.pair.right]
        result = assessment_module.assess_publication_pair(
            first=left,
            second=right,
            policy=supported_assessment,
        )
        if isinstance(result, PairAssessmentSuccess):
            if _success_matches_candidate(
                result,
                candidate,
                supported_assessment.version,
                left,
                right,
            ):
                provisional_items.append(
                    DuplicateCandidateAssessmentItemOutcome(
                        item_identity,
                        candidate,
                        result,
                    )
                )
            else:
                downstream_conflicts.append(
                    _conflict(
                        "downstream_assessment_conflict",
                        DownstreamAssessmentConflictSubject(
                            item_identity,
                            DownstreamAssessmentConflictKind.SUCCESS_BINDING_MISMATCH,
                            (),
                        ),
                    )
                )
        elif isinstance(result, PairNotAssessed):
            downstream_conflicts.append(
                _conflict(
                    "unexpected_pair_not_assessed",
                    UnexpectedPairNotAssessedSubject(item_identity, result),
                )
            )
        elif isinstance(result, PairAssessmentFailure):
            nested = getattr(result, "conflicts", ())
            if (
                isinstance(nested, tuple)
                and bool(nested)
                and all(isinstance(item, DuplicateAssessmentConflict) for item in nested)
            ):
                kind = DownstreamAssessmentConflictKind.PAIR_ASSESSMENT_FAILURE
                assessment_conflicts = nested
            else:
                kind = DownstreamAssessmentConflictKind.UNSUPPORTED_DOWNSTREAM_RESULT
                assessment_conflicts = ()
            downstream_conflicts.append(
                _conflict(
                    "downstream_assessment_conflict",
                    DownstreamAssessmentConflictSubject(
                        item_identity,
                        kind,
                        assessment_conflicts,
                    ),
                )
            )
        else:
            downstream_conflicts.append(
                _conflict(
                    "downstream_assessment_conflict",
                    DownstreamAssessmentConflictSubject(
                        item_identity,
                        DownstreamAssessmentConflictKind.UNSUPPORTED_DOWNSTREAM_RESULT,
                        (),
                    ),
                )
            )

    if downstream_conflicts:
        return DuplicateCandidateAssessmentBatchFailure(_canonical_conflicts(downstream_conflicts))
    batch = DuplicateCandidateAssessmentBatch(
        identity,
        typed_generation,
        supported_assessment,
        tuple(provisional_items),
    )
    return DuplicateCandidateAssessmentBatchSuccess(batch)


__all__ = [
    "BatchInputSubject",
    "CandidateBindingMismatchKind",
    "CandidateBindingMismatchSubject",
    "DownstreamAssessmentConflictKind",
    "DownstreamAssessmentConflictSubject",
    "DuplicateCandidateAssessmentBatch",
    "DuplicateCandidateAssessmentBatchConfiguration",
    "DuplicateCandidateAssessmentBatchConflict",
    "DuplicateCandidateAssessmentBatchConflictCategory",
    "DuplicateCandidateAssessmentBatchConflictCode",
    "DuplicateCandidateAssessmentBatchConflictSubject",
    "DuplicateCandidateAssessmentBatchFailure",
    "DuplicateCandidateAssessmentBatchIdentity",
    "DuplicateCandidateAssessmentBatchInput",
    "DuplicateCandidateAssessmentBatchOutcome",
    "DuplicateCandidateAssessmentBatchSuccess",
    "DuplicateCandidateAssessmentItemIdentity",
    "DuplicateCandidateAssessmentItemOutcome",
    "GenerationCurrentKeysMismatchKind",
    "GenerationCurrentKeysMismatchSubject",
    "UnexpectedPairNotAssessedSubject",
    "UnsupportedAssessmentPolicySubject",
    "UnsupportedCandidatePolicySubject",
    "assess_duplicate_candidate_batch",
]
