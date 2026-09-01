"""Deterministic normalization of one neutral publication snapshot."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from real_estate_parser.source_batch import (
    ContractIssue,
    InputLocation,
    MissingField,
    PublicationId,
    PublicationRef,
    RawField,
    SourceId,
    SourcePublicationSnapshot,
)

_MAX_CANONICAL_INTEGER = 9_223_372_036_854_775_807
_MAX_CANONICAL_INTEGER_TEXT = str(_MAX_CANONICAL_INTEGER)
_RFC3339_PATTERN = re.compile(
    r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})"
    r"T(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-](?P<offset_hour>[0-9]{2}):(?P<offset_minute>[0-9]{2}))",
    flags=re.ASCII,
)
_PRICE_PATTERN = re.compile(
    r"(?P<negative>-?)(?P<whole>[0-9]+)(?:\.(?P<fraction>[0-9]{1,2}))?", re.ASCII
)
_AREA_PATTERN = re.compile(
    r"(?P<negative>-?)(?P<whole>[0-9]+)(?:\.(?P<fraction>[0-9]+))?", re.ASCII
)
_CURRENCY_PATTERN = re.compile(r"[A-Z]{3}", re.ASCII)
_ROOMS_PATTERN = re.compile(r"[0-9]+", re.ASCII)


@dataclass(frozen=True, slots=True)
class SourceUrl:
    """An already checked absolute HTTPS source URL, preserved verbatim."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 2048 or not self.value.isascii():
            raise ValueError("invalid source URL")
        if any(character.isspace() for character in self.value):
            raise ValueError("invalid source URL")
        try:
            parsed = urlsplit(self.value)
            _ = parsed.port
        except ValueError as error:
            raise ValueError("invalid source URL") from error
        if (
            parsed.scheme.lower() != "https"
            or not parsed.netloc
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ValueError("invalid source URL")


@dataclass(frozen=True, slots=True)
class ObservedAt:
    """A timezone-aware canonical UTC observation moment."""

    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is not UTC or self.value.utcoffset() is None:
            raise ValueError("observed_at must be canonical UTC")

    def to_rfc3339(self) -> str:
        """Render canonical RFC 3339 with six fractional digits and ``Z``."""

        return self.value.isoformat(timespec="microseconds").removesuffix("+00:00") + "Z"


@dataclass(frozen=True, slots=True)
class LocationText:
    """Whitespace-normalized source location text."""

    value: str

    def __post_init__(self) -> None:
        if not 1 <= len(self.value) <= 500 or self.value != " ".join(self.value.split()):
            raise ValueError("invalid normalized location text")


@dataclass(frozen=True, slots=True)
class MoneyAmount:
    """A positive whole number of the currency's minimal units."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 1 <= self.value <= _MAX_CANONICAL_INTEGER:
            raise ValueError("money amount is out of range")


@dataclass(frozen=True, slots=True)
class Currency:
    """A currency supported by the first normalization slice."""

    value: str

    def __post_init__(self) -> None:
        if self.value != "RUB":
            raise ValueError("unsupported canonical currency")


@dataclass(frozen=True, slots=True)
class Area:
    """A positive whole number of hundredths of a square metre."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 1 <= self.value <= _MAX_CANONICAL_INTEGER:
            raise ValueError("area is out of range")


@dataclass(frozen=True, slots=True)
class RoomCount:
    """A canonical room count where zero denotes an explicit studio."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 0 <= self.value <= 99:
            raise ValueError("room count is out of range")


@dataclass(frozen=True, slots=True)
class NormalizationRuleVersion:
    """A stable opaque identifier for one normalization rule revision."""

    value: str

    def __post_init__(self) -> None:
        if (
            not 1 <= len(self.value) <= 128
            or not self.value.isascii()
            or any(not 0x21 <= ord(character) <= 0x7E for character in self.value)
        ):
            raise ValueError("invalid normalization rule version")


@dataclass(frozen=True, slots=True)
class ValueProvenance:
    """Complete evidence for one provided canonical value."""

    source_id: SourceId
    publication_id: PublicationId
    input_path: InputLocation
    source_field: str
    raw_value: str
    observed_at: ObservedAt
    normalization_rule_version: NormalizationRuleVersion


@dataclass(frozen=True, slots=True)
class MissingProvenance:
    """Complete evidence for an absent optional source field."""

    source_id: SourceId
    publication_id: PublicationId
    input_path: InputLocation
    source_field: str
    observed_at: ObservedAt
    normalization_rule_version: NormalizationRuleVersion


@dataclass(frozen=True, slots=True)
class UnsupportedProvenance:
    """Complete evidence for a valid but unsupported source value."""

    source_id: SourceId
    publication_id: PublicationId
    input_path: InputLocation
    source_field: str
    raw_value: str
    observed_at: ObservedAt
    normalization_rule_version: NormalizationRuleVersion
    reason_code: str

    def __post_init__(self) -> None:
        if not self.reason_code or not self.reason_code.isascii():
            raise ValueError("invalid unsupported reason code")


@dataclass(frozen=True, slots=True)
class TracedValue[T]:
    """A canonical value inseparable from its source evidence."""

    value: T
    provenance: ValueProvenance


@dataclass(frozen=True, slots=True)
class Present[T]:
    """A provided, valid and supported optional field."""

    value: TracedValue[T]


@dataclass(frozen=True, slots=True)
class Missing:
    """An optional source field that was not provided."""

    provenance: MissingProvenance


@dataclass(frozen=True, slots=True)
class Unsupported:
    """A valid source value without a supported canonical representation."""

    provenance: UnsupportedProvenance


type FieldOutcome[T] = Present[T] | Missing | Unsupported


@dataclass(frozen=True, slots=True)
class NormalizedListing:
    """Canonical representation of one source publication snapshot."""

    reference: TracedValue[PublicationRef]
    source_url: TracedValue[SourceUrl]
    observed_at: TracedValue[ObservedAt]
    location_text: FieldOutcome[LocationText]
    price_amount: FieldOutcome[MoneyAmount]
    currency: FieldOutcome[Currency]
    total_area: FieldOutcome[Area]
    rooms: FieldOutcome[RoomCount]


@dataclass(frozen=True, slots=True)
class NormalizationSuccess:
    """Successful normalization of one complete snapshot."""

    listing: NormalizedListing


@dataclass(frozen=True, slots=True)
class NormalizationFailure:
    """Atomic normalization failure without a partial listing."""

    issues: tuple[ContractIssue, ...]

    def __post_init__(self) -> None:
        if not self.issues:
            raise ValueError("a failed normalization must contain an issue")


type NormalizationResult = NormalizationSuccess | NormalizationFailure


@dataclass(frozen=True, slots=True)
class FixtureNormalizationRules:
    """Immutable rule versions used by the fixture-source normalizer."""

    publication_id: NormalizationRuleVersion
    source_url: NormalizationRuleVersion
    observed_at: NormalizationRuleVersion
    location_text: NormalizationRuleVersion
    price_major: NormalizationRuleVersion
    currency: NormalizationRuleVersion
    total_area_sqm: NormalizationRuleVersion
    rooms: NormalizationRuleVersion


FIXTURE_NORMALIZATION_RULES_V1 = FixtureNormalizationRules(
    publication_id=NormalizationRuleVersion("fixture-publication-id@1"),
    source_url=NormalizationRuleVersion("fixture-source-url@1"),
    observed_at=NormalizationRuleVersion("fixture-observed-at@1"),
    location_text=NormalizationRuleVersion("fixture-location-text@1"),
    price_major=NormalizationRuleVersion("fixture-price-major@1"),
    currency=NormalizationRuleVersion("fixture-currency@1"),
    total_area_sqm=NormalizationRuleVersion("fixture-total-area-sqm@1"),
    rooms=NormalizationRuleVersion("fixture-rooms@1"),
)


def _issue(location: InputLocation, code: str) -> ContractIssue:
    return ContractIssue(category="NORMALIZATION", code=code, location=location)


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


def _parse_observed_at(field: RawField) -> tuple[ObservedAt | None, ContractIssue | None]:
    match = _RFC3339_PATTERN.fullmatch(field.value)
    if match is None:
        return None, _issue(field.location, "invalid_value")
    if (
        int(match.group("hour")) > 23
        or int(match.group("minute")) > 59
        or int(match.group("second")) > 59
        or (match.group("offset_hour") is not None and int(match.group("offset_hour")) > 23)
        or (match.group("offset_minute") is not None and int(match.group("offset_minute")) > 59)
    ):
        return None, _issue(field.location, "invalid_value")
    iso_value = (
        field.value.removesuffix("Z") + "+00:00" if field.value.endswith("Z") else field.value
    )
    try:
        parsed = datetime.fromisoformat(iso_value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None, _issue(field.location, "invalid_value")
        canonical = parsed.astimezone(UTC)
    except OverflowError, ValueError:
        return None, _issue(field.location, "invalid_value")
    return ObservedAt(canonical), None


def _parse_source_url(field: RawField) -> tuple[SourceUrl | None, ContractIssue | None]:
    try:
        return SourceUrl(field.value), None
    except ValueError:
        return None, _issue(field.location, "invalid_value")


def _scaled_integer(whole: str, fraction: str, *, negative: bool) -> int | None:
    digits = (whole + fraction[:2].ljust(2, "0")).lstrip("0") or "0"
    if negative or len(digits) > len(_MAX_CANONICAL_INTEGER_TEXT):
        return None
    if len(digits) == len(_MAX_CANONICAL_INTEGER_TEXT) and digits > _MAX_CANONICAL_INTEGER_TEXT:
        return None
    value = int(digits)
    return value if value >= 1 else None


def _parse_price(field: RawField) -> tuple[MoneyAmount | None, ContractIssue | None]:
    match = _PRICE_PATTERN.fullmatch(field.value)
    if match is None:
        return None, _issue(field.location, "invalid_value")
    value = _scaled_integer(
        match.group("whole"),
        match.group("fraction") or "",
        negative=bool(match.group("negative")),
    )
    if value is None:
        return None, _issue(field.location, "out_of_range")
    return MoneyAmount(value), None


def _parse_currency(
    field: RawField,
) -> tuple[Currency | None, bool, ContractIssue | None]:
    if _CURRENCY_PATTERN.fullmatch(field.value) is None:
        return None, False, _issue(field.location, "invalid_value")
    if field.value == "RUB":
        return Currency("RUB"), False, None
    return None, True, None


def _parse_area(field: RawField) -> tuple[Area | None, ContractIssue | None]:
    match = _AREA_PATTERN.fullmatch(field.value)
    if match is None:
        return None, _issue(field.location, "invalid_value")
    fraction = match.group("fraction") or ""
    if len(fraction) > 2 and any(digit != "0" for digit in fraction[2:]):
        return None, _issue(field.location, "precision_loss")
    value = _scaled_integer(
        match.group("whole"),
        fraction,
        negative=bool(match.group("negative")),
    )
    if value is None:
        return None, _issue(field.location, "out_of_range")
    return Area(value), None


def _parse_rooms(field: RawField) -> tuple[RoomCount | None, ContractIssue | None]:
    if field.value == "studio":
        return RoomCount(0), None
    if _ROOMS_PATTERN.fullmatch(field.value) is None:
        return None, _issue(field.location, "invalid_value")
    digits = field.value.lstrip("0") or "0"
    if len(digits) > 2 or int(digits) > 99:
        return None, _issue(field.location, "out_of_range")
    value = int(digits)
    if value == 0:
        return None, _issue(field.location, "invalid_value")
    return RoomCount(value), None


def _parse_location(field: RawField) -> tuple[LocationText | None, ContractIssue | None]:
    normalized = " ".join(field.value.split())
    try:
        return LocationText(normalized), None
    except ValueError:
        return None, _issue(field.location, "invalid_value")


def _value_provenance(
    snapshot: SourcePublicationSnapshot,
    *,
    location: InputLocation,
    source_field: str,
    raw_value: str,
    observed_at: ObservedAt,
    rule: NormalizationRuleVersion,
) -> ValueProvenance:
    return ValueProvenance(
        source_id=snapshot.reference.source_id,
        publication_id=snapshot.reference.publication_id,
        input_path=location,
        source_field=source_field,
        raw_value=raw_value,
        observed_at=observed_at,
        normalization_rule_version=rule,
    )


def _missing_provenance(
    snapshot: SourcePublicationSnapshot,
    *,
    field: MissingField,
    source_field: str,
    observed_at: ObservedAt,
    rule: NormalizationRuleVersion,
) -> MissingProvenance:
    return MissingProvenance(
        source_id=snapshot.reference.source_id,
        publication_id=snapshot.reference.publication_id,
        input_path=field.location,
        source_field=source_field,
        observed_at=observed_at,
        normalization_rule_version=rule,
    )


def _present[T](
    snapshot: SourcePublicationSnapshot,
    *,
    field: RawField,
    source_field: str,
    value: T,
    observed_at: ObservedAt,
    rule: NormalizationRuleVersion,
) -> Present[T]:
    return Present(
        value=TracedValue(
            value=value,
            provenance=_value_provenance(
                snapshot,
                location=field.location,
                source_field=source_field,
                raw_value=field.value,
                observed_at=observed_at,
                rule=rule,
            ),
        )
    )


def _missing(
    snapshot: SourcePublicationSnapshot,
    *,
    field: MissingField,
    source_field: str,
    observed_at: ObservedAt,
    rule: NormalizationRuleVersion,
) -> Missing:
    return Missing(
        provenance=_missing_provenance(
            snapshot,
            field=field,
            source_field=source_field,
            observed_at=observed_at,
            rule=rule,
        )
    )


def _unsupported(
    snapshot: SourcePublicationSnapshot,
    *,
    field: RawField,
    source_field: str,
    observed_at: ObservedAt,
    rule: NormalizationRuleVersion,
    reason_code: str,
) -> Unsupported:
    return Unsupported(
        provenance=UnsupportedProvenance(
            source_id=snapshot.reference.source_id,
            publication_id=snapshot.reference.publication_id,
            input_path=field.location,
            source_field=source_field,
            raw_value=field.value,
            observed_at=observed_at,
            normalization_rule_version=rule,
            reason_code=reason_code,
        )
    )


def _reference_location(snapshot: SourcePublicationSnapshot) -> InputLocation:
    return InputLocation(
        document=snapshot.input_location.document,
        record_index=snapshot.input_location.record_index,
        source_path=("publication_id",),
    )


def normalize_fixture_snapshot(
    snapshot: SourcePublicationSnapshot,
    rules: FixtureNormalizationRules = FIXTURE_NORMALIZATION_RULES_V1,
) -> NormalizationResult:
    """Normalize exactly one already adapted fixture-source snapshot."""

    issues: list[ContractIssue] = []

    observed_at, observed_issue = _parse_observed_at(snapshot.observed_at)
    if observed_issue is not None:
        issues.append(observed_issue)

    source_url, source_url_issue = _parse_source_url(snapshot.source_url)
    if source_url_issue is not None:
        issues.append(source_url_issue)

    location_value: LocationText | None = None
    if isinstance(snapshot.location_text, RawField):
        location_value, location_issue = _parse_location(snapshot.location_text)
        if location_issue is not None:
            issues.append(location_issue)

    price_value: MoneyAmount | None = None
    currency_value: Currency | None = None
    currency_unsupported = False
    price_missing = isinstance(snapshot.price_amount, MissingField)
    currency_missing = isinstance(snapshot.currency, MissingField)
    if price_missing != currency_missing:
        issues.append(_issue(snapshot.input_location, "incomplete_money"))
    elif not price_missing and not currency_missing:
        assert isinstance(snapshot.price_amount, RawField)
        assert isinstance(snapshot.currency, RawField)
        price_value, price_issue = _parse_price(snapshot.price_amount)
        if price_issue is not None:
            issues.append(price_issue)
        currency_value, currency_unsupported, currency_issue = _parse_currency(snapshot.currency)
        if currency_issue is not None:
            issues.append(currency_issue)

    area_value: Area | None = None
    if isinstance(snapshot.total_area, RawField):
        area_value, area_issue = _parse_area(snapshot.total_area)
        if area_issue is not None:
            issues.append(area_issue)

    rooms_value: RoomCount | None = None
    if isinstance(snapshot.rooms, RawField):
        rooms_value, rooms_issue = _parse_rooms(snapshot.rooms)
        if rooms_issue is not None:
            issues.append(rooms_issue)

    if issues:
        return NormalizationFailure(issues=tuple(sorted(issues, key=_issue_sort_key)))

    assert observed_at is not None
    assert source_url is not None

    reference = TracedValue(
        value=snapshot.reference,
        provenance=_value_provenance(
            snapshot,
            location=_reference_location(snapshot),
            source_field="publication_id",
            raw_value=snapshot.reference.publication_id.value,
            observed_at=observed_at,
            rule=rules.publication_id,
        ),
    )
    traced_source_url = TracedValue(
        value=source_url,
        provenance=_value_provenance(
            snapshot,
            location=snapshot.source_url.location,
            source_field="url",
            raw_value=snapshot.source_url.value,
            observed_at=observed_at,
            rule=rules.source_url,
        ),
    )
    traced_observed_at = TracedValue(
        value=observed_at,
        provenance=_value_provenance(
            snapshot,
            location=snapshot.observed_at.location,
            source_field="observed_at",
            raw_value=snapshot.observed_at.value,
            observed_at=observed_at,
            rule=rules.observed_at,
        ),
    )

    if isinstance(snapshot.location_text, MissingField):
        location_outcome: FieldOutcome[LocationText] = _missing(
            snapshot,
            field=snapshot.location_text,
            source_field="location_text",
            observed_at=observed_at,
            rule=rules.location_text,
        )
    else:
        assert location_value is not None
        location_outcome = _present(
            snapshot,
            field=snapshot.location_text,
            source_field="location_text",
            value=location_value,
            observed_at=observed_at,
            rule=rules.location_text,
        )

    if isinstance(snapshot.price_amount, MissingField):
        assert isinstance(snapshot.currency, MissingField)
        price_outcome: FieldOutcome[MoneyAmount] = _missing(
            snapshot,
            field=snapshot.price_amount,
            source_field="price_major",
            observed_at=observed_at,
            rule=rules.price_major,
        )
        currency_outcome: FieldOutcome[Currency] = _missing(
            snapshot,
            field=snapshot.currency,
            source_field="currency",
            observed_at=observed_at,
            rule=rules.currency,
        )
    else:
        assert isinstance(snapshot.currency, RawField)
        assert price_value is not None
        price_outcome = _present(
            snapshot,
            field=snapshot.price_amount,
            source_field="price_major",
            value=price_value,
            observed_at=observed_at,
            rule=rules.price_major,
        )
        if currency_unsupported:
            currency_outcome = _unsupported(
                snapshot,
                field=snapshot.currency,
                source_field="currency",
                observed_at=observed_at,
                rule=rules.currency,
                reason_code="unsupported_currency",
            )
        else:
            assert currency_value is not None
            currency_outcome = _present(
                snapshot,
                field=snapshot.currency,
                source_field="currency",
                value=currency_value,
                observed_at=observed_at,
                rule=rules.currency,
            )

    if isinstance(snapshot.total_area, MissingField):
        area_outcome: FieldOutcome[Area] = _missing(
            snapshot,
            field=snapshot.total_area,
            source_field="total_area_sqm",
            observed_at=observed_at,
            rule=rules.total_area_sqm,
        )
    else:
        assert area_value is not None
        area_outcome = _present(
            snapshot,
            field=snapshot.total_area,
            source_field="total_area_sqm",
            value=area_value,
            observed_at=observed_at,
            rule=rules.total_area_sqm,
        )

    if isinstance(snapshot.rooms, MissingField):
        rooms_outcome: FieldOutcome[RoomCount] = _missing(
            snapshot,
            field=snapshot.rooms,
            source_field="rooms",
            observed_at=observed_at,
            rule=rules.rooms,
        )
    else:
        assert rooms_value is not None
        rooms_outcome = _present(
            snapshot,
            field=snapshot.rooms,
            source_field="rooms",
            value=rooms_value,
            observed_at=observed_at,
            rule=rules.rooms,
        )

    return NormalizationSuccess(
        listing=NormalizedListing(
            reference=reference,
            source_url=traced_source_url,
            observed_at=traced_observed_at,
            location_text=location_outcome,
            price_amount=price_outcome,
            currency=currency_outcome,
            total_area=area_outcome,
            rooms=rooms_outcome,
        )
    )


__all__ = [
    "Area",
    "Currency",
    "FIXTURE_NORMALIZATION_RULES_V1",
    "FieldOutcome",
    "FixtureNormalizationRules",
    "LocationText",
    "Missing",
    "MissingProvenance",
    "MoneyAmount",
    "NormalizationFailure",
    "NormalizationResult",
    "NormalizationRuleVersion",
    "NormalizationSuccess",
    "NormalizedListing",
    "ObservedAt",
    "Present",
    "RoomCount",
    "SourceUrl",
    "TracedValue",
    "Unsupported",
    "UnsupportedProvenance",
    "ValueProvenance",
    "normalize_fixture_snapshot",
]
