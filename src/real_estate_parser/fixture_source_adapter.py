"""Pure adapter for the structurally validated ``fixture_portal`` source."""

from __future__ import annotations

from urllib.parse import urlsplit

from real_estate_parser.source_batch import (
    ContractIssue,
    FixtureSourceAdaptationFailure,
    FixtureSourceAdaptationResult,
    FixtureSourceAdaptationSuccess,
    MissingField,
    MissingSourceField,
    PublicationId,
    PublicationRef,
    RawField,
    SourceBatch,
    SourceId,
    SourcePublicationSnapshot,
    ValidatedSourceBatch,
    ValidatedSourceField,
)

_FIXTURE_SOURCE_ID = SourceId("fixture_portal")
_FIXTURE_HOST = "listings.fixture.example"
_OFFER_PATH_PREFIX = "/offers/"


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


def _raw_field(field: ValidatedSourceField) -> RawField:
    return RawField(value=field.value, location=field.location)


def _raw_or_missing(field: ValidatedSourceField | MissingSourceField) -> RawField | MissingField:
    if isinstance(field, ValidatedSourceField):
        return _raw_field(field)
    return MissingField(location=field.location)


def _publication_id(value: str) -> PublicationId | None:
    try:
        return PublicationId(value)
    except ValueError:
        return None


def _valid_source_url(value: str, publication_id: PublicationId | None) -> bool:
    if not value.isascii() or "?" in value or "#" in value:
        return False

    try:
        parsed = urlsplit(value)
    except ValueError:
        return False

    if parsed.scheme != "https":
        return False
    if parsed.netloc != _FIXTURE_HOST:
        return False
    if parsed.query or parsed.fragment:
        return False
    if not parsed.path.startswith(_OFFER_PATH_PREFIX):
        return False

    path_publication_id = _publication_id(parsed.path.removeprefix(_OFFER_PATH_PREFIX))
    if path_publication_id is None:
        return False
    if publication_id is not None and path_publication_id != publication_id:
        return False
    return True


def adapt_fixture_source_batch(batch: ValidatedSourceBatch) -> FixtureSourceAdaptationResult:
    """Apply only ``fixture_portal`` identity and record-consistency rules."""

    issues: list[ContractIssue] = []
    snapshots: list[SourcePublicationSnapshot] = []

    if batch.source.value != _FIXTURE_SOURCE_ID.value:
        issues.append(
            ContractIssue(
                category="SOURCE_ADAPTER",
                code="source_mismatch",
                location=batch.source.location,
            )
        )

    for listing in batch.listings:
        publication_id = _publication_id(listing.publication_id.value)
        if publication_id is None:
            issues.append(
                ContractIssue(
                    category="SOURCE_ADAPTER",
                    code="inconsistent_record",
                    location=listing.publication_id.location,
                )
            )

        if not _valid_source_url(listing.url.value, publication_id):
            issues.append(
                ContractIssue(
                    category="SOURCE_ADAPTER",
                    code="invalid_source_url",
                    location=listing.url.location,
                )
            )

        if publication_id is None:
            continue

        snapshots.append(
            SourcePublicationSnapshot(
                reference=PublicationRef(
                    source_id=_FIXTURE_SOURCE_ID,
                    publication_id=publication_id,
                ),
                source_url=_raw_field(listing.url),
                observed_at=_raw_field(listing.observed_at),
                location_text=_raw_or_missing(listing.location_text),
                price_amount=_raw_or_missing(listing.price_major),
                currency=_raw_or_missing(listing.currency),
                total_area=_raw_or_missing(listing.total_area_sqm),
                rooms=_raw_or_missing(listing.rooms),
                input_location=listing.location,
            )
        )

    if issues:
        return FixtureSourceAdaptationFailure(issues=tuple(sorted(issues, key=_issue_sort_key)))
    return FixtureSourceAdaptationSuccess(batch=SourceBatch(snapshots=tuple(snapshots)))


__all__ = ["adapt_fixture_source_batch"]
