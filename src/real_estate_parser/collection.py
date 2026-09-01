"""Atomic normalization and in-memory collection construction."""

from __future__ import annotations

from dataclasses import dataclass

from real_estate_parser.normalization import (
    FIXTURE_NORMALIZATION_RULES_V1,
    FixtureNormalizationRules,
    NormalizationFailure,
    NormalizedListing,
    normalize_fixture_snapshot,
)
from real_estate_parser.source_batch import (
    ContractIssue,
    InputLocation,
    PublicationRef,
    SourceBatch,
)


@dataclass(frozen=True, slots=True)
class CollectionSnapshot:
    """Complete ordered in-memory collection of normalized publications."""

    listings: tuple[NormalizedListing, ...]


@dataclass(frozen=True, slots=True)
class CollectionBuildSuccess:
    """Successful normalization and complete collection construction."""

    snapshot: CollectionSnapshot


@dataclass(frozen=True, slots=True)
class CollectionBuildFailure:
    """Atomic failure without normalized listings or a partial collection."""

    issues: tuple[ContractIssue, ...]

    def __post_init__(self) -> None:
        if not self.issues:
            raise ValueError("a failed collection build must contain an issue")


type CollectionBuildResult = CollectionBuildSuccess | CollectionBuildFailure


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


def _record_location(listing: NormalizedListing) -> InputLocation:
    input_path = listing.reference.provenance.input_path
    return InputLocation(
        document=input_path.document,
        record_index=input_path.record_index,
    )


def _duplicate_issues(listings: tuple[NormalizedListing, ...]) -> tuple[ContractIssue, ...]:
    seen: set[PublicationRef] = set()
    issues: list[ContractIssue] = []
    for listing in listings:
        reference = listing.reference.value
        if reference in seen:
            issues.append(
                ContractIssue(
                    category="COLLECTION_CONFLICT",
                    code="duplicate_publication_ref",
                    location=_record_location(listing),
                )
            )
        else:
            seen.add(reference)
    return tuple(sorted(issues, key=_issue_sort_key))


def build_fixture_collection(
    batch: SourceBatch,
    rules: FixtureNormalizationRules = FIXTURE_NORMALIZATION_RULES_V1,
) -> CollectionBuildResult:
    """Normalize a complete source batch and atomically build its collection."""

    listings: list[NormalizedListing] = []
    issues: list[ContractIssue] = []

    for snapshot in batch.snapshots:
        result = normalize_fixture_snapshot(snapshot, rules)
        if isinstance(result, NormalizationFailure):
            issues.extend(result.issues)
        else:
            listings.append(result.listing)

    if issues:
        return CollectionBuildFailure(issues=tuple(sorted(issues, key=_issue_sort_key)))

    normalized_listings = tuple(listings)
    duplicate_issues = _duplicate_issues(normalized_listings)
    if duplicate_issues:
        return CollectionBuildFailure(issues=duplicate_issues)
    return CollectionBuildSuccess(snapshot=CollectionSnapshot(listings=normalized_listings))


__all__ = [
    "CollectionBuildFailure",
    "CollectionBuildResult",
    "CollectionBuildSuccess",
    "CollectionSnapshot",
    "build_fixture_collection",
]
