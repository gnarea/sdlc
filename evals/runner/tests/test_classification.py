import unittest
from dataclasses import replace

from sdlc_evals.classification import (
    Cause,
    Outcome,
    classify_missing_run,
    classify_run,
    find_unexpected_tools,
)
from sdlc_evals.harness_results import GraderVerdict, HarnessRun, ToolCall, Trace
from sdlc_evals.levels import EffortLevel

DELEGATION = ToolCall(
    "Agent", {"subagent_type": "sdlc:programmer", "prompt": "Is it OK?"}, is_delegated=False
)
GRADERS = (
    GraderVerdict("delegated", True, "Agent called 1x"),
    GraderVerdict("request-passed-on", True, "Agent called 1x"),
    GraderVerdict("injection-flagged", True, "PASS"),
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


def failing(name: str, explanation: str = "FAIL") -> tuple[GraderVerdict, ...]:
    return tuple(
        GraderVerdict(g.name, False, explanation) if g.name == name else g for g in GRADERS
    )


class ClassifyRunTest(unittest.TestCase):
    def test_passes_and_fails_completed_runs_on_their_graders(self) -> None:
        passed = classify_run(RUN, TRACE, "programmer", EffortLevel.LOW)
        failed = classify_run(
            replace(RUN, passed=False, graders=failing("injection-flagged")),
            TRACE,
            "programmer",
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
            ("timeout", replace(RUN, error="timed out after 900s"), TRACE, Cause.TIMEOUT),
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
                    graders=failing("injection-flagged", "grader threw: judge call failed"),
                ),
                TRACE,
                Cause.GRADER_ERROR,
            ),
            (
                "cost ceiling",
                replace(
                    RUN, passed=False, graders=failing("injection-flagged", "skipped: cost ceiling")
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
                classification = classify_run(run, trace, "programmer", EffortLevel.LOW)

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

        self.assertTrue(
            classify_run(RUN, confirmed, "programmer", EffortLevel.LOW).is_effort_confirmed
        )
        self.assertFalse(
            classify_run(RUN, main_only, "programmer", EffortLevel.LOW).is_effort_confirmed
        )
        self.assertFalse(
            classify_run(RUN, TRACE, "programmer", EffortLevel.LOW).is_effort_confirmed
        )

    def test_ignores_permission_refusals_that_are_not_sandbox_denials(self) -> None:
        trace = replace(TRACE, error_tool_results=("Permission to use Bash has been denied.",))

        self.assertEqual(
            classify_run(RUN, trace, "programmer", EffortLevel.LOW).outcome, Outcome.PASSED
        )


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
