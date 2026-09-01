"""Strict local-file boundary for ``search-criteria@1`` documents."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Never

from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError

from real_estate_parser.normalization import Area, Currency, MoneyAmount, RoomCount
from real_estate_parser.search_criteria import (
    Money,
    SearchCriteria,
    SearchCriteriaLoadFailure,
    SearchCriteriaLoadResult,
    SearchCriteriaLoadSuccess,
)
from real_estate_parser.source_batch import ContractIssue, InputLocation

_MAX_CANONICAL_INTEGER = 9_223_372_036_854_775_807
_MAX_CANONICAL_INTEGER_TEXT = str(_MAX_CANONICAL_INTEGER)
_AREA_PATTERN = re.compile(r"(?P<whole>[0-9]+)(?:\.(?P<fraction>[0-9]+))?", re.ASCII)


class _StrictDocumentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _MaximumPriceDocument(_StrictDocumentModel):
    amount_minor: StrictInt
    currency: str


class _CriteriaDocument(_StrictDocumentModel):
    maximum_price: _MaximumPriceDocument | None = None
    minimum_total_area: str | None = None
    allowed_rooms: list[StrictInt] | None = None


class _SearchCriteriaDocument(_StrictDocumentModel):
    schema_version: str
    criteria: _CriteriaDocument


def _reject_nonstandard_json_constant(value: str) -> Never:
    raise json.JSONDecodeError("non-standard JSON constant", value, 0)


def _load_json(text: str) -> Any:
    return json.loads(text, parse_constant=_reject_nonstandard_json_constant)


def _criteria_location(*parts: str | int) -> InputLocation:
    segments: list[str] = []
    for part in parts:
        if isinstance(part, int):
            if not segments:
                raise ValueError("an array index must follow a criteria path segment")
            segments[-1] = f"{segments[-1]}[{part}]"
        else:
            segments.append(part)
    return InputLocation("criteria", source_path=tuple(segments))


def _location_from_error(error_location: tuple[int | str, ...]) -> InputLocation:
    return _criteria_location(*error_location)


def _issue_code(error_type: str) -> str:
    if error_type == "missing":
        return "missing_field"
    if error_type == "extra_forbidden":
        return "extra_field"
    if error_type in {
        "dict_type",
        "int_type",
        "list_type",
        "model_type",
        "none_required",
        "string_type",
    }:
        return "wrong_type"
    return "wrong_type"


def _issue(location: InputLocation, code: str) -> ContractIssue:
    return ContractIssue(category="INPUT_SCHEMA", code=code, location=location)


def _issue_sort_key(issue: ContractIssue) -> tuple[int, int, str, str, str]:
    document_rank = {"listings": 0, "criteria": 1}[issue.location.document]
    record_index = issue.location.record_index
    return (
        document_rank,
        -1 if record_index is None else record_index,
        issue.location.json_path,
        issue.category,
        issue.code,
    )


def _schema_issues(error: ValidationError) -> list[ContractIssue]:
    issues: list[ContractIssue] = []
    for detail in error.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    ):
        issues.append(
            _issue(
                _location_from_error(detail["loc"]),
                _issue_code(detail["type"]),
            )
        )
    return issues


def _area_hundredths(value: str) -> int | None:
    match = _AREA_PATTERN.fullmatch(value)
    if match is None:
        return None
    fraction = match.group("fraction") or ""
    if len(fraction) > 2 and any(digit != "0" for digit in fraction[2:]):
        return None
    digits = (match.group("whole") + fraction[:2].ljust(2, "0")).lstrip("0") or "0"
    if len(digits) > len(_MAX_CANONICAL_INTEGER_TEXT):
        return None
    if len(digits) == len(_MAX_CANONICAL_INTEGER_TEXT) and digits > _MAX_CANONICAL_INTEGER_TEXT:
        return None
    result = int(digits)
    return result if result >= 1 else None


def _semantic_issues(parsed: Any) -> list[ContractIssue]:
    issues: list[ContractIssue] = []
    if not isinstance(parsed, dict):
        return issues

    schema_version = parsed.get("schema_version")
    if isinstance(schema_version, str) and schema_version != "search-criteria@1":
        issues.append(_issue(_criteria_location("schema_version"), "unsupported_schema_version"))

    criteria = parsed.get("criteria")
    if not isinstance(criteria, dict):
        return issues

    maximum_price = criteria.get("maximum_price")
    if "maximum_price" in criteria and maximum_price is None:
        issues.append(_issue(_criteria_location("criteria", "maximum_price"), "wrong_type"))
    elif isinstance(maximum_price, dict):
        amount = maximum_price.get("amount_minor")
        if type(amount) is int and not 1 <= amount <= _MAX_CANONICAL_INTEGER:
            issues.append(
                _issue(
                    _criteria_location("criteria", "maximum_price", "amount_minor"),
                    "invalid_criterion",
                )
            )
        currency = maximum_price.get("currency")
        if isinstance(currency, str) and currency != "RUB":
            issues.append(
                _issue(
                    _criteria_location("criteria", "maximum_price", "currency"),
                    "invalid_criterion",
                )
            )

    minimum_total_area = criteria.get("minimum_total_area")
    if "minimum_total_area" in criteria and minimum_total_area is None:
        issues.append(_issue(_criteria_location("criteria", "minimum_total_area"), "wrong_type"))
    elif isinstance(minimum_total_area, str) and _area_hundredths(minimum_total_area) is None:
        issues.append(
            _issue(_criteria_location("criteria", "minimum_total_area"), "invalid_criterion")
        )

    allowed_rooms = criteria.get("allowed_rooms")
    if "allowed_rooms" in criteria and allowed_rooms is None:
        issues.append(_issue(_criteria_location("criteria", "allowed_rooms"), "wrong_type"))
    elif isinstance(allowed_rooms, list):
        if not allowed_rooms:
            issues.append(
                _issue(_criteria_location("criteria", "allowed_rooms"), "invalid_criterion")
            )
        seen: set[int] = set()
        for index, room in enumerate(allowed_rooms):
            if type(room) is not int:
                continue
            location = _criteria_location("criteria", "allowed_rooms", index)
            if not 0 <= room <= 99 or room in seen:
                issues.append(_issue(location, "invalid_criterion"))
            seen.add(room)
    return issues


def _canonical_criteria(document: _SearchCriteriaDocument) -> SearchCriteria:
    maximum_price = document.criteria.maximum_price
    area_text = document.criteria.minimum_total_area
    room_values = document.criteria.allowed_rooms

    canonical_price = None
    if maximum_price is not None:
        canonical_price = Money(
            amount=MoneyAmount(maximum_price.amount_minor),
            currency=Currency(maximum_price.currency),
        )

    canonical_area = None
    if area_text is not None:
        area_hundredths = _area_hundredths(area_text)
        if area_hundredths is None:
            raise RuntimeError("validated criteria area unexpectedly became invalid")
        canonical_area = Area(area_hundredths)

    canonical_rooms = None
    if room_values is not None:
        canonical_rooms = frozenset(RoomCount(value) for value in room_values)

    return SearchCriteria(
        maximum_price=canonical_price,
        minimum_total_area=canonical_area,
        allowed_rooms=canonical_rooms,
    )


def load_search_criteria(path: Path) -> SearchCriteriaLoadResult:
    """Read and strictly validate one explicit local criteria JSON file.

    File access and UTF-8 decoding failures remain operational exceptions and
    are deliberately not converted into content diagnostics.
    """

    text = path.read_text(encoding="utf-8")
    try:
        parsed = _load_json(text)
    except json.JSONDecodeError:
        return SearchCriteriaLoadFailure(
            issues=(
                ContractIssue(
                    category="INPUT_SYNTAX",
                    code="invalid_json",
                    location=InputLocation("criteria"),
                ),
            )
        )

    document: _SearchCriteriaDocument | None = None
    issues: list[ContractIssue] = []
    try:
        document = _SearchCriteriaDocument.model_validate(parsed)
    except ValidationError as error:
        issues.extend(_schema_issues(error))
    issues.extend(_semantic_issues(parsed))
    if issues:
        return SearchCriteriaLoadFailure(issues=tuple(sorted(issues, key=_issue_sort_key)))
    if document is None:
        raise RuntimeError("criteria validation failed without a contract issue")
    return SearchCriteriaLoadSuccess(criteria=_canonical_criteria(document))


__all__ = ["load_search_criteria"]
