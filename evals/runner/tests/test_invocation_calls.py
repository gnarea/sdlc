import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sdlc_evals.code_check import Case
from sdlc_evals.credentials import CredentialSource
from sdlc_evals.harness import CaseSelection, HarnessCall
from sdlc_evals.harness_call import CallRecord
from sdlc_evals.invocation_calls import CallPlan, CallsOutcome, StopReason, run_calls
from sdlc_evals.levels import EffortLevel
from sdlc_evals.spend import ApiKeyBudget, ApiKeyChoice, SubscriptionBudget, SubscriptionChoice
from sdlc_evals.state.ledger import (
    LedgerEntry,
    WeeklyUtilisation,
    WeekReadings,
    load_entries,
    record_entry,
)
from sdlc_evals.state.store import StateStore

from .call_records import make_call_record

NOW = datetime(2026, 11, 9, 12, tzinfo=UTC)
RESET = datetime(2026, 11, 13, 12, tzinfo=UTC)
NEXT_RESET = RESET + timedelta(days=7)
CALL_SPEND_USD = 0.25
REVIEW = Case("programmer/review", "programmer", 3, frozenset({"Read"}), timedelta(seconds=900))
DOMAIN = Case("architect/domain", "architect", 2, frozenset({"Read"}), timedelta(seconds=300))
SELECTION = CaseSelection((REVIEW, DOMAIN), ("programmer", "architect"), None, None)
LEVELS = (EffortLevel.LOW, EffortLevel.HIGH)
SUBSCRIPTION_PLAN = CallPlan(SELECTION, LEVELS, SubscriptionChoice())


class _Subscription:
    """The subscription as the harness calls and the readings find it: each call raises the
    utilisation as scripted, and each reading reports it unless scripted to fail.

    It also stands in for the harness, recording each call, and the ledger as each call found it.
    """

    def __init__(
        self,
        store: StateStore,
        rises: tuple[float, ...] = (),
        failed_readings: frozenset[int] = frozenset(),
        interrupted_readings: frozenset[int] = frozenset(),
        interrupted_calls: frozenset[int] = frozenset(),
        reset_after_call: int | None = None,
        records: dict[int, dict[str, object]] | None = None,
    ) -> None:
        self._store = store
        self._rises = rises
        self._failed_readings = failed_readings
        self._interrupted_readings = interrupted_readings
        self._interrupted_calls = interrupted_calls
        self._reset_after_call = reset_after_call
        self._records = records or {}
        self.fraction = 0.29
        self.resets_at = RESET
        self.now = NOW
        self.calls: list[HarnessCall] = []
        self.ledgers_during_calls: list[tuple[LedgerEntry, ...]] = []
        self.readings_asked: list[int] = []

    def run_call(self, call: HarnessCall) -> CallRecord:
        index = len(self.calls)
        self.calls.append(call)
        self.ledgers_during_calls.append(load_entries(self._store, self.now))
        self.fraction = round(self.fraction + self._rises[index], 2)
        if index == self._reset_after_call:
            self.fraction, self.resets_at, self.now = 0.01, NEXT_RESET, RESET
        if index in self._interrupted_calls:
            raise KeyboardInterrupt
        return make_call_record(call, CALL_SPEND_USD, **self._records.get(index, {}))

    def take_reading(self, index: int) -> WeeklyUtilisation | None:
        self.readings_asked.append(index)
        if index in self._interrupted_readings:
            raise KeyboardInterrupt
        if index in self._failed_readings:
            return None
        return WeeklyUtilisation(self.fraction, self.resets_at)


class RunCallsTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = StateStore.init(Path(temporary.name))

    def _run(
        self,
        subscription: _Subscription,
        plan: CallPlan = SUBSCRIPTION_PLAN,
        has_room_for: dict[int, bool] | None = None,
    ) -> CallsOutcome:
        return run_calls(
            plan,
            self.store,
            "this",
            run_call=subscription.run_call,
            take_reading=subscription.take_reading,
            has_room_for=lambda runs: (has_room_for or {}).get(runs, True),
            now=lambda: subscription.now,
        )

    def _own_entry(self, subscription: _Subscription) -> LedgerEntry | None:
        entries = load_entries(self.store, subscription.now)
        return next((entry for entry in entries if entry.invocation_id == "this"), None)

    def test_runs_each_case_at_every_level_before_the_next_with_a_reading_around_each(
        self,
    ) -> None:
        subscription = _Subscription(self.store, rises=(0.01, 0.0, 0.02, 0.0))

        outcome = self._run(subscription)

        self.assertEqual(
            [(call.case, call.level, call.runs, call.cap_usd) for call in subscription.calls],
            [
                (REVIEW, EffortLevel.LOW, 3, 5.0),
                (REVIEW, EffortLevel.HIGH, 3, 5.0),
                (DOMAIN, EffortLevel.LOW, 2, 5.0),
                (DOMAIN, EffortLevel.HIGH, 2, 5.0),
            ],
        )
        self.assertEqual(subscription.readings_asked, [0, 1, 2, 3, 4])
        self.assertEqual(
            [reading.fraction for reading in outcome.readings], [0.29, 0.30, 0.30, 0.32, 0.32]
        )
        self.assertEqual(
            [(call.case, call.level) for call in outcome.calls],
            [(call.case.name, call.level) for call in subscription.calls],
        )
        measured = LedgerEntry(
            "this",
            CredentialSource.SUBSCRIPTION,
            4 * CALL_SPEND_USD,
            NOW,
            (WeekReadings(RESET, 0.29, 0.32),),
            False,
        )
        self.assertEqual((outcome.spend, self._own_entry(subscription)), (measured, measured))
        self.assertEqual(outcome.budget, SubscriptionBudget(4.0, ()))
        self.assertIsNone(outcome.stop_reason)

    def test_holds_the_rest_of_the_budget_with_a_provisional_charge_during_each_call(
        self,
    ) -> None:
        subscription = _Subscription(self.store, rises=(0.01, 0.0, 0.0, 0.0))

        self._run(subscription)

        held = [
            [(entry.invocation_id, entry.is_provisional) for entry in ledger]
            for ledger in subscription.ledgers_during_calls
        ]
        self.assertEqual(held, [[("this", True)]] * 4)
        self.assertEqual(
            subscription.ledgers_during_calls[1][0].weeks, (WeekReadings(RESET, 0.29, 0.30),)
        )

    def test_charges_a_week_that_began_during_the_invocation_from_zero(self) -> None:
        subscription = _Subscription(self.store, rises=(0.02, 0.0, 0.0, 0.0), reset_after_call=1)

        outcome = self._run(subscription)

        self.assertEqual(
            outcome.spend.weeks,  # type: ignore[union-attr]
            (WeekReadings(RESET, 0.29, 0.31), WeekReadings(NEXT_RESET, 0.01, 0.01)),
        )
        self.assertEqual(outcome.budget, SubscriptionBudget(2.0, ()))

    def test_stops_before_a_call_once_the_weeks_charges_reach_the_budget(self) -> None:
        cases = [
            ("others 8 points, so the second call starts at 10", 0.36, 1),
            ("others 9 points, so the first call starts at 10", 0.37, 0),
        ]
        for label, others_last_fraction, expected_calls in cases:
            with self.subTest(label):
                self.setUp()
                others = LedgerEntry(
                    "other",
                    CredentialSource.SUBSCRIPTION,
                    1.0,
                    NOW,
                    (WeekReadings(RESET, 0.29, others_last_fraction),),
                    False,
                )
                record_entry(self.store, others, NOW)
                subscription = _Subscription(self.store, rises=(0.01,))

                outcome = self._run(subscription)

                self.assertEqual(len(subscription.calls), expected_calls)
                self.assertEqual(outcome.stop_reason, StopReason.WEEKLY_BUDGET)
                self.assertEqual(outcome.budget.spent_points, 10.0)  # type: ignore[union-attr]
                own = self._own_entry(subscription)
                self.assertEqual(own is not None and not own.is_provisional, 0 < expected_calls)

    def test_makes_no_call_and_records_nothing_without_a_first_reading(self) -> None:
        cases = [
            ("failed", {"failed_readings": frozenset({0})}, StopReason.READING_FAILED),
            ("interrupted", {"interrupted_readings": frozenset({0})}, StopReason.INTERRUPTED),
        ]
        for label, script, expected_reason in cases:
            with self.subTest(label):
                subscription = _Subscription(self.store, **script)  # type: ignore[arg-type]

                outcome = self._run(subscription)

                self.assertEqual(subscription.calls, [])
                self.assertEqual(outcome, CallsOutcome((), (), None, None, expected_reason))
                self.assertEqual(load_entries(self.store, NOW), ())

    def test_keeps_the_provisional_charge_when_a_later_reading_is_missing(self) -> None:
        cases = [
            ("failed", {"failed_readings": frozenset({2})}, StopReason.READING_FAILED),
            ("interrupted", {"interrupted_readings": frozenset({2})}, StopReason.INTERRUPTED),
        ]
        for label, script, expected_reason in cases:
            with self.subTest(label):
                self.setUp()
                subscription = _Subscription(
                    self.store, rises=(0.01, 0.01), **script  # type: ignore[arg-type]
                )

                outcome = self._run(subscription)

                self.assertEqual(len(subscription.calls), 2)
                self.assertEqual(outcome.stop_reason, expected_reason)
                provisional = LedgerEntry(
                    "this",
                    CredentialSource.SUBSCRIPTION,
                    2 * CALL_SPEND_USD,
                    NOW,
                    (WeekReadings(RESET, 0.29, 0.30),),
                    True,
                )
                self.assertEqual(self._own_entry(subscription), provisional)
                budget = outcome.budget
                assert isinstance(budget, SubscriptionBudget)
                self.assertEqual(budget.provisional_invocations, ("this",))

    def test_measures_an_interrupted_call_by_the_reading_after_it(self) -> None:
        subscription = _Subscription(
            self.store, rises=(0.0, 0.03), interrupted_calls=frozenset({1})
        )

        outcome = self._run(subscription)

        self.assertEqual(outcome.stop_reason, StopReason.INTERRUPTED)
        self.assertEqual(len(outcome.calls), 1)
        self.assertEqual(subscription.readings_asked, [0, 1, 2])
        own = self._own_entry(subscription)
        self.assertEqual(own.weeks, (WeekReadings(RESET, 0.29, 0.32),))  # type: ignore[union-attr]
        self.assertEqual(own.list_price_usd, CALL_SPEND_USD + 5.0)  # type: ignore[union-attr]
        self.assertFalse(own.is_provisional)  # type: ignore[union-attr]

    def test_stops_after_a_call_that_was_voided_or_reached_its_cap(self) -> None:
        cases = [
            ("voided", {"unexpected_tools": frozenset({"WebFetch"})}, StopReason.CALL_VOIDED),
            ("capped", {"harness_partial_reason": "cost_ceiling"}, StopReason.SPEND_CAP),
        ]
        for label, record, expected_reason in cases:
            with self.subTest(label):
                self.setUp()
                subscription = _Subscription(self.store, rises=(0.0,), records={0: record})

                outcome = self._run(subscription)

                self.assertEqual(len(subscription.calls), 1)
                self.assertEqual(subscription.readings_asked, [0, 1])
                self.assertEqual(outcome.stop_reason, expected_reason)
                own = self._own_entry(subscription)
                self.assertFalse(own.is_provisional)  # type: ignore[union-attr]

    def test_stops_before_a_call_without_room_for_its_runs(self) -> None:
        subscription = _Subscription(self.store, rises=(0.0, 0.0))

        outcome = self._run(subscription, has_room_for={2: False})

        self.assertEqual(
            [(call.case, call.level) for call in subscription.calls],
            [(REVIEW, EffortLevel.LOW), (REVIEW, EffortLevel.HIGH)],
        )
        self.assertEqual(outcome.stop_reason, StopReason.NO_SPACE)
        own = self._own_entry(subscription)
        self.assertFalse(own.is_provisional)  # type: ignore[union-attr]

    def test_gives_each_call_what_remains_of_the_api_keys_cap(self) -> None:
        subscription = _Subscription(self.store, rises=(0.0, 0.0, 0.0))
        plan = replace(SUBSCRIPTION_PLAN, credential=ApiKeyChoice(0.6))

        outcome = self._run(subscription, plan)

        self.assertEqual(
            [round(call.cap_usd, 2) for call in subscription.calls], [0.6, 0.35, 0.1]
        )
        self.assertEqual(subscription.readings_asked, [])
        self.assertEqual(outcome.stop_reason, StopReason.SPEND_CAP)
        self.assertEqual(outcome.budget, ApiKeyBudget(0.6, 3 * CALL_SPEND_USD))
        self.assertEqual(
            self._own_entry(subscription),
            LedgerEntry("this", CredentialSource.API_KEY, 3 * CALL_SPEND_USD, NOW, (), False),
        )

    def test_charges_an_interrupted_call_on_an_api_key_its_whole_cap(self) -> None:
        subscription = _Subscription(self.store, rises=(0.0,), interrupted_calls=frozenset({0}))
        plan = replace(SUBSCRIPTION_PLAN, credential=ApiKeyChoice(2.0))

        outcome = self._run(subscription, plan)

        self.assertEqual(outcome.stop_reason, StopReason.INTERRUPTED)
        self.assertEqual(outcome.spend.list_price_usd, 2.0)  # type: ignore[union-attr]
        own = self._own_entry(subscription)
        self.assertEqual(own.list_price_usd, 2.0)  # type: ignore[union-attr]
