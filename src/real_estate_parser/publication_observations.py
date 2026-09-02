"""Pure observation history and publication-change comparison contracts."""

from __future__ import annotations

from dataclasses import dataclass
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
    NormalizedListing,
    ObservedAt,
    Present,
    RoomCount,
    SourceUrl,
    TracedValue,
    Unsupported,
    UnsupportedProvenance,
    ValueProvenance,
)
from real_estate_parser.source_batch import PublicationRef

type ComparableFieldName = Literal[
    "source_url",
    "location_text",
    "price_amount",
    "currency",
    "total_area",
    "rooms",
]
type CanonicalComparableValue = SourceUrl | LocationText | MoneyAmount | Currency | Area | RoomCount
type FieldProvenance = ValueProvenance | MissingProvenance | UnsupportedProvenance
type ObservationConflictCategory = Literal["OBSERVATION_CONFLICT"]
type ObservationConflictCode = Literal[
    "stream_reference_mismatch",
    "timestamp_content_conflict",
    "out_of_order_observation",
    "comparison_policy_mismatch",
    "expected_revision_mismatch",
]

_PUBLICATION_CHANGE_FIELDS: tuple[ComparableFieldName, ...] = (
    "source_url",
    "location_text",
    "price_amount",
    "currency",
    "total_area",
    "rooms",
)


def _validate_opaque_code(value: str, label: str) -> None:
    if (
        not 1 <= len(value) <= 128
        or not value.isascii()
        or any(not 0x21 <= ord(character) <= 0x7E for character in value)
    ):
        raise ValueError(f"invalid {label}")


@dataclass(frozen=True, slots=True)
class ComparisonPolicyVersion:
    """Stable opaque identifier for publication comparison semantics."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "comparison policy version")


@dataclass(frozen=True, slots=True)
class AvailabilityRuleVersion:
    """Stable opaque identifier for one availability interpretation rule."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "availability rule version")


@dataclass(frozen=True, slots=True)
class SourceReportedCause:
    """An opaque cause claimed explicitly by the source, not an inferred fact."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "source-reported cause")


@dataclass(frozen=True, slots=True)
class ConclusiveUnavailableOutcomeCode:
    """A versioned targeted-check outcome known to mean unavailable."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_code(self.value, "conclusive unavailable outcome code")


PUBLICATION_CHANGE_POLICY_V1_VERSION = ComparisonPolicyVersion("publication-change-policy@1")


@dataclass(frozen=True, slots=True)
class ComparisonPolicy:
    """An immutable supported publication-change policy."""

    version: ComparisonPolicyVersion
    field_order: tuple[ComparableFieldName, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.field_order, tuple):
            raise TypeError("comparison policy field order must be a tuple")
        if self.version != PUBLICATION_CHANGE_POLICY_V1_VERSION:
            raise ValueError("unsupported comparison policy version")
        if self.field_order != _PUBLICATION_CHANGE_FIELDS:
            raise ValueError("invalid field order for publication-change-policy@1")


PUBLICATION_CHANGE_POLICY_V1 = ComparisonPolicy(
    version=PUBLICATION_CHANGE_POLICY_V1_VERSION,
    field_order=_PUBLICATION_CHANGE_FIELDS,
)


@dataclass(frozen=True, slots=True)
class ObservationKey:
    """Deterministic identity of one observation of one publication."""

    reference: PublicationRef
    observed_at: ObservedAt


@dataclass(frozen=True, slots=True)
class DirectSourceStateEvidence:
    """A direct state reported by the source for the exact publication."""

    raw_source_state: str
    source_field: str
    adapter_rule_version: AvailabilityRuleVersion
    source_reported_cause: SourceReportedCause | None = None

    def __post_init__(self) -> None:
        if not self.raw_source_state:
            raise ValueError("raw source state must be non-empty")
        if not self.source_field:
            raise ValueError("source field must be non-empty")


@dataclass(frozen=True, slots=True)
class TargetedPublicationCheckEvidence:
    """A conclusive versioned check addressed to the exact publication."""

    outcome_code: ConclusiveUnavailableOutcomeCode
    check_rule_version: AvailabilityRuleVersion
    adapter_rule_version: AvailabilityRuleVersion


type UnavailableEvidence = DirectSourceStateEvidence | TargetedPublicationCheckEvidence


def _listing_provenances(listing: NormalizedListing) -> tuple[FieldProvenance, ...]:
    optional_outcomes: tuple[FieldOutcome[object], ...] = (
        listing.location_text,
        listing.price_amount,
        listing.currency,
        listing.total_area,
        listing.rooms,
    )
    optional_provenances: list[FieldProvenance] = []
    for outcome in optional_outcomes:
        if isinstance(outcome, Present):
            optional_provenances.append(outcome.value.provenance)
        elif isinstance(outcome, (Missing, Unsupported)):
            optional_provenances.append(outcome.provenance)
        else:
            raise TypeError("listing contains an unsupported field outcome")
    return (
        listing.reference.provenance,
        listing.source_url.provenance,
        listing.observed_at.provenance,
        *optional_provenances,
    )


@dataclass(frozen=True, slots=True)
class AvailableObservation:
    """One complete normalized listing proven available at its key."""

    key: ObservationKey
    listing: NormalizedListing

    def __post_init__(self) -> None:
        if not isinstance(self.listing, NormalizedListing):
            raise TypeError("available observation requires a normalized listing")
        if self.listing.reference.value != self.key.reference:
            raise ValueError("listing reference does not match observation key")
        if self.listing.observed_at.value != self.key.observed_at:
            raise ValueError("listing observed_at does not match observation key")
        for provenance in _listing_provenances(self.listing):
            if (
                provenance.source_id != self.key.reference.source_id
                or provenance.publication_id != self.key.reference.publication_id
            ):
                raise ValueError("field provenance reference does not match observation key")
            if provenance.observed_at != self.key.observed_at:
                raise ValueError("field provenance observed_at does not match observation key")


@dataclass(frozen=True, slots=True)
class UnavailableObservation:
    """One publication proven unavailable by sufficient explicit evidence."""

    key: ObservationKey
    evidence: UnavailableEvidence

    def __post_init__(self) -> None:
        if not isinstance(
            self.evidence,
            (DirectSourceStateEvidence, TargetedPublicationCheckEvidence),
        ):
            raise TypeError("unsupported unavailable evidence")


type PublicationObservation = AvailableObservation | UnavailableObservation


@dataclass(frozen=True, slots=True)
class PublicationObservationHistory:
    """Strictly ordered observations for one publication and one policy version."""

    reference: PublicationRef
    comparison_policy_version: ComparisonPolicyVersion
    observations: tuple[PublicationObservation, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.observations, tuple):
            raise TypeError("history observations must be a tuple")
        previous_at: ObservedAt | None = None
        for observation in self.observations:
            if not isinstance(observation, (AvailableObservation, UnavailableObservation)):
                raise TypeError("history contains an unsupported observation")
            if observation.key.reference != self.reference:
                raise ValueError("history contains another publication reference")
            if previous_at is not None and observation.key.observed_at.value <= previous_at.value:
                raise ValueError("history observations must be strictly increasing")
            previous_at = observation.key.observed_at


@dataclass(frozen=True, slots=True)
class PresentValue:
    """Canonical projection of one supported comparable field."""

    value: CanonicalComparableValue


@dataclass(frozen=True, slots=True)
class MissingValue:
    """Canonical projection of one missing comparable field."""


@dataclass(frozen=True, slots=True)
class UnsupportedValue:
    """Canonical projection of one unsupported comparable field."""

    reason_code: str

    def __post_init__(self) -> None:
        if not self.reason_code or not self.reason_code.isascii():
            raise ValueError("invalid unsupported reason code")


type CanonicalFieldOutcome = PresentValue | MissingValue | UnsupportedValue


@dataclass(frozen=True, slots=True)
class FieldSnapshot:
    """Canonical field outcome and its complete evidence."""

    canonical: CanonicalFieldOutcome
    provenance: FieldProvenance

    def __post_init__(self) -> None:
        if isinstance(self.canonical, PresentValue):
            if not isinstance(self.provenance, ValueProvenance):
                raise ValueError("present canonical value requires value provenance")
        elif isinstance(self.canonical, MissingValue):
            if not isinstance(self.provenance, MissingProvenance):
                raise ValueError("missing canonical value requires missing provenance")
        elif isinstance(self.canonical, UnsupportedValue):
            if not isinstance(self.provenance, UnsupportedProvenance):
                raise ValueError("unsupported canonical value requires unsupported provenance")
            if self.canonical.reason_code != self.provenance.reason_code:
                raise ValueError("unsupported reason code does not match provenance")
        else:
            raise TypeError("unsupported canonical field outcome")


def _raw_value(provenance: FieldProvenance) -> str | None:
    if isinstance(provenance, MissingProvenance):
        return None
    return provenance.raw_value


def _comparable_provenance(provenance: FieldProvenance) -> tuple[object, ...]:
    return (
        provenance.source_id,
        provenance.publication_id,
        provenance.input_path,
        provenance.source_field,
        provenance.normalization_rule_version,
    )


class FieldDeltaKind(StrEnum):
    """Mutually exclusive classification of one comparable field delta."""

    SUBSTANTIVE = "SUBSTANTIVE"
    SOURCE_REPRESENTATION_ONLY = "SOURCE_REPRESENTATION_ONLY"
    PROVENANCE_REFRESH = "PROVENANCE_REFRESH"


@dataclass(frozen=True, slots=True)
class FieldDelta:
    """At most one classified delta for one policy field."""

    field: ComparableFieldName
    kind: FieldDeltaKind
    before: FieldSnapshot
    after: FieldSnapshot

    def __post_init__(self) -> None:
        if self.field not in _PUBLICATION_CHANGE_FIELDS:
            raise ValueError("unsupported comparable field")
        if self.before.canonical != self.after.canonical:
            expected_kind = FieldDeltaKind.SUBSTANTIVE
        elif _raw_value(self.before.provenance) != _raw_value(self.after.provenance):
            expected_kind = FieldDeltaKind.SOURCE_REPRESENTATION_ONLY
        elif _comparable_provenance(self.before.provenance) != _comparable_provenance(
            self.after.provenance
        ):
            expected_kind = FieldDeltaKind.PROVENANCE_REFRESH
        else:
            raise ValueError("field delta requires a classified difference")
        if self.kind is not expected_kind:
            raise ValueError("field delta kind does not match snapshots")


@dataclass(frozen=True, slots=True)
class ConfirmedUnavailable:
    """A consecutive available-to-unavailable transition."""

    before: AvailableObservation
    after: UnavailableObservation

    def __post_init__(self) -> None:
        _validate_consecutive_keys(self.before.key, self.after.key)


@dataclass(frozen=True, slots=True)
class Reappeared:
    """A consecutive unavailable-to-available transition."""

    before: UnavailableObservation
    after: AvailableObservation

    def __post_init__(self) -> None:
        _validate_consecutive_keys(self.before.key, self.after.key)


type AvailabilityChange = ConfirmedUnavailable | Reappeared


@dataclass(frozen=True, slots=True)
class AvailabilityEvidenceDelta:
    """Different evidence across consecutive unavailable observations."""

    before: UnavailableEvidence
    after: UnavailableEvidence

    def __post_init__(self) -> None:
        if self.before == self.after:
            raise ValueError("availability evidence delta requires a difference")


@dataclass(frozen=True, slots=True)
class ChangeSet:
    """Deterministic changes between exactly two consecutive observations."""

    policy_version: ComparisonPolicyVersion
    from_key: ObservationKey
    to_key: ObservationKey
    availability_change: AvailabilityChange | None = None
    field_deltas: tuple[FieldDelta, ...] = ()
    availability_evidence_delta: AvailabilityEvidenceDelta | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.field_deltas, tuple):
            raise TypeError("field deltas must be a tuple")
        _validate_consecutive_keys(self.from_key, self.to_key)
        expected_order = {field: index for index, field in enumerate(_PUBLICATION_CHANGE_FIELDS)}
        positions = tuple(expected_order[delta.field] for delta in self.field_deltas)
        if positions != tuple(sorted(set(positions))):
            raise ValueError("field deltas must be unique and in policy order")
        if self.availability_change is not None:
            if (
                self.availability_change.before.key != self.from_key
                or self.availability_change.after.key != self.to_key
            ):
                raise ValueError("availability change keys do not match change set")
            if self.field_deltas or self.availability_evidence_delta is not None:
                raise ValueError("availability transition cannot contain field or evidence deltas")
        if self.field_deltas and self.availability_evidence_delta is not None:
            raise ValueError("field and availability evidence deltas cannot be combined")


@dataclass(frozen=True, slots=True)
class ObservationConflict:
    """Stable conflict without transport-specific location or exception text."""

    category: ObservationConflictCategory
    code: ObservationConflictCode
    subject: PublicationRef | ObservationKey

    def __post_init__(self) -> None:
        if self.category != "OBSERVATION_CONFLICT":
            raise ValueError("invalid observation conflict category")


class ObservationAppendDisposition(StrEnum):
    """Successful disposition of one append attempt."""

    APPENDED = "APPENDED"
    REPLAYED = "REPLAYED"


@dataclass(frozen=True, slots=True)
class ObservationAppendSuccess:
    """A complete new history or an idempotent replay of the original history."""

    disposition: ObservationAppendDisposition
    history: PublicationObservationHistory
    change_set: ChangeSet | None = None

    def __post_init__(self) -> None:
        if self.disposition is ObservationAppendDisposition.REPLAYED:
            if self.change_set is not None:
                raise ValueError("replayed observation cannot create a change set")
            if not self.history.observations:
                raise ValueError("replayed observation requires a non-empty history")
            return
        if not self.history.observations:
            raise ValueError("appended observation requires a non-empty history")
        if self.change_set is None:
            if len(self.history.observations) != 1:
                raise ValueError("only the first appended observation omits a change set")
            return
        if self.change_set.policy_version != self.history.comparison_policy_version:
            raise ValueError("change set policy does not match appended history")
        if len(self.history.observations) < 2:
            raise ValueError("change set requires an observation predecessor")
        if (
            self.change_set.from_key != self.history.observations[-2].key
            or self.change_set.to_key != self.history.observations[-1].key
        ):
            raise ValueError("change set does not match appended history tail")


@dataclass(frozen=True, slots=True)
class ObservationAppendFailure:
    """Atomic failure carrying conflicts and no partial history or changes."""

    conflicts: tuple[ObservationConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple):
            raise TypeError("observation conflicts must be a tuple")
        if not self.conflicts:
            raise ValueError("failed observation append must contain a conflict")
        if any(not isinstance(conflict, ObservationConflict) for conflict in self.conflicts):
            raise TypeError("observation append failure contains an unsupported conflict")


type ObservationAppendResult = ObservationAppendSuccess | ObservationAppendFailure


def _validate_consecutive_keys(previous: ObservationKey, current: ObservationKey) -> None:
    if previous.reference != current.reference:
        raise ValueError("consecutive observation references must match")
    if current.observed_at.value <= previous.observed_at.value:
        raise ValueError("consecutive observation timestamps must strictly increase")


def _conflict(
    code: ObservationConflictCode,
    subject: PublicationRef | ObservationKey,
) -> ObservationConflict:
    return ObservationConflict(category="OBSERVATION_CONFLICT", code=code, subject=subject)


def _field_snapshot_from_traced(
    traced: TracedValue[CanonicalComparableValue],
) -> FieldSnapshot:
    return FieldSnapshot(canonical=PresentValue(traced.value), provenance=traced.provenance)


def _field_snapshot_from_outcome(
    outcome: FieldOutcome[CanonicalComparableValue],
) -> FieldSnapshot:
    if isinstance(outcome, Present):
        return _field_snapshot_from_traced(outcome.value)
    if isinstance(outcome, Missing):
        return FieldSnapshot(canonical=MissingValue(), provenance=outcome.provenance)
    return FieldSnapshot(
        canonical=UnsupportedValue(outcome.provenance.reason_code),
        provenance=outcome.provenance,
    )


def _listing_field_snapshot(
    listing: NormalizedListing,
    field: ComparableFieldName,
) -> FieldSnapshot:
    if field == "source_url":
        return _field_snapshot_from_traced(listing.source_url)
    if field == "location_text":
        return _field_snapshot_from_outcome(listing.location_text)
    if field == "price_amount":
        return _field_snapshot_from_outcome(listing.price_amount)
    if field == "currency":
        return _field_snapshot_from_outcome(listing.currency)
    if field == "total_area":
        return _field_snapshot_from_outcome(listing.total_area)
    return _field_snapshot_from_outcome(listing.rooms)


def _field_delta(
    field: ComparableFieldName,
    before: FieldSnapshot,
    after: FieldSnapshot,
) -> FieldDelta | None:
    if before.canonical != after.canonical:
        kind = FieldDeltaKind.SUBSTANTIVE
    elif _raw_value(before.provenance) != _raw_value(after.provenance):
        kind = FieldDeltaKind.SOURCE_REPRESENTATION_ONLY
    elif _comparable_provenance(before.provenance) != _comparable_provenance(after.provenance):
        kind = FieldDeltaKind.PROVENANCE_REFRESH
    else:
        return None
    return FieldDelta(field=field, kind=kind, before=before, after=after)


def compare_consecutive_observations(
    previous: PublicationObservation,
    current: PublicationObservation,
    policy: ComparisonPolicy = PUBLICATION_CHANGE_POLICY_V1,
) -> ChangeSet | ObservationConflict:
    """Compare two strictly consecutive observations with no I/O or hidden state."""

    if previous.key.reference != current.key.reference:
        return _conflict("stream_reference_mismatch", current.key)
    if current.key.observed_at.value < previous.key.observed_at.value:
        return _conflict("out_of_order_observation", current.key)
    if current.key.observed_at == previous.key.observed_at:
        return _conflict("timestamp_content_conflict", current.key)

    availability_change: AvailabilityChange | None = None
    field_deltas: tuple[FieldDelta, ...] = ()
    evidence_delta: AvailabilityEvidenceDelta | None = None

    if isinstance(previous, AvailableObservation) and isinstance(current, AvailableObservation):
        deltas: list[FieldDelta] = []
        for field in policy.field_order:
            delta = _field_delta(
                field,
                _listing_field_snapshot(previous.listing, field),
                _listing_field_snapshot(current.listing, field),
            )
            if delta is not None:
                deltas.append(delta)
        field_deltas = tuple(deltas)
    elif isinstance(previous, AvailableObservation) and isinstance(current, UnavailableObservation):
        availability_change = ConfirmedUnavailable(previous, current)
    elif isinstance(previous, UnavailableObservation) and isinstance(current, AvailableObservation):
        availability_change = Reappeared(previous, current)
    else:
        assert isinstance(previous, UnavailableObservation)
        assert isinstance(current, UnavailableObservation)
        if previous.evidence != current.evidence:
            evidence_delta = AvailabilityEvidenceDelta(previous.evidence, current.evidence)

    return ChangeSet(
        policy_version=policy.version,
        from_key=previous.key,
        to_key=current.key,
        availability_change=availability_change,
        field_deltas=field_deltas,
        availability_evidence_delta=evidence_delta,
    )


def append_observation(
    history: PublicationObservationHistory,
    candidate: PublicationObservation,
    policy: ComparisonPolicy = PUBLICATION_CHANGE_POLICY_V1,
) -> ObservationAppendResult:
    """Atomically append one new observation or return an exact replay/conflict."""

    if history.comparison_policy_version != policy.version:
        return ObservationAppendFailure(
            conflicts=(_conflict("comparison_policy_mismatch", history.reference),)
        )
    if candidate.key.reference != history.reference:
        return ObservationAppendFailure(
            conflicts=(_conflict("stream_reference_mismatch", candidate.key),)
        )

    for accepted in history.observations:
        if accepted.key == candidate.key:
            if accepted == candidate:
                return ObservationAppendSuccess(
                    disposition=ObservationAppendDisposition.REPLAYED,
                    history=history,
                )
            return ObservationAppendFailure(
                conflicts=(_conflict("timestamp_content_conflict", candidate.key),)
            )

    if history.observations:
        predecessor = history.observations[-1]
        if candidate.key.observed_at.value < predecessor.key.observed_at.value:
            return ObservationAppendFailure(
                conflicts=(_conflict("out_of_order_observation", candidate.key),)
            )
        comparison = compare_consecutive_observations(predecessor, candidate, policy)
        if isinstance(comparison, ObservationConflict):
            return ObservationAppendFailure(conflicts=(comparison,))
        change_set: ChangeSet | None = comparison
    else:
        change_set = None

    appended_history = PublicationObservationHistory(
        reference=history.reference,
        comparison_policy_version=history.comparison_policy_version,
        observations=(*history.observations, candidate),
    )
    return ObservationAppendSuccess(
        disposition=ObservationAppendDisposition.APPENDED,
        history=appended_history,
        change_set=change_set,
    )


__all__ = [
    "AvailabilityChange",
    "AvailabilityEvidenceDelta",
    "AvailabilityRuleVersion",
    "AvailableObservation",
    "CanonicalFieldOutcome",
    "ChangeSet",
    "ComparableFieldName",
    "ComparisonPolicy",
    "ComparisonPolicyVersion",
    "ConclusiveUnavailableOutcomeCode",
    "ConfirmedUnavailable",
    "DirectSourceStateEvidence",
    "FieldDelta",
    "FieldDeltaKind",
    "FieldSnapshot",
    "MissingValue",
    "ObservationAppendDisposition",
    "ObservationAppendFailure",
    "ObservationAppendResult",
    "ObservationAppendSuccess",
    "ObservationConflict",
    "ObservationConflictCategory",
    "ObservationConflictCode",
    "ObservationKey",
    "PUBLICATION_CHANGE_POLICY_V1",
    "PUBLICATION_CHANGE_POLICY_V1_VERSION",
    "PresentValue",
    "PublicationObservation",
    "PublicationObservationHistory",
    "Reappeared",
    "SourceReportedCause",
    "TargetedPublicationCheckEvidence",
    "UnavailableEvidence",
    "UnavailableObservation",
    "UnsupportedValue",
    "append_observation",
    "compare_consecutive_observations",
]
