import unittest
from datetime import UTC, datetime, timedelta

from sdlc_evals.credentials import CredentialSource
from sdlc_evals.spend import (
    SUBSCRIPTION_CALL_CAP_USD,
    ApiKeyBudget,
    ApiKeyChoice,
    assess_subscription,
    charge_points,
    week_charge_points,
)
from sdlc_evals.state.ledger import LedgerEntry, WeekReadings

NOW = datetime(2026, 11, 9, tzinfo=UTC)
RESET = NOW + timedelta(days=3)
NEXT_RESET = RESET + timedelta(days=7)


def entry(
    *weeks: tuple[float, float, datetime],
    invocation_id: str = "a",
    is_provisional: bool = False,
) -> LedgerEntry:
    readings = tuple(WeekReadings(reset, first, last) for first, last, reset in weeks)
    return LedgerEntry(
        invocation_id, CredentialSource.SUBSCRIPTION, 1.0, NOW, readings, is_provisional
    )


class ChargeTest(unittest.TestCase):
    def test_charges_the_rise_in_a_week_plus_a_point_for_rounding(self) -> None:
        cases = [
            ("no rise", entry((0.29, 0.29, RESET)), 1.0),
            ("a rise", entry((0.29, 0.31, RESET)), 3.0),
            ("a fall", entry((0.31, 0.29, RESET)), 1.0),
            ("a rise that floating point puts below 9 points", entry((0.48, 0.57, RESET)), 10.0),
        ]
        for label, charged, expected_points in cases:
            with self.subTest(label):
                self.assertEqual(week_charge_points(charged, 0), expected_points)

    def test_charges_a_week_that_began_during_the_invocation_from_zero(self) -> None:
        straddling = entry((0.95, 0.97, RESET), (0.01, 0.02, NEXT_RESET))

        self.assertEqual(week_charge_points(straddling, 0), 3.0)
        self.assertEqual(week_charge_points(straddling, 1), 3.0)
        self.assertEqual(charge_points(straddling, NOW), 6.0)
        self.assertEqual(charge_points(straddling, RESET), 3.0)
        self.assertEqual(charge_points(straddling, NEXT_RESET), 0.0)


class AssessSubscriptionTest(unittest.TestCase):
    def test_adds_the_charges_of_every_invocation_on_the_subscription(self) -> None:
        api_key = LedgerEntry("c", CredentialSource.API_KEY, 9.0, NOW, (), False)
        entries = (
            entry((0.20, 0.24, RESET)),
            entry((0.24, 0.27, RESET), invocation_id="b"),
            api_key,
        )

        budget = assess_subscription(entries, NOW)

        self.assertEqual((budget.spent_points, budget.provisional_invocations), (9.0, ()))

    def test_lets_a_call_start_only_below_the_weekly_budget(self) -> None:
        cases = [
            ("just below", entry((0.20, 0.28, RESET)), SUBSCRIPTION_CALL_CAP_USD),
            ("at the budget", entry((0.20, 0.29, RESET)), None),
            ("at the budget, through floating point", entry((0.48, 0.57, RESET)), None),
        ]
        for label, charged, expected_cap in cases:
            with self.subTest(label):
                self.assertEqual(assess_subscription((charged,), NOW).call_cap_usd(), expected_cap)

    def test_lets_a_provisional_charge_hold_the_budget_even_once_its_week_reset(self) -> None:
        provisional = entry((0.20, 0.20, RESET), invocation_id="b", is_provisional=True)

        budget = assess_subscription((entry((0.20, 0.20, RESET)), provisional), NEXT_RESET)

        self.assertEqual(budget.spent_points, 0.0)
        self.assertEqual(budget.provisional_invocations, ("b",))
        self.assertIsNone(budget.call_cap_usd())


class ApiKeyBudgetTest(unittest.TestCase):
    def test_gives_the_next_call_what_remains_of_the_cap(self) -> None:
        cases = [
            ("nothing spent", 0.0, 1.0),
            ("a cent left", 0.99, 0.01),
            ("less than a cent left", 0.995, None),
            ("overspent", 1.5, None),
        ]
        for label, spent_usd, expected_cap in cases:
            with self.subTest(label):
                cap_usd = ApiKeyBudget(cap_usd=1.0, spent_usd=spent_usd).call_cap_usd()

                if expected_cap is None:
                    self.assertIsNone(cap_usd)
                else:
                    self.assertAlmostEqual(cap_usd, expected_cap)  # type: ignore[arg-type]

    def test_refuses_a_cap_that_is_not_positive(self) -> None:
        for cap_usd in (0.0, -1.0):
            with self.subTest(cap_usd):
                with self.assertRaisesRegex(ValueError, f"got {cap_usd}"):
                    ApiKeyChoice(cap_usd)
