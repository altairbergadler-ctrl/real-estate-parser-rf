from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from itertools import permutations
from typing import Any

import pytest

from real_estate_parser import (
    PUBLICATION_CHANGE_POLICY_V1,
    PUBLICATION_CHANGE_POLICY_V1_VERSION,
    Area,
    AvailabilityRuleVersion,
    AvailableObservation,
    ComparisonPolicyVersion,
    ConfirmedUnavailable,
    Currency,
    DirectSourceStateEvidence,
    FieldDeltaKind,
    InputLocation,
    LocationText,
    MoneyAmount,
    NormalizationRuleVersion,
    NormalizedListing,
    ObservationAppendDisposition,
    ObservationAppendSuccess,
    ObservationBatchAppendFailure,
    ObservationBatchAppendSuccess,
    ObservationBatchItemOutcome,
    ObservationConflict,
    ObservationKey,
    ObservedAt,
    Present,
    PublicationId,
    PublicationObservationHistories,
    PublicationObservationHistory,
    PublicationRef,
    Reappeared,
    RoomCount,
    SourceId,
    SourceUrl,
    TracedValue,
    UnavailableObservation,
    ValueProvenance,
    append_observation,
    append_observation_batch,
)

RULE = NormalizationRuleVersion("fictional-field@1")
AVAILABILITY_RULE = AvailabilityRuleVersion("fictional-availability@1")
REF_A = PublicationRef(SourceId("alpha_source"), PublicationId("offer-a"))
REF_B = PublicationRef(SourceId("alpha_source"), PublicationId("offer-b"))
REF_C = PublicationRef(SourceId("beta_source"), PublicationId("offer-a"))


def _at(hour: int, minute: int = 0) -> ObservedAt:
    return ObservedAt(datetime(2026, 9, 2, hour, minute, tzinfo=UTC))


def _provenance(
    reference: PublicationRef,
    observed_at: ObservedAt,
    field: str,
    raw_value: str,
) -> ValueProvenance:
    return ValueProvenance(
        source_id=reference.source_id,
        publication_id=reference.publication_id,
        input_path=InputLocation("listings", 0, (field,)),
        source_field=field,
        raw_value=raw_value,
        observed_at=observed_at,
        normalization_rule_version=RULE,
    )


def _present[T](
    value: T,
    reference: PublicationRef,
    observed_at: ObservedAt,
    field: str,
    raw_value: str,
) -> Present[T]:
    return Present(TracedValue(value, _provenance(reference, observed_at, field, raw_value)))


def _listing(
    reference: PublicationRef,
    observed_at: ObservedAt,
    *,
    price: int = 10_000_000,
) -> NormalizedListing:
    url = f"https://{reference.source_id.value}.example/{reference.publication_id.value}"
    return NormalizedListing(
        reference=TracedValue(
            reference,
            _provenance(
                reference,
                observed_at,
                "publication_id",
                reference.publication_id.value,
            ),
        ),
        source_url=TracedValue(
            SourceUrl(url),
            _provenance(reference, observed_at, "url", url),
        ),
        observed_at=TracedValue(
            observed_at,
            _provenance(reference, observed_at, "observed_at", observed_at.to_rfc3339()),
        ),
        location_text=_present(
            LocationText("Fictional District"),
            reference,
            observed_at,
            "location_text",
            "Fictional District",
        ),
        price_amount=_present(
            MoneyAmount(price),
            reference,
            observed_at,
            "price_amount",
            str(price),
        ),
        currency=_present(Currency("RUB"), reference, observed_at, "currency", "RUB"),
        total_area=_present(Area(4_700), reference, observed_at, "total_area", "47.00"),
        rooms=_present(RoomCount(2), reference, observed_at, "rooms", "2"),
    )


def _available(
    reference: PublicationRef,
    hour: int,
    *,
    minute: int = 0,
    price: int = 10_000_000,
) -> AvailableObservation:
    observed_at = _at(hour, minute)
    return AvailableObservation(
        ObservationKey(reference, observed_at),
        _listing(reference, observed_at, price=price),
    )


def _unavailable(
    reference: PublicationRef,
    hour: int,
    *,
    raw_state: str = "unavailable",
) -> UnavailableObservation:
    return UnavailableObservation(
        ObservationKey(reference, _at(hour)),
        DirectSourceStateEvidence(
            raw_source_state=raw_state,
            source_field="publication_state",
            adapter_rule_version=AVAILABILITY_RULE,
        ),
    )


def _history(
    reference: PublicationRef,
    *observations: AvailableObservation | UnavailableObservation,
    policy_version: ComparisonPolicyVersion = PUBLICATION_CHANGE_POLICY_V1_VERSION,
) -> PublicationObservationHistory:
    return PublicationObservationHistory(reference, policy_version, observations)


def _success(
    histories: PublicationObservationHistories,
    candidates: tuple[AvailableObservation | UnavailableObservation, ...],
) -> ObservationBatchAppendSuccess:
    result = append_observation_batch(histories, candidates, PUBLICATION_CHANGE_POLICY_V1)
    assert isinstance(result, ObservationBatchAppendSuccess)
    return result


def _failure(
    histories: PublicationObservationHistories,
    candidates: tuple[AvailableObservation | UnavailableObservation, ...],
) -> ObservationBatchAppendFailure:
    result = append_observation_batch(histories, candidates, PUBLICATION_CHANGE_POLICY_V1)
    assert isinstance(result, ObservationBatchAppendFailure)
    return result


def test_histories_container_is_tuple_only_unique_and_canonical() -> None:
    history_a = _history(REF_A)
    history_b = _history(REF_B)
    history_c = _history(REF_C)

    container = PublicationObservationHistories((history_c, history_b, history_a))

    assert container.histories == (history_a, history_b, history_c)
    with pytest.raises(TypeError, match="tuple"):
        PublicationObservationHistories([history_a])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="unsupported"):
        PublicationObservationHistories(("history",))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="duplicate"):
        PublicationObservationHistories((history_a, history_a))


def test_batch_requires_a_non_empty_tuple_of_supported_candidates() -> None:
    histories = PublicationObservationHistories()

    with pytest.raises(ValueError, match="non-empty"):
        append_observation_batch(histories, (), PUBLICATION_CHANGE_POLICY_V1)
    with pytest.raises(TypeError, match="tuple"):
        append_observation_batch(
            histories,
            [_available(REF_A, 10)],  # type: ignore[arg-type]
            PUBLICATION_CHANGE_POLICY_V1,
        )
    with pytest.raises(TypeError, match="unsupported"):
        append_observation_batch(
            histories,
            ("observation",),  # type: ignore[arg-type]
            PUBLICATION_CHANGE_POLICY_V1,
        )


def test_creates_multiple_histories_and_orders_each_new_stream_by_time() -> None:
    a10 = _available(REF_A, 10)
    b10 = _available(REF_B, 10)
    b11 = _available(REF_B, 11, price=9_500_000)

    result = _success(PublicationObservationHistories(), (b11, a10, b10))

    assert tuple(history.reference for history in result.histories.histories) == (REF_A, REF_B)
    assert result.histories.histories[0].observations == (a10,)
    assert result.histories.histories[1].observations == (b10, b11)
    assert tuple(outcome.key for outcome in result.outcomes) == (a10.key, b10.key, b11.key)
    assert all(
        outcome.disposition is ObservationAppendDisposition.APPENDED for outcome in result.outcomes
    )
    assert result.outcomes[0].change_set is None
    assert result.outcomes[1].change_set is None
    assert result.outcomes[2].change_set is not None


def test_updates_existing_history_and_preserves_untouched_history() -> None:
    a10 = _available(REF_A, 10)
    a11 = _available(REF_A, 11, price=9_000_000)
    untouched_observation = _available(REF_C, 8)
    untouched = _history(REF_C, untouched_observation)
    original = PublicationObservationHistories((untouched, _history(REF_A, a10)))

    result = _success(original, (a11,))

    assert result.histories.histories[0].observations == (a10, a11)
    assert result.histories.histories[1] is untouched
    assert original.histories[0].observations == (a10,)
    assert result.outcomes[0].change_set is not None
    assert tuple(delta.field for delta in result.outcomes[0].change_set.field_deltas) == (
        "price_amount",
    )
    assert result.outcomes[0].change_set.field_deltas[0].kind is FieldDeltaKind.SUBSTANTIVE


def test_tail_non_tail_replays_and_exact_batch_duplicates_have_one_outcome_per_key() -> None:
    a10 = _available(REF_A, 10)
    a11 = _available(REF_A, 11)
    histories = PublicationObservationHistories((_history(REF_A, a10, a11),))

    result = _success(histories, (a11, a10, a11, a10))

    assert result.histories == histories
    assert tuple(outcome.key for outcome in result.outcomes) == (a10.key, a11.key)
    assert all(
        outcome.disposition is ObservationAppendDisposition.REPLAYED for outcome in result.outcomes
    )
    assert all(outcome.change_set is None for outcome in result.outcomes)


def test_same_key_different_content_or_kind_inside_batch_is_one_conflict() -> None:
    original = _available(REF_A, 10)
    changed = _available(REF_A, 10, price=9_000_000)
    unavailable = _unavailable(REF_A, 10)

    failure = _failure(PublicationObservationHistories(), (changed, unavailable, original))

    assert failure.conflicts == (
        ObservationConflict(
            "OBSERVATION_CONFLICT",
            "timestamp_content_conflict",
            original.key,
        ),
    )


def test_same_key_different_content_and_evidence_against_histories_are_separate() -> None:
    accepted_a = _available(REF_A, 10)
    changed_a = _available(REF_A, 10, price=9_000_000)
    accepted_b = _unavailable(REF_B, 10)
    changed_b = _unavailable(REF_B, 10, raw_state="hidden")
    histories = PublicationObservationHistories(
        (_history(REF_B, accepted_b), _history(REF_A, accepted_a))
    )

    failure = _failure(histories, (changed_b, changed_a))

    assert tuple(conflict.subject for conflict in failure.conflicts) == (
        changed_a.key,
        changed_b.key,
    )
    assert tuple(conflict.code for conflict in failure.conflicts) == (
        "timestamp_content_conflict",
        "timestamp_content_conflict",
    )


def test_collects_all_independent_conflicts_once_in_exact_global_order() -> None:
    mismatch_history = _history(
        REF_A,
        policy_version=ComparisonPolicyVersion("publication-change-policy@2"),
    )
    b_tail = _available(REF_B, 12)
    c_tail = _available(REF_C, 12)
    c_tail_changed = _available(REF_C, 12, price=9_000_000)
    histories = PublicationObservationHistories(
        (mismatch_history, _history(REF_B, b_tail), _history(REF_C, c_tail))
    )
    candidates = (
        c_tail_changed,
        _available(REF_B, 11),
        _available(REF_C, 11),
        _available(REF_B, 9),
    )

    failure = _failure(histories, candidates)

    assert tuple((conflict.subject, conflict.code) for conflict in failure.conflicts) == (
        (REF_A, "comparison_policy_mismatch"),
        (ObservationKey(REF_B, _at(9)), "out_of_order_observation"),
        (ObservationKey(REF_B, _at(11)), "out_of_order_observation"),
        (ObservationKey(REF_C, _at(11)), "out_of_order_observation"),
        (c_tail.key, "timestamp_content_conflict"),
    )
    assert len(set(failure.conflicts)) == len(failure.conflicts)


def test_one_conflict_blocks_valid_candidates_in_every_other_stream() -> None:
    a10 = _available(REF_A, 10)
    original = PublicationObservationHistories((_history(REF_A, a10),))
    valid_b = _available(REF_B, 10)
    conflicting_a = _available(REF_A, 10, price=9_000_000)

    failure = _failure(original, (valid_b, conflicting_a))

    assert original.histories[0].observations == (a10,)
    assert not hasattr(failure, "histories")
    assert not hasattr(failure, "outcomes")
    assert not hasattr(failure, "change_set")


def test_result_is_invariant_to_history_and_candidate_permutations() -> None:
    a10 = _available(REF_A, 10)
    a11 = _available(REF_A, 11, price=9_500_000)
    b10 = _available(REF_B, 10)
    c10 = _available(REF_C, 10)
    source_histories = (_history(REF_B, b10), _history(REF_A, a10))
    candidates = (c10, b10, a11)

    expected = _success(PublicationObservationHistories(source_histories), candidates)

    for histories_order in permutations(source_histories):
        for candidates_order in permutations(candidates):
            assert (
                _success(
                    PublicationObservationHistories(histories_order),
                    candidates_order,
                )
                == expected
            )


def test_successful_batch_is_fully_idempotent_on_repeat() -> None:
    a10 = _available(REF_A, 10)
    a11 = _available(REF_A, 11, price=9_500_000)
    b10 = _available(REF_B, 10)
    candidates = (a11, b10, a10, a11)

    first = _success(PublicationObservationHistories(), candidates)
    repeated = _success(first.histories, candidates)

    assert repeated.histories == first.histories
    assert tuple(outcome.key for outcome in repeated.outcomes) == (a10.key, a11.key, b10.key)
    assert all(
        outcome.disposition is ObservationAppendDisposition.REPLAYED
        for outcome in repeated.outcomes
    )
    assert all(outcome.change_set is None for outcome in repeated.outcomes)


def test_batch_preserves_task_016_availability_and_reappearance_change_sets() -> None:
    a10 = _available(REF_A, 10)
    unavailable = _unavailable(REF_A, 11)
    reappeared = _available(REF_A, 12, price=8_500_000)
    history = _history(REF_A, a10)

    first_manual = append_observation(history, unavailable, PUBLICATION_CHANGE_POLICY_V1)
    assert isinstance(first_manual, ObservationAppendSuccess)
    second_manual = append_observation(
        first_manual.history,
        reappeared,
        PUBLICATION_CHANGE_POLICY_V1,
    )
    assert isinstance(second_manual, ObservationAppendSuccess)

    batch = _success(PublicationObservationHistories((history,)), (reappeared, unavailable))

    assert batch.histories.histories[0] == second_manual.history
    assert batch.outcomes[0].change_set == first_manual.change_set
    assert batch.outcomes[1].change_set == second_manual.change_set
    assert batch.outcomes[0].change_set is not None
    assert batch.outcomes[1].change_set is not None
    assert isinstance(batch.outcomes[0].change_set.availability_change, ConfirmedUnavailable)
    assert isinstance(batch.outcomes[1].change_set.availability_change, Reappeared)
    assert batch.outcomes[0].change_set.field_deltas == ()
    assert batch.outcomes[1].change_set.field_deltas == ()


def _assign_attribute(target: Any) -> None:
    target.outcomes = ()


def test_batch_public_types_are_frozen_slots_tuple_only_and_have_no_partial_state() -> None:
    first = _available(REF_A, 10)
    candidate = _available(REF_A, 11, price=9_000_000)
    success = _success(PublicationObservationHistories(), (candidate, first))
    conflict = ObservationConflict(
        "OBSERVATION_CONFLICT",
        "out_of_order_observation",
        candidate.key,
    )
    failure = ObservationBatchAppendFailure((conflict,))

    for target in (
        success.histories,
        success.outcomes[0],
        success,
        failure,
    ):
        assert not hasattr(target, "__dict__")
        with pytest.raises(FrozenInstanceError):
            _assign_attribute(target)
    assert isinstance(success.histories.histories, tuple)
    assert isinstance(success.outcomes, tuple)
    assert isinstance(failure.conflicts, tuple)
    assert not hasattr(success.outcomes[0], "history")
    assert not hasattr(failure, "histories")
    assert not hasattr(failure, "outcomes")

    with pytest.raises(TypeError, match="tuple"):
        ObservationBatchAppendFailure([conflict])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="contain a conflict"):
        ObservationBatchAppendFailure(())
    with pytest.raises(TypeError, match="tuple"):
        ObservationBatchAppendSuccess(success.histories, list(success.outcomes))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="item outcome"):
        ObservationBatchAppendSuccess(success.histories, ())
    with pytest.raises(ValueError, match="replayed"):
        ObservationBatchItemOutcome(
            candidate.key,
            ObservationAppendDisposition.REPLAYED,
            success.outcomes[1].change_set,
        )


def test_composition_exposes_no_io_storage_clock_or_expected_revision_surface() -> None:
    import real_estate_parser.publication_observation_batches as module

    assert "Path" not in vars(module)
    assert "uuid" not in vars(module)
    assert "datetime" not in vars(module)
    assert "expected_revision_mismatch" not in vars(module)
    assert not any(name.startswith("load_") or name.startswith("save_") for name in module.__all__)
