"""Each run's outcome: passed, failed, or inconclusive whenever something other than the agent
decided it.
"""

import enum
from collections.abc import Iterable
from dataclasses import dataclass

from .code_check import Case
from .harness_results import GraderVerdict, HarnessRun, Trace
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
    """Why a run is inconclusive, or, for a run that failed, the limit that cut it short."""

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


# A run cut short can fail, but never pass.
_PERMITTED_CAUSES: dict[Outcome, frozenset[Cause | None]] = {
    Outcome.PASSED: frozenset({None}),
    Outcome.FAILED: frozenset({None, Cause.TIMEOUT, Cause.TURN_LIMIT}),
    Outcome.INCONCLUSIVE: frozenset(Cause),
}


@dataclass(frozen=True)
class Classification:
    outcome: Outcome
    cause: Cause | None
    detail: str
    is_effort_confirmed: bool

    def __post_init__(self) -> None:
        if self.cause not in _PERMITTED_CAUSES[self.outcome]:
            raise ValueError(f"A {self.outcome} run can't have this cause (got {self.cause!r})")

    @property
    def is_cut_short_failure(self) -> bool:
        return self.outcome is Outcome.FAILED and self.cause is not None


def classify_run(
    run: HarnessRun, trace: Trace | None, case: Case, level: EffortLevel
) -> Classification:
    """Classify a run that the harness launched, from its record and its trace.

    A run cut short by its time or turn limit fails if it failed a prohibition of the trace, and
    nothing else makes it inconclusive. Otherwise, it's inconclusive.
    """
    if trace is None:
        return _inconclusive(
            Cause.HARNESS_ERROR, run.error or "no trace", is_effort_confirmed=False
        )
    is_effort_confirmed = _is_effort_confirmed(trace, level)
    cap = _find_cap(run, trace)
    run_check = (
        _check_completed_run(run, trace) if cap is None else _check_cut_short_run(run, trace, case)
    )
    inconclusive = (
        run_check or _check_delegation(trace, case.agent, level, run) or _check_effort(trace, level)
    )
    if inconclusive is not None:
        return _inconclusive(*inconclusive, is_effort_confirmed=is_effort_confirmed)
    if cap is not None:
        return _classify_cut_short_run(run, cap, case, is_effort_confirmed)
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


def _find_cap(run: HarnessRun, trace: Trace) -> tuple[Cause, str] | None:
    """The limit that cut the run short, if any, and what the harness said of it."""
    if run.error is not None and run.error.startswith(_TIMEOUT_PREFIX):
        return Cause.TIMEOUT, run.error
    if trace.result_subtype == _TURN_LIMIT_SUBTYPE:
        return Cause.TURN_LIMIT, run.error or trace.result_subtype
    return None


def _check_completed_run(run: HarnessRun, trace: Trace) -> tuple[Cause, str] | None:
    return (
        _check_harness_error(run, trace)
        or _check_trace_ending(trace)
        or _check_sandbox_denial(trace)
        or _check_graders(run.graders)
    )


def _check_cut_short_run(run: HarnessRun, trace: Trace, case: Case) -> tuple[Cause, str] | None:
    """Check a run cut short, whose error and missing result are the cap's doing, and whose only
    graders that count are its prohibitions of the trace.
    """
    return (
        _check_api_error(trace)
        or _check_sandbox_denial(trace)
        or _check_grader_errors(
            grader for grader in run.graders if grader.name in case.trace_prohibitions
        )
    )


def _check_harness_error(run: HarnessRun, trace: Trace) -> tuple[Cause, str] | None:
    if run.error is None:
        return None
    if trace.is_api_error or _API_ERROR_MARKER in run.error:
        return Cause.API_ERROR, run.error
    return Cause.HARNESS_ERROR, run.error


def _check_trace_ending(trace: Trace) -> tuple[Cause, str] | None:
    if trace.result_subtype is None:
        return Cause.HARNESS_ERROR, "the trace has no result"
    return _check_api_error(trace)


def _check_api_error(trace: Trace) -> tuple[Cause, str] | None:
    if trace.is_api_error:
        return Cause.API_ERROR, "the run ended on an API error"
    return None


def _check_sandbox_denial(trace: Trace) -> tuple[Cause, str] | None:
    for text in trace.error_tool_results:
        marker = next((marker for marker in SANDBOX_DENIAL_MARKERS if marker in text), None)
        if marker is not None:
            return Cause.SANDBOX_DENIAL, f"a tool failed with {marker}"
    return None


def _check_graders(graders: tuple[GraderVerdict, ...]) -> tuple[Cause, str] | None:
    if not graders:
        return Cause.HARNESS_ERROR, "the run wasn't graded"
    return _check_grader_errors(graders)


def _check_grader_errors(graders: Iterable[GraderVerdict]) -> tuple[Cause, str] | None:
    for grader in graders:
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


def _check_effort(trace: Trace, level: EffortLevel) -> tuple[Cause, str] | None:
    mismatch = sorted(
        (trace.main_session_efforts | trace.delegated_session_efforts) - {level.value}
    )
    if mismatch:
        return Cause.EFFORT, f"ran at {', '.join(mismatch)}"
    return None


def _classify_cut_short_run(
    run: HarnessRun, cap: tuple[Cause, str], case: Case, is_effort_confirmed: bool
) -> Classification:
    cause, detail = cap
    failed = sorted(
        grader.name
        for grader in run.graders
        if grader.name in case.trace_prohibitions and not grader.passed
    )
    if not failed:
        return _inconclusive(cause, detail, is_effort_confirmed=is_effort_confirmed)
    return Classification(
        Outcome.FAILED, cause, f"{detail}; failed: {', '.join(failed)}", is_effort_confirmed
    )


def _is_effort_confirmed(trace: Trace, level: EffortLevel) -> bool:
    return trace.main_session_efforts == {level.value} and trace.delegated_session_efforts == {
        level.value
    }
