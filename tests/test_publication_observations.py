from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from typing import Any, Literal

import pytest

from real_estate_parser import (
    PUBLICATION_CHANGE_POLICY_V1,
    PUBLICATION_CHANGE_POLICY_V1_VERSION,
    Area,
    AvailabilityEvidenceDelta,
    AvailabilityRuleVersion,
    AvailableObservation,
    ChangeSet,
    ComparisonPolicy,
    ComparisonPolicyVersion,
    ConclusiveUnavailableOutcomeCode,
    ConfirmedUnavailable,
    Currency,
    DirectSourceStateEvidence,
    FieldDelta,
    FieldDeltaKind,
    FieldSnapshot,
    InputLocation,
    LocationText,
    Missing,
    MissingProvenance,
    MissingValue,
    MoneyAmount,
    NormalizationRuleVersion,
    NormalizedListing,
    ObservationAppendDisposition,
    ObservationAppendFailure,
    ObservationAppendSuccess,
    ObservationConflict,
    ObservationKey,
    ObservedAt,
    Present,
    PresentValue,
    PublicationId,
    PublicationObservationHistory,
    PublicationRef,
    Reappeared,
    RoomCount,
    SourceId,
    SourceReportedCause,
    SourceUrl,
    TargetedPublicationCheckEvidence,
    TracedValue,
    UnavailableObservation,
    Unsupported,
    UnsupportedProvenance,
    UnsupportedValue,
    ValueProvenance,
    append_observation,
    compare_consecutive_observations,
)

REFERENCE = PublicationRef(SourceId("fixture_portal"), PublicationId("demo-016"))
OTHER_REFERENCE = PublicationRef(SourceId("fixture_portal"), PublicationId("other-016"))
RULE = NormalizationRuleVersion("fixture-field@1")
AVAILABILITY_RULE = AvailabilityRuleVersion("fixture-availability@1")


def _at(hour: int, minute: int = 0) -> ObservedAt:
    return ObservedAt(datetime(2026, 9, 2, hour, minute, tzinfo=UTC))


def _location(source_field: str) -> InputLocation:
    return InputLocation("listings", 0, (source_field,))


def _value_provenance(
    reference: PublicationRef,
    observed_at: ObservedAt,
    source_field: str,
    raw_value: str,
    *,
    rule: NormalizationRuleVersion = RULE,
) -> ValueProvenance:
    return ValueProvenance(
        source_id=reference.source_id,
        publication_id=reference.publication_id,
        input_path=_location(source_field),
        source_field=source_field,
        raw_value=raw_value,
        observed_at=observed_at,
        normalization_rule_version=rule,
    )


def _missing_provenance(
    reference: PublicationRef,
    observed_at: ObservedAt,
    source_field: str,
    *,
    rule: NormalizationRuleVersion = RULE,
) -> MissingProvenance:
    return MissingProvenance(
        source_id=reference.source_id,
        publication_id=reference.publication_id,
        input_path=_location(source_field),
        source_field=source_field,
        observed_at=observed_at,
        normalization_rule_version=rule,
    )


def _present[T](
    value: T,
    reference: PublicationRef,
    observed_at: ObservedAt,
    source_field: str,
    raw_value: str,
    *,
    rule: NormalizationRuleVersion = RULE,
) -> Present[T]:
    return Present(
        TracedValue(
            value,
            _value_provenance(
                reference,
                observed_at,
                source_field,
                raw_value,
                rule=rule,
            ),
        )
    )


def _missing(
    reference: PublicationRef,
    observed_at: ObservedAt,
    source_field: str,
    *,
    rule: NormalizationRuleVersion = RULE,
) -> Missing:
    return Missing(_missing_provenance(reference, observed_at, source_field, rule=rule))


def _unsupported(
    reference: PublicationRef,
    observed_at: ObservedAt,
    source_field: str,
    raw_value: str,
    reason_code: str,
    *,
    rule: NormalizationRuleVersion = RULE,
) -> Unsupported:
    return Unsupported(
        UnsupportedProvenance(
            source_id=reference.source_id,
            publication_id=reference.publication_id,
            input_path=_location(source_field),
            source_field=source_field,
            raw_value=raw_value,
            observed_at=observed_at,
            normalization_rule_version=rule,
            reason_code=reason_code,
        )
    )


def _listing(
    observed_at: ObservedAt,
    *,
    reference: PublicationRef = REFERENCE,
    source_url: TracedValue[SourceUrl] | None = None,
    location_text: Present[LocationText] | Missing | Unsupported | None = None,
    price_amount: Present[MoneyAmount] | Missing | Unsupported | None = None,
    currency: Present[Currency] | Missing | Unsupported | None = None,
    total_area: Present[Area] | Missing | Unsupported | None = None,
    rooms: Present[RoomCount] | Missing | Unsupported | None = None,
) -> NormalizedListing:
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
        source_url=source_url
        or TracedValue(
            SourceUrl("https://listings.fixture.example/offers/demo-016"),
            _value_provenance(
                reference,
                observed_at,
                "url",
                "https://listings.fixture.example/offers/demo-016",
            ),
        ),
        observed_at=TracedValue(
            observed_at,
            _value_provenance(
                reference,
                observed_at,
                "observed_at",
                observed_at.to_rfc3339(),
            ),
        ),
        location_text=location_text
        or _present(
            LocationText("Invented Quarter"),
            reference,
            observed_at,
            "location_text",
            "Invented Quarter",
        ),
        price_amount=price_amount
        or _present(
            MoneyAmount(10_000_000),
            reference,
            observed_at,
            "price_major",
            "100000.00",
        ),
        currency=currency or _present(Currency("RUB"), reference, observed_at, "currency", "RUB"),
        total_area=total_area
        or _present(Area(4_700), reference, observed_at, "total_area_sqm", "47.00"),
        rooms=rooms or _present(RoomCount(2), reference, observed_at, "rooms", "2"),
    )


def _available(
    observed_at: ObservedAt,
    *,
    reference: PublicationRef = REFERENCE,
    listing: NormalizedListing | None = None,
    **listing_changes: Any,
) -> AvailableObservation:
    complete_listing = listing or _listing(observed_at, reference=reference, **listing_changes)
    return AvailableObservation(ObservationKey(reference, observed_at), complete_listing)


def _direct_evidence(
    *,
    raw_state: str = "unavailable",
    cause: SourceReportedCause | None = None,
) -> DirectSourceStateEvidence:
    return DirectSourceStateEvidence(
        raw_source_state=raw_state,
        source_field="publication_state",
        adapter_rule_version=AVAILABILITY_RULE,
        source_reported_cause=cause,
    )


def _unavailable(
    observed_at: ObservedAt,
    *,
    reference: PublicationRef = REFERENCE,
    evidence: DirectSourceStateEvidence | TargetedPublicationCheckEvidence | None = None,
) -> UnavailableObservation:
    return UnavailableObservation(
        key=ObservationKey(reference, observed_at),
        evidence=evidence or _direct_evidence(),
    )


def _history(
    *observations: AvailableObservation | UnavailableObservation,
    reference: PublicationRef = REFERENCE,
    policy_version: ComparisonPolicyVersion = PUBLICATION_CHANGE_POLICY_V1_VERSION,
) -> PublicationObservationHistory:
    return PublicationObservationHistory(reference, policy_version, observations)


def _change(
    previous: AvailableObservation | UnavailableObservation,
    current: AvailableObservation | UnavailableObservation,
) -> ChangeSet:
    result = compare_consecutive_observations(previous, current)
    assert isinstance(result, ChangeSet)
    return result


def _append_success(
    history: PublicationObservationHistory,
    candidate: AvailableObservation | UnavailableObservation,
) -> ObservationAppendSuccess:
    result = append_observation(history, candidate)
    assert isinstance(result, ObservationAppendSuccess)
    return result


def _append_failure(
    history: PublicationObservationHistory,
    candidate: AvailableObservation | UnavailableObservation,
) -> ObservationAppendFailure:
    result = append_observation(history, candidate)
    assert isinstance(result, ObservationAppendFailure)
    return result


@pytest.mark.parametrize(
    "factory",
    [
        ComparisonPolicyVersion,
        AvailabilityRuleVersion,
        SourceReportedCause,
        ConclusiveUnavailableOutcomeCode,
    ],
)
@pytest.mark.parametrize("value", ["", "contains space", "non-ascii-ы", "x" * 129])
def test_opaque_codes_reject_invalid_values(factory: Any, value: str) -> None:
    with pytest.raises(ValueError):
        factory(value)


def test_policy_v1_has_exact_version_and_stable_six_field_order() -> None:
    assert PUBLICATION_CHANGE_POLICY_V1.version.value == "publication-change-policy@1"
    assert PUBLICATION_CHANGE_POLICY_V1.field_order == (
        "source_url",
        "location_text",
        "price_amount",
        "currency",
        "total_area",
        "rooms",
    )
    with pytest.raises(ValueError):
        ComparisonPolicy(PUBLICATION_CHANGE_POLICY_V1_VERSION, ("rooms",))


def test_available_observation_accepts_a_fully_consistent_listing() -> None:
    observation = _available(_at(10))

    assert observation.key.reference == REFERENCE
    assert observation.listing.observed_at.value == _at(10)


def _replace_field_provenance(
    listing: NormalizedListing,
    field: str,
    *,
    source_id: SourceId | None = None,
    observed_at: ObservedAt | None = None,
) -> NormalizedListing:
    def changed(provenance: ValueProvenance) -> ValueProvenance:
        return replace(
            provenance,
            source_id=source_id or provenance.source_id,
            observed_at=observed_at or provenance.observed_at,
        )

    if field == "reference":
        return replace(
            listing,
            reference=replace(listing.reference, provenance=changed(listing.reference.provenance)),
        )
    if field == "source_url":
        return replace(
            listing,
            source_url=replace(
                listing.source_url,
                provenance=changed(listing.source_url.provenance),
            ),
        )
    if field == "observed_at":
        return replace(
            listing,
            observed_at=replace(
                listing.observed_at,
                provenance=changed(listing.observed_at.provenance),
            ),
        )
    if field == "location_text":
        assert isinstance(listing.location_text, Present)
        return replace(
            listing,
            location_text=replace(
                listing.location_text,
                value=replace(
                    listing.location_text.value,
                    provenance=changed(listing.location_text.value.provenance),
                ),
            ),
        )
    if field == "price_amount":
        assert isinstance(listing.price_amount, Present)
        return replace(
            listing,
            price_amount=replace(
                listing.price_amount,
                value=replace(
                    listing.price_amount.value,
                    provenance=changed(listing.price_amount.value.provenance),
                ),
            ),
        )
    if field == "currency":
        assert isinstance(listing.currency, Present)
        return replace(
            listing,
            currency=replace(
                listing.currency,
                value=replace(
                    listing.currency.value,
                    provenance=changed(listing.currency.value.provenance),
                ),
            ),
        )
    if field == "total_area":
        assert isinstance(listing.total_area, Present)
        return replace(
            listing,
            total_area=replace(
                listing.total_area,
                value=replace(
                    listing.total_area.value,
                    provenance=changed(listing.total_area.value.provenance),
                ),
            ),
        )
    assert field == "rooms"
    assert isinstance(listing.rooms, Present)
    return replace(
        listing,
        rooms=replace(
            listing.rooms,
            value=replace(
                listing.rooms.value,
                provenance=changed(listing.rooms.value.provenance),
            ),
        ),
    )


@pytest.mark.parametrize(
    "field",
    [
        "reference",
        "source_url",
        "observed_at",
        "location_text",
        "price_amount",
        "currency",
        "total_area",
        "rooms",
    ],
)
@pytest.mark.parametrize("mismatch", ["reference", "observed_at"])
def test_available_observation_rejects_mismatched_provenance(
    field: str,
    mismatch: Literal["reference", "observed_at"],
) -> None:
    observed_at = _at(10)
    listing = _listing(observed_at)
    if mismatch == "reference":
        listing = _replace_field_provenance(
            listing,
            field,
            source_id=SourceId("another_source"),
        )
    else:
        listing = _replace_field_provenance(listing, field, observed_at=_at(9))

    with pytest.raises(ValueError, match="provenance"):
        AvailableObservation(ObservationKey(REFERENCE, observed_at), listing)


def test_available_observation_rejects_listing_identity_or_time_mismatch() -> None:
    observed_at = _at(10)
    listing = _listing(observed_at)
    wrong_reference_listing = replace(
        listing,
        reference=replace(listing.reference, value=OTHER_REFERENCE),
    )
    wrong_time_listing = replace(
        listing,
        observed_at=replace(listing.observed_at, value=_at(11)),
    )

    with pytest.raises(ValueError, match="reference"):
        AvailableObservation(ObservationKey(REFERENCE, observed_at), wrong_reference_listing)
    with pytest.raises(ValueError, match="observed_at"):
        AvailableObservation(ObservationKey(REFERENCE, observed_at), wrong_time_listing)


def test_unavailable_requires_one_of_two_sufficient_evidence_types() -> None:
    key = ObservationKey(REFERENCE, _at(10))
    direct = UnavailableObservation(key, _direct_evidence())
    targeted_evidence = TargetedPublicationCheckEvidence(
        outcome_code=ConclusiveUnavailableOutcomeCode("confirmed_absent"),
        check_rule_version=AvailabilityRuleVersion("targeted-check@1"),
        adapter_rule_version=AVAILABILITY_RULE,
    )
    targeted = UnavailableObservation(key, targeted_evidence)

    assert isinstance(direct.evidence, DirectSourceStateEvidence)
    assert isinstance(targeted.evidence, TargetedPublicationCheckEvidence)
    assert not hasattr(targeted_evidence, "source_reported_cause")
    with pytest.raises(TypeError):
        UnavailableObservation(key, "timeout")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        UnavailableObservation(key)  # type: ignore[call-arg]


def test_direct_source_cause_remains_an_explicit_source_claim() -> None:
    cause = SourceReportedCause("source_reported_deleted")
    observation = _unavailable(_at(10), evidence=_direct_evidence(cause=cause))

    assert isinstance(observation.evidence, DirectSourceStateEvidence)
    assert observation.evidence.source_reported_cause == cause


def test_history_enforces_one_reference_strict_order_and_tuple_storage() -> None:
    first = _available(_at(10))
    second = _available(_at(11))
    other = _available(_at(12), reference=OTHER_REFERENCE)

    assert _history(first, second).observations == (first, second)
    with pytest.raises(TypeError, match="tuple"):
        PublicationObservationHistory(
            REFERENCE,
            PUBLICATION_CHANGE_POLICY_V1_VERSION,
            [first],  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="reference"):
        _history(first, other)
    with pytest.raises(ValueError, match="strictly increasing"):
        _history(second, first)
    with pytest.raises(ValueError, match="strictly increasing"):
        _history(first, first)


def test_available_comparison_emits_all_six_fields_in_policy_order() -> None:
    before = _available(_at(10))
    current_at = _at(11)
    after = _available(
        current_at,
        source_url=TracedValue(
            SourceUrl("https://listings.fixture.example/offers/demo-016-new"),
            _value_provenance(
                REFERENCE,
                current_at,
                "url",
                "https://listings.fixture.example/offers/demo-016-new",
            ),
        ),
        location_text=_present(
            LocationText("Invented Quarter Changed"),
            REFERENCE,
            current_at,
            "location_text",
            "Invented Quarter Changed",
        ),
        price_amount=_present(
            MoneyAmount(9_500_000),
            REFERENCE,
            current_at,
            "price_major",
            "95000.00",
        ),
        currency=_missing(REFERENCE, current_at, "currency"),
        total_area=_present(Area(4_800), REFERENCE, current_at, "total_area_sqm", "48.00"),
        rooms=_present(RoomCount(3), REFERENCE, current_at, "rooms", "3"),
    )

    change = _change(before, after)

    assert tuple(delta.field for delta in change.field_deltas) == (
        "source_url",
        "location_text",
        "price_amount",
        "currency",
        "total_area",
        "rooms",
    )
    assert all(delta.kind is FieldDeltaKind.SUBSTANTIVE for delta in change.field_deltas)
    assert change.availability_change is None
    assert change.availability_evidence_delta is None


def _rooms_outcome(
    state: Literal["present_one", "present_two", "missing", "unsupported_a", "unsupported_b"],
    observed_at: ObservedAt,
) -> Present[RoomCount] | Missing | Unsupported:
    if state == "present_one":
        return _present(RoomCount(1), REFERENCE, observed_at, "rooms", "1")
    if state == "present_two":
        return _present(RoomCount(2), REFERENCE, observed_at, "rooms", "2")
    if state == "missing":
        return _missing(REFERENCE, observed_at, "rooms")
    if state == "unsupported_a":
        return _unsupported(REFERENCE, observed_at, "rooms", "many", "unsupported_many")
    return _unsupported(REFERENCE, observed_at, "rooms", "shared", "unsupported_shared")


@pytest.mark.parametrize(
    ("before_state", "after_state", "expected_kind"),
    [
        ("present_one", "present_one", None),
        ("present_one", "present_two", FieldDeltaKind.SUBSTANTIVE),
        ("present_one", "missing", FieldDeltaKind.SUBSTANTIVE),
        ("present_one", "unsupported_a", FieldDeltaKind.SUBSTANTIVE),
        ("missing", "present_one", FieldDeltaKind.SUBSTANTIVE),
        ("missing", "missing", None),
        ("missing", "unsupported_a", FieldDeltaKind.SUBSTANTIVE),
        ("unsupported_a", "present_one", FieldDeltaKind.SUBSTANTIVE),
        ("unsupported_a", "missing", FieldDeltaKind.SUBSTANTIVE),
        ("unsupported_a", "unsupported_a", None),
        ("unsupported_a", "unsupported_b", FieldDeltaKind.SUBSTANTIVE),
    ],
)
def test_full_field_outcome_transition_matrix(
    before_state: Literal[
        "present_one", "present_two", "missing", "unsupported_a", "unsupported_b"
    ],
    after_state: Literal["present_one", "present_two", "missing", "unsupported_a", "unsupported_b"],
    expected_kind: FieldDeltaKind | None,
) -> None:
    before = _available(_at(10), rooms=_rooms_outcome(before_state, _at(10)))
    after = _available(_at(11), rooms=_rooms_outcome(after_state, _at(11)))

    change = _change(before, after)

    room_deltas = tuple(delta for delta in change.field_deltas if delta.field == "rooms")
    if expected_kind is None:
        assert room_deltas == ()
    else:
        assert len(room_deltas) == 1
        assert room_deltas[0].kind is expected_kind


def test_same_canonical_present_with_new_raw_is_source_representation_only() -> None:
    before = _available(
        _at(10),
        total_area=_present(Area(4_700), REFERENCE, _at(10), "total_area_sqm", "47.0"),
    )
    after = _available(
        _at(11),
        total_area=_present(Area(4_700), REFERENCE, _at(11), "total_area_sqm", "47.00"),
    )

    change = _change(before, after)

    assert len(change.field_deltas) == 1
    assert change.field_deltas[0].field == "total_area"
    assert change.field_deltas[0].kind is FieldDeltaKind.SOURCE_REPRESENTATION_ONLY


def test_same_unsupported_reason_with_new_raw_is_source_representation_only() -> None:
    before = _available(
        _at(10),
        rooms=_unsupported(REFERENCE, _at(10), "rooms", "many", "unsupported_many"),
    )
    after = _available(
        _at(11),
        rooms=_unsupported(REFERENCE, _at(11), "rooms", "several", "unsupported_many"),
    )

    delta = _change(before, after).field_deltas[0]

    assert delta.field == "rooms"
    assert delta.kind is FieldDeltaKind.SOURCE_REPRESENTATION_ONLY


def test_raw_change_wins_over_simultaneous_other_provenance_change() -> None:
    refreshed_rule = NormalizationRuleVersion("fixture-field@2")
    before = _available(
        _at(10),
        total_area=_present(Area(4_700), REFERENCE, _at(10), "total_area_sqm", "47.0"),
    )
    after = _available(
        _at(11),
        total_area=_present(
            Area(4_700),
            REFERENCE,
            _at(11),
            "total_area_sqm",
            "47.00",
            rule=refreshed_rule,
        ),
    )

    delta = _change(before, after).field_deltas[0]

    assert delta.kind is FieldDeltaKind.SOURCE_REPRESENTATION_ONLY


def test_equal_canonical_and_raw_with_other_provenance_change_is_refresh() -> None:
    before = _available(_at(10))
    after = _available(
        _at(11),
        rooms=_present(
            RoomCount(2),
            REFERENCE,
            _at(11),
            "rooms",
            "2",
            rule=NormalizationRuleVersion("fixture-field@2"),
        ),
    )

    change = _change(before, after)

    assert len(change.field_deltas) == 1
    assert change.field_deltas[0].field == "rooms"
    assert change.field_deltas[0].kind is FieldDeltaKind.PROVENANCE_REFRESH


def test_missing_with_other_provenance_change_is_refresh() -> None:
    before = _available(_at(10), rooms=_missing(REFERENCE, _at(10), "rooms"))
    after = _available(
        _at(11),
        rooms=_missing(
            REFERENCE,
            _at(11),
            "rooms",
            rule=NormalizationRuleVersion("fixture-field@2"),
        ),
    )

    delta = _change(before, after).field_deltas[0]

    assert delta.field == "rooms"
    assert delta.kind is FieldDeltaKind.PROVENANCE_REFRESH


def test_timestamp_only_refresh_creates_successful_empty_change_set() -> None:
    change = _change(_available(_at(10)), _available(_at(11)))

    assert change.policy_version == PUBLICATION_CHANGE_POLICY_V1_VERSION
    assert change.field_deltas == ()
    assert change.availability_change is None
    assert change.availability_evidence_delta is None


def test_first_append_has_no_change_set_and_returns_a_new_history() -> None:
    history = _history()
    candidate = _available(_at(10))

    result = _append_success(history, candidate)

    assert result.disposition is ObservationAppendDisposition.APPENDED
    assert result.history.observations == (candidate,)
    assert result.history is not history
    assert result.change_set is None
    assert history.observations == ()


def test_successive_append_compares_only_the_immediate_predecessor() -> None:
    first = _available(
        _at(9),
        price_amount=_present(MoneyAmount(9_000_000), REFERENCE, _at(9), "price_major", "90000.00"),
    )
    tail = _available(_at(10))
    candidate = _available(_at(11))

    result = _append_success(_history(first, tail), candidate)

    assert result.change_set is not None
    assert result.change_set.from_key == tail.key
    assert result.change_set.to_key == candidate.key
    assert result.change_set.field_deltas == ()


@pytest.mark.parametrize("position", ["tail", "non_tail"])
def test_exact_replay_of_any_accepted_key_returns_the_original_history(position: str) -> None:
    first = _available(_at(10))
    tail = _available(_at(11))
    history = _history(first, tail)
    candidate = tail if position == "tail" else first

    result = _append_success(history, candidate)

    assert result.disposition is ObservationAppendDisposition.REPLAYED
    assert result.history is history
    assert result.change_set is None


def test_same_key_with_different_content_or_kind_is_timestamp_conflict() -> None:
    accepted = _available(_at(10))
    changed = _available(
        _at(10),
        rooms=_present(RoomCount(3), REFERENCE, _at(10), "rooms", "3"),
    )
    unavailable = _unavailable(_at(10))

    for candidate in (changed, unavailable):
        failure = _append_failure(_history(accepted), candidate)
        assert tuple(conflict.code for conflict in failure.conflicts) == (
            "timestamp_content_conflict",
        )


def test_same_unavailable_key_with_different_evidence_is_timestamp_conflict() -> None:
    accepted = _unavailable(_at(10))
    changed = _unavailable(_at(10), evidence=_direct_evidence(raw_state="hidden"))

    failure = _append_failure(_history(accepted), changed)

    assert failure.conflicts[0].code == "timestamp_content_conflict"


def test_unknown_earlier_key_is_out_of_order_without_partial_results() -> None:
    first = _available(_at(10))
    tail = _available(_at(12))
    history = _history(first, tail)
    candidate = _available(_at(11))

    failure = _append_failure(history, candidate)

    assert failure.conflicts[0].code == "out_of_order_observation"
    assert history.observations == (first, tail)
    assert not hasattr(failure, "history")
    assert not hasattr(failure, "change_set")


def test_stream_reference_mismatch_is_atomic() -> None:
    history = _history(_available(_at(10)))
    candidate = _available(_at(11), reference=OTHER_REFERENCE)

    failure = _append_failure(history, candidate)

    assert failure.conflicts == (
        ObservationConflict(
            "OBSERVATION_CONFLICT",
            "stream_reference_mismatch",
            candidate.key,
        ),
    )
    assert not hasattr(failure, "history")


def test_comparison_policy_mismatch_is_atomic() -> None:
    history = _history(policy_version=ComparisonPolicyVersion("publication-change-policy@2"))

    failure = _append_failure(history, _available(_at(10)))

    assert failure.conflicts[0].code == "comparison_policy_mismatch"
    assert failure.conflicts[0].subject == REFERENCE
    assert not hasattr(failure, "history")


def test_direct_comparison_returns_stable_reference_timestamp_and_order_conflicts() -> None:
    previous = _available(_at(10))
    cases = (
        (_available(_at(11), reference=OTHER_REFERENCE), "stream_reference_mismatch"),
        (_available(_at(10)), "timestamp_content_conflict"),
        (_available(_at(9)), "out_of_order_observation"),
    )

    for current, code in cases:
        result = compare_consecutive_observations(previous, current)
        assert isinstance(result, ObservationConflict)
        assert result.category == "OBSERVATION_CONFLICT"
        assert result.code == code


def test_available_to_unavailable_is_confirmed_without_field_comparison() -> None:
    before = _available(_at(10))
    after = _unavailable(_at(11))

    change = _change(before, after)

    assert change.availability_change == ConfirmedUnavailable(before, after)
    assert change.field_deltas == ()
    assert change.availability_evidence_delta is None


def test_unavailable_to_available_is_reappearance_without_field_comparison() -> None:
    before = _unavailable(_at(10))
    after = _available(
        _at(11),
        rooms=_present(RoomCount(4), REFERENCE, _at(11), "rooms", "4"),
    )

    change = _change(before, after)

    assert change.availability_change == Reappeared(before, after)
    assert change.field_deltas == ()
    assert change.availability_evidence_delta is None


def test_repeated_unavailable_with_equal_evidence_has_empty_change_set() -> None:
    evidence = _direct_evidence()
    change = _change(
        _unavailable(_at(10), evidence=evidence),
        _unavailable(_at(11), evidence=evidence),
    )

    assert change.availability_change is None
    assert change.field_deltas == ()
    assert change.availability_evidence_delta is None


def test_repeated_unavailable_with_different_evidence_has_one_evidence_delta() -> None:
    before_evidence = _direct_evidence()
    after_evidence = TargetedPublicationCheckEvidence(
        outcome_code=ConclusiveUnavailableOutcomeCode("confirmed_absent"),
        check_rule_version=AvailabilityRuleVersion("targeted-check@1"),
        adapter_rule_version=AVAILABILITY_RULE,
    )
    change = _change(
        _unavailable(_at(10), evidence=before_evidence),
        _unavailable(_at(11), evidence=after_evidence),
    )

    assert change.availability_change is None
    assert change.field_deltas == ()
    assert change.availability_evidence_delta == AvailabilityEvidenceDelta(
        before_evidence,
        after_evidence,
    )


def _assign_attribute(target: Any) -> None:
    target.change_set = None


def test_public_observation_types_results_and_tuples_are_immutable() -> None:
    observation = _available(_at(10))
    result = _append_success(_history(), observation)

    for target in (
        PUBLICATION_CHANGE_POLICY_V1,
        observation.key,
        observation,
        result.history,
        result,
    ):
        assert not hasattr(target, "__dict__")
        with pytest.raises(FrozenInstanceError):
            _assign_attribute(target)
    assert isinstance(result.history.observations, tuple)


def test_failure_and_change_set_reject_mutable_or_partial_containers() -> None:
    conflict = ObservationConflict(
        "OBSERVATION_CONFLICT",
        "out_of_order_observation",
        ObservationKey(REFERENCE, _at(10)),
    )
    with pytest.raises(ValueError, match="contain a conflict"):
        ObservationAppendFailure(())
    with pytest.raises(TypeError, match="tuple"):
        ObservationAppendFailure([conflict])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="tuple"):
        ChangeSet(
            PUBLICATION_CHANGE_POLICY_V1_VERSION,
            ObservationKey(REFERENCE, _at(10)),
            ObservationKey(REFERENCE, _at(11)),
            field_deltas=[],  # type: ignore[arg-type]
        )


def test_field_snapshot_and_evidence_delta_constructor_invariants() -> None:
    value_provenance = _value_provenance(REFERENCE, _at(10), "rooms", "2")
    unsupported_provenance = UnsupportedProvenance(
        source_id=REFERENCE.source_id,
        publication_id=REFERENCE.publication_id,
        input_path=_location("rooms"),
        source_field="rooms",
        raw_value="many",
        observed_at=_at(10),
        normalization_rule_version=RULE,
        reason_code="unsupported_many",
    )

    assert FieldSnapshot(PresentValue(RoomCount(2)), value_provenance).canonical == PresentValue(
        RoomCount(2)
    )
    with pytest.raises(ValueError, match="missing provenance"):
        FieldSnapshot(MissingValue(), value_provenance)
    with pytest.raises(ValueError, match="does not match"):
        FieldSnapshot(UnsupportedValue("another_reason"), unsupported_provenance)
    before_snapshot = FieldSnapshot(PresentValue(RoomCount(2)), value_provenance)
    changed_provenance = replace(value_provenance, raw_value="02", observed_at=_at(11))
    after_snapshot = FieldSnapshot(PresentValue(RoomCount(2)), changed_provenance)
    with pytest.raises(ValueError, match="kind does not match"):
        FieldDelta(
            "rooms",
            FieldDeltaKind.SUBSTANTIVE,
            before_snapshot,
            after_snapshot,
        )
    with pytest.raises(ValueError, match="classified difference"):
        FieldDelta(
            "rooms",
            FieldDeltaKind.PROVENANCE_REFRESH,
            before_snapshot,
            FieldSnapshot(
                PresentValue(RoomCount(2)),
                replace(value_provenance, observed_at=_at(11)),
            ),
        )
    evidence = _direct_evidence()
    with pytest.raises(ValueError, match="requires a difference"):
        AvailabilityEvidenceDelta(evidence, evidence)


def test_change_set_rejects_duplicate_or_non_policy_field_order() -> None:
    current_at = _at(11)
    change = _change(
        _available(_at(10)),
        _available(
            current_at,
            price_amount=_present(
                MoneyAmount(9_500_000),
                REFERENCE,
                current_at,
                "price_major",
                "95000.00",
            ),
            rooms=_present(RoomCount(3), REFERENCE, current_at, "rooms", "3"),
        ),
    )
    assert tuple(delta.field for delta in change.field_deltas) == ("price_amount", "rooms")

    with pytest.raises(ValueError, match="policy order"):
        replace(change, field_deltas=tuple(reversed(change.field_deltas)))
    with pytest.raises(ValueError, match="unique"):
        replace(change, field_deltas=(change.field_deltas[0], change.field_deltas[0]))


def test_no_time_uuid_io_or_attempt_failure_shortcuts_are_exposed() -> None:
    import real_estate_parser.publication_observations as module

    forbidden_names = {
        "from_batch_omission",
        "from_timeout",
        "from_block",
        "from_network_failure",
        "from_source_failure",
    }
    assert forbidden_names.isdisjoint(vars(module))
    assert "uuid" not in vars(module)
    assert "Path" not in vars(module)
