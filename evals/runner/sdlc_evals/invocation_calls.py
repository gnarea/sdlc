"""The invocation's harness calls: one for each case at each level, for as long as the budget
allows.

On the subscription, the wrapper reads the weekly utilisation before each call and after the last,
and charges the invocation from those readings alone. Before each call, it writes a provisional
charge for the rest of the week's budget, which only the reading after the call replaces.
"""

import enum
import itertools
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from .code_check import Case
from .harness import CaseSelection, HarnessCall
from .harness_call import CallRecord
from .levels import EffortLevel
from .spend import (
    ApiKeyBudget,
    ApiKeyChoice,
    SubscriptionBudget,
    SubscriptionChoice,
    assess_subscription,
)
from .state.ledger import LedgerEntry, WeeklyUtilisation, load_entries, record_entry
from .state.store import StateStore


class StopReason(enum.StrEnum):
    WEEKLY_BUDGET = "this week's eval invocations reached their share of the weekly allowance"
    SPEND_CAP = "the spend cap was reached"
    READING_FAILED = "a reading of the weekly utilisation failed, so the spend can't be measured"
    NO_SPACE = "not enough free space in the temporary root"
    CALL_VOIDED = "the harness offered a tool the suite doesn't expect"
    INTERRUPTED = "the operator interrupted it"


@dataclass(frozen=True)
class CallPlan:
    """The harness calls that an invocation may make, and how it pays for them."""

    selection: CaseSelection
    levels: tuple[EffortLevel, ...]
    credential: SubscriptionChoice | ApiKeyChoice


@dataclass(frozen=True)
class CallsOutcome:
    """What the harness calls did, what they were charged, and why they stopped early, if they
    did.

    `spend` and `budget` are None when the first reading failed, since nothing was charged.
    """

    calls: tuple[CallRecord, ...]
    readings: tuple[WeeklyUtilisation, ...]
    spend: LedgerEntry | None
    budget: SubscriptionBudget | ApiKeyBudget | None
    stop_reason: StopReason | None


def run_calls(
    plan: CallPlan,
    store: StateStore,
    invocation_id: str,
    run_call: Callable[[HarnessCall], CallRecord],
    take_reading: Callable[[int], WeeklyUtilisation | None],
    has_room_for: Callable[[int], bool],
    now: Callable[[], datetime],
) -> CallsOutcome:
    """Make each harness call in turn, recording its spend in the ledger as soon as it's known.

    `take_reading` gets the number of readings taken so far, and returns None if it fails.
    `has_room_for` gets the number of runs that the next call makes.
    """
    if isinstance(plan.credential, ApiKeyChoice):
        entry = LedgerEntry.make_api_key(invocation_id, now())
        meter: _SubscriptionMeter | _ApiKeyMeter = _ApiKeyMeter(
            store, entry, plan.credential.cap_usd, now
        )
    else:
        opened = _SubscriptionMeter.open(store, invocation_id, take_reading, now)
        if isinstance(opened, StopReason):
            return CallsOutcome((), (), None, None, opened)
        meter = opened
    calls: list[CallRecord] = []
    stop_reason: StopReason | None = None
    # Each case runs at every level before the next, so that an invocation that stops early still
    # compares the levels on the cases it covered.
    for case, level in itertools.product(plan.selection.cases, plan.levels):
        runs = plan.selection.runs_of(case)
        record, stop_reason = _make_call(meter, case, level, runs, run_call, has_room_for)
        if record is not None:
            calls.append(record)
        if stop_reason is not None:
            break
    return CallsOutcome(tuple(calls), meter.readings, meter.entry, meter.assess(), stop_reason)


def _make_call(
    meter: _SubscriptionMeter | _ApiKeyMeter,
    case: Case,
    level: EffortLevel,
    runs: int,
    run_call: Callable[[HarnessCall], CallRecord],
    has_room_for: Callable[[int], bool],
) -> tuple[CallRecord | None, StopReason | None]:
    cap_usd = meter.assess().call_cap_usd()
    if cap_usd is None:
        return None, meter.spent_reason
    if not has_room_for(runs):
        return None, StopReason.NO_SPACE
    meter.charge_ahead()
    try:
        record = run_call(HarnessCall(case, level, runs, cap_usd))
    except KeyboardInterrupt:
        # Whatever the interrupted call spent is unknown, so it's taken to be all it was allowed.
        return None, meter.measure(cap_usd) or StopReason.INTERRUPTED
    return record, meter.measure(record.spend_usd) or _find_stop_reason(record)


def _find_stop_reason(record: CallRecord) -> StopReason | None:
    if record.is_voided:
        return StopReason.CALL_VOIDED
    if record.is_spend_capped:
        return StopReason.SPEND_CAP
    return None


class _SubscriptionMeter:
    """Charges the invocation by the wrapper's own readings, and holds the rest of the week's
    budget in the ledger whilst a call runs after the last one.
    """

    spent_reason = StopReason.WEEKLY_BUDGET

    def __init__(
        self,
        store: StateStore,
        entry: LedgerEntry,
        first_reading: WeeklyUtilisation,
        take_reading: Callable[[int], WeeklyUtilisation | None],
        now: Callable[[], datetime],
    ) -> None:
        self._store = store
        self._take_reading = take_reading
        self._now = now
        self._readings = [first_reading]
        self.entry = entry

    @classmethod
    def open(
        cls,
        store: StateStore,
        invocation_id: str,
        take_reading: Callable[[int], WeeklyUtilisation | None],
        now: Callable[[], datetime],
    ) -> _SubscriptionMeter | StopReason:
        """Take the first reading, which records nothing until a call is about to run."""
        try:
            reading = take_reading(0)
        except KeyboardInterrupt:
            return StopReason.INTERRUPTED
        if reading is None:
            return StopReason.READING_FAILED
        entry = LedgerEntry.make_subscription(invocation_id, reading, now())
        return cls(store, entry, reading, take_reading, now)

    @property
    def readings(self) -> tuple[WeeklyUtilisation, ...]:
        return tuple(self._readings)

    def assess(self) -> SubscriptionBudget:
        """Add the invocation's charge, as its latest reading measures it, to the others in the
        ledger.
        """
        now = self._now()
        others = tuple(
            entry
            for entry in load_entries(self._store, now)
            if entry.invocation_id != self.entry.invocation_id
        )
        return assess_subscription(others + (self.entry,), now)

    def charge_ahead(self) -> None:
        self.entry = replace(self.entry, is_provisional=True, recorded_at=self._now())
        record_entry(self._store, self.entry, self._now())

    def measure(self, list_price_usd: float) -> StopReason | None:
        """Record what the call spent, and replace its provisional charge with what the next
        reading measures, unless that reading fails.
        """
        self.entry = self.entry.add_spend(list_price_usd, self._now())
        stop_reason: StopReason | None = None
        try:
            reading = self._take_reading(len(self._readings))
        except KeyboardInterrupt:
            reading, stop_reason = None, StopReason.INTERRUPTED
        if reading is not None:
            self._readings.append(reading)
            self.entry = self.entry.add_reading(reading, self._now())
        record_entry(self._store, self.entry, self._now())
        if reading is None:
            return stop_reason or StopReason.READING_FAILED
        return None


class _ApiKeyMeter:
    """Charges the invocation at list price, against the cap that the operator gave it."""

    spent_reason = StopReason.SPEND_CAP
    readings: tuple[WeeklyUtilisation, ...] = ()

    def __init__(
        self, store: StateStore, entry: LedgerEntry, cap_usd: float, now: Callable[[], datetime]
    ) -> None:
        self._store = store
        self._cap_usd = cap_usd
        self._now = now
        self.entry = entry

    def assess(self) -> ApiKeyBudget:
        return ApiKeyBudget(cap_usd=self._cap_usd, spent_usd=self.entry.list_price_usd)

    def charge_ahead(self) -> None:
        """Charge nothing ahead, since the harness keeps the call within what remains of the
        cap.
        """

    def measure(self, list_price_usd: float) -> StopReason | None:
        self.entry = self.entry.add_spend(list_price_usd, self._now())
        record_entry(self._store, self.entry, self._now())
        return None
