"""The spend ledger: an entry for each invocation, kept until the last week it touched resets, or,
for a provisional charge, until the owner clears it.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import TextIO

from ..controlling_terminal import ask_in_person
from ..credentials import CredentialSource
from .store import StateStore, StateStoreUnusable

LEDGER_FILE_NAME = "ledger.json"
LEDGER_FORMAT_VERSION = 2
# Format 1 held an entry for each level of an invocation, with the first and last readings that
# the runs' traces carried.
PER_LEVEL_FORMAT_VERSION = 1
# A format 1 invocation without a reading of when its week resets counts for a whole week after
# it was recorded, which covers whichever week it fell in.
UNKNOWN_WEEK_LENGTH = timedelta(days=7)


@dataclass(frozen=True)
class WeeklyUtilisation:
    """The share of the subscription's weekly allowance in use, as the model API reported it."""

    fraction: float
    resets_at: datetime


@dataclass(frozen=True)
class WeekReadings:
    """An invocation's first and last readings in the week that resets at `resets_at`."""

    resets_at: datetime
    first_fraction: float
    last_fraction: float


@dataclass(frozen=True)
class LedgerEntry:
    """What an invocation spent: at list price and, on the subscription, by its readings in each
    week that they touched, in the order it touched them.

    A provisional charge holds the rest of the week's budget whilst a harness call runs after the
    invocation's last reading.
    """

    invocation_id: str
    credential_source: CredentialSource
    list_price_usd: float
    recorded_at: datetime
    weeks: tuple[WeekReadings, ...]
    is_provisional: bool

    def __post_init__(self) -> None:
        is_subscription = self.credential_source is CredentialSource.SUBSCRIPTION
        if is_subscription != bool(self.weeks):
            raise ValueError("An entry has readings if, and only if, it's for the subscription")
        if self.is_provisional and not is_subscription:
            raise ValueError("Only an entry for the subscription can hold a provisional charge")
        if len({week.resets_at for week in self.weeks}) != len(self.weeks):
            raise ValueError("An entry must hold each week once")
        numbers = [self.list_price_usd]
        for week in self.weeks:
            numbers += [week.first_fraction, week.last_fraction]
        if not all(math.isfinite(number) and 0 <= number for number in numbers):
            raise ValueError(f"Spend and readings must be finite and non-negative (got {numbers})")

    @classmethod
    def make_subscription(
        cls, invocation_id: str, reading: WeeklyUtilisation, now: datetime
    ) -> LedgerEntry:
        """Start an entry for the subscription from the invocation's first reading."""
        week = WeekReadings(reading.resets_at, reading.fraction, reading.fraction)
        return cls(invocation_id, CredentialSource.SUBSCRIPTION, 0.0, now, (week,), False)

    @classmethod
    def make_api_key(cls, invocation_id: str, now: datetime) -> LedgerEntry:
        return cls(invocation_id, CredentialSource.API_KEY, 0.0, now, (), False)

    def add_spend(self, list_price_usd: float, now: datetime) -> LedgerEntry:
        return replace(self, list_price_usd=self.list_price_usd + list_price_usd, recorded_at=now)

    def add_reading(self, reading: WeeklyUtilisation, now: datetime) -> LedgerEntry:
        """Add a reading, which measures the charge, so that the entry is no longer provisional."""
        weeks = list(self.weeks)
        index = next(
            (index for index, week in enumerate(weeks) if week.resets_at == reading.resets_at),
            None,
        )
        if index is None:
            weeks.append(WeekReadings(reading.resets_at, reading.fraction, reading.fraction))
        else:
            weeks[index] = replace(weeks[index], last_fraction=reading.fraction)
        return replace(self, recorded_at=now, weeks=tuple(weeks), is_provisional=False)

    def is_current(self, now: datetime) -> bool:
        """Whether the entry still counts: until the last week it touched resets, or for a
        provisional charge, which a call can carry across the reset, until the owner clears it.
        """
        if self.is_provisional:
            return True
        if self.weeks:
            return now < max(week.resets_at for week in self.weeks)
        return now < self.recorded_at + UNKNOWN_WEEK_LENGTH


def load_entries(store: StateStore, now: datetime) -> tuple[LedgerEntry, ...]:
    """Return the entries that still count, deleting the others."""
    document = store.read(LEDGER_FILE_NAME, LEDGER_FORMAT_VERSION, PER_LEVEL_FORMAT_VERSION)
    if document is None:
        return ()
    raw_entries = document.get("entries")
    if not isinstance(raw_entries, list):
        raise StateStoreUnusable(f"{LEDGER_FILE_NAME} must hold a list of entries")
    is_per_level = document["format_version"] == PER_LEVEL_FORMAT_VERSION
    if is_per_level:
        entries = _fold_per_level_entries(raw_entries)
    else:
        entries = tuple(_decode_entry(raw) for raw in raw_entries)
    if len({entry.invocation_id for entry in entries}) != len(entries):
        raise StateStoreUnusable(f"{LEDGER_FILE_NAME} holds two entries for one invocation")
    current = tuple(entry for entry in entries if entry.is_current(now))
    if is_per_level or current != entries:
        _write_entries(store, current)
    return current


def record_entry(store: StateStore, entry: LedgerEntry, now: datetime) -> None:
    """Record the invocation's entry in place of any earlier one, so that recording it again
    changes nothing.
    """
    others = tuple(
        other for other in load_entries(store, now) if other.invocation_id != entry.invocation_id
    )
    _write_entries(store, others + (entry,))


def find_provisional_charges(store: StateStore, now: datetime) -> tuple[LedgerEntry, ...]:
    return tuple(entry for entry in load_entries(store, now) if entry.is_provisional)


def clear_provisional_charge(
    store: StateStore, charge: LedgerEntry, now: datetime, open_terminal: Callable[[], TextIO]
) -> bool:
    """Ask the owner in person whether to clear the provisional charge and, if they confirm, leave
    the invocation charged what its readings measured before the call that was running.

    Returns whether the charge was cleared.
    """
    readings = ", ".join(
        f"{week.first_fraction:.0%} → {week.last_fraction:.0%} in the week resetting "
        f"{week.resets_at:%Y-%m-%d %H:%M %Z}"
        for week in charge.weeks
    )
    explanation = (
        f"Invocation {charge.invocation_id} left a provisional charge at "
        f"{charge.recorded_at:%Y-%m-%d %H:%M %Z}, which holds the rest of the subscription's "
        "weekly budget for the evals, because a harness call ran after its last reading of the "
        "weekly utilisation.\n"
        f"Its readings before that call measured {readings}. Clearing the charge leaves it "
        "charged for those alone, so whatever the call spent goes uncharged.\n"
        "Check your subscription's usage first, and keep the charge if the usage has risen more "
        "than the evals should have made it."
    )
    if not ask_in_person(explanation, "clear the charge", open_terminal):
        return False
    record_entry(store, replace(charge, is_provisional=False), now)
    return True


def _write_entries(store: StateStore, entries: tuple[LedgerEntry, ...]) -> None:
    store.write(
        LEDGER_FILE_NAME,
        LEDGER_FORMAT_VERSION,
        {"entries": [_encode_entry(entry) for entry in entries]},
    )


def _encode_entry(entry: LedgerEntry) -> dict[str, object]:
    return {
        "invocation_id": entry.invocation_id,
        "credential_source": entry.credential_source.value,
        "list_price_usd": entry.list_price_usd,
        "recorded_at": entry.recorded_at.isoformat(),
        "weeks": [
            {
                "resets_at": week.resets_at.isoformat(),
                "first_fraction": week.first_fraction,
                "last_fraction": week.last_fraction,
            }
            for week in entry.weeks
        ],
        "is_provisional": entry.is_provisional,
    }


def _decode_entry(raw: object) -> LedgerEntry:
    try:
        raw = _require_mapping(raw)
        is_provisional = raw["is_provisional"]
        if not isinstance(is_provisional, bool):
            raise TypeError(f"Expected a boolean (got {type(is_provisional).__name__})")
        return LedgerEntry(
            invocation_id=_decode_string(raw["invocation_id"]),
            credential_source=CredentialSource(raw["credential_source"]),
            list_price_usd=_decode_number(raw["list_price_usd"]),
            recorded_at=_decode_time(raw["recorded_at"]),
            weeks=tuple(_decode_week(week) for week in _require_list(raw["weeks"])),
            is_provisional=is_provisional,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StateStoreUnusable(f"{LEDGER_FILE_NAME} holds a malformed entry") from error


def _decode_week(raw: object) -> WeekReadings:
    raw = _require_mapping(raw)
    return WeekReadings(
        resets_at=_decode_time(raw["resets_at"]),
        first_fraction=_decode_number(raw["first_fraction"]),
        last_fraction=_decode_number(raw["last_fraction"]),
    )


@dataclass(frozen=True)
class _LevelEntry:
    """A format 1 entry, for one level of an invocation."""

    invocation_id: str
    credential_source: CredentialSource
    list_price_usd: float
    recorded_at: datetime
    readings: tuple[WeeklyUtilisation, ...]


def _fold_per_level_entries(raw_entries: list[object]) -> tuple[LedgerEntry, ...]:
    levels_by_invocation: dict[str, list[_LevelEntry]] = {}
    for raw in raw_entries:
        level = _decode_level_entry(raw)
        levels_by_invocation.setdefault(level.invocation_id, []).append(level)
    entries = (_fold_levels(levels) for levels in levels_by_invocation.values())
    return tuple(entry for entry in entries if entry is not None)


def _fold_levels(levels: list[_LevelEntry]) -> LedgerEntry | None:
    """Charge a format 1 invocation as format 2 would from the readings it has, or, if it spent
    without a reading, the point for rounding alone, over the week after it was recorded.

    Returns None for an invocation that spent nothing and has no reading, which has nothing to
    charge.
    """
    if len({level.credential_source for level in levels}) != 1:
        raise StateStoreUnusable(f"{LEDGER_FILE_NAME} holds an invocation with two credentials")
    invocation_id = levels[0].invocation_id
    list_price_usd = sum(level.list_price_usd for level in levels)
    recorded_at = max(level.recorded_at for level in levels)
    if levels[0].credential_source is CredentialSource.API_KEY:
        return LedgerEntry.make_api_key(invocation_id, recorded_at).add_spend(
            list_price_usd, recorded_at
        )
    readings = [reading for level in levels for reading in level.readings]
    if not readings and not list_price_usd:
        return None
    if not readings:
        readings = [WeeklyUtilisation(0.0, recorded_at + UNKNOWN_WEEK_LENGTH)]
    entry = LedgerEntry.make_subscription(invocation_id, readings[0], recorded_at)
    for reading in readings[1:]:
        entry = entry.add_reading(reading, recorded_at)
    return entry.add_spend(list_price_usd, recorded_at)


def _decode_level_entry(raw: object) -> _LevelEntry:
    try:
        raw = _require_mapping(raw)
        readings = (
            _decode_utilisation(raw["utilisation_before"]),
            _decode_utilisation(raw["utilisation_after"]),
        )
        return _LevelEntry(
            invocation_id=_decode_string(raw["invocation_id"]),
            credential_source=CredentialSource(raw["credential_source"]),
            list_price_usd=_decode_number(raw["list_price_usd"]),
            recorded_at=_decode_time(raw["recorded_at"]),
            readings=tuple(reading for reading in readings if reading is not None),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StateStoreUnusable(f"{LEDGER_FILE_NAME} holds a malformed entry") from error


def _decode_utilisation(raw: object) -> WeeklyUtilisation | None:
    if raw is None:
        return None
    raw = _require_mapping(raw)
    return WeeklyUtilisation(
        fraction=_decode_number(raw["fraction"]), resets_at=_decode_time(raw["resets_at"])
    )


def _require_mapping(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise TypeError(f"Expected a JSON object (got {type(raw).__name__})")
    return raw


def _require_list(raw: object) -> list[object]:
    if not isinstance(raw, list):
        raise TypeError(f"Expected a JSON array (got {type(raw).__name__})")
    return raw


def _decode_string(raw: object) -> str:
    if not isinstance(raw, str) or not raw:
        raise TypeError(f"Expected a non-empty string (got {type(raw).__name__})")
    return raw


def _decode_number(raw: object) -> float:
    # JSON parsing in Python accepts NaN and Infinity, either of which would defeat the budget's
    # comparisons.
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
        raise ValueError(f"Expected a finite number (got {raw!r})")
    if raw < 0:
        raise ValueError(f"Expected a non-negative number (got {raw!r})")
    return float(raw)


def _decode_time(raw: object) -> datetime:
    time = datetime.fromisoformat(str(raw))
    if time.tzinfo is None:
        raise ValueError("Times must have a time zone")
    return time
