from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

import pytest

from real_estate_parser import (
    Area,
    CollectionBuildSuccess,
    CollectionSnapshot,
    Currency,
    FixtureSourceAdaptationSuccess,
    InputLocation,
    MissingField,
    Money,
    MoneyAmount,
    NormalizationSuccess,
    NormalizedListing,
    PublicationId,
    PublicationRef,
    RawField,
    RoomCount,
    SearchCriteria,
    SearchCriteriaLoadSuccess,
    SearchMatch,
    SearchResult,
    SourceBatchLoadSuccess,
    SourceId,
    SourcePublicationSnapshot,
    Unsupported,
    adapt_fixture_source_batch,
    build_fixture_collection,
    load_fixture_source_batch,
    load_search_criteria,
    normalize_fixture_snapshot,
    search_collection,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v1"
VALID_BATCH = FIXTURE_ROOT / "valid" / "listings-comprehensive.json"
CRITERIA_ROOT = FIXTURE_ROOT / "criteria"


def _raw(record_index: int, source_field: str, value: str) -> RawField:
    return RawField(value, InputLocation("listings", record_index, (source_field,)))


def _optional(record_index: int, source_field: str, value: str | None) -> RawField | MissingField:
    if value is None:
        return MissingField(InputLocation("listings", record_index, (source_field,)))
    return _raw(record_index, source_field, value)


def _listing(
    publication_id: str,
    *,
    record_index: int = 0,
    source_id: str = "fixture_portal",
    source_url: str | None = None,
    observed_at: str = "2026-02-03T10:15:30Z",
    price_major: str | None = "100.00",
    currency: str | None = "RUB",
    total_area_sqm: str | None = "50.00",
    rooms: str | None = "2",
) -> NormalizedListing:
    snapshot = SourcePublicationSnapshot(
        reference=PublicationRef(SourceId(source_id), PublicationId(publication_id)),
        source_url=_raw(
            record_index,
            "url",
            source_url or f"https://listings.fixture.example/offers/{publication_id}",
        ),
        observed_at=_raw(record_index, "observed_at", observed_at),
        location_text=_optional(record_index, "location_text", "Invented Quarter"),
        price_amount=_optional(record_index, "price_major", price_major),
        currency=_optional(record_index, "currency", currency),
        total_area=_optional(record_index, "total_area_sqm", total_area_sqm),
        rooms=_optional(record_index, "rooms", rooms),
        input_location=InputLocation("listings", record_index),
    )
    result = normalize_fixture_snapshot(snapshot)
    assert isinstance(result, NormalizationSuccess)
    return result.listing


def _ids(result: SearchResult) -> tuple[str, ...]:
    return tuple(match.listing.reference.value.publication_id.value for match in result.matches)


def _assign_listing(target: Any) -> None:
    target.listing = target.listing


def _assign_matches(target: Any) -> None:
    target.matches = target.matches


def test_search_types_are_immutable_and_keep_original_objects_and_provenance() -> None:
    listing = _listing("identity-001")
    collection = CollectionSnapshot((listing,))
    criteria = SearchCriteria()
    match = SearchMatch(listing=listing)
    direct_result = SearchResult(criteria=criteria, matches=(match,))
    result = search_collection(collection, criteria)

    assert result.criteria is criteria
    assert result.matches == (match,)
    assert type(result.matches) is tuple
    assert result.matches[0].listing is listing
    assert result.matches[0].listing.reference.provenance is listing.reference.provenance
    assert collection.listings == (listing,)
    with pytest.raises(FrozenInstanceError):
        _assign_listing(match)
    with pytest.raises(FrozenInstanceError):
        _assign_matches(direct_result)


def test_maximum_price_matches_only_complete_same_currency_money_at_or_below_limit() -> None:
    collection = CollectionSnapshot(
        listings=(
            _listing("above", price_major="100.01"),
            _listing("exact", price_major="100.00"),
            _listing("below", price_major="99.99"),
            _listing("missing", price_major=None, currency=None),
            _listing("unsupported", price_major="50.00", currency="USD"),
        )
    )
    criteria = SearchCriteria(maximum_price=Money(MoneyAmount(10_000), Currency("RUB")))

    assert _ids(search_collection(collection, criteria)) == ("below", "exact")


def test_minimum_area_matches_present_values_at_or_above_exact_boundary() -> None:
    unsupported = _listing("unsupported-area", currency="USD")
    assert isinstance(unsupported.currency, Unsupported)
    unsupported = replace(unsupported, total_area=unsupported.currency)
    collection = CollectionSnapshot(
        listings=(
            _listing("below", total_area_sqm="49.99"),
            _listing("exact", total_area_sqm="50.00"),
            _listing("above", total_area_sqm="50.01"),
            _listing("missing", total_area_sqm=None),
            unsupported,
        )
    )

    result = search_collection(collection, SearchCriteria(minimum_total_area=Area(5_000)))

    assert _ids(result) == ("above", "exact")


def test_allowed_rooms_matches_present_members_and_treats_studio_as_zero() -> None:
    unsupported = _listing("unsupported-rooms", currency="USD")
    assert isinstance(unsupported.currency, Unsupported)
    unsupported = replace(unsupported, rooms=unsupported.currency)
    collection = CollectionSnapshot(
        listings=(
            _listing("two", rooms="2"),
            _listing("one", rooms="1"),
            _listing("studio", rooms="studio"),
            _listing("missing", rooms=None),
            unsupported,
        )
    )
    criteria = SearchCriteria(allowed_rooms=frozenset((RoomCount(0), RoomCount(2))))

    assert _ids(search_collection(collection, criteria)) == ("studio", "two")


def test_all_three_criteria_are_conjunctive() -> None:
    collection = CollectionSnapshot(
        listings=(
            _listing("all", price_major="100.00", total_area_sqm="50.00", rooms="2"),
            _listing("price", price_major="100.01", total_area_sqm="50.00", rooms="2"),
            _listing("area", price_major="100.00", total_area_sqm="49.99", rooms="2"),
            _listing("rooms", price_major="100.00", total_area_sqm="50.00", rooms="1"),
        )
    )
    criteria = SearchCriteria(
        maximum_price=Money(MoneyAmount(10_000), Currency("RUB")),
        minimum_total_area=Area(5_000),
        allowed_rooms=frozenset((RoomCount(2),)),
    )

    assert _ids(search_collection(collection, criteria)) == ("all",)


def test_absent_criteria_return_every_listing_and_ignore_unrelated_field_states() -> None:
    missing = _listing(
        "missing",
        price_major=None,
        currency=None,
        total_area_sqm=None,
        rooms=None,
    )
    unsupported_currency = _listing("unsupported", currency="USD", rooms="1")
    collection = CollectionSnapshot(listings=(unsupported_currency, missing))

    assert _ids(search_collection(collection, SearchCriteria())) == ("missing", "unsupported")
    assert _ids(search_collection(collection, SearchCriteria(minimum_total_area=Area(5_000)))) == (
        "unsupported",
    )
    assert _ids(
        search_collection(
            collection,
            SearchCriteria(allowed_rooms=frozenset((RoomCount(1),))),
        )
    ) == ("unsupported",)


def test_valid_search_with_no_matches_is_successful_and_empty() -> None:
    criteria = SearchCriteria(maximum_price=Money(MoneyAmount(1), Currency("RUB")))

    result = search_collection(CollectionSnapshot((_listing("too-expensive"),)), criteria)

    assert result == SearchResult(criteria=criteria, matches=())


def test_full_composite_order_is_independent_of_collection_order() -> None:
    ordered = (
        _listing("amount-low", source_id="z_source", price_major="1.00"),
        _listing("Case", source_id="a_source", price_major="2.00"),
        _listing("case", source_id="a_source", price_major="2.00"),
        _listing("source", source_id="b_source", price_major="2.00"),
        _listing(
            "same",
            source_id="same_source",
            price_major="2.00",
            observed_at="2026-01-01T00:00:00Z",
            source_url="https://a.example/earlier",
        ),
        _listing(
            "same",
            source_id="same_source",
            price_major="2.00",
            observed_at="2026-01-02T00:00:00Z",
            source_url="https://a.example/first",
        ),
        _listing(
            "same",
            source_id="same_source",
            price_major="2.00",
            observed_at="2026-01-02T00:00:00Z",
            source_url="https://b.example/second",
        ),
        _listing("missing-money", price_major=None, currency=None),
        _listing("unsupported-money", currency="USD"),
    )
    reverse_result = search_collection(
        CollectionSnapshot(tuple(reversed(ordered))), SearchCriteria()
    )
    shuffled_result = search_collection(
        CollectionSnapshot(
            (
                ordered[5],
                ordered[8],
                ordered[2],
                ordered[0],
                *ordered[3:5],
                ordered[6],
                ordered[1],
                ordered[7],
            )
        ),
        SearchCriteria(),
    )

    assert tuple(match.listing for match in reverse_result.matches) == ordered
    assert shuffled_result.matches == reverse_result.matches
    assert _ids(reverse_result) == (
        "amount-low",
        "Case",
        "case",
        "source",
        "same",
        "same",
        "same",
        "missing-money",
        "unsupported-money",
    )


def test_impossible_present_and_missing_money_pair_fails_fast() -> None:
    present = _listing("inconsistent")
    missing = _listing("missing", price_major=None, currency=None)
    inconsistent = replace(present, currency=missing.currency)

    with pytest.raises(ValueError, match="inconsistent normalized money pair"):
        search_collection(CollectionSnapshot((inconsistent,)), SearchCriteria())


def _fixture_search(criteria_filename: str) -> SearchResult:
    load_result = load_fixture_source_batch(VALID_BATCH)
    assert isinstance(load_result, SourceBatchLoadSuccess)
    adaptation_result = adapt_fixture_source_batch(load_result.batch)
    assert isinstance(adaptation_result, FixtureSourceAdaptationSuccess)
    collection_result = build_fixture_collection(adaptation_result.batch)
    assert isinstance(collection_result, CollectionBuildSuccess)
    criteria_result = load_search_criteria(CRITERIA_ROOT / criteria_filename)
    assert isinstance(criteria_result, SearchCriteriaLoadSuccess)
    return search_collection(collection_result.snapshot, criteria_result.criteria)


@pytest.mark.parametrize(
    ("criteria_filename", "expected_ids"),
    (
        ("all-three.json", ("studio-002", "alpha-001")),
        ("partial-area.json", ("currency-004",)),
        ("none.json", ("studio-002", "alpha-001", "missing-003", "currency-004")),
        ("no-match.json", ()),
    ),
)
def test_static_boundaries_integrate_offline_without_output_mapping(
    criteria_filename: str,
    expected_ids: tuple[str, ...],
) -> None:
    assert _ids(_fixture_search(criteria_filename)) == expected_ids
