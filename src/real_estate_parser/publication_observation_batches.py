"""Pure atomic composition of observations across publication histories."""

from __future__ import annotations

from dataclasses import dataclass

from real_estate_parser.publication_observations import (
    AvailableObservation,
    ChangeSet,
    ComparisonPolicy,
    ObservationAppendDisposition,
    ObservationAppendFailure,
    ObservationAppendSuccess,
    ObservationConflict,
    ObservationKey,
    PublicationObservation,
    PublicationObservationHistory,
    UnavailableObservation,
    append_observation,
)
from real_estate_parser.source_batch import PublicationRef


def _reference_sort_key(reference: PublicationRef) -> tuple[str, str]:
    return reference.source_id.value, reference.publication_id.value


def _observation_key_sort_key(key: ObservationKey) -> tuple[str, str, str]:
    return (*_reference_sort_key(key.reference), key.observed_at.to_rfc3339())


def _conflict_sort_key(conflict: ObservationConflict) -> tuple[str, str, int, str, str, str]:
    if isinstance(conflict.subject, ObservationKey):
        reference = conflict.subject.reference
        has_observed_at = 1
        observed_at = conflict.subject.observed_at.to_rfc3339()
    else:
        reference = conflict.subject
        has_observed_at = 0
        observed_at = ""
    return (
        *_reference_sort_key(reference),
        has_observed_at,
        observed_at,
        conflict.category,
        conflict.code,
    )


@dataclass(frozen=True, slots=True)
class PublicationObservationHistories:
    """Canonical immutable histories with at most one stream per reference."""

    histories: tuple[PublicationObservationHistory, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.histories, tuple):
            raise TypeError("publication observation histories must be a tuple")
        references: set[PublicationRef] = set()
        for history in self.histories:
            if not isinstance(history, PublicationObservationHistory):
                raise TypeError("histories contain an unsupported history")
            if history.reference in references:
                raise ValueError("histories contain a duplicate publication reference")
            references.add(history.reference)
        canonical = tuple(
            sorted(self.histories, key=lambda history: _reference_sort_key(history.reference))
        )
        if canonical != self.histories:
            object.__setattr__(self, "histories", canonical)


@dataclass(frozen=True, slots=True)
class ObservationBatchItemOutcome:
    """One canonical outcome for one unique successful candidate key."""

    key: ObservationKey
    disposition: ObservationAppendDisposition
    change_set: ChangeSet | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, ObservationAppendDisposition):
            raise TypeError("batch item disposition must be an observation append disposition")
        if (
            self.disposition is ObservationAppendDisposition.REPLAYED
            and self.change_set is not None
        ):
            raise ValueError("replayed batch item cannot contain a change set")
        if self.change_set is not None and self.change_set.to_key != self.key:
            raise ValueError("batch item change set does not match its observation key")


@dataclass(frozen=True, slots=True)
class ObservationBatchAppendSuccess:
    """Complete atomic histories and outcomes for a conflict-free batch."""

    histories: PublicationObservationHistories
    outcomes: tuple[ObservationBatchItemOutcome, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.histories, PublicationObservationHistories):
            raise TypeError("batch success requires publication observation histories")
        if not isinstance(self.outcomes, tuple):
            raise TypeError("batch item outcomes must be a tuple")
        if not self.outcomes:
            raise ValueError("batch success must contain an item outcome")
        if any(not isinstance(outcome, ObservationBatchItemOutcome) for outcome in self.outcomes):
            raise TypeError("batch success contains an unsupported item outcome")
        keys = tuple(outcome.key for outcome in self.outcomes)
        if len(set(keys)) != len(keys):
            raise ValueError("batch item outcomes must have unique observation keys")
        if keys != tuple(sorted(keys, key=_observation_key_sort_key)):
            raise ValueError("batch item outcomes must be in canonical order")


@dataclass(frozen=True, slots=True)
class ObservationBatchAppendFailure:
    """Global atomic failure with conflicts and no partial success state."""

    conflicts: tuple[ObservationConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple):
            raise TypeError("batch conflicts must be a tuple")
        if not self.conflicts:
            raise ValueError("failed observation batch must contain a conflict")
        if any(not isinstance(conflict, ObservationConflict) for conflict in self.conflicts):
            raise TypeError("batch failure contains an unsupported conflict")
        if len(set(self.conflicts)) != len(self.conflicts):
            raise ValueError("batch conflicts must be unique")
        if self.conflicts != tuple(sorted(self.conflicts, key=_conflict_sort_key)):
            raise ValueError("batch conflicts must be in canonical order")


type ObservationBatchAppendResult = ObservationBatchAppendSuccess | ObservationBatchAppendFailure


def _timestamp_content_conflict(key: ObservationKey) -> ObservationConflict:
    return ObservationConflict(
        category="OBSERVATION_CONFLICT",
        code="timestamp_content_conflict",
        subject=key,
    )


def _canonical_conflicts(
    conflicts: list[ObservationConflict],
) -> tuple[ObservationConflict, ...]:
    unique: list[ObservationConflict] = []
    for conflict in conflicts:
        if conflict not in unique:
            unique.append(conflict)
    return tuple(sorted(unique, key=_conflict_sort_key))


def append_observation_batch(
    histories: PublicationObservationHistories,
    candidates: tuple[PublicationObservation, ...],
    policy: ComparisonPolicy,
) -> ObservationBatchAppendResult:
    """Atomically compose one non-empty candidate batch across independent streams."""

    if not isinstance(histories, PublicationObservationHistories):
        raise TypeError("observation batch requires publication observation histories")
    if not isinstance(candidates, tuple):
        raise TypeError("observation batch candidates must be a tuple")
    if not candidates:
        raise ValueError("observation batch candidates must be non-empty")
    if not isinstance(policy, ComparisonPolicy):
        raise TypeError("observation batch requires a comparison policy")

    candidates_by_key: dict[ObservationKey, list[PublicationObservation]] = {}
    for candidate in candidates:
        if not isinstance(candidate, (AvailableObservation, UnavailableObservation)):
            raise TypeError("observation batch contains an unsupported candidate")
        variants = candidates_by_key.setdefault(candidate.key, [])
        if candidate not in variants:
            variants.append(candidate)

    conflicts: list[ObservationConflict] = []
    working_by_reference = {history.reference: history for history in histories.histories}
    for history in histories.histories:
        if history.comparison_policy_version != policy.version:
            conflicts.append(
                ObservationConflict(
                    category="OBSERVATION_CONFLICT",
                    code="comparison_policy_mismatch",
                    subject=history.reference,
                )
            )

    outcomes: list[ObservationBatchItemOutcome] = []
    for key in sorted(candidates_by_key, key=_observation_key_sort_key):
        variants = candidates_by_key[key]
        if len(variants) > 1:
            conflicts.append(_timestamp_content_conflict(key))
            continue

        current_history = working_by_reference.get(key.reference)
        if current_history is None:
            current_history = PublicationObservationHistory(
                reference=key.reference,
                comparison_policy_version=policy.version,
            )
        result = append_observation(current_history, variants[0], policy)
        if isinstance(result, ObservationAppendFailure):
            conflicts.extend(result.conflicts)
            continue
        assert isinstance(result, ObservationAppendSuccess)
        working_by_reference[key.reference] = result.history
        outcomes.append(
            ObservationBatchItemOutcome(
                key=key,
                disposition=result.disposition,
                change_set=result.change_set,
            )
        )

    if conflicts:
        return ObservationBatchAppendFailure(_canonical_conflicts(conflicts))

    return ObservationBatchAppendSuccess(
        histories=PublicationObservationHistories(tuple(working_by_reference.values())),
        outcomes=tuple(outcomes),
    )


__all__ = [
    "ObservationBatchAppendFailure",
    "ObservationBatchAppendResult",
    "ObservationBatchAppendSuccess",
    "ObservationBatchItemOutcome",
    "PublicationObservationHistories",
    "append_observation_batch",
]
