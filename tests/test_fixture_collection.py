from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from real_estate_parser import (
    FIXTURE_NORMALIZATION_RULES_V1,
    CollectionBuildFailure,
    CollectionBuildSuccess,
    FixtureSourceAdaptationSuccess,
    InputLocation,
    MissingField,
    NormalizationSuccess,
    PublicationId,
    PublicationRef,
    RawField,
    SourceBatch,
    SourceBatchLoadSuccess,
    SourceId,
    SourcePublicationSnapshot,
    Unsupported,
    adapt_fixture_source_batch,
    build_fixture_collection,
    load_fixture_source_batch,
    normalize_fixture_snapshot,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v1"
VALID_BATCH = FIXTURE_ROOT / "valid" / "listings-comprehensive.json"
ATOMIC_BATCH = FIXTURE_ROOT / "invalid" / "normalization-atomic.json"
DUPLICATE_BATCH = FIXTURE_ROOT / "invalid" / "duplicate-publication-ref.json"


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
    record_index: int,
    publication_id: str,
    *,
    source_id: str = "fixture_portal",
    observed_at: str = "2026-02-03T10:15:30Z",
    location_text: str | None = "Invented Quarter",
    price_major: str | None = "110000.00",
    currency: str | None = "RUB",
    total_area_sqm: str | None = "52.50",
    rooms: str | None = "2",
) -> SourcePublicationSnapshot:
    return SourcePublicationSnapshot(
        reference=PublicationRef(SourceId(source_id), PublicationId(publication_id)),
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


def _comprehensive_source_batch() -> SourceBatch:
    return SourceBatch(
        snapshots=(
            _snapshot(
                0,
                "alpha-001",
                observed_at="2026-02-03T10:15:30.123456+03:00",
                location_text="  Invented Quarter   Alpha  ",
            ),
            _snapshot(
                1,
                "missing-003",
                observed_at="2026-02-01T00:00:00Z",
                location_text=None,
                price_major=None,
                currency=None,
                total_area_sqm=None,
                rooms=None,
            ),
            _snapshot(
                2,
                "currency-004",
                observed_at="2026-02-04T23:30:00.5-04:00",
                location_text="Invented Quarter Currency",
                price_major="120000.00",
                currency="USD",
                total_area_sqm="61.75",
                rooms="1",
            ),
            _snapshot(
                3,
                "studio-002",
                observed_at="2026-02-02T08:00:00+05:30",
                location_text="Invented Quarter Studio",
                price_major="95000.25",
                total_area_sqm="40",
                rooms="studio",
            ),
        )
    )


def _success(batch: SourceBatch) -> CollectionBuildSuccess:
    result = build_fixture_collection(batch, FIXTURE_NORMALIZATION_RULES_V1)
    assert isinstance(result, CollectionBuildSuccess)
    return result


def _failure(batch: SourceBatch) -> CollectionBuildFailure:
    result = build_fixture_collection(batch, FIXTURE_NORMALIZATION_RULES_V1)
    assert isinstance(result, CollectionBuildFailure)
    return result


def _issue_triples(result: CollectionBuildFailure) -> list[tuple[str, str, str]]:
    return [(issue.category, issue.code, issue.location.json_path) for issue in result.issues]


def _adapted_fixture(path: Path) -> SourceBatch:
    load_result = load_fixture_source_batch(path)
    assert isinstance(load_result, SourceBatchLoadSuccess)
    adaptation_result = adapt_fixture_source_batch(load_result.batch)
    assert isinstance(adaptation_result, FixtureSourceAdaptationSuccess)
    return adaptation_result.batch


def _assign_snapshots(target: Any) -> None:
    target.snapshots = ()


def _assign_listings(target: Any) -> None:
    target.listings = ()


def test_complete_batch_preserves_order_normalized_values_and_provenance() -> None:
    batch = _comprehensive_source_batch()
    expected_listings = []
    for source_snapshot in batch.snapshots:
        normalization_result = normalize_fixture_snapshot(
            source_snapshot,
            FIXTURE_NORMALIZATION_RULES_V1,
        )
        assert isinstance(normalization_result, NormalizationSuccess)
        expected_listings.append(normalization_result.listing)

    collection = _success(batch).snapshot

    assert isinstance(collection.listings, tuple)
    assert collection.listings == tuple(expected_listings)
    assert [listing.reference.value.publication_id.value for listing in collection.listings] == [
        "alpha-001",
        "missing-003",
        "currency-004",
        "studio-002",
    ]
    assert collection.listings[0].reference.provenance.raw_value == "alpha-001"
    assert (
        collection.listings[0].reference.provenance.normalization_rule_version.value
        == "fixture-publication-id@1"
    )
    assert collection.listings[0].reference.provenance.input_path.json_path == (
        "$.listings[0].publication_id"
    )
    assert isinstance(collection.listings[2].currency, Unsupported)
    assert collection.listings[2].currency.provenance.raw_value == "USD"
    assert collection.listings[2].currency.provenance.reason_code == "unsupported_currency"


def test_source_batch_collection_and_nested_listings_are_immutable() -> None:
    batch = _comprehensive_source_batch()
    collection = _success(batch).snapshot

    with pytest.raises(FrozenInstanceError):
        _assign_snapshots(batch)
    with pytest.raises(FrozenInstanceError):
        _assign_listings(collection)
    with pytest.raises(FrozenInstanceError):
        _assign_listings(collection.listings[0])


def test_normalization_issues_from_all_records_are_collected_and_globally_sorted() -> None:
    batch = SourceBatch(
        snapshots=(
            _snapshot(2, "duplicate-001", rooms="100"),
            _snapshot(0, "duplicate-001", total_area_sqm="47.125"),
            _snapshot(1, "other-002", location_text="   "),
        )
    )

    result = _failure(batch)

    assert _issue_triples(result) == [
        ("NORMALIZATION", "precision_loss", "$.listings[0].total_area_sqm"),
        ("NORMALIZATION", "invalid_value", "$.listings[1].location_text"),
        ("NORMALIZATION", "out_of_range", "$.listings[2].rooms"),
    ]
    assert not hasattr(result, "snapshot")
    assert not hasattr(result, "listings")


def test_normalization_failure_prevents_duplicate_conflict_check() -> None:
    result = _failure(
        SourceBatch(
            snapshots=(
                _snapshot(0, "duplicate-001"),
                _snapshot(1, "duplicate-001", total_area_sqm="47.125"),
            )
        )
    )

    assert _issue_triples(result) == [
        ("NORMALIZATION", "precision_loss", "$.listings[1].total_area_sqm")
    ]


def test_same_publication_id_in_different_sources_is_not_a_conflict() -> None:
    collection = _success(
        SourceBatch(
            snapshots=(
                _snapshot(0, "same-001", source_id="fixture_portal"),
                _snapshot(1, "same-001", source_id="other_source"),
            )
        )
    ).snapshot

    assert len(collection.listings) == 2


def test_publication_id_comparison_is_case_sensitive() -> None:
    collection = _success(
        SourceBatch(
            snapshots=(
                _snapshot(0, "Case-001"),
                _snapshot(1, "case-001"),
            )
        )
    ).snapshot

    assert len(collection.listings) == 2


def test_three_occurrences_report_second_and_third_record_locations() -> None:
    result = _failure(
        SourceBatch(
            snapshots=(
                _snapshot(0, "triple-001"),
                _snapshot(1, "triple-001"),
                _snapshot(2, "triple-001"),
            )
        )
    )

    assert _issue_triples(result) == [
        ("COLLECTION_CONFLICT", "duplicate_publication_ref", "$.listings[1]"),
        ("COLLECTION_CONFLICT", "duplicate_publication_ref", "$.listings[2]"),
    ]
    assert not hasattr(result, "snapshot")


def test_multiple_duplicate_references_are_sorted_by_the_common_issue_key() -> None:
    result = _failure(
        SourceBatch(
            snapshots=(
                _snapshot(0, "alpha-001"),
                _snapshot(1, "beta-002"),
                _snapshot(3, "beta-002"),
                _snapshot(2, "alpha-001"),
            )
        )
    )

    assert _issue_triples(result) == [
        ("COLLECTION_CONFLICT", "duplicate_publication_ref", "$.listings[2]"),
        ("COLLECTION_CONFLICT", "duplicate_publication_ref", "$.listings[3]"),
    ]


def test_later_duplicate_is_not_selected_by_observation_time() -> None:
    result = _failure(
        SourceBatch(
            snapshots=(
                _snapshot(0, "duplicate-001", observed_at="2026-04-02T00:00:00Z"),
                _snapshot(1, "duplicate-001", observed_at="2026-04-03T00:00:00Z"),
            )
        )
    )

    assert _issue_triples(result) == [
        ("COLLECTION_CONFLICT", "duplicate_publication_ref", "$.listings[1]")
    ]
    assert not hasattr(result, "snapshot")


def test_operation_is_deterministic_for_identical_offline_input() -> None:
    batch = _comprehensive_source_batch()

    assert build_fixture_collection(batch) == build_fixture_collection(batch)


def test_static_comprehensive_fixture_builds_four_listings_in_input_order() -> None:
    result = _success(_adapted_fixture(VALID_BATCH))

    assert [
        listing.reference.value.publication_id.value for listing in result.snapshot.listings
    ] == ["alpha-001", "missing-003", "currency-004", "studio-002"]
    assert isinstance(result.snapshot.listings[2].currency, Unsupported)


def test_static_atomic_normalization_fixture_has_only_its_exact_issue() -> None:
    result = _failure(_adapted_fixture(ATOMIC_BATCH))

    assert _issue_triples(result) == [
        ("NORMALIZATION", "precision_loss", "$.listings[1].total_area_sqm")
    ]
    assert not hasattr(result, "snapshot")


def test_static_duplicate_fixture_has_only_its_exact_collection_issue() -> None:
    result = _failure(_adapted_fixture(DUPLICATE_BATCH))

    assert _issue_triples(result) == [
        ("COLLECTION_CONFLICT", "duplicate_publication_ref", "$.listings[1]")
    ]
    assert not hasattr(result, "snapshot")


def test_failure_type_requires_at_least_one_issue() -> None:
    with pytest.raises(ValueError, match="must contain an issue"):
        CollectionBuildFailure(issues=())
