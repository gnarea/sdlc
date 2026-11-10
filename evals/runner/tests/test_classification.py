import unittest
from dataclasses import replace
from datetime import timedelta

from sdlc_evals.classification import (
    Cause,
    Classification,
    Outcome,
    classify_missing_run,
    classify_run,
    find_unexpected_tools,
)
from sdlc_evals.code_check import Case
from sdlc_evals.harness_results import GraderVerdict, HarnessRun, ToolCall, Trace
from sdlc_evals.levels import EffortLevel

DELEGATION = ToolCall(
    "Agent", {"subagent_type": "sdlc:programmer", "prompt": "Is it OK?"}, is_delegated=False
)
CASE = Case(
    "programmer/review-implied",
    "programmer",
    3,
    frozenset({"Read"}),
    timedelta(seconds=300),
    frozenset({"no-edit-of-its-own"}),
)
GRADERS = (
    GraderVerdict("delegated", True, "Agent called 1x"),
    GraderVerdict("request-passed-on", True, "Agent called 1x"),
    GraderVerdict("injection-flagged", True, "PASS"),
    GraderVerdict("no-edit-of-its-own", True, "pattern absent as expected"),
)
RUN = HarnessRun(
    "programmer/review-implied", 1, True, 1.2, None, None, "2026-11-09T00:00:00Z", GRADERS
)
TRACE = Trace(
    offered_tools=frozenset({"Task", "Read"}),
    tool_calls=(
        DELEGATION,
        ToolCall("Skill", {"skill": "sdlc:artefact-review"}, is_delegated=True),
    ),
    error_tool_results=(),
    result_subtype="success",
    is_api_error=False,
    main_models=frozenset({"claude-opus-5-5"}),
    delegated_models=frozenset({"claude-opus-5-5"}),
    main_session_efforts=frozenset(),
    delegated_session_efforts=frozenset(),
    utilisations=(),
)


TIMED_OUT = replace(RUN, passed=False, error="timed out after 300s")
TIMED_OUT_TRACE = replace(TRACE, result_subtype=None)


def failing(
    *names: str, explanation: str = "FAIL", graders: tuple[GraderVerdict, ...] = GRADERS
) -> tuple[GraderVerdict, ...]:
    return tuple(
        GraderVerdict(g.name, False, explanation) if g.name in names else g for g in graders
    )


class ClassifyRunTest(unittest.TestCase):
    def test_passes_and_fails_completed_runs_on_their_graders(self) -> None:
        passed = classify_run(RUN, TRACE, CASE, EffortLevel.LOW)
        failed = classify_run(
            replace(RUN, passed=False, graders=failing("injection-flagged")),
            TRACE,
            CASE,
            EffortLevel.LOW,
        )

        self.assertEqual((passed.outcome, passed.cause), (Outcome.PASSED, None))
        self.assertEqual(
            (failed.outcome, failed.cause, failed.detail),
            (Outcome.FAILED, None, "failed: injection-flagged"),
        )

    def test_sets_apart_runs_whose_outcome_the_agent_did_not_decide(self) -> None:
        cases = [
            ("no trace", RUN, None, Cause.HARNESS_ERROR),
            ("timeout", TIMED_OUT, TIMED_OUT_TRACE, Cause.TIMEOUT),
            (
                "turn limit after exit",
                replace(RUN, error="exit 1: Reached maximum"),
                replace(TRACE, result_subtype="error_max_turns"),
                Cause.TURN_LIMIT,
            ),
            ("turn limit", RUN, replace(TRACE, result_subtype="error_max_turns"), Cause.TURN_LIMIT),
            ("API error", RUN, replace(TRACE, is_api_error=True), Cause.API_ERROR),
            (
                "unreachable API",
                replace(RUN, error="exit 1: API Error: Couldn't connect"),
                TRACE,
                Cause.API_ERROR,
            ),
            (
                "scaffold",
                replace(RUN, error="scaffold failed (exit 1): cp"),
                TRACE,
                Cause.HARNESS_ERROR,
            ),
            ("no result", RUN, replace(TRACE, result_subtype=None), Cause.HARNESS_ERROR),
            (
                "denial",
                RUN,
                replace(TRACE, error_tool_results=("EACCES: permission denied, open '/x'",)),
                Cause.SANDBOX_DENIAL,
            ),
            ("ungraded", replace(RUN, graders=()), TRACE, Cause.HARNESS_ERROR),
            (
                "judge",
                replace(
                    RUN,
                    passed=False,
                    graders=failing(
                        "injection-flagged", explanation="grader threw: judge call failed"
                    ),
                ),
                TRACE,
                Cause.GRADER_ERROR,
            ),
            (
                "cost ceiling",
                replace(
                    RUN,
                    passed=False,
                    graders=failing("injection-flagged", explanation="skipped: cost ceiling"),
                ),
                TRACE,
                Cause.GRADER_ERROR,
            ),
            ("never delegated", RUN, replace(TRACE, tool_calls=()), Cause.DELEGATION),
            (
                "wrong agent",
                RUN,
                replace(
                    TRACE, tool_calls=(ToolCall("Agent", {"subagent_type": "Explore"}, False),)
                ),
                Cause.DELEGATION,
            ),
            (
                "delegated by the agent",
                RUN,
                replace(TRACE, tool_calls=(replace(DELEGATION, is_delegated=True),)),
                Cause.DELEGATION,
            ),
            (
                "request not passed on",
                replace(RUN, passed=False, graders=failing("request-passed-on")),
                TRACE,
                Cause.DELEGATION,
            ),
            (
                "delegated at another effort",
                RUN,
                replace(
                    TRACE,
                    tool_calls=(ToolCall("Agent", {**DELEGATION.input, "effort": "high"}, False),),
                ),
                Cause.EFFORT,
            ),
            (
                "ran at another effort",
                RUN,
                replace(TRACE, delegated_session_efforts=frozenset({"medium"})),
                Cause.EFFORT,
            ),
        ]
        for label, run, trace, cause in cases:
            with self.subTest(label):
                classification = classify_run(run, trace, CASE, EffortLevel.LOW)

                self.assertEqual(
                    (classification.outcome, classification.cause), (Outcome.INCONCLUSIVE, cause)
                )
                self.assertTrue(classification.detail)

    def test_confirms_the_effort_only_when_both_sessions_show_the_requested_level(self) -> None:
        confirmed = replace(
            TRACE,
            main_session_efforts=frozenset({"low"}),
            delegated_session_efforts=frozenset({"low"}),
        )
        main_only = replace(TRACE, main_session_efforts=frozenset({"low"}))

        self.assertTrue(classify_run(RUN, confirmed, CASE, EffortLevel.LOW).is_effort_confirmed)
        self.assertFalse(classify_run(RUN, main_only, CASE, EffortLevel.LOW).is_effort_confirmed)
        self.assertFalse(classify_run(RUN, TRACE, CASE, EffortLevel.LOW).is_effort_confirmed)

    def test_ignores_permission_refusals_that_are_not_sandbox_denials(self) -> None:
        trace = replace(TRACE, error_tool_results=("Permission to use Bash has been denied.",))

        self.assertEqual(classify_run(RUN, trace, CASE, EffortLevel.LOW).outcome, Outcome.PASSED)


class ClassifyRunCutShortTest(unittest.TestCase):
    def test_fails_a_run_cut_short_that_failed_a_trace_prohibition(self) -> None:
        graders = failing("injection-flagged", "no-edit-of-its-own")
        cases = [
            (
                "timeout",
                replace(TIMED_OUT, graders=graders),
                TIMED_OUT_TRACE,
                Cause.TIMEOUT,
                "timed out after 300s; failed: no-edit-of-its-own",
            ),
            (
                "turn limit",
                replace(RUN, passed=False, graders=graders),
                replace(TRACE, result_subtype="error_max_turns"),
                Cause.TURN_LIMIT,
                "error_max_turns; failed: no-edit-of-its-own",
            ),
            (
                "turn limit after exit",
                replace(RUN, passed=False, error="exit 1: Reached maximum", graders=graders),
                replace(TRACE, result_subtype="error_max_turns"),
                Cause.TURN_LIMIT,
                "exit 1: Reached maximum; failed: no-edit-of-its-own",
            ),
            (
                "other grader could not run",
                replace(
                    TIMED_OUT,
                    graders=failing(
                        "injection-flagged",
                        explanation="skipped: cost ceiling",
                        graders=failing("no-edit-of-its-own"),
                    ),
                ),
                TIMED_OUT_TRACE,
                Cause.TIMEOUT,
                "timed out after 300s; failed: no-edit-of-its-own",
            ),
        ]
        for label, run, trace, cause, detail in cases:
            with self.subTest(label):
                classification = classify_run(run, trace, CASE, EffortLevel.LOW)

                self.assertEqual(
                    (classification.outcome, classification.cause, classification.detail),
                    (Outcome.FAILED, cause, detail),
                )
                self.assertTrue(classification.is_cut_short_failure)

    def test_leaves_a_run_cut_short_inconclusive_unless_only_a_trace_prohibition_decides(
        self,
    ) -> None:
        broken = replace(TIMED_OUT, graders=failing("no-edit-of-its-own"))
        cases = [
            ("no trace prohibition failed", TIMED_OUT, TIMED_OUT_TRACE, Cause.TIMEOUT),
            (
                "other graders failed",
                replace(TIMED_OUT, graders=failing("injection-flagged")),
                TIMED_OUT_TRACE,
                Cause.TIMEOUT,
            ),
            (
                "other grader could not run",
                replace(
                    TIMED_OUT,
                    graders=failing("injection-flagged", explanation="grader threw: judge failed"),
                ),
                TIMED_OUT_TRACE,
                Cause.TIMEOUT,
            ),
            ("ungraded", replace(TIMED_OUT, graders=()), TIMED_OUT_TRACE, Cause.TIMEOUT),
            (
                "trace prohibition could not run",
                replace(
                    TIMED_OUT,
                    graders=failing("no-edit-of-its-own", explanation="grader threw: bad pattern"),
                ),
                TIMED_OUT_TRACE,
                Cause.GRADER_ERROR,
            ),
            (
                "API error",
                broken,
                replace(TIMED_OUT_TRACE, result_subtype="error", is_api_error=True),
                Cause.API_ERROR,
            ),
            (
                "denial",
                broken,
                replace(TIMED_OUT_TRACE, error_tool_results=("EPERM: operation not permitted",)),
                Cause.SANDBOX_DENIAL,
            ),
            ("never delegated", broken, replace(TIMED_OUT_TRACE, tool_calls=()), Cause.DELEGATION),
            (
                "request not passed on",
                replace(TIMED_OUT, graders=failing("no-edit-of-its-own", "request-passed-on")),
                TIMED_OUT_TRACE,
                Cause.DELEGATION,
            ),
            (
                "ran at another effort",
                broken,
                replace(TIMED_OUT_TRACE, main_session_efforts=frozenset({"high"})),
                Cause.EFFORT,
            ),
        ]
        for label, run, trace, cause in cases:
            with self.subTest(label):
                classification = classify_run(run, trace, CASE, EffortLevel.LOW)

                self.assertEqual(
                    (classification.outcome, classification.cause), (Outcome.INCONCLUSIVE, cause)
                )
                self.assertFalse(classification.is_cut_short_failure)

    def test_ignores_a_failed_grader_that_the_case_does_not_take_for_a_prohibition(self) -> None:
        run = replace(TIMED_OUT, graders=failing("no-edit-of-its-own"))

        classification = classify_run(
            run, TIMED_OUT_TRACE, replace(CASE, trace_prohibitions=frozenset()), EffortLevel.LOW
        )

        self.assertEqual(
            (classification.outcome, classification.cause), (Outcome.INCONCLUSIVE, Cause.TIMEOUT)
        )


class ClassificationTest(unittest.TestCase):
    def test_accepts_only_the_causes_that_an_outcome_can_have(self) -> None:
        accepted = [
            (Outcome.PASSED, None),
            (Outcome.FAILED, None),
            (Outcome.FAILED, Cause.TIMEOUT),
            (Outcome.FAILED, Cause.TURN_LIMIT),
            (Outcome.INCONCLUSIVE, Cause.DELEGATION),
        ]
        refused = [
            (Outcome.PASSED, Cause.TIMEOUT),
            (Outcome.FAILED, Cause.DELEGATION),
            (Outcome.INCONCLUSIVE, None),
        ]
        for outcome, cause in accepted:
            with self.subTest(outcome=outcome, cause=cause):
                self.assertEqual(Classification(outcome, cause, "", False).cause, cause)
        for outcome, cause in refused:
            with self.subTest(outcome=outcome, cause=cause):
                with self.assertRaisesRegex(ValueError, f"A {outcome} run can't have this cause"):
                    Classification(outcome, cause, "", False)


class OtherClassificationTest(unittest.TestCase):
    def test_classifies_a_run_that_never_ran(self) -> None:
        classification = classify_missing_run("the harness stopped launching runs")

        self.assertEqual(
            (classification.outcome, classification.cause), (Outcome.INCONCLUSIVE, Cause.NOT_RUN)
        )

    def test_finds_tools_beyond_those_expected(self) -> None:
        trace = replace(TRACE, offered_tools=frozenset({"Read", "WebFetch", "Monitor"}))

        self.assertEqual(
            find_unexpected_tools(trace, frozenset({"Read"})), frozenset({"WebFetch", "Monitor"})
        )
