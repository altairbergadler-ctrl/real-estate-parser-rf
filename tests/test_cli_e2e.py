from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "v1"
VALID_LISTINGS = FIXTURE_ROOT / "valid" / "listings-comprehensive.json"
CRITERIA_ROOT = FIXTURE_ROOT / "criteria"
INVALID_ROOT = FIXTURE_ROOT / "invalid"
EXPECTED_ROOT = FIXTURE_ROOT / "expected"
MODULE_COMMAND = (sys.executable, "-m", "real_estate_parser")


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        (*MODULE_COMMAND, *arguments),
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
    )


def _search(listings: Path, criteria: Path) -> subprocess.CompletedProcess[bytes]:
    return _run_cli(
        "search",
        "--listings",
        str(listings),
        "--criteria",
        str(criteria),
    )


@pytest.mark.parametrize(
    ("criteria_filename", "golden_filename"),
    (
        ("all-three.json", "search-all-three.json"),
        ("none.json", "search-none.json"),
        ("no-match.json", "search-no-match.json"),
    ),
)
def test_cli_success_is_byte_exact_and_keeps_stderr_empty(
    criteria_filename: str,
    golden_filename: str,
) -> None:
    completed = _search(VALID_LISTINGS, CRITERIA_ROOT / criteria_filename)

    assert completed.returncode == 0
    assert completed.stderr == b""
    assert completed.stdout == (EXPECTED_ROOT / golden_filename).read_bytes()


def test_cli_partial_search_preserves_currency_004_semantics() -> None:
    completed = _search(VALID_LISTINGS, CRITERIA_ROOT / "partial-area.json")

    assert completed.returncode == 0
    assert completed.stderr == b""
    payload = json.loads(completed.stdout)
    assert tuple(
        match["publication_ref"]["value"]["publication_id"] for match in payload["matches"]
    ) == ("currency-004",)
    assert payload["matches"][0]["currency"]["state"] == "unsupported"


@pytest.mark.parametrize(
    ("listings_filename", "expected_stderr"),
    (
        ("syntax-truncated.json", b"INPUT_SYNTAX/invalid_json/$\n"),
        (
            "normalization-atomic.json",
            b"NORMALIZATION/precision_loss/$.listings[1].total_area_sqm\n",
        ),
        (
            "duplicate-publication-ref.json",
            b"COLLECTION_CONFLICT/duplicate_publication_ref/$.listings[1]\n",
        ),
    ),
)
def test_cli_contract_failures_are_atomic_and_exact(
    listings_filename: str,
    expected_stderr: bytes,
) -> None:
    completed = _search(INVALID_ROOT / listings_filename, CRITERIA_ROOT / "none.json")

    assert completed.returncode == 1
    assert completed.stdout == b""
    assert completed.stderr == expected_stderr
    assert b"Traceback" not in completed.stderr


def test_cli_multiple_issues_match_the_existing_oracle_exactly() -> None:
    completed = _search(
        INVALID_ROOT / "schema-multiple-errors.json",
        CRITERIA_ROOT / "none.json",
    )
    expected = json.loads(
        (EXPECTED_ROOT / "schema-multiple-errors.diagnostics.json").read_text(encoding="utf-8")
    )
    expected_stderr = "".join(
        f"{issue['category']}/{issue['code']}/{issue['location']}\n" for issue in expected["issues"]
    ).encode("ascii")

    assert completed.returncode == 1
    assert completed.stdout == b""
    assert completed.stderr == expected_stderr


def test_cli_reports_a_criteria_issue_without_success_json(tmp_path: Path) -> None:
    criteria_path = tmp_path / "invalid-criteria.json"
    criteria_path.write_text(
        '{"schema_version":"search-criteria@1","criteria":{"allowed_rooms":[]}}\n',
        encoding="utf-8",
    )

    completed = _search(VALID_LISTINGS, criteria_path)

    assert completed.returncode == 1
    assert completed.stdout == b""
    assert completed.stderr == b"INPUT_SCHEMA/invalid_criterion/$.criteria.allowed_rooms\n"


def test_cli_usage_error_has_exit_two_without_traceback() -> None:
    completed = _run_cli("search", "--listings", str(VALID_LISTINGS))

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert b"usage: real-estate-parser search" in completed.stderr
    assert str(VALID_LISTINGS).encode() not in completed.stderr
    assert b"Traceback" not in completed.stderr


def test_cli_missing_file_is_safe_and_does_not_reveal_the_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "private-missing-listings.json"

    completed = _search(missing_path, CRITERIA_ROOT / "none.json")

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"listings/unreadable_input\n"
    assert str(missing_path).encode() not in completed.stderr
    assert b"Traceback" not in completed.stderr


def test_cli_non_utf8_file_is_safe_and_does_not_reveal_the_path(tmp_path: Path) -> None:
    criteria_path = tmp_path / "private-non-utf8-criteria.json"
    criteria_path.write_bytes(b"\xff")

    completed = _search(VALID_LISTINGS, criteria_path)

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"criteria/invalid_utf8\n"
    assert str(criteria_path).encode() not in completed.stderr
    assert b"Traceback" not in completed.stderr


def test_repeated_cli_runs_produce_identical_bytes() -> None:
    first = _search(VALID_LISTINGS, CRITERIA_ROOT / "all-three.json")
    second = _search(VALID_LISTINGS, CRITERIA_ROOT / "all-three.json")

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout


def test_installed_console_script_exposes_the_same_cli() -> None:
    script_name = "real-estate-parser.exe" if sys.platform == "win32" else "real-estate-parser"
    script_path = Path(sys.executable).with_name(script_name)

    completed = subprocess.run(
        (script_path, "--help"),
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert completed.stderr == b""
    assert b"usage: real-estate-parser" in completed.stdout
    assert b"search" in completed.stdout
