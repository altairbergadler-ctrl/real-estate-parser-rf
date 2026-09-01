from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
from typing import Any, cast

import pytest

from real_estate_parser import (
    CollectionBuildSuccess,
    FixtureSourceAdaptationSuccess,
    SearchCriteriaDocument,
    SearchCriteriaLoadSuccess,
    SearchResultDocument,
    SearchResultSerializationFailure,
    SearchResultSerializationSuccess,
    SourceBatchLoadSuccess,
    adapt_fixture_source_batch,
    build_fixture_collection,
    load_fixture_source_batch,
    load_search_criteria,
    map_search_result,
    search_collection,
    serialize_search_result_document,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v1"
VALID_BATCH = FIXTURE_ROOT / "valid" / "listings-comprehensive.json"
CRITERIA_ROOT = FIXTURE_ROOT / "criteria"
EXPECTED_ROOT = FIXTURE_ROOT / "expected"


def _fixture_document(criteria_filename: str) -> SearchResultDocument:
    load_result = load_fixture_source_batch(VALID_BATCH)
    assert isinstance(load_result, SourceBatchLoadSuccess)
    adaptation_result = adapt_fixture_source_batch(load_result.batch)
    assert isinstance(adaptation_result, FixtureSourceAdaptationSuccess)
    collection_result = build_fixture_collection(adaptation_result.batch)
    assert isinstance(collection_result, CollectionBuildSuccess)
    criteria_result = load_search_criteria(CRITERIA_ROOT / criteria_filename)
    assert isinstance(criteria_result, SearchCriteriaLoadSuccess)
    search_result = search_collection(collection_result.snapshot, criteria_result.criteria)
    return map_search_result(search_result)


def _serialized(document: SearchResultDocument) -> bytes:
    result = serialize_search_result_document(document)
    assert isinstance(result, SearchResultSerializationSuccess)
    return result.json_bytes


def _payload(document: SearchResultDocument) -> dict[str, Any]:
    return asdict(document)


def _corrupted(payload: object) -> SearchResultDocument:
    return cast(SearchResultDocument, payload)


def _assert_output_failure(document: SearchResultDocument) -> SearchResultSerializationFailure:
    result = serialize_search_result_document(document)
    assert isinstance(result, SearchResultSerializationFailure)
    assert not hasattr(result, "json_bytes")
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert (issue.category, issue.code, issue.location.json_path, issue.safe_text) == (
        "OUTPUT_CONTRACT",
        "invalid_result_document",
        "$",
        None,
    )
    return result


def test_empty_document_has_exact_canonical_bytes() -> None:
    document = SearchResultDocument(
        schema_version="search-result@1",
        criteria=SearchCriteriaDocument(),
        matches=(),
    )

    assert _serialized(document) == (
        b'{"criteria":{},"matches":[],"schema_version":"search-result@1"}\n'
    )


def test_serialization_is_repeatedly_deterministic_and_canonical() -> None:
    document = _fixture_document("none.json")

    first = _serialized(document)
    second = _serialized(document)
    parsed = json.loads(first)
    independently_canonical = (
        json.dumps(
            parsed,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )

    assert first == second == independently_canonical
    assert not first.startswith(b"\xef\xbb\xbf")
    assert first.endswith(b"\n")
    assert first.count(b"\n") == 1
    assert b": " not in first
    assert b", " not in first
    assert b"null" not in first


def test_absent_criteria_are_omitted_and_rooms_remain_increasing() -> None:
    without_criteria = json.loads(_serialized(_fixture_document("none.json")))
    all_criteria = json.loads(_serialized(_fixture_document("all-three.json")))

    assert without_criteria["criteria"] == {}
    assert all_criteria["criteria"] == {
        "allowed_rooms": [0, 2],
        "maximum_price": {"amount_minor": 11_000_000, "currency": "RUB"},
        "minimum_total_area": "40.00",
    }


def test_present_missing_and_unsupported_have_exact_distinct_shapes() -> None:
    payload = json.loads(_serialized(_fixture_document("none.json")))
    present = payload["matches"][0]["currency"]
    missing = payload["matches"][2]["currency"]
    unsupported = payload["matches"][3]["currency"]

    assert present["state"] == "present"
    assert "value" in present
    assert "raw_value" in present["provenance"]
    assert missing["state"] == "missing"
    assert "value" not in missing
    assert "raw_value" not in missing["provenance"]
    assert unsupported["state"] == "unsupported"
    assert unsupported["reason_code"] == "unsupported_currency"
    assert "value" not in unsupported
    assert unsupported["provenance"]["raw_value"] == "USD"


def test_boundary_preserves_the_document_match_order_without_resorting() -> None:
    document = _fixture_document("none.json")
    reversed_document = replace(document, matches=tuple(reversed(document.matches)))

    payload = json.loads(_serialized(reversed_document))

    assert tuple(
        match["publication_ref"]["value"]["publication_id"] for match in payload["matches"]
    ) == ("currency-004", "missing-003", "alpha-001", "studio-002")


@pytest.mark.parametrize(
    "payload",
    (
        {
            "schema_version": "search-result@1",
            "criteria": {},
            "matches": (),
            "extra": "forbidden",
        },
        {"schema_version": 1, "criteria": {}, "matches": ()},
        {
            "schema_version": "search-result@1",
            "criteria": {"maximum_price": {"amount_minor": "1", "currency": "RUB"}},
            "matches": (),
        },
        {
            "schema_version": "search-result@1",
            "criteria": {"allowed_rooms": ()},
            "matches": (),
        },
        {
            "schema_version": "search-result@1",
            "criteria": {"allowed_rooms": (2, 0)},
            "matches": (),
        },
        {
            "schema_version": "search-result@1",
            "criteria": {"minimum_total_area": "60.0"},
            "matches": (),
        },
    ),
)
def test_strict_boundary_rejects_extra_coercion_and_noncanonical_values(
    payload: object,
) -> None:
    _assert_output_failure(_corrupted(payload))


def test_out_001_missing_cannot_gain_raw_value() -> None:
    payload = _payload(_fixture_document("none.json"))
    payload["matches"][2]["currency"]["provenance"]["raw_value"] = "invented"

    failure = _assert_output_failure(_corrupted(payload))

    assert repr(failure).find("invented") == -1


def test_unsupported_cannot_gain_a_canonical_value() -> None:
    payload = _payload(_fixture_document("none.json"))
    payload["matches"][3]["currency"]["value"] = "USD"

    _assert_output_failure(_corrupted(payload))


def test_provided_provenance_requires_raw_value() -> None:
    payload = _payload(_fixture_document("none.json"))
    del payload["matches"][0]["currency"]["provenance"]["raw_value"]

    _assert_output_failure(_corrupted(payload))


def test_unknown_outcome_state_is_rejected_as_one_safe_root_issue() -> None:
    payload = _payload(_fixture_document("none.json"))
    payload["matches"][0]["currency"]["state"] = "guessed"

    _assert_output_failure(_corrupted(payload))


def test_public_result_types_are_frozen_and_slotted() -> None:
    success = serialize_search_result_document(
        SearchResultDocument("search-result@1", SearchCriteriaDocument(), ())
    )
    failure = _assert_output_failure(_corrupted({}))

    assert isinstance(success, SearchResultSerializationSuccess)
    for target, attribute in ((success, "json_bytes"), (failure, "issues")):
        assert not hasattr(target, "__dict__")
        with pytest.raises(FrozenInstanceError):
            setattr(target, attribute, getattr(target, attribute))


@pytest.mark.parametrize(
    ("criteria_filename", "golden_filename"),
    (
        ("all-three.json", "search-all-three.json"),
        ("none.json", "search-none.json"),
        ("no-match.json", "search-no-match.json"),
    ),
)
def test_offline_pipeline_matches_existing_golden_bytes_exactly(
    criteria_filename: str,
    golden_filename: str,
) -> None:
    actual = _serialized(_fixture_document(criteria_filename))
    expected = (EXPECTED_ROOT / golden_filename).read_bytes()

    assert actual == expected


def test_partial_area_pipeline_has_the_approved_semantics_without_a_golden() -> None:
    payload = json.loads(_serialized(_fixture_document("partial-area.json")))

    assert payload["schema_version"] == "search-result@1"
    assert payload["criteria"] == {"minimum_total_area": "60.00"}
    assert tuple(
        match["publication_ref"]["value"]["publication_id"] for match in payload["matches"]
    ) == ("currency-004",)
    assert payload["matches"][0]["currency"]["state"] == "unsupported"
