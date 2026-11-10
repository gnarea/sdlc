import json
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sdlc_evals.classification import Cause, Classification, Outcome
from sdlc_evals.code_check import Case
from sdlc_evals.credentials import CredentialSource
from sdlc_evals.exit_status import ExitStatus
from sdlc_evals.harness import CaseSelection, HarnessCall
from sdlc_evals.harness_call import CallRecord
from sdlc_evals.invocation_calls import StopReason
from sdlc_evals.levels import EffortLevel
from sdlc_evals.records import (
    InvocationRecord,
    count_passes,
    decide_exit_status,
    render_brief,
    render_manifest,
    render_summary,
)
from sdlc_evals.spend import ApiKeyBudget, SubscriptionBudget
from sdlc_evals.state.ledger import LedgerEntry, WeeklyUtilisation, WeekReadings
from sdlc_evals.working_tree import CodeRecord, FilesRecord

from .call_records import make_call_record

NOW = datetime(2026, 11, 9, tzinfo=UTC)
RESET = datetime(2026, 11, 13, 12, tzinfo=UTC)
CASE = Case(
    "programmer/review-implied",
    "programmer",
    3,
    frozenset({"Read"}),
    timedelta(seconds=300),
    frozenset({"artefact-review-not-loaded"}),
)
OTHER_CASE = Case(
    "architect/domain", "architect", 3, frozenset({"Read"}), timedelta(seconds=300), frozenset()
)
PASSED = Classification(Outcome.PASSED, None, "", True)
FAILED = Classification(Outcome.FAILED, None, "failed: x", True)
TIMED_OUT = Classification(Outcome.INCONCLUSIVE, Cause.TIMEOUT, "timed out after 300s", False)
CUT_SHORT = Classification(
    Outcome.FAILED, Cause.TIMEOUT, "timed out after 300s; failed: artefact-review-not-loaded", True
)
SPEND = LedgerEntry(
    "abc", CredentialSource.SUBSCRIPTION, 3.0, NOW, (WeekReadings(RESET, 0.29, 0.31),), False
)
READINGS = (WeeklyUtilisation(0.29, RESET), WeeklyUtilisation(0.31, RESET))


def call(
    *classifications: Classification,
    level: EffortLevel = EffortLevel.LOW,
    case: Case = CASE,
) -> CallRecord:
    return make_call_record(HarnessCall(case, level, 3, 5.0), 1.5, classifications)


def invocation(
    *calls: CallRecord,
    stop_reason: StopReason | None = None,
    spend: LedgerEntry | None = SPEND,
    budget: SubscriptionBudget | ApiKeyBudget | None = SubscriptionBudget(4.0, ()),
) -> InvocationRecord:
    return InvocationRecord(
        invocation_id="abc",
        started_at=NOW,
        finished_at=NOW,
        directory=Path("/tmp/sdlc-evals-x"),
        worktree=Path("/tree"),
        code=CodeRecord("deadbeef", FilesRecord("", "f" * 64), FilesRecord("+x\n", "e" * 64)),
        claude_code_version="2.1.317",
        credential_source=CredentialSource.SUBSCRIPTION,
        selection=CaseSelection((CASE, OTHER_CASE), ("programmer", "architect"), None),
        levels_requested=(EffortLevel.LOW, EffortLevel.HIGH),
        self_test_checks=43,
        allowed_hosts=frozenset({"api.anthropic.com"}),
        calls=calls,
        readings=READINGS,
        spend=spend,
        budget=budget,
        proxy_refusals=(),
        proxy_failures=(),
        stop_reason=stop_reason,
    )


class ExitStatusTest(unittest.TestCase):
    def test_lets_the_most_severe_condition_win(self) -> None:
        cases = [
            ("all passed", invocation(call(PASSED, PASSED, PASSED)), ExitStatus.THRESHOLD_MET),
            ("one failed", invocation(call(PASSED, FAILED, TIMED_OUT)), ExitStatus.BELOW_THRESHOLD),
            ("inconclusive", invocation(call(PASSED, PASSED, TIMED_OUT)), ExitStatus.INCONCLUSIVE),
            ("nothing completed", invocation(call(TIMED_OUT)), ExitStatus.INCONCLUSIVE),
            (
                "one cut short and failed",
                invocation(call(PASSED, PASSED, CUT_SHORT)),
                ExitStatus.BELOW_THRESHOLD,
            ),
            ("only failures cut short", invocation(call(CUT_SHORT)), ExitStatus.BELOW_THRESHOLD),
        ]
        stops = [
            (StopReason.CALL_VOIDED, ExitStatus.INCONCLUSIVE),
            (StopReason.WEEKLY_BUDGET, ExitStatus.SPEND_CAP),
            (StopReason.SPEND_CAP, ExitStatus.SPEND_CAP),
            (StopReason.READING_FAILED, ExitStatus.SPEND_UNMEASURED),
            (StopReason.NO_SPACE, ExitStatus.REFUSED),
            (StopReason.INTERRUPTED, ExitStatus.INTERRUPTED),
        ]
        cases += [
            (reason.name, invocation(call(PASSED), stop_reason=reason), expected)
            for reason, expected in stops
        ]
        for label, record, expected in cases:
            with self.subTest(label):
                self.assertEqual(decide_exit_status(record), expected)

    def test_counts_completed_runs_and_the_failures_of_runs_cut_short(self) -> None:
        (count,) = count_passes((call(PASSED, FAILED, CUT_SHORT, TIMED_OUT),))

        self.assertEqual(
            (count.passed, count.failed, count.cut_short_failures, count.inconclusive),
            (1, 2, 1, 1),
        )
        self.assertEqual(count.counted, 3)
        self.assertTrue(count.is_below_threshold)


class RenderTest(unittest.TestCase):
    def test_records_what_produced_the_results_without_the_credential(self) -> None:
        record = invocation(call(PASSED, TIMED_OUT))

        manifest = render_manifest(record, ExitStatus.INCONCLUSIVE)

        self.assertEqual(manifest["format_version"], 4)
        self.assertEqual(
            manifest["code"],
            {
                "commit": "deadbeef",
                "snapshot": {"differs_from_commit": False, "diff": "", "sha256": "f" * 64},
                "wrapper": {"differs_from_commit": True, "diff": "+x\n", "sha256": "e" * 64},
            },
        )
        self.assertEqual(
            (manifest["model"], manifest["credential_source"], manifest["exit_status"]),
            ("claude-opus-5-5", "subscription", 2),
        )
        (call_entry,) = manifest["calls"]  # type: ignore[misc]
        self.assertEqual(
            (call_entry["case"], call_entry["level"], call_entry["cap_usd"]),
            ("programmer/review-implied", "low", 5.0),
        )
        self.assertEqual(call_entry["inherited_variables"], ["CLAUDE_CODE_OAUTH_TOKEN"])
        self.assertEqual([run["cause"] for run in call_entry["runs"]], [None, "timeout"])
        json.dumps(manifest)

    def test_records_every_chosen_case_and_summarises_those_that_never_ran(self) -> None:
        record = invocation(call(PASSED), stop_reason=StopReason.WEEKLY_BUDGET)

        manifest = render_manifest(record, ExitStatus.SPEND_CAP)
        summary = render_summary(record, ExitStatus.SPEND_CAP)

        self.assertEqual(
            manifest["subset"],
            {
                "agents": ["programmer", "architect"],
                "levels": ["low", "high"],
                "cases": ["programmer/review-implied", "architect/domain"],
                "runs_per_case": None,
            },
        )
        self.assertIn(
            "Inconclusive runs:\n  none\n\nNot run:\n  architect/domain\n\nEffort level", summary
        )

    def test_leaves_out_the_cases_not_run_when_every_case_ran(self) -> None:
        record = invocation(call(PASSED), call(PASSED, case=OTHER_CASE))

        summary = render_summary(record, ExitStatus.THRESHOLD_MET)

        self.assertNotIn("Not run:", summary)

    def test_records_the_limit_that_cut_a_failed_run_short(self) -> None:
        manifest = render_manifest(invocation(call(FAILED, CUT_SHORT)), ExitStatus.BELOW_THRESHOLD)

        (call_entry,) = manifest["calls"]  # type: ignore[misc]
        self.assertEqual(
            [(run["outcome"], run["cause"]) for run in call_entry["runs"]],
            [("failed", None), ("failed", "timeout")],
        )

    def test_records_every_reading_and_the_charge_they_measured(self) -> None:
        manifest = render_manifest(invocation(call(PASSED)), ExitStatus.THRESHOLD_MET)

        self.assertEqual(
            manifest["readings"],
            [
                {"fraction": 0.29, "resets_at": "2026-11-13T12:00:00+00:00"},
                {"fraction": 0.31, "resets_at": "2026-11-13T12:00:00+00:00"},
            ],
        )
        self.assertEqual(
            manifest["spend"],
            {
                "list_price_usd": 3.0,
                "is_provisional": False,
                "weeks": [
                    {
                        "resets_at": "2026-11-13T12:00:00+00:00",
                        "first_fraction": 0.29,
                        "last_fraction": 0.31,
                        "charged_points": 3.0,
                    }
                ],
                "week_spent_points": 4.0,
                "weekly_budget_points": 10.0,
                "provisional_invocations": [],
            },
        )

    def test_summarises_pass_counts_and_inconclusive_runs(self) -> None:
        summary = render_summary(invocation(call(PASSED, TIMED_OUT)), ExitStatus.INCONCLUSIVE)

        self.assertIn("programmer/review-implied  low  1/1  (1 inconclusive)", summary)
        self.assertIn("Inconclusive runs:\n  programmer/review-implied  low  run 2: timeout", summary)
        self.assertIn("run 2: timeout (timed out after 300s)", summary)
        self.assertIn("Exit status: 2 (inconclusive)", summary)
        self.assertIn("with uncommitted changes to the wrapper (snapshot ffffffffffff)", summary)
        self.assertIn("Effort level confirmed for 1 of 2 run(s).", summary)

    def test_summarises_the_failures_of_runs_cut_short_apart(self) -> None:
        record = invocation(call(PASSED, FAILED, CUT_SHORT, TIMED_OUT))

        summary = render_summary(record, ExitStatus.BELOW_THRESHOLD)

        self.assertIn(
            "Pass counts (completed runs, and runs cut short that failed):\n"
            "  programmer/review-implied  low  1/3  "
            "(1 of the failures cut short, 1 inconclusive)\n"
            "\n"
            "Failures of runs cut short:\n"
            "  programmer/review-implied  low  run 3: timeout "
            "(timed out after 300s; failed: artefact-review-not-loaded)\n"
            "\n"
            "Inconclusive runs:\n"
            "  programmer/review-implied  low  run 4: timeout (timed out after 300s)\n",
            summary,
        )

    def test_summarises_the_spend_at_list_price_and_by_the_readings(self) -> None:
        calls = (call(PASSED), call(PASSED, level=EffortLevel.HIGH), call(PASSED))

        summary = render_summary(invocation(*calls), ExitStatus.THRESHOLD_MET)

        self.assertIn(
            "Spend:\n"
            "  low: $3.00 at list price\n"
            "  high: $1.50 at list price\n"
            "  Weekly utilisation 29% → 31% (week resetting 2026-11-13 12:00 UTC): "
            "charged 3 points\n"
            "  This week's eval invocations have used 4 of their 10 points.\n",
            summary,
        )

    def test_summarises_a_week_that_began_during_the_invocation(self) -> None:
        next_reset = RESET + timedelta(days=7)
        spend = replace(
            SPEND, weeks=(WeekReadings(RESET, 0.95, 0.95), WeekReadings(next_reset, 0.01, 0.02))
        )

        summary = render_summary(invocation(call(PASSED), spend=spend), ExitStatus.THRESHOLD_MET)

        self.assertIn(
            "  Weekly utilisation 95% → 95% (week resetting 2026-11-13 12:00 UTC): "
            "charged 1 point\n"
            "  Weekly utilisation 0% at the reset → 2% (week resetting 2026-11-20 12:00 UTC): "
            "charged 3 points\n",
            summary,
        )

    def test_summarises_the_spend_against_an_api_keys_cap(self) -> None:
        spend = LedgerEntry("abc", CredentialSource.API_KEY, 1.5, NOW, (), False)
        record = invocation(call(PASSED), spend=spend, budget=ApiKeyBudget(10.0, 1.5))

        summary = render_summary(record, ExitStatus.THRESHOLD_MET)

        self.assertIn(
            "  low: $1.50 at list price\n  Charged $1.50 of the invocation's $10.00 cap.\n",
            summary,
        )

    def test_says_where_an_invocation_stopped_and_what_it_left_behind(self) -> None:
        provisional = replace(SPEND, is_provisional=True)
        cases = [
            (
                "the budget",
                invocation(
                    call(PASSED),
                    call(PASSED, level=EffortLevel.HIGH),
                    call(PASSED, case=OTHER_CASE),
                    stop_reason=StopReason.WEEKLY_BUDGET,
                ),
                "Stopped early: this week's eval invocations reached their share of the weekly "
                "allowance. 1 of 2 case(s) ran at every level.\n",
            ),
            (
                "a failed reading",
                invocation(
                    call(PASSED),
                    stop_reason=StopReason.READING_FAILED,
                    spend=provisional,
                    budget=SubscriptionBudget(0.0, ("abc",)),
                ),
                "Stopped early: a reading of the weekly utilisation failed, so the spend can't be "
                "measured. 0 of 2 case(s) ran at every level. Its provisional charge blocks the "
                "subscription until the owner checks the usage and clears it with the "
                "clear-charge command.\n",
            ),
            (
                "a failed first reading",
                invocation(stop_reason=StopReason.READING_FAILED, spend=None, budget=None),
                "Spend:\n  none\n\nStopped early: a reading of the weekly utilisation failed, "
                "so the spend can't be measured. 0 of 2 case(s) ran at every level.\n",
            ),
        ]
        for label, record, expected in cases:
            with self.subTest(label):
                summary = render_summary(record, decide_exit_status(record))
                brief = render_brief(record, decide_exit_status(record), Path("/x/summary.txt"))

                self.assertIn(expected, summary)
                self.assertIn(expected.split("Stopped early")[-1], brief)
        self.assertIn(
            "  This week's budget is held by the provisional charge of abc.",
            render_summary(cases[1][1], ExitStatus.SPEND_UNMEASURED),
        )

    def test_briefs_the_terminal_on_failures_and_inconclusive_runs_only(self) -> None:
        summary = Path("/tmp/x/summary.txt")

        brief = render_brief(
            invocation(call(PASSED, FAILED, TIMED_OUT, TIMED_OUT)),
            ExitStatus.BELOW_THRESHOLD,
            summary,
        )

        self.assertEqual(
            brief,
            "programmer/review-implied: low 1/2\n"
            "1 of 4 runs passed, 1 failed, 2 inconclusive (timeout × 2)\n"
            "Exit status 1 (below threshold). Details: /tmp/x/summary.txt\n",
        )
        self.assertEqual(
            render_brief(invocation(call(PASSED)), ExitStatus.THRESHOLD_MET, summary),
            "1 of 1 runs passed, 0 failed, 0 inconclusive\n"
            "Exit status 0 (threshold met). Details: /tmp/x/summary.txt\n",
        )
        self.assertEqual(
            render_brief(
                invocation(call(PASSED, PASSED, CUT_SHORT)), ExitStatus.BELOW_THRESHOLD, summary
            ),
            "programmer/review-implied: low 2/3 (1 cut short)\n"
            "2 of 3 runs passed, 1 failed (1 cut short), 0 inconclusive\n"
            "Exit status 1 (below threshold). Details: /tmp/x/summary.txt\n",
        )

    def test_reports_no_runs_as_none(self) -> None:
        summary = render_summary(invocation(), ExitStatus.INCONCLUSIVE)

        self.assertIn(
            "Pass counts (completed runs, and runs cut short that failed):\n  none\n\n"
            "Failures of runs cut short:\n  none\n",
            summary,
        )
