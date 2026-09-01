"""Pure canonical mapping from a search result to an immutable document tree."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from real_estate_parser.normalization import (
    Area,
    Currency,
    FieldOutcome,
    LocationText,
    Missing,
    MissingProvenance,
    MoneyAmount,
    ObservedAt,
    Present,
    RoomCount,
    SourceUrl,
    TracedValue,
    UnsupportedProvenance,
    ValueProvenance,
)
from real_estate_parser.search import SearchMatch, SearchResult
from real_estate_parser.search_criteria import SearchCriteria
from real_estate_parser.source_batch import PublicationRef


@dataclass(frozen=True, slots=True)
class PublicationRefDocument:
    """String representation of one canonical publication reference."""

    source_id: str
    publication_id: str


@dataclass(frozen=True, slots=True)
class ProvidedProvenanceDocument:
    """Document evidence for a source value that was provided."""

    input_path: str
    normalization_rule_version: str
    observed_at: str
    publication_id: str
    raw_value: str
    source_field: str
    source_id: str


@dataclass(frozen=True, slots=True)
class MissingProvenanceDocument:
    """Document evidence for an absent field, structurally without a raw value."""

    input_path: str
    normalization_rule_version: str
    observed_at: str
    publication_id: str
    source_field: str
    source_id: str


@dataclass(frozen=True, slots=True)
class TracedValueDocument[T]:
    """Mandatory canonical value with its provided-value evidence."""

    value: T
    provenance: ProvidedProvenanceDocument


@dataclass(frozen=True, slots=True)
class PresentDocument[T]:
    """Document form of a provided, valid and supported optional value."""

    state: Literal["present"]
    value: T
    provenance: ProvidedProvenanceDocument


@dataclass(frozen=True, slots=True)
class MissingDocument:
    """Document form of an absent optional value."""

    state: Literal["missing"]
    provenance: MissingProvenanceDocument


@dataclass(frozen=True, slots=True)
class UnsupportedDocument:
    """Document form of a provided value without a canonical representation."""

    state: Literal["unsupported"]
    reason_code: str
    provenance: ProvidedProvenanceDocument


type FieldOutcomeDocument[T] = PresentDocument[T] | MissingDocument | UnsupportedDocument


@dataclass(frozen=True, slots=True)
class MoneyDocument:
    """Canonical search-criteria money in minimal currency units."""

    amount_minor: int
    currency: str


@dataclass(frozen=True, slots=True)
class SearchCriteriaDocument:
    """Canonical document criteria; absent fields remain explicit only in Python."""

    maximum_price: MoneyDocument | None = None
    minimum_total_area: str | None = None
    allowed_rooms: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class SearchMatchDocument:
    """Exactly the eight semantic fields of one canonical result match."""

    currency: FieldOutcomeDocument[str]
    location_text: FieldOutcomeDocument[str]
    observed_at: TracedValueDocument[str]
    price_amount: FieldOutcomeDocument[int]
    publication_ref: TracedValueDocument[PublicationRefDocument]
    rooms: FieldOutcomeDocument[int]
    source_url: TracedValueDocument[str]
    total_area: FieldOutcomeDocument[str]


@dataclass(frozen=True, slots=True)
class SearchResultDocument:
    """Immutable structural representation of ``search-result@1``."""

    schema_version: Literal["search-result@1"]
    criteria: SearchCriteriaDocument
    matches: tuple[SearchMatchDocument, ...]


def _provided_provenance(
    provenance: ValueProvenance | UnsupportedProvenance,
) -> ProvidedProvenanceDocument:
    return ProvidedProvenanceDocument(
        input_path=provenance.input_path.json_path,
        normalization_rule_version=provenance.normalization_rule_version.value,
        observed_at=provenance.observed_at.to_rfc3339(),
        publication_id=provenance.publication_id.value,
        raw_value=provenance.raw_value,
        source_field=provenance.source_field,
        source_id=provenance.source_id.value,
    )


def _missing_provenance(provenance: MissingProvenance) -> MissingProvenanceDocument:
    return MissingProvenanceDocument(
        input_path=provenance.input_path.json_path,
        normalization_rule_version=provenance.normalization_rule_version.value,
        observed_at=provenance.observed_at.to_rfc3339(),
        publication_id=provenance.publication_id.value,
        source_field=provenance.source_field,
        source_id=provenance.source_id.value,
    )


def _traced_document[T, U](
    traced: TracedValue[T],
    value_mapper: Callable[[T], U],
) -> TracedValueDocument[U]:
    return TracedValueDocument(
        value=value_mapper(traced.value),
        provenance=_provided_provenance(traced.provenance),
    )


def _outcome_document[T, U](
    outcome: FieldOutcome[T],
    value_mapper: Callable[[T], U],
) -> FieldOutcomeDocument[U]:
    if isinstance(outcome, Present):
        return PresentDocument(
            state="present",
            value=value_mapper(outcome.value.value),
            provenance=_provided_provenance(outcome.value.provenance),
        )
    if isinstance(outcome, Missing):
        return MissingDocument(
            state="missing",
            provenance=_missing_provenance(outcome.provenance),
        )
    return UnsupportedDocument(
        state="unsupported",
        reason_code=outcome.provenance.reason_code,
        provenance=_provided_provenance(outcome.provenance),
    )


def _publication_ref_document(reference: PublicationRef) -> PublicationRefDocument:
    return PublicationRefDocument(
        source_id=reference.source_id.value,
        publication_id=reference.publication_id.value,
    )


def _source_url_document(value: SourceUrl) -> str:
    return value.value


def _observed_at_document(value: ObservedAt) -> str:
    return value.to_rfc3339()


def _location_text_document(value: LocationText) -> str:
    return value.value


def _money_amount_document(value: MoneyAmount) -> int:
    return value.value


def _currency_document(value: Currency) -> str:
    return value.value


def _area_document(value: Area) -> str:
    square_metres, hundredths = divmod(value.value, 100)
    return f"{square_metres}.{hundredths:02d}"


def _room_count_document(value: RoomCount) -> int:
    return value.value


def _criteria_document(criteria: SearchCriteria) -> SearchCriteriaDocument:
    maximum_price = criteria.maximum_price
    return SearchCriteriaDocument(
        maximum_price=(
            None
            if maximum_price is None
            else MoneyDocument(
                amount_minor=maximum_price.amount.value,
                currency=maximum_price.currency.value,
            )
        ),
        minimum_total_area=(
            None
            if criteria.minimum_total_area is None
            else _area_document(criteria.minimum_total_area)
        ),
        allowed_rooms=(
            None
            if criteria.allowed_rooms is None
            else tuple(sorted(room.value for room in criteria.allowed_rooms))
        ),
    )


def _match_document(match: SearchMatch) -> SearchMatchDocument:
    listing = match.listing
    return SearchMatchDocument(
        currency=_outcome_document(listing.currency, _currency_document),
        location_text=_outcome_document(listing.location_text, _location_text_document),
        observed_at=_traced_document(listing.observed_at, _observed_at_document),
        price_amount=_outcome_document(listing.price_amount, _money_amount_document),
        publication_ref=_traced_document(listing.reference, _publication_ref_document),
        rooms=_outcome_document(listing.rooms, _room_count_document),
        source_url=_traced_document(listing.source_url, _source_url_document),
        total_area=_outcome_document(listing.total_area, _area_document),
    )


def map_search_result(result: SearchResult) -> SearchResultDocument:
    """Map one ready canonical result without filtering or reordering its matches."""

    return SearchResultDocument(
        schema_version="search-result@1",
        criteria=_criteria_document(result.criteria),
        matches=tuple(_match_document(match) for match in result.matches),
    )


__all__ = [
    "FieldOutcomeDocument",
    "MissingDocument",
    "MissingProvenanceDocument",
    "MoneyDocument",
    "PresentDocument",
    "ProvidedProvenanceDocument",
    "PublicationRefDocument",
    "SearchCriteriaDocument",
    "SearchMatchDocument",
    "SearchResultDocument",
    "TracedValueDocument",
    "UnsupportedDocument",
    "map_search_result",
]
