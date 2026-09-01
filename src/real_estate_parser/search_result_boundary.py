"""Strict validation and canonical JSON bytes for ``search-result@1``."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from real_estate_parser.search_result_mapping import SearchResultDocument
from real_estate_parser.source_batch import ContractIssue, InputLocation

_MAX_CANONICAL_INTEGER = 9_223_372_036_854_775_807
_CANONICAL_AREA_PATTERN = r"^(?:0\.(?:0[1-9]|[1-9][0-9])|[1-9][0-9]*\.[0-9]{2})$"
_CANONICAL_TIMESTAMP_PATTERN = (
    r"^[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])"
    r"T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\.[0-9]{6}Z$"
)
_INPUT_PATH_PATTERN = r"^\$\.listings\[[0-9]+\](?:\.[^\s.\[\]]+)+$"
_PUBLICATION_ID_PATTERN = r"^[A-Za-z0-9._:-]{1,128}$"
_SOURCE_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"
_VERSION_PATTERN = r"^[\x21-\x7e]{1,128}$"

type _PositiveCanonicalInteger = Annotated[int, Field(ge=1, le=_MAX_CANONICAL_INTEGER)]
type _RoomInteger = Annotated[int, Field(ge=0, le=99)]
type _CanonicalArea = Annotated[str, Field(pattern=_CANONICAL_AREA_PATTERN)]
type _CanonicalTimestamp = Annotated[str, Field(pattern=_CANONICAL_TIMESTAMP_PATTERN)]
type _InputPath = Annotated[str, Field(pattern=_INPUT_PATH_PATTERN)]
type _PublicationId = Annotated[str, Field(pattern=_PUBLICATION_ID_PATTERN)]
type _SourceId = Annotated[str, Field(pattern=_SOURCE_ID_PATTERN)]
type _Version = Annotated[str, Field(pattern=_VERSION_PATTERN)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
        strict=True,
    )


class _PublicationRefModel(_StrictModel):
    publication_id: _PublicationId
    source_id: _SourceId


class _ProvidedProvenanceModel(_StrictModel):
    input_path: _InputPath
    normalization_rule_version: _Version
    observed_at: _CanonicalTimestamp
    publication_id: _PublicationId
    raw_value: str
    source_field: str
    source_id: _SourceId


class _MissingProvenanceModel(_StrictModel):
    input_path: _InputPath
    normalization_rule_version: _Version
    observed_at: _CanonicalTimestamp
    publication_id: _PublicationId
    source_field: str
    source_id: _SourceId


class _TracedValueModel[T](_StrictModel):
    provenance: _ProvidedProvenanceModel
    value: T


class _PresentModel[T](_StrictModel):
    provenance: _ProvidedProvenanceModel
    state: Literal["present"]
    value: T


class _MissingModel(_StrictModel):
    provenance: _MissingProvenanceModel
    state: Literal["missing"]


class _UnsupportedModel(_StrictModel):
    provenance: _ProvidedProvenanceModel
    reason_code: str
    state: Literal["unsupported"]


type _FieldOutcomeModel[T] = Annotated[
    _PresentModel[T] | _MissingModel | _UnsupportedModel,
    Field(discriminator="state"),
]


class _MoneyModel(_StrictModel):
    amount_minor: _PositiveCanonicalInteger
    currency: Literal["RUB"]


class _CriteriaModel(_StrictModel):
    allowed_rooms: tuple[_RoomInteger, ...] | None = None
    maximum_price: _MoneyModel | None = None
    minimum_total_area: _CanonicalArea | None = None

    @field_validator("allowed_rooms")
    @classmethod
    def _rooms_are_strictly_increasing(
        cls,
        value: tuple[int, ...] | None,
    ) -> tuple[int, ...] | None:
        if value is not None and (
            not value or any(left >= right for left, right in zip(value, value[1:], strict=False))
        ):
            raise ValueError("allowed_rooms must be non-empty and strictly increasing")
        return value


class _MatchModel(_StrictModel):
    currency: _FieldOutcomeModel[Literal["RUB"]]
    location_text: _FieldOutcomeModel[str]
    observed_at: _TracedValueModel[_CanonicalTimestamp]
    price_amount: _FieldOutcomeModel[_PositiveCanonicalInteger]
    publication_ref: _TracedValueModel[_PublicationRefModel]
    rooms: _FieldOutcomeModel[_RoomInteger]
    source_url: _TracedValueModel[str]
    total_area: _FieldOutcomeModel[_CanonicalArea]


class _SearchResultModel(_StrictModel):
    criteria: _CriteriaModel
    matches: tuple[_MatchModel, ...]
    schema_version: Literal["search-result@1"]


@dataclass(frozen=True, slots=True)
class SearchResultSerializationSuccess:
    """Complete canonical bytes for one validated result document."""

    json_bytes: bytes


@dataclass(frozen=True, slots=True)
class SearchResultSerializationFailure:
    """Atomic output-contract failure without partial serialized bytes."""

    issues: tuple[ContractIssue, ...]

    def __post_init__(self) -> None:
        if not self.issues:
            raise ValueError("a failed result serialization must contain an issue")


type SearchResultSerializationResult = (
    SearchResultSerializationSuccess | SearchResultSerializationFailure
)


def _failure() -> SearchResultSerializationFailure:
    return SearchResultSerializationFailure(
        issues=(
            ContractIssue(
                category="OUTPUT_CONTRACT",
                code="invalid_result_document",
                location=InputLocation("criteria"),
            ),
        )
    )


def serialize_search_result_document(
    document: SearchResultDocument,
) -> SearchResultSerializationResult:
    """Validate and atomically serialize one ready result document."""

    try:
        validated = _SearchResultModel.model_validate(document)
        payload = validated.model_dump(mode="json", exclude_none=True)
        text = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return SearchResultSerializationSuccess(json_bytes=text.encode("utf-8") + b"\n")
    except Exception:
        return _failure()


__all__ = [
    "SearchResultSerializationFailure",
    "SearchResultSerializationResult",
    "SearchResultSerializationSuccess",
    "serialize_search_result_document",
]
