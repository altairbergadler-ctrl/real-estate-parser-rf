"""Pure bounded generation of duplicate-candidate publication pairs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from real_estate_parser.normalization import (
    Area,
    LocationText,
    Missing,
    Present,
    RoomCount,
    Unsupported,
)
from real_estate_parser.publication_duplicate_assessments import PublicationPair
from real_estate_parser.publication_observations import (
    AvailableObservation,
    ObservationKey,
    PublicationObservation,
    UnavailableObservation,
)
from real_estate_parser.source_batch import PublicationRef

type CandidateBlockingField = Literal["total_area", "rooms", "location_text"]
type DuplicateCandidateGenerationConflictCategory = Literal[
    "DUPLICATE_CANDIDATE_GENERATION_CONFLICT"
]
type DuplicateCandidateGenerationConflictCode = Literal[
    "observations_not_tuple",
    "empty_generation_input",
    "observation_not_available",
    "unsupported_observation",
    "observation_key_content_conflict",
    "duplicate_publication_ref",
    "unsupported_candidate_policy",
    "invalid_bucket_pair_limit",
    "candidate_identity_content_conflict",
    "generation_identity_content_conflict",
]

_CANDIDATE_FIELDS: tuple[CandidateBlockingField, ...] = (
    "total_area",
    "rooms",
    "location_text",
)
_OVERSIZED_REASON = "prospective_pair_count_exceeds_limit"


def _validate_opaque_code(value: str, label: str) -> None:
    if (
        not 1 <= len(value) <= 128
        or not value.isascii()
        or any(not 0x21 <= ord(character) <= 0x7E for character in value)
    ):
        raise ValueError(f"invalid {label}")


@dataclass(frozen=True, slots=True)
class DuplicateCandidatePolicyVersion:
    """Stable identity of candidate-selection semantics, separate from assessment."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "candidate policy version")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateRuleId:
    """Stable identity of one candidate blocking rule."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "candidate rule id")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateRuleVersion:
    """Stable revision identity of one candidate blocking rule."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "candidate rule version")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateReasonCode:
    """Safe opaque reason code without source text or personal data."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "candidate reason code")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateRule:
    """Immutable exact component shape of one candidate blocking pass."""

    rule_id: DuplicateCandidateRuleId
    rule_version: DuplicateCandidateRuleVersion
    components: tuple[CandidateBlockingField, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, DuplicateCandidateRuleId) or not isinstance(
            self.rule_version, DuplicateCandidateRuleVersion
        ):
            raise TypeError("candidate rule requires typed rule codes")
        if not isinstance(self.components, tuple):
            raise TypeError("candidate rule components must be a tuple")
        if not self.components:
            raise ValueError("candidate rule must contain a component")
        if any(component not in _CANDIDATE_FIELDS for component in self.components):
            raise ValueError("candidate rule contains an unsupported component")
        if len(set(self.components)) != len(self.components):
            raise ValueError("candidate rule components must be unique")


@dataclass(frozen=True, slots=True)
class DuplicateCandidatePolicy:
    """Immutable ordered candidate rules; support is checked by generation."""

    version: DuplicateCandidatePolicyVersion
    rules: tuple[DuplicateCandidateRule, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.version, DuplicateCandidatePolicyVersion):
            raise TypeError("candidate policy requires a typed version")
        if not isinstance(self.rules, tuple):
            raise TypeError("candidate policy rules must be a tuple")
        if not self.rules:
            raise ValueError("candidate policy must contain a rule")
        if any(not isinstance(rule, DuplicateCandidateRule) for rule in self.rules):
            raise TypeError("candidate policy contains an unsupported rule")
        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("candidate policy rule ids must be unique")


PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION = DuplicateCandidatePolicyVersion(
    "publication-duplicate-candidate-policy@1"
)
_AREA_ROOMS_RULE = DuplicateCandidateRule(
    DuplicateCandidateRuleId("area-rooms-exact-block"),
    DuplicateCandidateRuleVersion("candidate-area-rooms@1"),
    ("total_area", "rooms"),
)
_AREA_LOCATION_TEXT_RULE = DuplicateCandidateRule(
    DuplicateCandidateRuleId("area-location-text-exact-block"),
    DuplicateCandidateRuleVersion("candidate-area-location-text@1"),
    ("total_area", "location_text"),
)
PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1 = DuplicateCandidatePolicy(
    version=PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION,
    rules=(_AREA_ROOMS_RULE, _AREA_LOCATION_TEXT_RULE),
)


def _require_rule(
    rule_id: DuplicateCandidateRuleId,
    rule_version: DuplicateCandidateRuleVersion,
    expected: DuplicateCandidateRule,
) -> None:
    if rule_id != expected.rule_id or rule_version != expected.rule_version:
        raise ValueError("blocking key rule does not match its typed variant")


@dataclass(frozen=True, slots=True)
class AreaRoomsBlockingKey:
    """Exact total-area and room-count membership for the first pass."""

    rule_id: DuplicateCandidateRuleId
    rule_version: DuplicateCandidateRuleVersion
    total_area: Area
    rooms: RoomCount

    def __post_init__(self) -> None:
        _require_rule(self.rule_id, self.rule_version, _AREA_ROOMS_RULE)
        if not isinstance(self.total_area, Area) or not isinstance(self.rooms, RoomCount):
            raise TypeError("area/rooms blocking key requires canonical typed values")


@dataclass(frozen=True, slots=True)
class AreaLocationTextBlockingKey:
    """Exact total-area and canonical location-text membership for the second pass."""

    rule_id: DuplicateCandidateRuleId
    rule_version: DuplicateCandidateRuleVersion
    total_area: Area
    location_text: LocationText

    def __post_init__(self) -> None:
        _require_rule(self.rule_id, self.rule_version, _AREA_LOCATION_TEXT_RULE)
        if not isinstance(self.total_area, Area) or not isinstance(
            self.location_text, LocationText
        ):
            raise TypeError("area/location blocking key requires canonical typed values")


type DuplicateBlockingKey = AreaRoomsBlockingKey | AreaLocationTextBlockingKey


def _observation_key_sort_key(key: ObservationKey) -> tuple[str, str, object]:
    return (
        key.reference.source_id.value,
        key.reference.publication_id.value,
        key.observed_at.value,
    )


def _blocking_key_sort_key(key: DuplicateBlockingKey) -> tuple[int, int, int, str]:
    if isinstance(key, AreaRoomsBlockingKey):
        return (0, key.total_area.value, key.rooms.value, "")
    return (1, key.total_area.value, -1, key.location_text.value)


class BlockingComponentState(StrEnum):
    """Why one exact blocking component cannot participate."""

    MISSING = "MISSING"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class BlockingComponentNonParticipation:
    """One component-level Missing or Unsupported outcome."""

    field: CandidateBlockingField
    state: BlockingComponentState
    unsupported_reason_code: DuplicateCandidateReasonCode | None = None

    def __post_init__(self) -> None:
        if self.field not in _CANDIDATE_FIELDS:
            raise ValueError("unsupported candidate blocking field")
        if not isinstance(self.state, BlockingComponentState):
            raise TypeError("component non-participation requires a typed state")
        if self.state is BlockingComponentState.MISSING:
            if self.unsupported_reason_code is not None:
                raise ValueError("missing component cannot have an unsupported reason")
        elif not isinstance(self.unsupported_reason_code, DuplicateCandidateReasonCode):
            raise ValueError("unsupported component requires an exact reason code")


def _supported_rule(
    rule_id: DuplicateCandidateRuleId,
    rule_version: DuplicateCandidateRuleVersion,
) -> DuplicateCandidateRule:
    for rule in PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1.rules:
        if rule.rule_id == rule_id and rule.rule_version == rule_version:
            return rule
    raise ValueError("non-participation rule is not supported")


@dataclass(frozen=True, slots=True)
class BlockingNonParticipation:
    """Complete ordered reasons one observation cannot enter one pass."""

    observation_key: ObservationKey
    rule_id: DuplicateCandidateRuleId
    rule_version: DuplicateCandidateRuleVersion
    reasons: tuple[BlockingComponentNonParticipation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.observation_key, ObservationKey):
            raise TypeError("blocking non-participation requires an observation key")
        if not isinstance(self.reasons, tuple):
            raise TypeError("blocking non-participation reasons must be a tuple")
        if not self.reasons:
            raise ValueError("blocking non-participation requires a reason")
        if any(
            not isinstance(reason, BlockingComponentNonParticipation) for reason in self.reasons
        ):
            raise TypeError("blocking non-participation contains an unsupported reason")
        rule = _supported_rule(self.rule_id, self.rule_version)
        positions = tuple(rule.components.index(reason.field) for reason in self.reasons)
        if positions != tuple(sorted(set(positions))):
            raise ValueError("non-participation reasons must be unique and in component order")


def _validate_member_keys(member_keys: tuple[ObservationKey, ...]) -> None:
    if not isinstance(member_keys, tuple):
        raise TypeError("blocking bucket members must be a tuple")
    if not member_keys:
        raise ValueError("blocking bucket must contain a member")
    if any(not isinstance(key, ObservationKey) for key in member_keys):
        raise TypeError("blocking bucket contains an unsupported member")
    if len(set(member_keys)) != len(member_keys):
        raise ValueError("blocking bucket members must be unique")
    if member_keys != tuple(sorted(member_keys, key=_observation_key_sort_key)):
        raise ValueError("blocking bucket members must be canonical")


@dataclass(frozen=True, slots=True)
class BlockingBucket:
    """One full logical exact-key bucket before its size decision."""

    key: DuplicateBlockingKey
    member_keys: tuple[ObservationKey, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.key, (AreaRoomsBlockingKey, AreaLocationTextBlockingKey)):
            raise TypeError("blocking bucket requires a typed key")
        _validate_member_keys(self.member_keys)


@dataclass(frozen=True, slots=True)
class BucketPairLimit:
    """Caller-supplied positive exact upper bound for one bucket's pairs."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise ValueError("bucket pair limit must be a positive exact integer")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateGenerationConfiguration:
    """Full candidate policy and explicit caller-supplied bucket limit."""

    policy: DuplicateCandidatePolicy
    bucket_pair_limit: BucketPairLimit

    def __post_init__(self) -> None:
        if not isinstance(self.policy, DuplicateCandidatePolicy):
            raise TypeError("candidate configuration requires a candidate policy")
        if not isinstance(self.bucket_pair_limit, BucketPairLimit):
            raise TypeError("candidate configuration requires a bucket pair limit")


@dataclass(frozen=True, slots=True)
class OversizedBucket:
    """A whole skipped bucket with exact membership and prospective count."""

    key: DuplicateBlockingKey
    member_keys: tuple[ObservationKey, ...]
    prospective_pair_count: int
    reason_code: DuplicateCandidateReasonCode

    def __post_init__(self) -> None:
        if not isinstance(self.key, (AreaRoomsBlockingKey, AreaLocationTextBlockingKey)):
            raise TypeError("oversized bucket requires a typed key")
        _validate_member_keys(self.member_keys)
        expected = len(self.member_keys) * (len(self.member_keys) - 1) // 2
        if type(self.prospective_pair_count) is not int or self.prospective_pair_count != expected:
            raise ValueError("oversized bucket prospective count must be exact")
        if self.reason_code != DuplicateCandidateReasonCode(_OVERSIZED_REASON):
            raise ValueError("unsupported oversized bucket reason")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateIdentity:
    """Exact pair, current observation keys and candidate-policy identity."""

    pair: PublicationPair
    left_observation_key: ObservationKey
    right_observation_key: ObservationKey
    candidate_policy_version: DuplicateCandidatePolicyVersion

    def __post_init__(self) -> None:
        if not isinstance(self.pair, PublicationPair):
            raise TypeError("candidate identity requires a publication pair")
        if self.left_observation_key.reference != self.pair.left:
            raise ValueError("left observation key does not match candidate pair")
        if self.right_observation_key.reference != self.pair.right:
            raise ValueError("right observation key does not match candidate pair")
        if not isinstance(self.candidate_policy_version, DuplicateCandidatePolicyVersion):
            raise TypeError("candidate identity requires a candidate policy version")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateBlockingMatch:
    """Exact materialized blocking route, never assessment evidence."""

    blocking_key: DuplicateBlockingKey

    def __post_init__(self) -> None:
        if not isinstance(self.blocking_key, (AreaRoomsBlockingKey, AreaLocationTextBlockingKey)):
            raise TypeError("candidate blocking match requires a typed key")


@dataclass(frozen=True, slots=True)
class DuplicateCandidate:
    """One unique candidate with all and only its materialized exact matches."""

    identity: DuplicateCandidateIdentity
    blocking_matches: tuple[DuplicateCandidateBlockingMatch, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateCandidateIdentity):
            raise TypeError("candidate requires a candidate identity")
        if not isinstance(self.blocking_matches, tuple):
            raise TypeError("candidate blocking matches must be a tuple")
        if not self.blocking_matches:
            raise ValueError("candidate requires a blocking match")
        if any(
            not isinstance(match, DuplicateCandidateBlockingMatch)
            for match in self.blocking_matches
        ):
            raise TypeError("candidate contains an unsupported blocking match")
        keys = tuple(match.blocking_key for match in self.blocking_matches)
        if len(set(keys)) != len(keys):
            raise ValueError("candidate blocking matches must be unique")
        if keys != tuple(sorted(keys, key=_blocking_key_sort_key)):
            raise ValueError("candidate blocking matches must be in policy order")
        if (
            self.identity.candidate_policy_version
            != PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION
        ):
            raise ValueError("candidate matches are not bound to the supported policy")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateGenerationIdentity:
    """Replay identity for a full current context, policy and bucket limit."""

    candidate_policy_version: DuplicateCandidatePolicyVersion
    bucket_pair_limit: BucketPairLimit
    canonical_input_keys: tuple[ObservationKey, ...]

    def __post_init__(self) -> None:
        if self.candidate_policy_version != PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION:
            raise ValueError("generation identity requires the supported candidate policy")
        if not isinstance(self.bucket_pair_limit, BucketPairLimit):
            raise TypeError("generation identity requires a bucket pair limit")
        if not isinstance(self.canonical_input_keys, tuple):
            raise TypeError("generation input keys must be a tuple")
        if not self.canonical_input_keys:
            raise ValueError("generation identity requires an input key")
        if any(not isinstance(key, ObservationKey) for key in self.canonical_input_keys):
            raise TypeError("generation identity contains an unsupported input key")
        if len(set(self.canonical_input_keys)) != len(self.canonical_input_keys):
            raise ValueError("generation input keys must be unique")
        if self.canonical_input_keys != tuple(
            sorted(self.canonical_input_keys, key=_observation_key_sort_key)
        ):
            raise ValueError("generation input keys must be canonical")
        references = tuple(key.reference for key in self.canonical_input_keys)
        if len(set(references)) != len(references):
            raise ValueError("generation input keys must contain unique references")


def _candidate_sort_key(candidate: DuplicateCandidate) -> tuple[object, ...]:
    identity = candidate.identity
    return (
        identity.pair.left.source_id.value,
        identity.pair.left.publication_id.value,
        identity.pair.right.source_id.value,
        identity.pair.right.publication_id.value,
        identity.left_observation_key.observed_at.value,
        identity.right_observation_key.observed_at.value,
        identity.candidate_policy_version.value,
    )


def _non_participation_sort_key(item: BlockingNonParticipation) -> tuple[object, ...]:
    rule_position = 0 if item.rule_id == _AREA_ROOMS_RULE.rule_id else 1
    return (*_observation_key_sort_key(item.observation_key), rule_position)


@dataclass(frozen=True, slots=True)
class DuplicateCandidateGenerationResult:
    """Complete successful bounded generation result and explanations."""

    identity: DuplicateCandidateGenerationIdentity
    policy: DuplicateCandidatePolicy
    candidates: tuple[DuplicateCandidate, ...]
    non_participations: tuple[BlockingNonParticipation, ...]
    oversized_buckets: tuple[OversizedBucket, ...]

    def __post_init__(self) -> None:
        if self.policy != PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1:
            raise ValueError("generation result requires the full supported candidate policy")
        if self.identity.candidate_policy_version != self.policy.version:
            raise ValueError("generation identity and policy do not match")
        collections = (self.candidates, self.non_participations, self.oversized_buckets)
        if any(not isinstance(collection, tuple) for collection in collections):
            raise TypeError("generation result collections must be tuples")
        if any(not isinstance(candidate, DuplicateCandidate) for candidate in self.candidates):
            raise TypeError("generation result contains an unsupported candidate")
        if any(not isinstance(item, BlockingNonParticipation) for item in self.non_participations):
            raise TypeError("generation result contains unsupported non-participation")
        if any(not isinstance(bucket, OversizedBucket) for bucket in self.oversized_buckets):
            raise TypeError("generation result contains an unsupported oversized bucket")
        if self.candidates != tuple(sorted(self.candidates, key=_candidate_sort_key)):
            raise ValueError("generation candidates must be canonical")
        identities = tuple(candidate.identity for candidate in self.candidates)
        if len(set(identities)) != len(identities):
            raise ValueError("generation candidates must be unique")
        if self.non_participations != tuple(
            sorted(self.non_participations, key=_non_participation_sort_key)
        ):
            raise ValueError("generation non-participations must be canonical")
        if len(set(self.non_participations)) != len(self.non_participations):
            raise ValueError("generation non-participations must be unique")
        if self.oversized_buckets != tuple(
            sorted(self.oversized_buckets, key=lambda bucket: _blocking_key_sort_key(bucket.key))
        ):
            raise ValueError("generation oversized buckets must be canonical")
        if len(set(self.oversized_buckets)) != len(self.oversized_buckets):
            raise ValueError("generation oversized buckets must be unique")
        input_keys = set(self.identity.canonical_input_keys)
        for candidate in self.candidates:
            if candidate.identity.candidate_policy_version != self.policy.version:
                raise ValueError("candidate policy does not match generation result")
            if {
                candidate.identity.left_observation_key,
                candidate.identity.right_observation_key,
            } - input_keys:
                raise ValueError("candidate observation keys are outside generation input")
        if any(item.observation_key not in input_keys for item in self.non_participations):
            raise ValueError("non-participation key is outside generation input")
        for bucket in self.oversized_buckets:
            if set(bucket.member_keys) - input_keys:
                raise ValueError("oversized bucket member is outside generation input")
            if bucket.prospective_pair_count <= self.identity.bucket_pair_limit.value:
                raise ValueError("oversized bucket must exceed the configured limit")
        oversized_keys = {bucket.key for bucket in self.oversized_buckets}
        if any(
            match.blocking_key in oversized_keys
            for candidate in self.candidates
            for match in candidate.blocking_matches
        ):
            raise ValueError("skipped oversized key cannot be a candidate match")

    @property
    def configuration(self) -> DuplicateCandidateGenerationConfiguration:
        """Return the exact full configuration represented by the result."""

        return DuplicateCandidateGenerationConfiguration(
            self.policy,
            self.identity.bucket_pair_limit,
        )


@dataclass(frozen=True, slots=True)
class UnsupportedObservationSubject:
    """Stable zero-based input coordinate when no observation key exists."""

    input_ordinal: int

    def __post_init__(self) -> None:
        if type(self.input_ordinal) is not int or self.input_ordinal < 0:
            raise ValueError("unsupported observation ordinal must be non-negative")


@dataclass(frozen=True, slots=True)
class DuplicatePublicationRefSubject:
    """A repeated reference and all canonically ordered conflicting keys."""

    reference: PublicationRef
    observation_keys: tuple[ObservationKey, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.reference, PublicationRef):
            raise TypeError("duplicate reference subject requires a publication reference")
        if not isinstance(self.observation_keys, tuple) or len(self.observation_keys) < 2:
            raise ValueError("duplicate reference subject requires conflicting keys")
        if any(key.reference != self.reference for key in self.observation_keys):
            raise ValueError("duplicate reference subject keys must match its reference")
        if self.observation_keys != tuple(
            sorted(self.observation_keys, key=_observation_key_sort_key)
        ):
            raise ValueError("duplicate reference subject keys must be canonical")


@dataclass(frozen=True, slots=True)
class InvalidBucketPairLimitSubject:
    """Safe deterministic description of an invalid supplied limit."""

    value_type: str
    value_code: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value_type, "bucket limit value type")
        _validate_opaque_code(self.value_code, "bucket limit value code")


type DuplicateCandidateGenerationConflictSubject = (
    Literal["generation_input"]
    | ObservationKey
    | UnsupportedObservationSubject
    | DuplicatePublicationRefSubject
    | DuplicateCandidatePolicyVersion
    | InvalidBucketPairLimitSubject
    | DuplicateCandidateIdentity
    | DuplicateCandidateGenerationIdentity
)


@dataclass(frozen=True, slots=True)
class DuplicateCandidateGenerationConflict:
    """Stable generation/future-consumer conflict with structural coordinates."""

    category: DuplicateCandidateGenerationConflictCategory
    code: DuplicateCandidateGenerationConflictCode
    subject: DuplicateCandidateGenerationConflictSubject

    def __post_init__(self) -> None:
        if self.category != "DUPLICATE_CANDIDATE_GENERATION_CONFLICT":
            raise ValueError("invalid duplicate candidate conflict category")
        expected: tuple[type[object], ...] | None
        if self.code in {"observations_not_tuple", "empty_generation_input"}:
            if self.subject != "generation_input":
                raise ValueError("generation-input conflict has an invalid subject")
            return
        if self.code in {"observation_not_available", "observation_key_content_conflict"}:
            expected = (ObservationKey,)
        elif self.code == "unsupported_observation":
            expected = (UnsupportedObservationSubject,)
        elif self.code == "duplicate_publication_ref":
            expected = (DuplicatePublicationRefSubject,)
        elif self.code == "unsupported_candidate_policy":
            expected = (DuplicateCandidatePolicyVersion,)
        elif self.code == "invalid_bucket_pair_limit":
            expected = (InvalidBucketPairLimitSubject,)
        elif self.code == "candidate_identity_content_conflict":
            expected = (DuplicateCandidateIdentity,)
        else:
            expected = (DuplicateCandidateGenerationIdentity,)
        if not isinstance(self.subject, expected):
            raise ValueError("duplicate candidate conflict subject does not match its code")


_CONFLICT_CODE_POSITION: dict[DuplicateCandidateGenerationConflictCode, int] = {
    "observations_not_tuple": 0,
    "empty_generation_input": 1,
    "observation_not_available": 2,
    "unsupported_observation": 3,
    "observation_key_content_conflict": 4,
    "duplicate_publication_ref": 5,
    "unsupported_candidate_policy": 6,
    "invalid_bucket_pair_limit": 7,
    "candidate_identity_content_conflict": 8,
    "generation_identity_content_conflict": 9,
}


def _conflict_subject_sort_key(
    subject: DuplicateCandidateGenerationConflictSubject,
) -> tuple[object, ...]:
    if subject == "generation_input":
        return ()
    if isinstance(subject, ObservationKey):
        return _observation_key_sort_key(subject)
    if isinstance(subject, UnsupportedObservationSubject):
        return (subject.input_ordinal,)
    if isinstance(subject, DuplicatePublicationRefSubject):
        return (
            subject.reference.source_id.value,
            subject.reference.publication_id.value,
            tuple(_observation_key_sort_key(key) for key in subject.observation_keys),
        )
    if isinstance(subject, DuplicateCandidatePolicyVersion):
        return (subject.value,)
    if isinstance(subject, InvalidBucketPairLimitSubject):
        return (subject.value_type, subject.value_code)
    if isinstance(subject, DuplicateCandidateIdentity):
        return _candidate_identity_sort_key(subject)
    return (
        subject.candidate_policy_version.value,
        subject.bucket_pair_limit.value,
        tuple(_observation_key_sort_key(key) for key in subject.canonical_input_keys),
    )


def _conflict_sort_key(conflict: DuplicateCandidateGenerationConflict) -> tuple[object, ...]:
    return (
        _CONFLICT_CODE_POSITION[conflict.code],
        _conflict_subject_sort_key(conflict.subject),
        conflict.category,
        conflict.code,
    )


def _canonical_conflicts(
    conflicts: list[DuplicateCandidateGenerationConflict],
) -> tuple[DuplicateCandidateGenerationConflict, ...]:
    ordered = sorted(conflicts, key=_conflict_sort_key)
    unique: list[DuplicateCandidateGenerationConflict] = []
    for conflict in ordered:
        if conflict not in unique:
            unique.append(conflict)
    return tuple(unique)


@dataclass(frozen=True, slots=True)
class DuplicateCandidateGenerationSuccess:
    """A complete successful result, including valid empty candidate output."""

    result: DuplicateCandidateGenerationResult

    def __post_init__(self) -> None:
        if not isinstance(self.result, DuplicateCandidateGenerationResult):
            raise TypeError("generation success requires a complete result")


@dataclass(frozen=True, slots=True)
class DuplicateCandidateGenerationFailure:
    """Atomic canonical conflicts without partial input, candidates or outcomes."""

    conflicts: tuple[DuplicateCandidateGenerationConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple):
            raise TypeError("generation conflicts must be a tuple")
        if not self.conflicts:
            raise ValueError("generation failure must contain a conflict")
        if any(
            not isinstance(conflict, DuplicateCandidateGenerationConflict)
            for conflict in self.conflicts
        ):
            raise TypeError("generation failure contains an unsupported conflict")
        canonical = _canonical_conflicts(list(self.conflicts))
        if canonical != self.conflicts:
            raise ValueError("generation conflicts must be unique and canonical")


type DuplicateCandidateGenerationOutcome = (
    DuplicateCandidateGenerationSuccess | DuplicateCandidateGenerationFailure
)


def _conflict(
    code: DuplicateCandidateGenerationConflictCode,
    subject: DuplicateCandidateGenerationConflictSubject,
) -> DuplicateCandidateGenerationConflict:
    return DuplicateCandidateGenerationConflict(
        "DUPLICATE_CANDIDATE_GENERATION_CONFLICT", code, subject
    )


def _safe_invalid_limit_subject(value: object) -> InvalidBucketPairLimitSubject:
    if value is None:
        return InvalidBucketPairLimitSubject("none", "none")
    if type(value) is bool:
        return InvalidBucketPairLimitSubject("bool", "true" if value else "false")
    if type(value) is int:
        return InvalidBucketPairLimitSubject("int", str(value))
    if type(value) is float:
        float_value = value
        assert isinstance(float_value, float)
        value_code = float_value.hex() if float_value == float_value else "nan"
        return InvalidBucketPairLimitSubject("float", value_code)
    return InvalidBucketPairLimitSubject("unsupported", "unsupported")


def _configuration_conflicts(
    configuration: DuplicateCandidateGenerationConfiguration,
) -> list[DuplicateCandidateGenerationConflict]:
    conflicts: list[DuplicateCandidateGenerationConflict] = []
    policy = getattr(configuration, "policy", None)
    if not isinstance(policy, DuplicateCandidatePolicy):
        version = DuplicateCandidatePolicyVersion("unsupported-candidate-policy")
        conflicts.append(_conflict("unsupported_candidate_policy", version))
    elif policy != PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1:
        conflicts.append(_conflict("unsupported_candidate_policy", policy.version))
    limit = getattr(configuration, "bucket_pair_limit", None)
    if (
        not isinstance(limit, BucketPairLimit)
        or type(getattr(limit, "value", None)) is not int
        or limit.value <= 0
    ):
        conflicts.append(
            _conflict(
                "invalid_bucket_pair_limit",
                _safe_invalid_limit_subject(getattr(limit, "value", limit)),
            )
        )
    return conflicts


def _validated_observations_and_conflicts(
    current_observations: object,
) -> tuple[tuple[AvailableObservation, ...], list[DuplicateCandidateGenerationConflict]]:
    if not isinstance(current_observations, tuple):
        return (), [_conflict("observations_not_tuple", "generation_input")]
    if not current_observations:
        return (), [_conflict("empty_generation_input", "generation_input")]

    conflicts: list[DuplicateCandidateGenerationConflict] = []
    available_with_ordinals: list[tuple[int, AvailableObservation]] = []
    for ordinal, observation in enumerate(current_observations):
        if isinstance(observation, UnavailableObservation):
            conflicts.append(_conflict("observation_not_available", observation.key))
        elif isinstance(observation, AvailableObservation):
            available_with_ordinals.append((ordinal, observation))
        else:
            conflicts.append(
                _conflict("unsupported_observation", UnsupportedObservationSubject(ordinal))
            )

    by_key: dict[ObservationKey, list[AvailableObservation]] = {}
    by_reference: dict[PublicationRef, list[AvailableObservation]] = {}
    for _, observation in available_with_ordinals:
        by_key.setdefault(observation.key, []).append(observation)
        by_reference.setdefault(observation.key.reference, []).append(observation)

    conflicting_keys: set[ObservationKey] = set()
    for key in sorted(by_key, key=_observation_key_sort_key):
        group = by_key[key]
        if any(observation != group[0] for observation in group[1:]):
            conflicting_keys.add(key)
            conflicts.append(_conflict("observation_key_content_conflict", key))

    for reference in sorted(
        by_reference,
        key=lambda item: (item.source_id.value, item.publication_id.value),
    ):
        group = by_reference[reference]
        if len(group) < 2:
            continue
        keys = tuple(
            sorted(
                (observation.key for observation in group),
                key=_observation_key_sort_key,
            )
        )
        distinct_keys = set(keys)
        only_conflicting_same_key = len(distinct_keys) == 1 and keys[0] in conflicting_keys
        if not only_conflicting_same_key:
            conflicts.append(
                _conflict(
                    "duplicate_publication_ref",
                    DuplicatePublicationRefSubject(reference, keys),
                )
            )

    canonical = tuple(
        sorted(
            (observation for _, observation in available_with_ordinals),
            key=lambda observation: _observation_key_sort_key(observation.key),
        )
    )
    return canonical, conflicts


def _component_non_participation(
    field: CandidateBlockingField,
    outcome: object,
) -> BlockingComponentNonParticipation | None:
    if isinstance(outcome, Missing):
        return BlockingComponentNonParticipation(field, BlockingComponentState.MISSING)
    if isinstance(outcome, Unsupported):
        return BlockingComponentNonParticipation(
            field,
            BlockingComponentState.UNSUPPORTED,
            DuplicateCandidateReasonCode(outcome.provenance.reason_code),
        )
    return None


def _project_rule(
    observation: AvailableObservation,
    rule: DuplicateCandidateRule,
) -> DuplicateBlockingKey | BlockingNonParticipation:
    listing = observation.listing
    component_outcomes: tuple[tuple[CandidateBlockingField, object], ...]
    if rule == _AREA_ROOMS_RULE:
        component_outcomes = (
            ("total_area", listing.total_area),
            ("rooms", listing.rooms),
        )
    elif rule == _AREA_LOCATION_TEXT_RULE:
        component_outcomes = (
            ("total_area", listing.total_area),
            ("location_text", listing.location_text),
        )
    else:
        raise ValueError("unsupported candidate policy rule")

    reasons = tuple(
        reason
        for field, outcome in component_outcomes
        if (reason := _component_non_participation(field, outcome)) is not None
    )
    if reasons:
        return BlockingNonParticipation(
            observation.key,
            rule.rule_id,
            rule.rule_version,
            reasons,
        )

    area_outcome = listing.total_area
    if not isinstance(area_outcome, Present) or not isinstance(area_outcome.value.value, Area):
        raise TypeError("present total_area must contain canonical Area")
    if rule == _AREA_ROOMS_RULE:
        rooms_outcome = listing.rooms
        if not isinstance(rooms_outcome, Present) or not isinstance(
            rooms_outcome.value.value, RoomCount
        ):
            raise TypeError("present rooms must contain canonical RoomCount")
        return AreaRoomsBlockingKey(
            rule.rule_id,
            rule.rule_version,
            area_outcome.value.value,
            rooms_outcome.value.value,
        )
    location_outcome = listing.location_text
    if not isinstance(location_outcome, Present) or not isinstance(
        location_outcome.value.value, LocationText
    ):
        raise TypeError("present location_text must contain canonical LocationText")
    return AreaLocationTextBlockingKey(
        rule.rule_id,
        rule.rule_version,
        area_outcome.value.value,
        location_outcome.value.value,
    )


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


def _identity_for_member_pair(
    first: ObservationKey,
    second: ObservationKey,
) -> DuplicateCandidateIdentity:
    pair = PublicationPair(first.reference, second.reference)
    if first.reference == pair.left:
        left_key, right_key = first, second
    else:
        left_key, right_key = second, first
    return DuplicateCandidateIdentity(
        pair,
        left_key,
        right_key,
        PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION,
    )


def generate_duplicate_candidates(
    current_observations: tuple[PublicationObservation, ...],
    configuration: DuplicateCandidateGenerationConfiguration,
) -> DuplicateCandidateGenerationOutcome:
    """Generate a deterministic bounded exact-key union without assessment or I/O."""

    observations, conflicts = _validated_observations_and_conflicts(current_observations)
    conflicts.extend(_configuration_conflicts(configuration))
    if conflicts:
        return DuplicateCandidateGenerationFailure(_canonical_conflicts(conflicts))

    policy = configuration.policy
    limit = configuration.bucket_pair_limit
    memberships: dict[DuplicateBlockingKey, list[ObservationKey]] = {}
    non_participations: list[BlockingNonParticipation] = []
    for observation in observations:
        for rule in policy.rules:
            projection = _project_rule(observation, rule)
            if isinstance(projection, BlockingNonParticipation):
                non_participations.append(projection)
            else:
                memberships.setdefault(projection, []).append(observation.key)

    matches_by_identity: dict[
        DuplicateCandidateIdentity, list[DuplicateCandidateBlockingMatch]
    ] = {}
    oversized_buckets: list[OversizedBucket] = []
    for key in sorted(memberships, key=_blocking_key_sort_key):
        member_keys = tuple(sorted(memberships[key], key=_observation_key_sort_key))
        bucket = BlockingBucket(key, member_keys)
        member_count = len(bucket.member_keys)
        prospective_pair_count = member_count * (member_count - 1) // 2
        if prospective_pair_count > limit.value:
            oversized_buckets.append(
                OversizedBucket(
                    bucket.key,
                    bucket.member_keys,
                    prospective_pair_count,
                    DuplicateCandidateReasonCode(_OVERSIZED_REASON),
                )
            )
            continue
        for left_index in range(member_count):
            for right_index in range(left_index + 1, member_count):
                identity = _identity_for_member_pair(
                    bucket.member_keys[left_index],
                    bucket.member_keys[right_index],
                )
                matches_by_identity.setdefault(identity, []).append(
                    DuplicateCandidateBlockingMatch(bucket.key)
                )

    candidates = tuple(
        sorted(
            (
                DuplicateCandidate(identity, tuple(matches))
                for identity, matches in matches_by_identity.items()
            ),
            key=_candidate_sort_key,
        )
    )
    generation_identity = DuplicateCandidateGenerationIdentity(
        policy.version,
        limit,
        tuple(observation.key for observation in observations),
    )
    result = DuplicateCandidateGenerationResult(
        identity=generation_identity,
        policy=policy,
        candidates=candidates,
        non_participations=tuple(non_participations),
        oversized_buckets=tuple(oversized_buckets),
    )
    return DuplicateCandidateGenerationSuccess(result)


__all__ = [
    "AreaLocationTextBlockingKey",
    "AreaRoomsBlockingKey",
    "BlockingBucket",
    "BlockingComponentNonParticipation",
    "BlockingComponentState",
    "BlockingNonParticipation",
    "BucketPairLimit",
    "CandidateBlockingField",
    "DuplicateBlockingKey",
    "DuplicateCandidate",
    "DuplicateCandidateBlockingMatch",
    "DuplicateCandidateGenerationConfiguration",
    "DuplicateCandidateGenerationConflict",
    "DuplicateCandidateGenerationConflictCategory",
    "DuplicateCandidateGenerationConflictCode",
    "DuplicateCandidateGenerationConflictSubject",
    "DuplicateCandidateGenerationFailure",
    "DuplicateCandidateGenerationIdentity",
    "DuplicateCandidateGenerationOutcome",
    "DuplicateCandidateGenerationResult",
    "DuplicateCandidateGenerationSuccess",
    "DuplicateCandidateIdentity",
    "DuplicateCandidatePolicy",
    "DuplicateCandidatePolicyVersion",
    "DuplicateCandidateReasonCode",
    "DuplicateCandidateRule",
    "DuplicateCandidateRuleId",
    "DuplicateCandidateRuleVersion",
    "DuplicatePublicationRefSubject",
    "InvalidBucketPairLimitSubject",
    "OversizedBucket",
    "PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1",
    "PUBLICATION_DUPLICATE_CANDIDATE_POLICY_V1_VERSION",
    "UnsupportedObservationSubject",
    "generate_duplicate_candidates",
]
