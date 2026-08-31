"""Strict local-file boundary for ``fixture-source-batch@1`` documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from real_estate_parser.source_batch import (
    ContractIssue,
    InputLocation,
    MissingSourceField,
    OptionalValidatedSourceField,
    SourceBatchLoadFailure,
    SourceBatchLoadResult,
    SourceBatchLoadSuccess,
    ValidatedSourceBatch,
    ValidatedSourceField,
    ValidatedSourceListing,
)

_OPTIONAL_LISTING_FIELDS = (
    "location_text",
    "price_major",
    "currency",
    "total_area_sqm",
    "rooms",
)


class _StrictDocumentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _FixtureListingDocument(_StrictDocumentModel):
    publication_id: str
    url: str
    observed_at: str
    location_text: str | None = None
    price_major: str | None = None
    currency: str | None = None
    total_area_sqm: str | None = None
    rooms: str | None = None

    @field_validator(*_OPTIONAL_LISTING_FIELDS, mode="before")
    @classmethod
    def _reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("explicit null is not a source string")
        return value


class _FixtureSourceBatchDocument(_StrictDocumentModel):
    schema_version: Literal["fixture-source-batch@1"]
    source: str
    listings: list[_FixtureListingDocument] = Field(min_length=1)


def _reject_nonstandard_json_constant(value: str) -> Never:
    raise json.JSONDecodeError("non-standard JSON constant", value, 0)


def _load_json(text: str) -> Any:
    return json.loads(text, parse_constant=_reject_nonstandard_json_constant)


def _location_from_error(error_location: tuple[int | str, ...]) -> InputLocation:
    if len(error_location) >= 2 and error_location[0] == "listings":
        possible_index = error_location[1]
        if isinstance(possible_index, int):
            source_path = tuple(str(part) for part in error_location[2:])
            return InputLocation("listings", possible_index, source_path)
    return InputLocation("listings", source_path=tuple(str(part) for part in error_location))


def _issue_code(error_type: str, location: InputLocation) -> str:
    if error_type == "missing":
        return "missing_field"
    if error_type == "extra_forbidden":
        return "extra_field"
    if error_type == "literal_error" and location.json_path == "$.schema_version":
        return "unsupported_schema_version"
    if error_type == "too_short" and location.json_path == "$.listings":
        return "invalid_value"
    if error_type in {"dict_type", "list_type", "model_type", "string_type", "value_error"}:
        return "wrong_type"
    return "invalid_value"


def _schema_issues(error: ValidationError) -> tuple[ContractIssue, ...]:
    issues: list[ContractIssue] = []
    for detail in error.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    ):
        location = _location_from_error(detail["loc"])
        issues.append(
            ContractIssue(
                category="INPUT_SCHEMA",
                code=_issue_code(detail["type"], location),
                location=location,
            )
        )
    return tuple(sorted(issues, key=_issue_sort_key))


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


def _field(value: str, record_index: int | None, name: str) -> ValidatedSourceField:
    return ValidatedSourceField(
        value=value,
        location=InputLocation("listings", record_index, (name,)),
    )


def _optional_field(
    document: _FixtureListingDocument,
    record_index: int,
    name: Literal["location_text", "price_major", "currency", "total_area_sqm", "rooms"],
) -> OptionalValidatedSourceField:
    location = InputLocation("listings", record_index, (name,))
    if name not in document.model_fields_set:
        return MissingSourceField(location=location)
    value = getattr(document, name)
    if value is None:
        raise RuntimeError("validated optional source field unexpectedly contains null")
    return ValidatedSourceField(value=value, location=location)


def _validated_batch(document: _FixtureSourceBatchDocument) -> ValidatedSourceBatch:
    listings = tuple(
        ValidatedSourceListing(
            publication_id=_field(listing.publication_id, index, "publication_id"),
            url=_field(listing.url, index, "url"),
            observed_at=_field(listing.observed_at, index, "observed_at"),
            location_text=_optional_field(listing, index, "location_text"),
            price_major=_optional_field(listing, index, "price_major"),
            currency=_optional_field(listing, index, "currency"),
            total_area_sqm=_optional_field(listing, index, "total_area_sqm"),
            rooms=_optional_field(listing, index, "rooms"),
            location=InputLocation("listings", index),
        )
        for index, listing in enumerate(document.listings)
    )
    return ValidatedSourceBatch(
        schema_version=_field(document.schema_version, None, "schema_version"),
        source=_field(document.source, None, "source"),
        listings=listings,
    )


def load_fixture_source_batch(path: Path) -> SourceBatchLoadResult:
    """Read and structurally validate exactly one explicit local JSON file.

    File access and UTF-8 decoding failures are operational exceptions. They are
    deliberately not reclassified as content syntax or schema issues.
    """

    text = path.read_text(encoding="utf-8")
    try:
        parsed = _load_json(text)
    except json.JSONDecodeError:
        return SourceBatchLoadFailure(
            issues=(
                ContractIssue(
                    category="INPUT_SYNTAX",
                    code="invalid_json",
                    location=InputLocation("listings"),
                ),
            )
        )

    try:
        document = _FixtureSourceBatchDocument.model_validate(parsed)
    except ValidationError as error:
        return SourceBatchLoadFailure(issues=_schema_issues(error))
    return SourceBatchLoadSuccess(batch=_validated_batch(document))


__all__ = ["load_fixture_source_batch"]
