from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from real_estate_parser import (
    LocalSearchFailure,
    LocalSearchSuccess,
    run_local_search,
)
from real_estate_parser.application import LocalSearchOperationalError

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v1"
VALID_LISTINGS = FIXTURE_ROOT / "valid" / "listings-comprehensive.json"
CRITERIA_ROOT = FIXTURE_ROOT / "criteria"
INVALID_ROOT = FIXTURE_ROOT / "invalid"
EXPECTED_ROOT = FIXTURE_ROOT / "expected"


@pytest.mark.parametrize(
    ("criteria_filename", "golden_filename"),
    (
        ("all-three.json", "search-all-three.json"),
        ("none.json", "search-none.json"),
        ("no-match.json", "search-no-match.json"),
    ),
)
def test_application_flow_matches_existing_golden_bytes(
    criteria_filename: str,
    golden_filename: str,
) -> None:
    result = run_local_search(VALID_LISTINGS, CRITERIA_ROOT / criteria_filename)

    assert isinstance(result, LocalSearchSuccess)
    assert result.json_bytes == (EXPECTED_ROOT / golden_filename).read_bytes()


def test_application_flow_preserves_partial_search_semantics() -> None:
    result = run_local_search(VALID_LISTINGS, CRITERIA_ROOT / "partial-area.json")

    assert isinstance(result, LocalSearchSuccess)
    payload = json.loads(result.json_bytes)
    assert payload["criteria"] == {"minimum_total_area": "60.00"}
    assert tuple(
        match["publication_ref"]["value"]["publication_id"] for match in payload["matches"]
    ) == ("currency-004",)
    assert payload["matches"][0]["currency"]["state"] == "unsupported"


@pytest.mark.parametrize(
    ("listings_filename", "expected_issue"),
    (
        ("syntax-truncated.json", ("INPUT_SYNTAX", "invalid_json", "$")),
        (
            "normalization-atomic.json",
            ("NORMALIZATION", "precision_loss", "$.listings[1].total_area_sqm"),
        ),
        (
            "duplicate-publication-ref.json",
            ("COLLECTION_CONFLICT", "duplicate_publication_ref", "$.listings[1]"),
        ),
    ),
)
def test_application_flow_rejects_invalid_listings_atomically(
    listings_filename: str,
    expected_issue: tuple[str, str, str],
) -> None:
    result = run_local_search(INVALID_ROOT / listings_filename, CRITERIA_ROOT / "none.json")

    assert isinstance(result, LocalSearchFailure)
    assert not hasattr(result, "json_bytes")
    assert tuple(
        (issue.category, issue.code, issue.location.json_path) for issue in result.issues
    ) == (expected_issue,)


def test_valid_listings_report_an_independent_criteria_issue(tmp_path: Path) -> None:
    criteria_path = tmp_path / "invalid-criteria.json"
    criteria_path.write_text(
        '{"schema_version":"search-criteria@1","criteria":{"allowed_rooms":[]}}\n',
        encoding="utf-8",
    )

    result = run_local_search(VALID_LISTINGS, criteria_path)

    assert isinstance(result, LocalSearchFailure)
    assert tuple(
        (issue.category, issue.code, issue.location.json_path) for issue in result.issues
    ) == (("INPUT_SCHEMA", "invalid_criterion", "$.criteria.allowed_rooms"),)


def test_two_invalid_documents_are_loaded_independently_and_globally_ordered() -> None:
    invalid_json = INVALID_ROOT / "syntax-truncated.json"

    result = run_local_search(invalid_json, invalid_json)

    assert isinstance(result, LocalSearchFailure)
    assert tuple(
        (
            issue.location.document,
            issue.category,
            issue.code,
            issue.location.json_path,
        )
        for issue in result.issues
    ) == (
        ("listings", "INPUT_SYNTAX", "invalid_json", "$"),
        ("criteria", "INPUT_SYNTAX", "invalid_json", "$"),
    )


def test_multiple_schema_issues_follow_the_existing_oracle() -> None:
    result = run_local_search(
        INVALID_ROOT / "schema-multiple-errors.json",
        CRITERIA_ROOT / "none.json",
    )
    expected = json.loads(
        (EXPECTED_ROOT / "schema-multiple-errors.diagnostics.json").read_text(encoding="utf-8")
    )

    assert isinstance(result, LocalSearchFailure)
    assert [
        {
            "category": issue.category,
            "code": issue.code,
            "location": issue.location.json_path,
        }
        for issue in result.issues
    ] == expected["issues"]


def test_operational_failure_is_not_reclassified_as_a_contract_issue(tmp_path: Path) -> None:
    missing_path = tmp_path / "not-present.json"

    with pytest.raises(LocalSearchOperationalError) as captured:
        run_local_search(missing_path, CRITERIA_ROOT / "none.json")

    assert (captured.value.role, captured.value.reason) == (
        "listings",
        "unreadable_input",
    )
    assert not hasattr(captured.value, "issues")


def test_application_result_types_are_frozen_and_slotted() -> None:
    success = run_local_search(VALID_LISTINGS, CRITERIA_ROOT / "none.json")
    failure = run_local_search(INVALID_ROOT / "syntax-truncated.json", CRITERIA_ROOT / "none.json")

    assert isinstance(success, LocalSearchSuccess)
    assert isinstance(failure, LocalSearchFailure)
    for target, attribute in ((success, "json_bytes"), (failure, "issues")):
        assert not hasattr(target, "__dict__")
        with pytest.raises(FrozenInstanceError):
            setattr(target, attribute, getattr(target, attribute))
