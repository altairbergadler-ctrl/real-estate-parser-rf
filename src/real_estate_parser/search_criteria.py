"""Neutral canonical search criteria and their atomic boundary result."""

from __future__ import annotations

from dataclasses import dataclass

from real_estate_parser.normalization import Area, Currency, MoneyAmount, RoomCount
from real_estate_parser.source_batch import ContractIssue


@dataclass(frozen=True, slots=True)
class Money:
    """An exact amount in one supported canonical currency."""

    amount: MoneyAmount
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.amount, MoneyAmount) or not isinstance(self.currency, Currency):
            raise TypeError("money requires canonical amount and currency values")


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    """The immutable conjunction of the optional standard search limits."""

    maximum_price: Money | None = None
    minimum_total_area: Area | None = None
    allowed_rooms: frozenset[RoomCount] | None = None

    def __post_init__(self) -> None:
        if self.maximum_price is not None and not isinstance(self.maximum_price, Money):
            raise TypeError("maximum price must be canonical money")
        if self.minimum_total_area is not None and not isinstance(self.minimum_total_area, Area):
            raise TypeError("minimum total area must be canonical area")
        if self.allowed_rooms is not None:
            if type(self.allowed_rooms) is not frozenset:
                raise TypeError("allowed rooms must be an immutable set")
            if not self.allowed_rooms:
                raise ValueError("allowed rooms must not be empty")
            if any(not isinstance(room, RoomCount) for room in self.allowed_rooms):
                raise TypeError("allowed rooms must contain canonical room counts")


@dataclass(frozen=True, slots=True)
class SearchCriteriaLoadSuccess:
    """Successful and complete criteria boundary result."""

    criteria: SearchCriteria


@dataclass(frozen=True, slots=True)
class SearchCriteriaLoadFailure:
    """Atomic criteria boundary failure without partial criteria."""

    issues: tuple[ContractIssue, ...]

    def __post_init__(self) -> None:
        if not self.issues:
            raise ValueError("a failed search criteria load must contain an issue")


type SearchCriteriaLoadResult = SearchCriteriaLoadSuccess | SearchCriteriaLoadFailure


__all__ = [
    "Money",
    "SearchCriteria",
    "SearchCriteriaLoadFailure",
    "SearchCriteriaLoadResult",
    "SearchCriteriaLoadSuccess",
]
