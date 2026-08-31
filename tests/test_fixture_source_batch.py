from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from real_estate_parser import (
    MissingSourceField,
    SourceBatchLoadFailure,
    SourceBatchLoadSuccess,
    ValidatedSourceField,
    load_fixture_source_batch,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v1"
VALID_BATCH = FIXTURE_ROOT / "valid" / "listings-comprehensive.json"


def _valid_document() -> dict[str, Any]:
    document: dict[str, Any] = json.loads(VALID_BATCH.read_text(encoding="utf-8"))
    return document


def _write_document(tmp_path: Path, document: object) -> Path:
    path = tmp_path / "input.json"
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def _success(path: Path) -> SourceBatchLoadSuccess:
    result = load_fixture_source_batch(path)
    assert isinstance(result, SourceBatchLoadSuccess)
    return result


def _failure(path: Path) -> SourceBatchLoadFailure:
    result = load_fixture_source_batch(path)
    assert isinstance(result, SourceBatchLoadFailure)
    return result


def _issue_triples(result: SourceBatchLoadFailure) -> list[tuple[str, str, str]]:
    return [(issue.category, issue.code, issue.location.json_path) for issue in result.issues]


def _assign_source(target: Any) -> None:
    target.source = target.source


def _assign_first_listing(target: Any) -> None:
    target.listings[0] = target.listings[0]


def test_comprehensive_batch_preserves_order_raw_strings_and_locations() -> None:
    batch = _success(VALID_BATCH).batch

    assert batch.schema_version.value == "fixture-source-batch@1"
    assert batch.schema_version.location.json_path == "$.schema_version"
    assert batch.source.value == "fixture_portal"
    assert batch.source.location.json_path == "$.source"
    assert [listing.publication_id.value for listing in batch.listings] == [
        "alpha-001",
        "missing-003",
        "currency-004",
        "studio-002",
    ]

    first = batch.listings[0]
    assert first.location.json_path == "$.listings[0]"
    assert first.observed_at.value == "2026-02-03T10:15:30.123456+03:00"
    assert first.observed_at.location.json_path == "$.listings[0].observed_at"
    assert isinstance(first.location_text, ValidatedSourceField)
    assert first.location_text.value == "  Invented Quarter   Alpha  "
    assert first.location_text.location.json_path == "$.listings[0].location_text"
    assert isinstance(first.price_major, ValidatedSourceField)
    assert first.price_major.value == "110000.00"
    assert isinstance(first.total_area_sqm, ValidatedSourceField)
    assert first.total_area_sqm.value == "52.50"
    assert isinstance(first.rooms, ValidatedSourceField)
    assert first.rooms.value == "2"

    missing = batch.listings[1]
    assert isinstance(missing.location_text, MissingSourceField)
    assert missing.location_text.location.json_path == "$.listings[1].location_text"
    assert isinstance(missing.price_major, MissingSourceField)
    assert missing.price_major.location.json_path == "$.listings[1].price_major"
    assert isinstance(missing.currency, MissingSourceField)
    assert missing.currency.location.json_path == "$.listings[1].currency"
    assert isinstance(missing.total_area_sqm, MissingSourceField)
    assert missing.total_area_sqm.location.json_path == "$.listings[1].total_area_sqm"
    assert isinstance(missing.rooms, MissingSourceField)
    assert missing.rooms.location.json_path == "$.listings[1].rooms"


def test_successful_batch_and_nested_values_are_immutable() -> None:
    result = _success(VALID_BATCH)

    with pytest.raises(FrozenInstanceError):
        _assign_source(result.batch)
    with pytest.raises(TypeError):
        _assign_first_listing(result.batch)


def test_truncated_json_returns_one_syntax_issue() -> None:
    result = _failure(FIXTURE_ROOT / "invalid" / "syntax-truncated.json")

    assert _issue_triples(result) == [("INPUT_SYNTAX", "invalid_json", "$")]


def test_multiple_schema_errors_match_static_diagnostic_oracle() -> None:
    result = _failure(FIXTURE_ROOT / "invalid" / "schema-multiple-errors.json")
    oracle = json.loads(
        (FIXTURE_ROOT / "expected" / "schema-multiple-errors.diagnostics.json").read_text(
            encoding="utf-8"
        )
    )

    actual = [
        {
            "category": issue.category,
            "code": issue.code,
            "location": issue.location.json_path,
        }
        for issue in result.issues
    ]
    assert actual == oracle["issues"]


@pytest.mark.parametrize(
    ("mutation", "expected_code", "expected_path"),
    (
        ("missing_url", "missing_field", "$.listings[0].url"),
        ("numeric_price", "wrong_type", "$.listings[0].price_major"),
        ("extra_note", "extra_field", "$.listings[0].extra_note"),
        ("null_location", "wrong_type", "$.listings[0].location_text"),
    ),
)
def test_schema_mutations_have_stable_diagnostics(
    tmp_path: Path,
    mutation: str,
    expected_code: str,
    expected_path: str,
) -> None:
    document = _valid_document()
    listing = document["listings"][0]
    if mutation == "missing_url":
        del listing["url"]
    elif mutation == "numeric_price":
        listing["price_major"] = 100
    elif mutation == "extra_note":
        listing["extra_note"] = "fictional"
    elif mutation == "null_location":
        listing["location_text"] = None
    else:
        pytest.fail(f"unknown test mutation: {mutation}")

    result = _failure(_write_document(tmp_path, document))

    assert _issue_triples(result) == [("INPUT_SCHEMA", expected_code, expected_path)]


@pytest.mark.parametrize(
    ("mutate", "expected_code", "expected_path"),
    (
        (
            lambda document: document.__setitem__("schema_version", "future@2"),
            "unsupported_schema_version",
            "$.schema_version",
        ),
        (lambda document: document.__setitem__("listings", []), "invalid_value", "$.listings"),
    ),
)
def test_document_value_rules_have_stable_diagnostics(
    tmp_path: Path,
    mutate: Any,
    expected_code: str,
    expected_path: str,
) -> None:
    document = _valid_document()
    mutate(document)

    result = _failure(_write_document(tmp_path, document))

    assert _issue_triples(result) == [("INPUT_SCHEMA", expected_code, expected_path)]


def test_explicit_null_is_rejected_instead_of_becoming_missing(tmp_path: Path) -> None:
    document = _valid_document()
    document["listings"][1]["rooms"] = None

    result = load_fixture_source_batch(_write_document(tmp_path, document))

    assert isinstance(result, SourceBatchLoadFailure)
    assert _issue_triples(result) == [("INPUT_SCHEMA", "wrong_type", "$.listings[1].rooms")]


def test_one_invalid_item_rejects_the_whole_batch(tmp_path: Path) -> None:
    document = _valid_document()
    document["listings"][3]["rooms"] = False

    result = load_fixture_source_batch(_write_document(tmp_path, document))

    assert isinstance(result, SourceBatchLoadFailure)
    assert not hasattr(result, "batch")
    assert _issue_triples(result) == [("INPUT_SCHEMA", "wrong_type", "$.listings[3].rooms")]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("publication_id", ""),
        ("url", "http://other.example/not-an-offer"),
        ("observed_at", "2026-02-03T10:15:30"),
        ("currency", "USD"),
        ("total_area_sqm", "47.125"),
    ),
)
def test_future_stage_invalidities_remain_raw_strings_at_this_boundary(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    document = _valid_document()
    document["listings"][0][field] = value

    batch = _success(_write_document(tmp_path, document)).batch
    validated_field = getattr(batch.listings[0], field)

    assert isinstance(validated_field, ValidatedSourceField)
    assert validated_field.value == value


def test_source_mismatch_is_not_checked_at_schema_boundary(tmp_path: Path) -> None:
    document = _valid_document()
    document["source"] = "other_fixture"

    batch = _success(_write_document(tmp_path, document)).batch

    assert batch.source.value == "other_fixture"


def test_file_and_utf8_failures_remain_operational(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_fixture_source_batch(tmp_path / "missing.json")

    invalid_utf8 = tmp_path / "invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        load_fixture_source_batch(invalid_utf8)
