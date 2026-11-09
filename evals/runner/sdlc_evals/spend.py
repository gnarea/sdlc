"""The budget: whether the next harness call may start, and the most it may spend, decided before
it's spent.

Wherever a reading is uncertain, spend is attributed in the direction that stops the suite earlier.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from .credentials import CredentialSource
from .state.ledger import LedgerEntry

# All eval invocations together may raise the subscription's weekly utilisation by this many
# percentage points.
WEEKLY_BUDGET_POINTS = 10.0
# Each reading may be rounded to a whole point, so the rise between two of them may be short by up
# to one.
ROUNDING_POINTS = 1.0
# A harness call runs one case at one level, at most three times, and the pilots' runs cost about
# $0.20 each at list price, so this bounds a call that goes wrong with room to spare.
SUBSCRIPTION_CALL_CAP_USD = 5.0
# The harness takes its cap in whole cents.
MIN_CALL_CAP_USD = 0.01
_POINTS_PER_FRACTION = 100.0
# Readings are decimal fractions, which binary floating point would otherwise put a hair either
# side of a whole point.
_POINT_DECIMALS = 6


@dataclass(frozen=True)
class SubscriptionChoice:
    """Spend from the subscription, within this week's share of its allowance."""

    source: ClassVar[CredentialSource] = CredentialSource.SUBSCRIPTION


@dataclass(frozen=True)
class ApiKeyChoice:
    """Spend from an API key, within a cap that the operator gives, since it has no default."""

    source: ClassVar[CredentialSource] = CredentialSource.API_KEY
    cap_usd: float

    def __post_init__(self) -> None:
        if not 0 < self.cap_usd:
            raise ValueError(
                f"The API key's cap must be a positive number of dollars (got {self.cap_usd})"
            )


@dataclass(frozen=True)
class SubscriptionBudget:
    """This week's charges for every eval invocation, and the invocations whose provisional charge
    holds the rest of the budget.
    """

    spent_points: float
    provisional_invocations: tuple[str, ...]

    def call_cap_usd(self) -> float | None:
        """The next harness call's cap, or None if no call may start."""
        if self.provisional_invocations or WEEKLY_BUDGET_POINTS <= self.spent_points:
            return None
        return SUBSCRIPTION_CALL_CAP_USD


@dataclass(frozen=True)
class ApiKeyBudget:
    """The invocation's spend against the cap that the operator gave it."""

    cap_usd: float
    spent_usd: float

    def call_cap_usd(self) -> float | None:
        """What remains of the cap, all of which the next harness call may spend, or None if too
        little remains for a call to start.
        """
        remaining_usd = self.cap_usd - self.spent_usd
        return remaining_usd if MIN_CALL_CAP_USD <= remaining_usd else None


def assess_subscription(entries: tuple[LedgerEntry, ...], now: datetime) -> SubscriptionBudget:
    """Add up the subscription's charges in the weeks that haven't reset, setting apart the
    provisional ones.
    """
    subscription = [
        entry for entry in entries if entry.credential_source is CredentialSource.SUBSCRIPTION
    ]
    spent_points = sum(
        charge_points(entry, now) for entry in subscription if not entry.is_provisional
    )
    return SubscriptionBudget(
        spent_points=round(spent_points, _POINT_DECIMALS),
        provisional_invocations=tuple(
            entry.invocation_id for entry in subscription if entry.is_provisional
        ),
    )


def charge_points(entry: LedgerEntry, now: datetime) -> float:
    """What the invocation's readings measured in the weeks that haven't reset."""
    return sum(
        week_charge_points(entry, index)
        for index, week in enumerate(entry.weeks)
        if now < week.resets_at
    )


def week_charge_points(entry: LedgerEntry, week_index: int) -> float:
    """The invocation's charge for one week: how far its readings rose, plus a point for rounding.

    A week that began during the invocation rose from zero, since utilisation restarts at the
    reset.
    """
    week = entry.weeks[week_index]
    start_fraction = week.first_fraction if week_index == 0 else 0.0
    rise_points = max(0.0, week.last_fraction - start_fraction) * _POINTS_PER_FRACTION
    return round(rise_points, _POINT_DECIMALS) + ROUNDING_POINTS
