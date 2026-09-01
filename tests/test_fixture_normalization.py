from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from real_estate_parser import (
    FIXTURE_NORMALIZATION_RULES_V1,
    Area,
    Currency,
    FixtureSourceAdaptationSuccess,
    InputLocation,
    LocationText,
    Missing,
    MissingField,
    MoneyAmount,
    NormalizationFailure,
    NormalizationSuccess,
    ObservedAt,
    Present,
    PublicationId,
    PublicationRef,
    RawField,
    RoomCount,
    SourceBatchLoadSuccess,
    SourceId,
    SourcePublicationSnapshot,
    Unsupported,
    ValueProvenance,
    adapt_fixture_source_batch,
    load_fixture_source_batch,
    normalize_fixture_snapshot,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v1"
VALID_BATCH = FIXTURE_ROOT / "valid" / "listings-comprehensive.json"
ATOMIC_BATCH = FIXTURE_ROOT / "invalid" / "normalization-atomic.json"


def _raw(record_index: int, source_field: str, value: str) -> RawField:
    return RawField(
        value=value,
        location=InputLocation("listings", record_index, (source_field,)),
    )


def _optional(record_index: int, source_field: str, value: str | None) -> RawField | MissingField:
    if value is None:
        return MissingField(InputLocation("listings", record_index, (source_field,)))
    return _raw(record_index, source_field, value)


def _snapshot(
    record_index: int = 0,
    publication_id: str = "alpha-001",
    *,
    observed_at: str = "2026-02-03T10:15:30.123456+03:00",
    location_text: str | None = "  Invented Quarter   Alpha  ",
    price_major: str | None = "110000.00",
    currency: str | None = "RUB",
    total_area_sqm: str | None = "52.50",
    rooms: str | None = "2",
) -> SourcePublicationSnapshot:
    return SourcePublicationSnapshot(
        reference=PublicationRef(SourceId("fixture_portal"), PublicationId(publication_id)),
        source_url=_raw(
            record_index,
            "url",
            f"https://listings.fixture.example/offers/{publication_id}",
        ),
        observed_at=_raw(record_index, "observed_at", observed_at),
        location_text=_optional(record_index, "location_text", location_text),
        price_amount=_optional(record_index, "price_major", price_major),
        currency=_optional(record_index, "currency", currency),
        total_area=_optional(record_index, "total_area_sqm", total_area_sqm),
        rooms=_optional(record_index, "rooms", rooms),
        input_location=InputLocation("listings", record_index),
    )


def _success(snapshot: SourcePublicationSnapshot) -> NormalizationSuccess:
    result = normalize_fixture_snapshot(snapshot, FIXTURE_NORMALIZATION_RULES_V1)
    assert isinstance(result, NormalizationSuccess)
    return result


def _failure(snapshot: SourcePublicationSnapshot) -> NormalizationFailure:
    result = normalize_fixture_snapshot(snapshot, FIXTURE_NORMALIZATION_RULES_V1)
    assert isinstance(result, NormalizationFailure)
    return result


def _issue_triples(result: NormalizationFailure) -> list[tuple[str, str, str]]:
    return [(issue.category, issue.code, issue.location.json_path) for issue in result.issues]


def _assign_listing(target: Any) -> None:
    target.listing = target.listing


def _assign_provenance_raw_value(target: Any) -> None:
    target.raw_value = "changed"


def test_comprehensive_alpha_snapshot_normalizes_exactly() -> None:
    listing = _success(_snapshot()).listing

    assert listing.reference.value == PublicationRef(
        SourceId("fixture_portal"), PublicationId("alpha-001")
    )
    assert listing.source_url.value.value == "https://listings.fixture.example/offers/alpha-001"
    assert listing.observed_at.value == ObservedAt(
        datetime(2026, 2, 3, 7, 15, 30, 123456, tzinfo=UTC)
    )
    assert listing.observed_at.value.to_rfc3339() == "2026-02-03T07:15:30.123456Z"

    assert isinstance(listing.location_text, Present)
    assert listing.location_text.value.value == LocationText("Invented Quarter Alpha")
    assert isinstance(listing.price_amount, Present)
    assert listing.price_amount.value.value == MoneyAmount(11_000_000)
    assert isinstance(listing.currency, Present)
    assert listing.currency.value.value == Currency("RUB")
    assert isinstance(listing.total_area, Present)
    assert listing.total_area.value.value == Area(5_250)
    assert isinstance(listing.rooms, Present)
    assert listing.rooms.value.value == RoomCount(2)


def test_missing_snapshot_has_independent_missing_provenance_without_raw_values() -> None:
    listing = _success(
        _snapshot(
            1,
            "missing-003",
            observed_at="2026-02-01T00:00:00Z",
            location_text=None,
            price_major=None,
            currency=None,
            total_area_sqm=None,
            rooms=None,
        )
    ).listing

    outcomes = (
        (
            listing.location_text,
            "location_text",
            "$.listings[1].location_text",
            "fixture-location-text@1",
        ),
        (
            listing.price_amount,
            "price_major",
            "$.listings[1].price_major",
            "fixture-price-major@1",
        ),
        (listing.currency, "currency", "$.listings[1].currency", "fixture-currency@1"),
        (
            listing.total_area,
            "total_area_sqm",
            "$.listings[1].total_area_sqm",
            "fixture-total-area-sqm@1",
        ),
        (listing.rooms, "rooms", "$.listings[1].rooms", "fixture-rooms@1"),
    )
    for outcome, source_field, json_path, rule in outcomes:
        assert isinstance(outcome, Missing)
        assert outcome.provenance.source_id == SourceId("fixture_portal")
        assert outcome.provenance.publication_id == PublicationId("missing-003")
        assert outcome.provenance.source_field == source_field
        assert outcome.provenance.input_path.json_path == json_path
        assert outcome.provenance.observed_at.to_rfc3339() == "2026-02-01T00:00:00.000000Z"
        assert outcome.provenance.normalization_rule_version.value == rule
        assert not hasattr(outcome.provenance, "raw_value")


def test_unsupported_currency_keeps_price_and_complete_provenance() -> None:
    listing = _success(
        _snapshot(
            2,
            "currency-004",
            observed_at="2026-02-04T23:30:00.5-04:00",
            location_text="Invented Quarter Currency",
            price_major="120000.00",
            currency="USD",
            total_area_sqm="61.75",
            rooms="1",
        )
    ).listing

    assert listing.observed_at.value.to_rfc3339() == "2026-02-05T03:30:00.500000Z"
    assert isinstance(listing.price_amount, Present)
    assert listing.price_amount.value.value == MoneyAmount(12_000_000)
    assert isinstance(listing.currency, Unsupported)
    assert listing.currency.provenance.reason_code == "unsupported_currency"
    assert listing.currency.provenance.source_id == SourceId("fixture_portal")
    assert listing.currency.provenance.publication_id == PublicationId("currency-004")
    assert listing.currency.provenance.raw_value == "USD"
    assert listing.currency.provenance.input_path.json_path == "$.listings[2].currency"
    assert listing.currency.provenance.source_field == "currency"
    assert listing.currency.provenance.observed_at == listing.observed_at.value
    assert listing.currency.provenance.normalization_rule_version.value == "fixture-currency@1"
    assert isinstance(listing.total_area, Present)
    assert listing.total_area.value.value == Area(6_175)
    assert isinstance(listing.rooms, Present)
    assert listing.rooms.value.value == RoomCount(1)


def test_studio_snapshot_normalizes_exactly() -> None:
    listing = _success(
        _snapshot(
            3,
            "studio-002",
            observed_at="2026-02-02T08:00:00+05:30",
            location_text="Invented Quarter Studio",
            price_major="95000.25",
            currency="RUB",
            total_area_sqm="40",
            rooms="studio",
        )
    ).listing

    assert listing.observed_at.value.to_rfc3339() == "2026-02-02T02:30:00.000000Z"
    assert isinstance(listing.price_amount, Present)
    assert listing.price_amount.value.value == MoneyAmount(9_500_025)
    assert isinstance(listing.total_area, Present)
    assert listing.total_area.value.value == Area(4_000)
    assert isinstance(listing.rooms, Present)
    assert listing.rooms.value.value == RoomCount(0)


def test_required_values_have_independent_full_provenance_and_rule_versions() -> None:
    listing = _success(_snapshot()).listing
    provenances = (
        (
            listing.reference.provenance,
            "publication_id",
            "alpha-001",
            "$.listings[0].publication_id",
            "fixture-publication-id@1",
        ),
        (
            listing.source_url.provenance,
            "url",
            "https://listings.fixture.example/offers/alpha-001",
            "$.listings[0].url",
            "fixture-source-url@1",
        ),
        (
            listing.observed_at.provenance,
            "observed_at",
            "2026-02-03T10:15:30.123456+03:00",
            "$.listings[0].observed_at",
            "fixture-observed-at@1",
        ),
    )
    for provenance, source_field, raw_value, json_path, rule in provenances:
        assert provenance.source_id == SourceId("fixture_portal")
        assert provenance.publication_id == PublicationId("alpha-001")
        assert provenance.source_field == source_field
        assert provenance.raw_value == raw_value
        assert provenance.input_path.json_path == json_path
        assert provenance.observed_at == listing.observed_at.value
        assert provenance.normalization_rule_version.value == rule


def test_every_present_field_keeps_its_own_full_provenance() -> None:
    listing = _success(_snapshot()).listing
    outcomes = (
        (
            listing.location_text,
            "location_text",
            "  Invented Quarter   Alpha  ",
            "fixture-location-text@1",
        ),
        (listing.price_amount, "price_major", "110000.00", "fixture-price-major@1"),
        (listing.currency, "currency", "RUB", "fixture-currency@1"),
        (listing.total_area, "total_area_sqm", "52.50", "fixture-total-area-sqm@1"),
        (listing.rooms, "rooms", "2", "fixture-rooms@1"),
    )
    for outcome, source_field, raw_value, rule in outcomes:
        assert isinstance(outcome, Present)
        provenance = outcome.value.provenance
        assert isinstance(provenance, ValueProvenance)
        assert provenance.source_id == SourceId("fixture_portal")
        assert provenance.publication_id == PublicationId("alpha-001")
        assert provenance.source_field == source_field
        assert provenance.raw_value == raw_value
        assert provenance.input_path.json_path == f"$.listings[0].{source_field}"
        assert provenance.observed_at == listing.observed_at.value
        assert provenance.normalization_rule_version.value == rule


@pytest.mark.parametrize(
    ("raw_value", "canonical"),
    (
        ("2026-02-03T10:15:30Z", "2026-02-03T10:15:30.000000Z"),
        ("2026-02-03T10:15:30.1Z", "2026-02-03T10:15:30.100000Z"),
        ("2026-02-03T10:15:30.123456Z", "2026-02-03T10:15:30.123456Z"),
        ("2026-02-03T10:15:30+03:00", "2026-02-03T07:15:30.000000Z"),
        ("2026-02-03T10:15:30-04:30", "2026-02-03T14:45:30.000000Z"),
    ),
)
def test_rfc3339_supported_boundaries_preserve_microseconds(
    raw_value: str,
    canonical: str,
) -> None:
    listing = _success(_snapshot(observed_at=raw_value)).listing

    assert listing.observed_at.value.to_rfc3339() == canonical


@pytest.mark.parametrize(
    "raw_value",
    (
        "2026-02-03T10:15:30",
        "2026-02-03T10:15Z",
        "2026-02-03 10:15:30Z",
        "2026-02-03T10:15:60Z",
        "2026-02-03T10:15:30.1234567Z",
        "2026-02-30T10:15:30Z",
        "2026-02-03T24:00:00Z",
        "2026-02-03T10:15:30+24:00",
        "0001-01-01T00:00:00+23:59",
        "9999-12-31T23:59:59-23:59",
    ),
)
def test_invalid_rfc3339_has_exact_nrm_001_diagnostic(raw_value: str) -> None:
    result = _failure(_snapshot(observed_at=raw_value))

    assert _issue_triples(result) == [
        ("NORMALIZATION", "invalid_value", "$.listings[0].observed_at")
    ]


def test_unicode_whitespace_is_collapsed_without_other_text_changes() -> None:
    listing = _success(_snapshot(location_text="\u2003Invented\tQuarter\nAlpha\u00a0")).listing

    assert isinstance(listing.location_text, Present)
    assert listing.location_text.value.value == LocationText("Invented Quarter Alpha")
    assert (
        listing.location_text.value.provenance.raw_value == "\u2003Invented\tQuarter\nAlpha\u00a0"
    )


@pytest.mark.parametrize("length", (1, 500))
def test_location_code_point_boundaries_are_accepted(length: int) -> None:
    listing = _success(_snapshot(location_text="Я" * length)).listing

    assert isinstance(listing.location_text, Present)
    assert len(listing.location_text.value.value.value) == length


@pytest.mark.parametrize("raw_value", ("   ", "Я" * 501))
def test_invalid_location_has_exact_nrm_002_diagnostic(raw_value: str) -> None:
    result = _failure(_snapshot(location_text=raw_value))

    assert _issue_triples(result) == [
        ("NORMALIZATION", "invalid_value", "$.listings[0].location_text")
    ]


@pytest.mark.parametrize(
    ("raw_value", "amount_minor"),
    (("110000.00", 11_000_000), ("95000.25", 9_500_025), ("1", 100), ("0.01", 1)),
)
def test_price_is_scaled_exactly_without_float(raw_value: str, amount_minor: int) -> None:
    listing = _success(_snapshot(price_major=raw_value)).listing

    assert isinstance(listing.price_amount, Present)
    assert listing.price_amount.value.value == MoneyAmount(amount_minor)


@pytest.mark.parametrize("raw_value", ("0.00", "-1.00", "92233720368547758.08"))
def test_price_range_has_exact_nrm_003_diagnostic(raw_value: str) -> None:
    result = _failure(_snapshot(price_major=raw_value))

    assert _issue_triples(result) == [
        ("NORMALIZATION", "out_of_range", "$.listings[0].price_major")
    ]


@pytest.mark.parametrize("raw_value", ("1.000", "+1.00", "1e2", "1,00", " 1.00"))
def test_invalid_price_lexeme_is_rejected(raw_value: str) -> None:
    result = _failure(_snapshot(price_major=raw_value))

    assert _issue_triples(result) == [
        ("NORMALIZATION", "invalid_value", "$.listings[0].price_major")
    ]


def test_both_money_parts_missing_are_successful_independent_missing_states() -> None:
    listing = _success(_snapshot(price_major=None, currency=None)).listing

    assert isinstance(listing.price_amount, Missing)
    assert isinstance(listing.currency, Missing)
    assert listing.price_amount.provenance.input_path.json_path == "$.listings[0].price_major"
    assert listing.currency.provenance.input_path.json_path == "$.listings[0].currency"


@pytest.mark.parametrize(
    ("price_major", "currency"),
    ((None, "RUB"), ("110000.00", None)),
)
def test_one_money_part_missing_has_one_exact_nrm_004_diagnostic(
    price_major: str | None,
    currency: str | None,
) -> None:
    result = _failure(_snapshot(price_major=price_major, currency=currency))

    assert _issue_triples(result) == [("NORMALIZATION", "incomplete_money", "$.listings[0]")]


@pytest.mark.parametrize("raw_value", ("rub", "RU", "RUB ", "РУБ"))
def test_invalid_currency_lexeme_is_rejected(raw_value: str) -> None:
    result = _failure(_snapshot(currency=raw_value))

    assert _issue_triples(result) == [("NORMALIZATION", "invalid_value", "$.listings[0].currency")]


@pytest.mark.parametrize(
    ("raw_value", "hundredths"),
    (("52.50", 5_250), ("40", 4_000), ("61.75", 6_175), ("1.2300", 123)),
)
def test_area_is_scaled_exactly_and_allows_only_extra_zero_precision(
    raw_value: str,
    hundredths: int,
) -> None:
    listing = _success(_snapshot(total_area_sqm=raw_value)).listing

    assert isinstance(listing.total_area, Present)
    assert listing.total_area.value.value == Area(hundredths)


def test_area_precision_loss_has_exact_nrm_006_diagnostic() -> None:
    result = _failure(_snapshot(total_area_sqm="47.125"))

    assert _issue_triples(result) == [
        ("NORMALIZATION", "precision_loss", "$.listings[0].total_area_sqm")
    ]


@pytest.mark.parametrize("raw_value", ("0", "-1.00", "92233720368547758.08"))
def test_area_range_has_exact_nrm_007_diagnostic(raw_value: str) -> None:
    result = _failure(_snapshot(total_area_sqm=raw_value))

    assert _issue_triples(result) == [
        ("NORMALIZATION", "out_of_range", "$.listings[0].total_area_sqm")
    ]


@pytest.mark.parametrize("raw_value", ("1e2", "+1", ".5", "1,5", " 1"))
def test_invalid_area_lexeme_is_rejected(raw_value: str) -> None:
    result = _failure(_snapshot(total_area_sqm=raw_value))

    assert _issue_triples(result) == [
        ("NORMALIZATION", "invalid_value", "$.listings[0].total_area_sqm")
    ]


@pytest.mark.parametrize(("raw_value", "count"), (("studio", 0), ("1", 1), ("99", 99), ("01", 1)))
def test_room_tokens_normalize_to_canonical_integers(raw_value: str, count: int) -> None:
    listing = _success(_snapshot(rooms=raw_value)).listing

    assert isinstance(listing.rooms, Present)
    assert listing.rooms.value.value == RoomCount(count)


def test_rooms_100_has_exact_nrm_008_diagnostic() -> None:
    result = _failure(_snapshot(rooms="100"))

    assert _issue_triples(result) == [("NORMALIZATION", "out_of_range", "$.listings[0].rooms")]


@pytest.mark.parametrize("raw_value", ("0", "00", "+1", "-1", " 1", "1 ", "١", "Studio"))
def test_invalid_room_tokens_are_not_guessed(raw_value: str) -> None:
    result = _failure(_snapshot(rooms=raw_value))

    assert _issue_triples(result) == [("NORMALIZATION", "invalid_value", "$.listings[0].rooms")]


def test_multiple_independent_issues_are_stably_sorted() -> None:
    snapshot = _snapshot(
        observed_at="2026-02-03T10:15:30",
        location_text="   ",
        price_major="0.00",
        currency="rub",
        total_area_sqm="47.125",
        rooms="100",
    )

    result = _failure(snapshot)

    assert _issue_triples(result) == [
        ("NORMALIZATION", "invalid_value", "$.listings[0].currency"),
        ("NORMALIZATION", "invalid_value", "$.listings[0].location_text"),
        ("NORMALIZATION", "invalid_value", "$.listings[0].observed_at"),
        ("NORMALIZATION", "out_of_range", "$.listings[0].price_major"),
        ("NORMALIZATION", "out_of_range", "$.listings[0].rooms"),
        ("NORMALIZATION", "precision_loss", "$.listings[0].total_area_sqm"),
    ]


def test_failure_does_not_expose_partial_listing() -> None:
    result = normalize_fixture_snapshot(
        _snapshot(location_text="   ", total_area_sqm="47.125"),
        FIXTURE_NORMALIZATION_RULES_V1,
    )

    assert isinstance(result, NormalizationFailure)
    assert not hasattr(result, "listing")


def test_result_rules_and_nested_provenance_are_immutable() -> None:
    result = _success(_snapshot())

    with pytest.raises(FrozenInstanceError):
        _assign_listing(result)
    with pytest.raises(FrozenInstanceError):
        _assign_provenance_raw_value(result.listing.reference.provenance)
    with pytest.raises(FrozenInstanceError):
        _assign_provenance_raw_value(FIXTURE_NORMALIZATION_RULES_V1)


def test_loader_adapter_and_normalizer_integrate_offline_for_static_fixtures() -> None:
    load_result = load_fixture_source_batch(VALID_BATCH)
    assert isinstance(load_result, SourceBatchLoadSuccess)
    adaptation_result = adapt_fixture_source_batch(load_result.batch)
    assert isinstance(adaptation_result, FixtureSourceAdaptationSuccess)

    results = tuple(
        normalize_fixture_snapshot(snapshot, FIXTURE_NORMALIZATION_RULES_V1)
        for snapshot in adaptation_result.batch.snapshots
    )

    assert len(results) == 4
    assert all(isinstance(result, NormalizationSuccess) for result in results)

    atomic_load_result = load_fixture_source_batch(ATOMIC_BATCH)
    assert isinstance(atomic_load_result, SourceBatchLoadSuccess)
    atomic_adaptation_result = adapt_fixture_source_batch(atomic_load_result.batch)
    assert isinstance(atomic_adaptation_result, FixtureSourceAdaptationSuccess)

    second_result = normalize_fixture_snapshot(
        atomic_adaptation_result.batch.snapshots[1],
        FIXTURE_NORMALIZATION_RULES_V1,
    )
    assert isinstance(second_result, NormalizationFailure)
    assert _issue_triples(second_result) == [
        ("NORMALIZATION", "precision_loss", "$.listings[1].total_area_sqm")
    ]
