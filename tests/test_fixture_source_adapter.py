from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from real_estate_parser import (
    FixtureSourceAdaptationFailure,
    FixtureSourceAdaptationSuccess,
    InputLocation,
    MissingField,
    MissingSourceField,
    PublicationId,
    RawField,
    SourceBatchLoadSuccess,
    SourceId,
    ValidatedSourceBatch,
    ValidatedSourceField,
    ValidatedSourceListing,
    adapt_fixture_source_batch,
    load_fixture_source_batch,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v1"
VALID_BATCH = FIXTURE_ROOT / "valid" / "listings-comprehensive.json"


def _field(record_index: int | None, name: str, value: str) -> ValidatedSourceField:
    return ValidatedSourceField(
        value=value,
        location=InputLocation("listings", record_index, (name,)),
    )


def _optional_field(
    record_index: int,
    name: str,
    value: str | None,
) -> ValidatedSourceField | MissingSourceField:
    location = InputLocation("listings", record_index, (name,))
    if value is None:
        return MissingSourceField(location=location)
    return ValidatedSourceField(value=value, location=location)


def _listing(
    record_index: int,
    publication_id: str = "alpha-001",
    *,
    url: str | None = None,
    observed_at: str = "2026-02-03T10:15:30.123456+03:00",
    location_text: str | None = "  Invented Quarter   Alpha  ",
    price_major: str | None = "110000.00",
    currency: str | None = "RUB",
    total_area_sqm: str | None = "52.50",
    rooms: str | None = "2",
) -> ValidatedSourceListing:
    source_url = f"https://listings.fixture.example/offers/{publication_id}" if url is None else url
    return ValidatedSourceListing(
        publication_id=_field(record_index, "publication_id", publication_id),
        url=_field(record_index, "url", source_url),
        observed_at=_field(record_index, "observed_at", observed_at),
        location_text=_optional_field(record_index, "location_text", location_text),
        price_major=_optional_field(record_index, "price_major", price_major),
        currency=_optional_field(record_index, "currency", currency),
        total_area_sqm=_optional_field(record_index, "total_area_sqm", total_area_sqm),
        rooms=_optional_field(record_index, "rooms", rooms),
        location=InputLocation("listings", record_index),
    )


def _batch(
    *listings: ValidatedSourceListing,
    source: str = "fixture_portal",
) -> ValidatedSourceBatch:
    return ValidatedSourceBatch(
        schema_version=_field(None, "schema_version", "fixture-source-batch@1"),
        source=_field(None, "source", source),
        listings=tuple(listings),
    )


def _comprehensive_batch() -> ValidatedSourceBatch:
    return _batch(
        _listing(0),
        _listing(
            1,
            "missing-003",
            observed_at="2026-02-01T00:00:00Z",
            location_text=None,
            price_major=None,
            currency=None,
            total_area_sqm=None,
            rooms=None,
        ),
        _listing(
            2,
            "currency-004",
            observed_at="2026-02-04T23:30:00.5-04:00",
            location_text="Invented Quarter Currency",
            price_major="120000.00",
            currency="USD",
            total_area_sqm="61.75",
            rooms="1",
        ),
        _listing(
            3,
            "studio-002",
            observed_at="2026-02-02T08:00:00+05:30",
            location_text="Invented Quarter Studio",
            price_major="95000.25",
            currency="RUB",
            total_area_sqm="40",
            rooms="studio",
        ),
    )


def _success(batch: ValidatedSourceBatch) -> FixtureSourceAdaptationSuccess:
    result = adapt_fixture_source_batch(batch)
    assert isinstance(result, FixtureSourceAdaptationSuccess)
    return result


def _failure(batch: ValidatedSourceBatch) -> FixtureSourceAdaptationFailure:
    result = adapt_fixture_source_batch(batch)
    assert isinstance(result, FixtureSourceAdaptationFailure)
    return result


def _issue_triples(
    result: FixtureSourceAdaptationFailure,
) -> list[tuple[str, str, str]]:
    return [(issue.category, issue.code, issue.location.json_path) for issue in result.issues]


def _assign_snapshots(target: Any) -> None:
    target.snapshots = ()


def test_comprehensive_batch_becomes_four_ordered_neutral_snapshots() -> None:
    source_batch = _comprehensive_batch()
    snapshots = _success(source_batch).batch.snapshots

    assert [snapshot.reference.source_id.value for snapshot in snapshots] == [
        "fixture_portal",
        "fixture_portal",
        "fixture_portal",
        "fixture_portal",
    ]
    assert [snapshot.reference.publication_id.value for snapshot in snapshots] == [
        "alpha-001",
        "missing-003",
        "currency-004",
        "studio-002",
    ]
    assert [snapshot.input_location for snapshot in snapshots] == [
        listing.location for listing in source_batch.listings
    ]


def test_raw_and_missing_fields_preserve_values_and_location_objects() -> None:
    source_batch = _comprehensive_batch()
    snapshots = _success(source_batch).batch.snapshots
    first_source = source_batch.listings[0]
    first = snapshots[0]

    pairs = (
        (first.source_url, first_source.url),
        (first.observed_at, first_source.observed_at),
        (first.location_text, first_source.location_text),
        (first.price_amount, first_source.price_major),
        (first.currency, first_source.currency),
        (first.total_area, first_source.total_area_sqm),
        (first.rooms, first_source.rooms),
    )
    for neutral, source in pairs:
        assert isinstance(neutral, RawField)
        assert isinstance(source, ValidatedSourceField)
        assert neutral.value == source.value
        assert neutral.location is source.location

    missing_source = source_batch.listings[1]
    missing = snapshots[1]
    missing_pairs = (
        (missing.location_text, missing_source.location_text),
        (missing.price_amount, missing_source.price_major),
        (missing.currency, missing_source.currency),
        (missing.total_area, missing_source.total_area_sqm),
        (missing.rooms, missing_source.rooms),
    )
    for neutral, source in missing_pairs:
        assert isinstance(neutral, MissingField)
        assert isinstance(source, MissingSourceField)
        assert neutral.location is source.location


def test_neutral_result_is_immutable() -> None:
    batch = _success(_batch(_listing(0))).batch

    with pytest.raises(FrozenInstanceError):
        _assign_snapshots(batch)


@pytest.mark.parametrize("value", ("a", "0", "fixture_portal", "a" * 64))
def test_source_id_accepts_the_contract_format(value: str) -> None:
    assert SourceId(value).value == value


@pytest.mark.parametrize("value", ("", "A", "-fixture", "a" * 65, "источник"))
def test_source_id_rejects_values_outside_the_contract_format(value: str) -> None:
    with pytest.raises(ValueError, match="invalid source id"):
        SourceId(value)


def test_source_mismatch_has_exact_adp_003_diagnostic() -> None:
    result = _failure(_batch(_listing(0), source="other_fixture"))

    assert _issue_triples(result) == [("SOURCE_ADAPTER", "source_mismatch", "$.source")]


@pytest.mark.parametrize("publication_id", ("", "bad id"))
def test_invalid_publication_id_has_only_identifier_diagnostic(
    publication_id: str,
) -> None:
    listing = _listing(
        0,
        publication_id,
        url="https://listings.fixture.example/offers/alpha-001",
    )

    result = _failure(_batch(listing))

    assert _issue_triples(result) == [
        ("SOURCE_ADAPTER", "inconsistent_record", "$.listings[0].publication_id")
    ]


@pytest.mark.parametrize("length", (1, 128))
def test_publication_id_boundary_lengths_are_accepted(length: int) -> None:
    publication_id = "A" * length

    snapshot = _success(_batch(_listing(0, publication_id))).batch.snapshots[0]

    assert snapshot.reference.publication_id == PublicationId(publication_id)


@pytest.mark.parametrize(
    "publication_id",
    (
        "A" * 129,
        "идентификатор",
        "bad/id",
        "bad%id",
        "bad@id",
    ),
)
def test_publication_id_rejects_length_unicode_and_punctuation(
    publication_id: str,
) -> None:
    result = _failure(
        _batch(
            _listing(
                0,
                publication_id,
                url="https://listings.fixture.example/offers/alpha-001",
            )
        )
    )

    assert _issue_triples(result) == [
        ("SOURCE_ADAPTER", "inconsistent_record", "$.listings[0].publication_id")
    ]


@pytest.mark.parametrize(
    "url",
    (
        "http://listings.fixture.example/offers/alpha-001",
        "/offers/alpha-001",
        "https://other.example/offers/alpha-001",
        "https://user@listings.fixture.example/offers/alpha-001",
        "https://listings.fixture.example:443/offers/alpha-001",
        "https://listings.fixture.example/offers/alpha-001?view=full",
        "https://listings.fixture.example/offers/alpha-001#details",
        "https://listings.fixture.example/offers/альфа-001",
        "https://listings.fixture.example/listings/alpha-001",
        "https://listings.fixture.example/offers/other-002",
        "https://listings.fixture.example/offers/alpha%2D001",
    ),
)
def test_invalid_url_matrix_has_exact_adp_002_diagnostic(url: str) -> None:
    result = _failure(_batch(_listing(0, url=url)))

    assert _issue_triples(result) == [("SOURCE_ADAPTER", "invalid_source_url", "$.listings[0].url")]


def test_valid_url_and_case_sensitive_publication_id_are_unchanged() -> None:
    publication_id = "Case.Sensitive:ID_1-2"
    url = f"https://listings.fixture.example/offers/{publication_id}"

    snapshot = _success(_batch(_listing(0, publication_id, url=url))).batch.snapshots[0]

    assert snapshot.reference.publication_id.value == publication_id
    assert snapshot.source_url.value == url


def test_https_scheme_is_compared_by_standard_url_semantics_and_preserved() -> None:
    url = "HTTPS://listings.fixture.example/offers/alpha-001"

    snapshot = _success(_batch(_listing(0, url=url))).batch.snapshots[0]

    assert snapshot.source_url.value == url


def test_independently_invalid_url_is_reported_with_invalid_identifier() -> None:
    result = _failure(
        _batch(
            _listing(
                0,
                "bad id",
                url="http://listings.fixture.example/offers/alpha-001",
            )
        )
    )

    assert _issue_triples(result) == [
        ("SOURCE_ADAPTER", "inconsistent_record", "$.listings[0].publication_id"),
        ("SOURCE_ADAPTER", "invalid_source_url", "$.listings[0].url"),
    ]


@pytest.mark.parametrize(
    ("price_major", "currency", "missing_attribute"),
    ((None, "RUB", "price_amount"), ("110000.00", None, "currency")),
)
def test_one_missing_money_component_is_transferred_successfully(
    price_major: str | None,
    currency: str | None,
    missing_attribute: str,
) -> None:
    snapshot = _success(
        _batch(_listing(0, price_major=price_major, currency=currency))
    ).batch.snapshots[0]

    assert isinstance(getattr(snapshot, missing_attribute), MissingField)


def test_normalization_specific_values_remain_raw_without_adapter_errors() -> None:
    listing = _listing(
        0,
        observed_at="2026-02-03T10:15:30",
        location_text="   ",
        price_major="-1.00",
        currency="USD",
        total_area_sqm="47.125",
        rooms="100",
    )

    snapshot = _success(_batch(listing)).batch.snapshots[0]

    assert snapshot.observed_at.value == "2026-02-03T10:15:30"
    assert isinstance(snapshot.location_text, RawField)
    assert snapshot.location_text.value == "   "
    assert isinstance(snapshot.price_amount, RawField)
    assert snapshot.price_amount.value == "-1.00"
    assert isinstance(snapshot.currency, RawField)
    assert snapshot.currency.value == "USD"
    assert isinstance(snapshot.total_area, RawField)
    assert snapshot.total_area.value == "47.125"
    assert isinstance(snapshot.rooms, RawField)
    assert snapshot.rooms.value == "100"


def test_multiple_independent_issues_have_stable_contract_order() -> None:
    result = _failure(
        _batch(
            _listing(
                2,
                "later-002",
                url="https://other.example/offers/later-002",
            ),
            _listing(
                0,
                "bad id",
                url="http://listings.fixture.example/offers/alpha-001",
            ),
            source="other_fixture",
        )
    )

    assert _issue_triples(result) == [
        ("SOURCE_ADAPTER", "source_mismatch", "$.source"),
        ("SOURCE_ADAPTER", "inconsistent_record", "$.listings[0].publication_id"),
        ("SOURCE_ADAPTER", "invalid_source_url", "$.listings[0].url"),
        ("SOURCE_ADAPTER", "invalid_source_url", "$.listings[2].url"),
    ]


def test_failure_does_not_expose_a_partial_batch() -> None:
    result = adapt_fixture_source_batch(
        _batch(
            _listing(0),
            _listing(1, "broken-002", url="https://other.example/offers/broken-002"),
        )
    )

    assert isinstance(result, FixtureSourceAdaptationFailure)
    assert not hasattr(result, "batch")


def test_duplicate_publication_refs_are_left_for_the_collection_boundary() -> None:
    result = _success(_batch(_listing(0), _listing(1)))

    assert len(result.batch.snapshots) == 2
    assert result.batch.snapshots[0].reference == result.batch.snapshots[1].reference


def test_loader_and_adapter_integrate_offline_on_the_static_valid_fixture() -> None:
    load_result = load_fixture_source_batch(VALID_BATCH)
    assert isinstance(load_result, SourceBatchLoadSuccess)

    result = adapt_fixture_source_batch(load_result.batch)

    assert isinstance(result, FixtureSourceAdaptationSuccess)
    assert len(result.batch.snapshots) == 4
