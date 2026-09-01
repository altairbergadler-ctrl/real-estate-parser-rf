"""Path-level composition for the first deterministic local search slice."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from real_estate_parser.collection import CollectionBuildFailure, build_fixture_collection
from real_estate_parser.fixture_source_adapter import adapt_fixture_source_batch
from real_estate_parser.fixture_source_batch import load_fixture_source_batch
from real_estate_parser.search import search_collection
from real_estate_parser.search_criteria import (
    SearchCriteriaLoadFailure,
    SearchCriteriaLoadResult,
    SearchCriteriaLoadSuccess,
)
from real_estate_parser.search_criteria_boundary import load_search_criteria
from real_estate_parser.search_result_boundary import (
    SearchResultSerializationFailure,
    serialize_search_result_document,
)
from real_estate_parser.search_result_mapping import map_search_result
from real_estate_parser.source_batch import (
    ContractIssue,
    FixtureSourceAdaptationFailure,
    SourceBatchLoadFailure,
    SourceBatchLoadResult,
    SourceBatchLoadSuccess,
)

type InputRole = Literal["listings", "criteria"]
type OperationalFailureReason = Literal["invalid_utf8", "unreadable_input"]


class LocalSearchOperationalError(Exception):
    """Safe role-aware operational failure for the outer CLI adapter."""

    __slots__ = ("reason", "role")

    def __init__(self, role: InputRole, reason: OperationalFailureReason) -> None:
        self.role = role
        self.reason = reason
        super().__init__(f"{role}/{reason}")


@dataclass(frozen=True, slots=True)
class LocalSearchSuccess:
    """Complete canonical result bytes for one successful local search."""

    json_bytes: bytes


@dataclass(frozen=True, slots=True)
class LocalSearchFailure:
    """Atomic application failure without a collection or result bytes."""

    issues: tuple[ContractIssue, ...]

    def __post_init__(self) -> None:
        if not self.issues:
            raise ValueError("a failed local search must contain an issue")


type LocalSearchResult = LocalSearchSuccess | LocalSearchFailure


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


def _failure(issues: tuple[ContractIssue, ...]) -> LocalSearchFailure:
    return LocalSearchFailure(issues=tuple(sorted(issues, key=_issue_sort_key)))


def _load_listings(path: Path) -> SourceBatchLoadResult:
    try:
        return load_fixture_source_batch(path)
    except UnicodeDecodeError:
        raise LocalSearchOperationalError("listings", "invalid_utf8") from None
    except OSError:
        raise LocalSearchOperationalError("listings", "unreadable_input") from None


def _load_criteria(path: Path) -> SearchCriteriaLoadResult:
    try:
        return load_search_criteria(path)
    except UnicodeDecodeError:
        raise LocalSearchOperationalError("criteria", "invalid_utf8") from None
    except OSError:
        raise LocalSearchOperationalError("criteria", "unreadable_input") from None


def run_local_search(listings_path: Path, criteria_path: Path) -> LocalSearchResult:
    """Run the complete local fixture search or return all provable input issues."""

    listings_result = _load_listings(listings_path)
    criteria_result = _load_criteria(criteria_path)

    input_issues: list[ContractIssue] = []
    if isinstance(listings_result, SourceBatchLoadFailure):
        input_issues.extend(listings_result.issues)
    if isinstance(criteria_result, SearchCriteriaLoadFailure):
        input_issues.extend(criteria_result.issues)
    if input_issues:
        return _failure(tuple(input_issues))
    if not isinstance(listings_result, SourceBatchLoadSuccess):
        raise RuntimeError("listings load ended without success or issues")
    if not isinstance(criteria_result, SearchCriteriaLoadSuccess):
        raise RuntimeError("criteria load ended without success or issues")

    adaptation_result = adapt_fixture_source_batch(listings_result.batch)
    if isinstance(adaptation_result, FixtureSourceAdaptationFailure):
        return _failure(adaptation_result.issues)

    collection_result = build_fixture_collection(adaptation_result.batch)
    if isinstance(collection_result, CollectionBuildFailure):
        return _failure(collection_result.issues)

    search_result = search_collection(collection_result.snapshot, criteria_result.criteria)
    result_document = map_search_result(search_result)
    serialization_result = serialize_search_result_document(result_document)
    if isinstance(serialization_result, SearchResultSerializationFailure):
        return _failure(serialization_result.issues)
    return LocalSearchSuccess(json_bytes=serialization_result.json_bytes)


__all__ = [
    "LocalSearchFailure",
    "LocalSearchResult",
    "LocalSearchSuccess",
    "run_local_search",
]
