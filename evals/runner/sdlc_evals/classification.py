"""Each run's outcome: passed, failed, or inconclusive whenever something other than the agent
decided it.
"""

import enum
from dataclasses import dataclass

from .harness_results import HarnessRun, Trace
from .levels import EffortLevel

DELEGATION_GRADERS = frozenset({"delegated", "request-passed-on"})
DELEGATION_TOOL = "Agent"
# Error text that the operating system puts in a tool's result when the confinement refuses an
# operation.
SANDBOX_DENIAL_MARKERS = ("EACCES", "EPERM", "Operation not permitted")
GRADER_FAILURE_PREFIXES = ("grader threw:", "skipped:")
_TIMEOUT_PREFIX = "timed out after"
# Claude Code's prefix for a request that failed, whether the API refused it or it never reached
# the API.
_API_ERROR_MARKER = "API Error:"
_TURN_LIMIT_SUBTYPE = "error_max_turns"


class Outcome(enum.StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class Cause(enum.StrEnum):
    """Why a run is inconclusive."""

    HARNESS_ERROR = "harness error"
    API_ERROR = "API error"
    TIMEOUT = "timeout"
    TURN_LIMIT = "turn limit"
    GRADER_ERROR = "grader could not run"
    DELEGATION = "delegation not as asked"
    EFFORT = "effort level other than the requested one"
    SANDBOX_DENIAL = "sandbox denial"
    NOT_RUN = "not run"
    UNEXPECTED_TOOL = "harness call voided: unexpected tool"


@dataclass(frozen=True)
class Classification:
    outcome: Outcome
    cause: Cause | None
    detail: str
    is_effort_confirmed: bool


def classify_run(
    run: HarnessRun, trace: Trace | None, agent: str, level: EffortLevel
) -> Classification:
    """Classify a run that the harness launched, from its record and its trace."""
    if trace is None:
        return _inconclusive(
            Cause.HARNESS_ERROR, run.error or "no trace", is_effort_confirmed=False
        )
    is_effort_confirmed = _is_effort_confirmed(trace, level)
    for check in (_check_harness_error, _check_trace_ending, _check_sandbox_denial, _check_graders):
        inconclusive = check(run, trace)
        if inconclusive is not None:
            return _inconclusive(*inconclusive, is_effort_confirmed=is_effort_confirmed)
    delegation = _check_delegation(trace, agent, level, run)
    if delegation is not None:
        return _inconclusive(*delegation, is_effort_confirmed=is_effort_confirmed)
    mismatch = sorted(
        (trace.main_session_efforts | trace.delegated_session_efforts) - {level.value}
    )
    if mismatch:
        return _inconclusive(
            Cause.EFFORT, f"ran at {', '.join(mismatch)}", is_effort_confirmed=False
        )
    if run.passed:
        return Classification(Outcome.PASSED, None, "", is_effort_confirmed)
    failed = ", ".join(grader.name for grader in run.graders if not grader.passed)
    return Classification(Outcome.FAILED, None, f"failed: {failed}", is_effort_confirmed)


def classify_missing_run(detail: str) -> Classification:
    """Classify a run that the harness never launched, or never reported."""
    return Classification(Outcome.INCONCLUSIVE, Cause.NOT_RUN, detail, is_effort_confirmed=False)


def find_unexpected_tools(trace: Trace, expected: frozenset[str]) -> frozenset[str]:
    return trace.offered_tools - expected


def _inconclusive(cause: Cause, detail: str, *, is_effort_confirmed: bool) -> Classification:
    return Classification(Outcome.INCONCLUSIVE, cause, detail, is_effort_confirmed)


def _check_harness_error(run: HarnessRun, trace: Trace) -> tuple[Cause, str] | None:
    if run.error is None:
        return None
    if run.error.startswith(_TIMEOUT_PREFIX):
        return Cause.TIMEOUT, run.error
    if trace.result_subtype == _TURN_LIMIT_SUBTYPE:
        return Cause.TURN_LIMIT, run.error
    if trace.is_api_error or _API_ERROR_MARKER in run.error:
        return Cause.API_ERROR, run.error
    return Cause.HARNESS_ERROR, run.error


def _check_trace_ending(run: HarnessRun, trace: Trace) -> tuple[Cause, str] | None:
    if trace.result_subtype is None:
        return Cause.HARNESS_ERROR, "the trace has no result"
    if trace.result_subtype == _TURN_LIMIT_SUBTYPE:
        return Cause.TURN_LIMIT, trace.result_subtype
    if trace.is_api_error:
        return Cause.API_ERROR, "the run ended on an API error"
    return None


def _check_sandbox_denial(run: HarnessRun, trace: Trace) -> tuple[Cause, str] | None:
    for text in trace.error_tool_results:
        marker = next((marker for marker in SANDBOX_DENIAL_MARKERS if marker in text), None)
        if marker is not None:
            return Cause.SANDBOX_DENIAL, f"a tool failed with {marker}"
    return None


def _check_graders(run: HarnessRun, trace: Trace) -> tuple[Cause, str] | None:
    if not run.graders:
        return Cause.HARNESS_ERROR, "the run wasn't graded"
    for grader in run.graders:
        if grader.explanation.startswith(GRADER_FAILURE_PREFIXES):
            return Cause.GRADER_ERROR, f"{grader.name}: {grader.explanation}"
    return None


def _check_delegation(
    trace: Trace, agent: str, level: EffortLevel, run: HarnessRun
) -> tuple[Cause, str] | None:
    delegations = [
        call for call in trace.tool_calls if not call.is_delegated and call.name == DELEGATION_TOOL
    ]
    subagent_type = f"sdlc:{agent}"
    if not any(call.input.get("subagent_type") == subagent_type for call in delegations):
        return Cause.DELEGATION, f"the main session never delegated to {subagent_type}"
    for call in delegations:
        effort = call.input.get("effort")
        if effort is not None and effort != level.value:
            return Cause.EFFORT, f"the main session delegated at {effort}"
    failed = sorted(
        grader.name
        for grader in run.graders
        if grader.name in DELEGATION_GRADERS and not grader.passed
    )
    if failed:
        return Cause.DELEGATION, f"failed: {', '.join(failed)}"
    return None


def _is_effort_confirmed(trace: Trace, level: EffortLevel) -> bool:
    return trace.main_session_efforts == {level.value} and trace.delegated_session_efforts == {
        level.value
    }
