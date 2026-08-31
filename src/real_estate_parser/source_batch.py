"""Neutral contracts for a structurally validated source batch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

type InputDocument = Literal["listings", "criteria"]
type IssueCategory = Literal[
    "INPUT_SYNTAX",
    "INPUT_SCHEMA",
    "SOURCE_ADAPTER",
    "NORMALIZATION",
    "COLLECTION_CONFLICT",
    "OUTPUT_CONTRACT",
]


@dataclass(frozen=True, slots=True)
class InputLocation:
    """Structured location inside one input document."""

    document: InputDocument
    record_index: int | None = None
    source_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.record_index is not None:
            if self.document != "listings":
                raise ValueError("only a listings document can have a record index")
            if self.record_index < 0:
                raise ValueError("record index must be non-negative")
        if any(not segment for segment in self.source_path):
            raise ValueError("source path segments must be non-empty")

    @property
    def json_path(self) -> str:
        """Render the stable JSONPath-like contract representation."""

        if self.record_index is None:
            base = "$"
        else:
            base = f"$.listings[{self.record_index}]"
        return base + "".join(f".{segment}" for segment in self.source_path)


@dataclass(frozen=True, slots=True)
class ContractIssue:
    """Stable issue fields returned by a contract boundary."""

    category: IssueCategory
    code: str
    location: InputLocation
    safe_text: str | None = None


@dataclass(frozen=True, slots=True)
class ValidatedSourceField:
    """A provided source string with its exact input location."""

    value: str
    location: InputLocation


@dataclass(frozen=True, slots=True)
class MissingSourceField:
    """An absent optional source field with its expected location."""

    location: InputLocation


type OptionalValidatedSourceField = ValidatedSourceField | MissingSourceField


@dataclass(frozen=True, slots=True)
class ValidatedSourceListing:
    """One source-specific listing after structural validation only."""

    publication_id: ValidatedSourceField
    url: ValidatedSourceField
    observed_at: ValidatedSourceField
    location_text: OptionalValidatedSourceField
    price_major: OptionalValidatedSourceField
    currency: OptionalValidatedSourceField
    total_area_sqm: OptionalValidatedSourceField
    rooms: OptionalValidatedSourceField
    location: InputLocation


@dataclass(frozen=True, slots=True)
class ValidatedSourceBatch:
    """Complete immutable source-specific batch accepted by the boundary."""

    schema_version: ValidatedSourceField
    source: ValidatedSourceField
    listings: tuple[ValidatedSourceListing, ...]


@dataclass(frozen=True, slots=True)
class SourceBatchLoadSuccess:
    """Successful and complete boundary result."""

    batch: ValidatedSourceBatch


@dataclass(frozen=True, slots=True)
class SourceBatchLoadFailure:
    """Atomic boundary failure with no partial batch."""

    issues: tuple[ContractIssue, ...]

    def __post_init__(self) -> None:
        if not self.issues:
            raise ValueError("a failed source batch load must contain an issue")


type SourceBatchLoadResult = SourceBatchLoadSuccess | SourceBatchLoadFailure


__all__ = [
    "ContractIssue",
    "InputLocation",
    "MissingSourceField",
    "OptionalValidatedSourceField",
    "SourceBatchLoadFailure",
    "SourceBatchLoadResult",
    "SourceBatchLoadSuccess",
    "ValidatedSourceBatch",
    "ValidatedSourceField",
    "ValidatedSourceListing",
]
