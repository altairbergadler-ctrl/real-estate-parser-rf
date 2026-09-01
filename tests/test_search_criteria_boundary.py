from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from real_estate_parser import (
    Area,
    Currency,
    Money,
    MoneyAmount,
    RoomCount,
    SearchCriteria,
    SearchCriteriaLoadFailure,
    SearchCriteriaLoadSuccess,
    load_search_criteria,
)

FIXTURES = Path(__file__).parent / "fixtures" / "v1"
CRITERIA = FIXTURES / "criteria"
MAX_INTEGER = 9_223_372_036_854_775_807


def _write_payload(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "criteria.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _load_payload(
    tmp_path: Path, payload: object
) -> SearchCriteriaLoadSuccess | SearchCriteriaLoadFailure:
    return load_search_criteria(_write_payload(tmp_path, payload))


def _valid_payload(**criteria: object) -> dict[str, object]:
    return {"schema_version": "search-criteria@1", "criteria": criteria}


def _failure(tmp_path: Path, payload: object) -> SearchCriteriaLoadFailure:
    result = _load_payload(tmp_path, payload)
    assert isinstance(result, SearchCriteriaLoadFailure)
    return result


def _issue_triples(result: SearchCriteriaLoadFailure) -> list[tuple[str, str, str]]:
    return [(issue.category, issue.code, issue.location.json_path) for issue in result.issues]


def _assign_maximum_price(target: Any) -> None:
    target.maximum_price = target.maximum_price


def _assign_amount(target: Any) -> None:
    target.amount = target.amount


def _assign_issues(target: Any) -> None:
    target.issues = target.issues


def test_canonical_money_and_search_criteria_are_immutable_and_exact() -> None:
    money = Money(MoneyAmount(11_000_000), Currency("RUB"))
    criteria = SearchCriteria(
        maximum_price=money,
        minimum_total_area=Area(4_000),
        allowed_rooms=frozenset((RoomCount(2), RoomCount(0))),
    )

    assert criteria.maximum_price == money
    assert criteria.minimum_total_area == Area(4_000)
    assert criteria.allowed_rooms == frozenset((RoomCount(0), RoomCount(2)))
    with pytest.raises(FrozenInstanceError):
        _assign_amount(money)
    with pytest.raises(FrozenInstanceError):
        _assign_maximum_price(criteria)
    assert criteria.allowed_rooms is not None
    with pytest.raises(AttributeError):
        criteria.allowed_rooms.add(RoomCount(1))  # type: ignore[attr-defined]


def test_canonical_search_criteria_supports_complete_absence() -> None:
    assert SearchCriteria() == SearchCriteria(None, None, None)


def test_canonical_search_criteria_rejects_empty_or_mutable_room_sets() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        SearchCriteria(allowed_rooms=frozenset())
    with pytest.raises(TypeError, match="immutable set"):
        SearchCriteria(allowed_rooms={RoomCount(1)})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("filename", "expected"),
    (
        (
            "all-three.json",
            SearchCriteria(
                maximum_price=Money(MoneyAmount(11_000_000), Currency("RUB")),
                minimum_total_area=Area(4_000),
                allowed_rooms=frozenset((RoomCount(0), RoomCount(2))),
            ),
        ),
        ("partial-area.json", SearchCriteria(minimum_total_area=Area(6_000))),
        ("none.json", SearchCriteria()),
        (
            "no-match.json",
            SearchCriteria(maximum_price=Money(MoneyAmount(1), Currency("RUB"))),
        ),
    ),
)
def test_static_criteria_fixtures_load_to_exact_canonical_values(
    filename: str,
    expected: SearchCriteria,
) -> None:
    result = load_search_criteria(CRITERIA / filename)

    assert isinstance(result, SearchCriteriaLoadSuccess)
    assert result.criteria == expected


def test_external_room_order_does_not_enter_the_canonical_model(tmp_path: Path) -> None:
    first = _load_payload(tmp_path, _valid_payload(allowed_rooms=[99, 0, 2]))
    assert isinstance(first, SearchCriteriaLoadSuccess)
    second = _load_payload(tmp_path, _valid_payload(allowed_rooms=[2, 99, 0]))
    assert isinstance(second, SearchCriteriaLoadSuccess)

    assert first.criteria.allowed_rooms == second.criteria.allowed_rooms
    assert first.criteria.allowed_rooms == frozenset((RoomCount(0), RoomCount(2), RoomCount(99)))


def test_invalid_json_is_one_atomic_criteria_syntax_issue(tmp_path: Path) -> None:
    path = tmp_path / "private-name.json"
    path.write_text('{"schema_version":', encoding="utf-8")

    result = load_search_criteria(path)

    assert isinstance(result, SearchCriteriaLoadFailure)
    assert _issue_triples(result) == [("INPUT_SYNTAX", "invalid_json", "$")]
    assert not hasattr(result, "criteria")


@pytest.mark.parametrize("constant", ("NaN", "Infinity", "-Infinity"))
def test_nonstandard_json_constants_are_syntax_errors(tmp_path: Path, constant: str) -> None:
    path = tmp_path / "criteria.json"
    path.write_text(
        f'{{"schema_version":"search-criteria@1","criteria":{{"allowed_rooms":[{constant}]}}}}',
        encoding="utf-8",
    )

    result = load_search_criteria(path)

    assert isinstance(result, SearchCriteriaLoadFailure)
    assert _issue_triples(result) == [("INPUT_SYNTAX", "invalid_json", "$")]


def test_unsupported_schema_version_has_exact_issue(tmp_path: Path) -> None:
    result = _failure(tmp_path, {"schema_version": "search-criteria@2", "criteria": {}})

    assert _issue_triples(result) == [
        ("INPUT_SCHEMA", "unsupported_schema_version", "$.schema_version")
    ]


@pytest.mark.parametrize(
    ("payload", "expected_path"),
    (
        ({"criteria": {}}, "$.schema_version"),
        ({"schema_version": "search-criteria@1"}, "$.criteria"),
        (
            _valid_payload(maximum_price={"currency": "RUB"}),
            "$.criteria.maximum_price.amount_minor",
        ),
        (
            _valid_payload(maximum_price={"amount_minor": 1}),
            "$.criteria.maximum_price.currency",
        ),
    ),
)
def test_missing_structural_fields_have_narrow_exact_paths(
    tmp_path: Path,
    payload: object,
    expected_path: str,
) -> None:
    assert _issue_triples(_failure(tmp_path, payload)) == [
        ("INPUT_SCHEMA", "missing_field", expected_path)
    ]


@pytest.mark.parametrize(
    ("payload", "expected_path"),
    (
        (
            {"schema_version": "search-criteria@1", "criteria": {}, "extra": 1},
            "$.extra",
        ),
        (
            {"schema_version": "search-criteria@1", "criteria": {"extra": 1}},
            "$.criteria.extra",
        ),
        (
            _valid_payload(maximum_price={"amount_minor": 1, "currency": "RUB", "extra": 1}),
            "$.criteria.maximum_price.extra",
        ),
    ),
)
def test_extra_fields_are_forbidden_at_every_object_level(
    tmp_path: Path,
    payload: object,
    expected_path: str,
) -> None:
    assert _issue_triples(_failure(tmp_path, payload)) == [
        ("INPUT_SCHEMA", "extra_field", expected_path)
    ]


@pytest.mark.parametrize(
    ("payload", "expected_path"),
    (
        ([], "$"),
        ({"schema_version": "search-criteria@1", "criteria": []}, "$.criteria"),
        (_valid_payload(maximum_price=[]), "$.criteria.maximum_price"),
        (
            _valid_payload(maximum_price={"amount_minor": "1", "currency": "RUB"}),
            "$.criteria.maximum_price.amount_minor",
        ),
        (
            _valid_payload(maximum_price={"amount_minor": 1, "currency": 643}),
            "$.criteria.maximum_price.currency",
        ),
        (_valid_payload(minimum_total_area=47.12), "$.criteria.minimum_total_area"),
        (_valid_payload(allowed_rooms={"rooms": [1]}), "$.criteria.allowed_rooms"),
    ),
)
def test_wrong_root_nested_and_scalar_types_are_not_coerced(
    tmp_path: Path,
    payload: object,
    expected_path: str,
) -> None:
    assert _issue_triples(_failure(tmp_path, payload)) == [
        ("INPUT_SCHEMA", "wrong_type", expected_path)
    ]


@pytest.mark.parametrize("field", ("maximum_price", "minimum_total_area", "allowed_rooms"))
def test_explicit_null_is_wrong_type_for_every_optional_criterion(
    tmp_path: Path,
    field: str,
) -> None:
    assert _issue_triples(_failure(tmp_path, _valid_payload(**{field: None}))) == [
        ("INPUT_SCHEMA", "wrong_type", f"$.criteria.{field}")
    ]


@pytest.mark.parametrize("value", (True, 1.0, "1"))
def test_amount_minor_requires_a_strict_json_integer(tmp_path: Path, value: object) -> None:
    payload = _valid_payload(maximum_price={"amount_minor": value, "currency": "RUB"})

    assert _issue_triples(_failure(tmp_path, payload)) == [
        ("INPUT_SCHEMA", "wrong_type", "$.criteria.maximum_price.amount_minor")
    ]


@pytest.mark.parametrize("value", (True, 1.0, "1"))
def test_room_items_require_strict_json_integers(tmp_path: Path, value: object) -> None:
    assert _issue_triples(_failure(tmp_path, _valid_payload(allowed_rooms=[value]))) == [
        ("INPUT_SCHEMA", "wrong_type", "$.criteria.allowed_rooms[0]")
    ]


@pytest.mark.parametrize("amount", (1, MAX_INTEGER))
def test_amount_boundaries_are_accepted(tmp_path: Path, amount: int) -> None:
    result = _load_payload(
        tmp_path,
        _valid_payload(maximum_price={"amount_minor": amount, "currency": "RUB"}),
    )

    assert isinstance(result, SearchCriteriaLoadSuccess)
    assert result.criteria.maximum_price == Money(MoneyAmount(amount), Currency("RUB"))


@pytest.mark.parametrize("amount", (0, -1, MAX_INTEGER + 1))
def test_amount_outside_the_canonical_range_is_an_invalid_criterion(
    tmp_path: Path,
    amount: int,
) -> None:
    payload = _valid_payload(maximum_price={"amount_minor": amount, "currency": "RUB"})

    assert _issue_triples(_failure(tmp_path, payload)) == [
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.maximum_price.amount_minor")
    ]


def test_currency_must_be_the_exact_supported_value(tmp_path: Path) -> None:
    payload = _valid_payload(maximum_price={"amount_minor": 1, "currency": "USD"})

    assert _issue_triples(_failure(tmp_path, payload)) == [
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.maximum_price.currency")
    ]


@pytest.mark.parametrize(
    ("text", "hundredths"),
    (("0.01", 1), ("47.120", 4_712), ("1.2300", 123), ("92233720368547758.07", MAX_INTEGER)),
)
def test_area_is_parsed_exactly_without_rounding(
    tmp_path: Path,
    text: str,
    hundredths: int,
) -> None:
    result = _load_payload(tmp_path, _valid_payload(minimum_total_area=text))

    assert isinstance(result, SearchCriteriaLoadSuccess)
    assert result.criteria.minimum_total_area == Area(hundredths)


@pytest.mark.parametrize(
    "text",
    ("47.125", "0", "-1", "+1", ".5", "1e2", "1,5", " 1", "١", "92233720368547758.08"),
)
def test_invalid_or_inexact_area_is_rejected_at_the_criterion(
    tmp_path: Path,
    text: str,
) -> None:
    assert _issue_triples(_failure(tmp_path, _valid_payload(minimum_total_area=text))) == [
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.minimum_total_area")
    ]


@pytest.mark.parametrize("rooms", ([0], [99], [0, 99]))
def test_room_boundaries_are_accepted(tmp_path: Path, rooms: list[int]) -> None:
    result = _load_payload(tmp_path, _valid_payload(allowed_rooms=rooms))

    assert isinstance(result, SearchCriteriaLoadSuccess)
    assert result.criteria.allowed_rooms == frozenset(RoomCount(room) for room in rooms)


@pytest.mark.parametrize(
    ("rooms", "expected_path"),
    (
        ([], "$.criteria.allowed_rooms"),
        ([-1], "$.criteria.allowed_rooms[0]"),
        ([100], "$.criteria.allowed_rooms[0]"),
    ),
)
def test_empty_or_out_of_range_rooms_are_invalid_criteria(
    tmp_path: Path,
    rooms: list[int],
    expected_path: str,
) -> None:
    assert _issue_triples(_failure(tmp_path, _valid_payload(allowed_rooms=rooms))) == [
        ("INPUT_SCHEMA", "invalid_criterion", expected_path)
    ]


def test_each_duplicate_room_after_the_first_has_a_narrow_issue(tmp_path: Path) -> None:
    result = _failure(tmp_path, _valid_payload(allowed_rooms=[2, 0, 2, 2]))

    assert _issue_triples(result) == [
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.allowed_rooms[2]"),
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.allowed_rooms[3]"),
    ]


def test_multiple_independent_issues_are_atomic_and_stably_sorted(tmp_path: Path) -> None:
    payload = {
        "schema_version": "search-criteria@2",
        "criteria": {
            "allowed_rooms": [2, True, 2, 100],
            "minimum_total_area": "47.125",
            "maximum_price": {"amount_minor": 0, "currency": "USD", "extra": 1},
            "extra": "private input",
        },
        "extra": "private root input",
    }

    result = _failure(tmp_path, payload)

    assert _issue_triples(result) == [
        ("INPUT_SCHEMA", "wrong_type", "$.criteria.allowed_rooms[1]"),
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.allowed_rooms[2]"),
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.allowed_rooms[3]"),
        ("INPUT_SCHEMA", "extra_field", "$.criteria.extra"),
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.maximum_price.amount_minor"),
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.maximum_price.currency"),
        ("INPUT_SCHEMA", "extra_field", "$.criteria.maximum_price.extra"),
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.minimum_total_area"),
        ("INPUT_SCHEMA", "extra_field", "$.extra"),
        ("INPUT_SCHEMA", "unsupported_schema_version", "$.schema_version"),
    ]
    assert not hasattr(result, "criteria")


def test_type_error_inside_room_array_is_also_sorted_with_semantic_issues(tmp_path: Path) -> None:
    result = _failure(tmp_path, _valid_payload(allowed_rooms=[2, True, 2, 100]))

    assert _issue_triples(result) == [
        ("INPUT_SCHEMA", "wrong_type", "$.criteria.allowed_rooms[1]"),
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.allowed_rooms[2]"),
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.allowed_rooms[3]"),
    ]


def test_failure_and_nested_issue_tuple_are_immutable(tmp_path: Path) -> None:
    result = _failure(tmp_path, _valid_payload(allowed_rooms=[]))

    with pytest.raises(ValueError, match="must contain an issue"):
        SearchCriteriaLoadFailure(issues=())
    with pytest.raises(FrozenInstanceError):
        _assign_issues(result)
    assert isinstance(result.issues, tuple)


def test_operational_file_and_utf8_failures_are_not_content_issues(tmp_path: Path) -> None:
    missing = tmp_path / "private-absolute-name.json"
    with pytest.raises(OSError):
        load_search_criteria(missing)

    invalid_utf8 = tmp_path / "private-invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff")
    with pytest.raises(UnicodeError):
        load_search_criteria(invalid_utf8)


def test_contract_issues_do_not_leak_path_or_input_values(tmp_path: Path) -> None:
    secret_value = "private-value-that-must-not-leak"
    path = tmp_path / "private-absolute-name.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": secret_value,
                "criteria": {"minimum_total_area": secret_value},
            }
        ),
        encoding="utf-8",
    )

    result = load_search_criteria(path)

    assert isinstance(result, SearchCriteriaLoadFailure)
    assert _issue_triples(result) == [
        ("INPUT_SCHEMA", "invalid_criterion", "$.criteria.minimum_total_area"),
        ("INPUT_SCHEMA", "unsupported_schema_version", "$.schema_version"),
    ]

    rendered = repr(result.issues)
    assert secret_value not in rendered
    assert str(path.resolve()) not in rendered
    assert all(issue.safe_text is None for issue in result.issues)
