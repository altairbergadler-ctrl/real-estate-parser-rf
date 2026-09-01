from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import Any

import pytest

from real_estate_parser import (
    Area,
    CollectionBuildSuccess,
    Currency,
    FixtureSourceAdaptationSuccess,
    InputLocation,
    MissingDocument,
    MissingField,
    MissingProvenanceDocument,
    Money,
    MoneyAmount,
    MoneyDocument,
    NormalizationSuccess,
    PresentDocument,
    ProvidedProvenanceDocument,
    PublicationId,
    PublicationRef,
    PublicationRefDocument,
    RawField,
    RoomCount,
    SearchCriteria,
    SearchCriteriaDocument,
    SearchCriteriaLoadSuccess,
    SearchMatch,
    SearchMatchDocument,
    SearchResult,
    SearchResultDocument,
    SourceBatchLoadSuccess,
    SourceId,
    SourcePublicationSnapshot,
    TracedValueDocument,
    UnsupportedDocument,
    adapt_fixture_source_batch,
    build_fixture_collection,
    load_fixture_source_batch,
    load_search_criteria,
    map_search_result,
    normalize_fixture_snapshot,
    search_collection,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v1"
VALID_BATCH = FIXTURE_ROOT / "valid" / "listings-comprehensive.json"
CRITERIA_ROOT = FIXTURE_ROOT / "criteria"


def _assign_attribute(target: Any, attribute: str) -> None:
    setattr(target, attribute, getattr(target, attribute))


def _raw(record_index: int, source_field: str, value: str) -> RawField:
    return RawField(value, InputLocation("listings", record_index, (source_field,)))


def _optional(record_index: int, source_field: str, value: str | None) -> RawField | MissingField:
    if value is None:
        return MissingField(InputLocation("listings", record_index, (source_field,)))
    return _raw(record_index, source_field, value)


def _listing(
    publication_id: str = "alpha-001",
    *,
    record_index: int = 0,
    observed_at: str = "2026-02-03T10:15:30.123456+03:00",
    location_text: str | None = "  Invented Quarter   Alpha  ",
    price_major: str | None = "110000.00",
    currency: str | None = "RUB",
    total_area_sqm: str | None = "52.50",
    rooms: str | None = "2",
) -> NormalizationSuccess:
    snapshot = SourcePublicationSnapshot(
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
    result = normalize_fixture_snapshot(snapshot)
    assert isinstance(result, NormalizationSuccess)
    return result


def _document_for_listing(
    listing: NormalizationSuccess,
    criteria: SearchCriteria | None = None,
) -> SearchResultDocument:
    return map_search_result(
        SearchResult(
            criteria=criteria or SearchCriteria(),
            matches=(SearchMatch(listing=listing.listing),),
        )
    )


def _provided(
    *,
    source_field: str,
    raw_value: str,
    input_path: str,
    rule: str,
    publication_id: str = "alpha-001",
    observed_at: str = "2026-02-03T07:15:30.123456Z",
) -> ProvidedProvenanceDocument:
    return ProvidedProvenanceDocument(
        input_path=input_path,
        normalization_rule_version=rule,
        observed_at=observed_at,
        publication_id=publication_id,
        raw_value=raw_value,
        source_field=source_field,
        source_id="fixture_portal",
    )


def test_mandatory_and_every_present_value_map_to_exact_document_types() -> None:
    document = _document_for_listing(_listing())
    match = document.matches[0]

    assert document.schema_version == "search-result@1"
    assert match.publication_ref == TracedValueDocument(
        value=PublicationRefDocument(
            source_id="fixture_portal",
            publication_id="alpha-001",
        ),
        provenance=_provided(
            source_field="publication_id",
            raw_value="alpha-001",
            input_path="$.listings[0].publication_id",
            rule="fixture-publication-id@1",
        ),
    )
    assert match.source_url == TracedValueDocument(
        value="https://listings.fixture.example/offers/alpha-001",
        provenance=_provided(
            source_field="url",
            raw_value="https://listings.fixture.example/offers/alpha-001",
            input_path="$.listings[0].url",
            rule="fixture-source-url@1",
        ),
    )
    assert match.observed_at == TracedValueDocument(
        value="2026-02-03T07:15:30.123456Z",
        provenance=_provided(
            source_field="observed_at",
            raw_value="2026-02-03T10:15:30.123456+03:00",
            input_path="$.listings[0].observed_at",
            rule="fixture-observed-at@1",
        ),
    )

    assert match.location_text == PresentDocument(
        state="present",
        value="Invented Quarter Alpha",
        provenance=_provided(
            source_field="location_text",
            raw_value="  Invented Quarter   Alpha  ",
            input_path="$.listings[0].location_text",
            rule="fixture-location-text@1",
        ),
    )
    assert match.price_amount == PresentDocument(
        state="present",
        value=11_000_000,
        provenance=_provided(
            source_field="price_major",
            raw_value="110000.00",
            input_path="$.listings[0].price_major",
            rule="fixture-price-major@1",
        ),
    )
    assert match.currency == PresentDocument(
        state="present",
        value="RUB",
        provenance=_provided(
            source_field="currency",
            raw_value="RUB",
            input_path="$.listings[0].currency",
            rule="fixture-currency@1",
        ),
    )
    assert match.total_area == PresentDocument(
        state="present",
        value="52.50",
        provenance=_provided(
            source_field="total_area_sqm",
            raw_value="52.50",
            input_path="$.listings[0].total_area_sqm",
            rule="fixture-total-area-sqm@1",
        ),
    )
    assert match.rooms == PresentDocument(
        state="present",
        value=2,
        provenance=_provided(
            source_field="rooms",
            raw_value="2",
            input_path="$.listings[0].rooms",
            rule="fixture-rooms@1",
        ),
    )
    assert not hasattr(match.publication_ref, "state")
    assert not hasattr(match.source_url, "state")
    assert not hasattr(match.observed_at, "state")


def test_missing_documents_have_neither_value_nor_raw_value() -> None:
    document = _document_for_listing(
        _listing(
            "missing-003",
            record_index=1,
            observed_at="2026-02-01T00:00:00Z",
            location_text=None,
            price_major=None,
            currency=None,
            total_area_sqm=None,
            rooms=None,
        )
    )
    match = document.matches[0]
    outcomes = (
        (match.currency, "currency", "fixture-currency@1"),
        (match.location_text, "location_text", "fixture-location-text@1"),
        (match.price_amount, "price_major", "fixture-price-major@1"),
        (match.rooms, "rooms", "fixture-rooms@1"),
        (match.total_area, "total_area_sqm", "fixture-total-area-sqm@1"),
    )

    for outcome, source_field, rule in outcomes:
        assert isinstance(outcome, MissingDocument)
        assert outcome.state == "missing"
        assert not hasattr(outcome, "value")
        assert not hasattr(outcome.provenance, "raw_value")
        assert not hasattr(outcome, "__dict__")
        assert not hasattr(outcome.provenance, "__dict__")
        with pytest.raises(FrozenInstanceError):
            _assign_attribute(outcome, "state")
        with pytest.raises(FrozenInstanceError):
            _assign_attribute(outcome.provenance, "source_field")
        assert outcome.provenance == MissingProvenanceDocument(
            input_path=f"$.listings[1].{source_field}",
            normalization_rule_version=rule,
            observed_at="2026-02-01T00:00:00.000000Z",
            publication_id="missing-003",
            source_field=source_field,
            source_id="fixture_portal",
        )


def test_unsupported_document_has_reason_and_raw_value_but_no_canonical_value() -> None:
    document = _document_for_listing(
        _listing(
            "currency-004",
            record_index=2,
            observed_at="2026-02-04T23:30:00.5-04:00",
            currency="USD",
            total_area_sqm="61.75",
            rooms="1",
        )
    )
    currency = document.matches[0].currency

    assert isinstance(currency, UnsupportedDocument)
    assert currency.state == "unsupported"
    assert currency.reason_code == "unsupported_currency"
    assert not hasattr(currency, "value")
    assert not hasattr(currency, "__dict__")
    assert not hasattr(currency.provenance, "__dict__")
    with pytest.raises(FrozenInstanceError):
        _assign_attribute(currency, "reason_code")
    with pytest.raises(FrozenInstanceError):
        _assign_attribute(currency.provenance, "raw_value")
    assert currency.provenance == _provided(
        source_field="currency",
        raw_value="USD",
        input_path="$.listings[2].currency",
        rule="fixture-currency@1",
        publication_id="currency-004",
        observed_at="2026-02-05T03:30:00.500000Z",
    )


@pytest.mark.parametrize(
    ("raw_area", "expected"),
    (("0.01", "0.01"), ("40", "40.00"), ("61.75", "61.75")),
)
def test_area_uses_exact_two_decimal_string_without_float(raw_area: str, expected: str) -> None:
    match = _document_for_listing(_listing(total_area_sqm=raw_area)).matches[0]

    assert isinstance(match.total_area, PresentDocument)
    assert match.total_area.value == expected


def test_all_criteria_map_canonically_without_mutating_source_values() -> None:
    allowed_rooms = frozenset((RoomCount(99), RoomCount(0), RoomCount(2)))
    criteria = SearchCriteria(
        maximum_price=Money(MoneyAmount(11_000_000), Currency("RUB")),
        minimum_total_area=Area(4_000),
        allowed_rooms=allowed_rooms,
    )

    document = map_search_result(SearchResult(criteria=criteria, matches=()))

    assert document.criteria == SearchCriteriaDocument(
        maximum_price=MoneyDocument(
            amount_minor=11_000_000,
            currency="RUB",
        ),
        minimum_total_area="40.00",
        allowed_rooms=(0, 2, 99),
    )
    assert criteria.allowed_rooms is allowed_rooms
    assert criteria.allowed_rooms == frozenset((RoomCount(99), RoomCount(0), RoomCount(2)))


@pytest.mark.parametrize(
    ("criteria", "expected"),
    (
        (
            SearchCriteria(minimum_total_area=Area(1)),
            SearchCriteriaDocument(minimum_total_area="0.01"),
        ),
        (SearchCriteria(), SearchCriteriaDocument()),
    ),
)
def test_partial_and_absent_criteria_remain_explicitly_absent_in_python(
    criteria: SearchCriteria,
    expected: SearchCriteriaDocument,
) -> None:
    assert map_search_result(SearchResult(criteria=criteria, matches=())).criteria == expected


def test_empty_search_result_maps_successfully_to_empty_tuple() -> None:
    document = map_search_result(SearchResult(criteria=SearchCriteria(), matches=()))

    assert document == SearchResultDocument(
        schema_version="search-result@1",
        criteria=SearchCriteriaDocument(),
        matches=(),
    )
    assert type(document.matches) is tuple


def test_mapper_preserves_the_given_match_order_without_resorting() -> None:
    first = _listing("alpha-001", price_major="200.00").listing
    second = _listing("studio-002", price_major="100.00", rooms="studio").listing
    result = SearchResult(
        criteria=SearchCriteria(),
        matches=(SearchMatch(first), SearchMatch(second)),
    )

    document = map_search_result(result)

    assert tuple(match.publication_ref.value.publication_id for match in document.matches) == (
        "alpha-001",
        "studio-002",
    )
    assert tuple(match.listing for match in result.matches) == (first, second)


def test_two_mappings_are_equal_and_contain_only_contract_fields() -> None:
    result = SearchResult(
        criteria=SearchCriteria(),
        matches=(SearchMatch(_listing().listing),),
    )

    first = map_search_result(result)
    second = map_search_result(result)

    assert first == second
    assert tuple(field.name for field in fields(SearchResultDocument)) == (
        "schema_version",
        "criteria",
        "matches",
    )
    assert tuple(field.name for field in fields(SearchMatchDocument)) == (
        "currency",
        "location_text",
        "observed_at",
        "price_amount",
        "publication_ref",
        "rooms",
        "source_url",
        "total_area",
    )
    assert tuple(field.name for field in fields(ProvidedProvenanceDocument)) == (
        "input_path",
        "normalization_rule_version",
        "observed_at",
        "publication_id",
        "raw_value",
        "source_field",
        "source_id",
    )
    assert tuple(field.name for field in fields(MissingProvenanceDocument)) == (
        "input_path",
        "normalization_rule_version",
        "observed_at",
        "publication_id",
        "source_field",
        "source_id",
    )


def test_entire_document_tree_is_frozen_slotted_and_uses_only_tuples_for_sequences() -> None:
    document = _document_for_listing(
        _listing(),
        SearchCriteria(
            maximum_price=Money(MoneyAmount(11_000_000), Currency("RUB")),
            minimum_total_area=Area(4_000),
            allowed_rooms=frozenset((RoomCount(2), RoomCount(0))),
        ),
    )
    match = document.matches[0]
    assert isinstance(match.location_text, PresentDocument)
    assert document.criteria.maximum_price is not None
    targets_and_attributes = (
        (document, "schema_version"),
        (document.criteria, "allowed_rooms"),
        (document.criteria.maximum_price, "amount_minor"),
        (match, "currency"),
        (match.publication_ref, "value"),
        (match.publication_ref.value, "source_id"),
        (match.location_text, "state"),
        (match.location_text.provenance, "raw_value"),
    )

    for target, attribute in targets_and_attributes:
        assert not hasattr(target, "__dict__")
        with pytest.raises(FrozenInstanceError):
            _assign_attribute(target, attribute)
    assert type(document.matches) is tuple
    assert type(document.criteria.allowed_rooms) is tuple


def _fixture_document(criteria_filename: str) -> SearchResultDocument:
    load_result = load_fixture_source_batch(VALID_BATCH)
    assert isinstance(load_result, SourceBatchLoadSuccess)
    adaptation_result = adapt_fixture_source_batch(load_result.batch)
    assert isinstance(adaptation_result, FixtureSourceAdaptationSuccess)
    collection_result = build_fixture_collection(adaptation_result.batch)
    assert isinstance(collection_result, CollectionBuildSuccess)
    criteria_result = load_search_criteria(CRITERIA_ROOT / criteria_filename)
    assert isinstance(criteria_result, SearchCriteriaLoadSuccess)
    result = search_collection(collection_result.snapshot, criteria_result.criteria)
    return map_search_result(result)


@pytest.mark.parametrize(
    ("criteria_filename", "expected_ids"),
    (
        ("all-three.json", ("studio-002", "alpha-001")),
        ("partial-area.json", ("currency-004",)),
        ("none.json", ("studio-002", "alpha-001", "missing-003", "currency-004")),
        ("no-match.json", ()),
    ),
)
def test_four_static_pipelines_integrate_offline_without_serialization_or_golden_comparison(
    criteria_filename: str,
    expected_ids: tuple[str, ...],
) -> None:
    document = _fixture_document(criteria_filename)

    assert tuple(match.publication_ref.value.publication_id for match in document.matches) == (
        expected_ids
    )
    assert type(document.matches) is tuple


def test_none_fixture_document_proves_present_missing_and_unsupported_states() -> None:
    document = _fixture_document("none.json")

    assert isinstance(document.matches[0].currency, PresentDocument)
    assert isinstance(document.matches[2].currency, MissingDocument)
    assert isinstance(document.matches[2].total_area, MissingDocument)
    assert isinstance(document.matches[3].currency, UnsupportedDocument)
    assert document.matches[3].currency.reason_code == "unsupported_currency"
