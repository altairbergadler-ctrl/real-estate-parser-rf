"""Pure deterministic standard search over a normalized collection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from real_estate_parser.collection import CollectionSnapshot
from real_estate_parser.normalization import Missing, NormalizedListing, Present, Unsupported
from real_estate_parser.search_criteria import SearchCriteria


@dataclass(frozen=True, slots=True)
class SearchMatch:
    """A reference to one normalized listing that satisfied the criteria."""

    listing: NormalizedListing


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A successful search result, including an empty match sequence."""

    criteria: SearchCriteria
    matches: tuple[SearchMatch, ...]


def _matches(listing: NormalizedListing, criteria: SearchCriteria) -> bool:
    maximum_price = criteria.maximum_price
    if maximum_price is not None:
        if not isinstance(listing.price_amount, Present) or not isinstance(
            listing.currency, Present
        ):
            return False
        if listing.currency.value.value != maximum_price.currency:
            return False
        if listing.price_amount.value.value.value > maximum_price.amount.value:
            return False

    minimum_total_area = criteria.minimum_total_area
    if minimum_total_area is not None:
        if not isinstance(listing.total_area, Present):
            return False
        if listing.total_area.value.value.value < minimum_total_area.value:
            return False

    allowed_rooms = criteria.allowed_rooms
    if allowed_rooms is not None:
        if not isinstance(listing.rooms, Present):
            return False
        if listing.rooms.value.value not in allowed_rooms:
            return False

    return True


def _money_sort_key(listing: NormalizedListing) -> tuple[int, bytes, int]:
    price = listing.price_amount
    currency = listing.currency
    if isinstance(price, Unsupported) or isinstance(currency, Unsupported):
        return 2, b"", 0
    if isinstance(price, Present) and isinstance(currency, Present):
        return 0, currency.value.value.value.encode("ascii"), price.value.value.value
    if isinstance(price, Missing) and isinstance(currency, Missing):
        return 1, b"", 0
    raise ValueError("inconsistent normalized money pair")


def _listing_sort_key(
    listing: NormalizedListing,
) -> tuple[int, bytes, int, bytes, bytes, datetime, bytes]:
    money_state, currency, amount = _money_sort_key(listing)
    reference = listing.reference.value
    return (
        money_state,
        currency,
        amount,
        reference.source_id.value.encode("ascii"),
        reference.publication_id.value.encode("ascii"),
        listing.observed_at.value.value,
        listing.source_url.value.value.encode("ascii"),
    )


def search_collection(
    collection: CollectionSnapshot,
    criteria: SearchCriteria,
) -> SearchResult:
    """Apply all criteria and return matches in the canonical deterministic order."""

    matching_listings = (listing for listing in collection.listings if _matches(listing, criteria))
    ordered_listings = sorted(matching_listings, key=_listing_sort_key)
    return SearchResult(
        criteria=criteria,
        matches=tuple(SearchMatch(listing=listing) for listing in ordered_listings),
    )


__all__ = ["SearchMatch", "SearchResult", "search_collection"]
