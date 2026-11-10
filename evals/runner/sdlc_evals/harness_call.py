"""One harness call: the confined harness's run of one case at one level, and what the wrapper
makes of it afterwards.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TextIO

from .classification import (
    Cause,
    Classification,
    Outcome,
    classify_missing_run,
    classify_run,
    find_unexpected_tools,
)
from .code_check import Case
from .confinement import ConfinedResult, Confinement, Policy
from .harness import ConfinedCommand, HarnessCall, make_harness_command
from .harness_results import (
    HarnessResult,
    HarnessResultUnreadable,
    HarnessRun,
    collect_sandboxes,
    measure_bytes,
    read_harness_result,
    read_trace,
    unseal,
)
from .invocation_directory import InvocationDirectory
from .levels import EffortLevel
from .state.trust import ConfirmedTrust
from .terminal_status import end_status, show_status

# The statuses with which the harness ends a call on its own: met, below threshold, and partial.
HARNESS_EXIT_CODES = frozenset({0, 1, 2})
# The tools that the pinned harness offers each run, given the tools that the code check permits a
# case.
EXPECTED_OFFERED_TOOLS = frozenset(
    {
        "Task",
        "Agent",
        "Read",
        "Glob",
        "Grep",
        "Skill",
        "Write",
        "Edit",
        "NotebookEdit",
        "TaskStop",
        "ToolSearch",
    }
)


@dataclass(frozen=True)
class RunRecord:
    case: str
    index: int
    classification: Classification
    cost_usd: float
    main_models: tuple[str, ...]
    delegated_models: tuple[str, ...]
    trace_directory: Path | None


@dataclass(frozen=True)
class CallRecord:
    case: str
    level: EffortLevel
    cap_usd: float
    spend_usd: float
    command: ConfinedCommand
    inherited_variables: tuple[str, ...]
    harness_exit_code: int | None
    is_harness_timed_out: bool
    harness_version: str | None
    harness_partial_reason: str | None
    space_bytes: int
    unexpected_tools: frozenset[str]
    runs: tuple[RunRecord, ...]

    @property
    def is_voided(self) -> bool:
        return bool(self.unexpected_tools)

    @property
    def is_spend_capped(self) -> bool:
        return self.harness_partial_reason == "cost_ceiling"


@dataclass(frozen=True)
class CallContext:
    """What every harness call of an invocation, and every reading between them, shares."""

    confinement: Confinement
    claude: Path
    plugin: Path
    trust: ConfirmedTrust
    directory: InvocationDirectory
    proxy_url: str
    make_policy: Callable[[Path, dict[str, str]], Policy]
    progress: TextIO


def run_harness_call(context: CallContext, call: HarnessCall) -> CallRecord:
    directory = context.directory.call(call.case.name, call.level)
    directory.make()
    command = make_harness_command(
        context.claude, context.plugin, context.trust, directory, call, context.proxy_url
    )
    policy = context.make_policy(directory.path, command.environment)
    show_status(context.progress, f"Running {call.case.name} at {call.level}")
    try:
        confined = context.confinement.run(
            policy, list(command.argv), command.timeout, output_log=directory.path / "harness.log"
        )
    except KeyboardInterrupt:
        unseal(directory.tmp)
        raise
    try:
        result: HarnessResult | None = read_harness_result(directory)
    except HarnessResultUnreadable as error:
        end_status(context.progress)
        context.progress.write(f"{error}\n")
        result = None
    space_bytes = measure_bytes(directory.tmp)
    copies = collect_sandboxes(directory, result, context.directory.traces(call.level))
    runs, unexpected_tools = _classify_runs(call, result, copies)
    return CallRecord(
        case=call.case.name,
        level=call.level,
        cap_usd=call.cap_usd,
        spend_usd=_charge_usd(confined, result, call.cap_usd),
        command=command,
        inherited_variables=policy.inherited_variables,
        harness_exit_code=confined.exit_code,
        is_harness_timed_out=confined.is_timed_out,
        harness_version=result.claude_version if result else None,
        harness_partial_reason=result.partial_reason if result else None,
        space_bytes=space_bytes,
        unexpected_tools=unexpected_tools,
        runs=tuple(run.record for run in runs),
    )


def _charge_usd(confined: ConfinedResult, result: HarnessResult | None, cap_usd: float) -> float:
    # What a call spent is unknown when its harness timed out, exited abnormally, or left no
    # readable result, so the call is charged all it was allowed.
    if result is None or confined.is_timed_out or confined.exit_code not in HARNESS_EXIT_CODES:
        return max(cap_usd, result.cost_usd if result else 0.0)
    return result.cost_usd


@dataclass(frozen=True)
class _ClassifiedRun:
    record: RunRecord
    unexpected_tools: frozenset[str]


def _classify_runs(
    call: HarnessCall, result: HarnessResult | None, copies: dict[tuple[str, int], Path]
) -> tuple[list[_ClassifiedRun], frozenset[str]]:
    reported = {(run.case, run.index): run for run in result.runs} if result else {}
    missing = "the harness stopped launching runs" if result else "the harness left no result"
    runs = [
        _classify_one(
            call.case, index, reported.get((call.case.name, index)), copies, call.level, missing
        )
        for index in range(1, call.runs + 1)
    ]
    unexpected_tools = frozenset().union(*(run.unexpected_tools for run in runs))
    if not unexpected_tools:
        return runs, unexpected_tools
    voided = Classification(
        Outcome.INCONCLUSIVE, Cause.UNEXPECTED_TOOL, ", ".join(sorted(unexpected_tools)), False
    )
    return [
        replace(run, record=replace(run.record, classification=voided)) for run in runs
    ], unexpected_tools


def _classify_one(
    case: Case,
    index: int,
    run: HarnessRun | None,
    copies: dict[tuple[str, int], Path],
    level: EffortLevel,
    missing: str,
) -> _ClassifiedRun:
    trace_directory = copies.get((case.name, index))
    if run is None:
        record = RunRecord(case.name, index, classify_missing_run(missing), 0.0, (), (), None)
        return _ClassifiedRun(record, frozenset())
    trace = read_trace(trace_directory) if trace_directory else None
    record = RunRecord(
        case=case.name,
        index=index,
        classification=classify_run(run, trace, case, level),
        cost_usd=run.cost_usd,
        main_models=tuple(sorted(trace.main_models)) if trace else (),
        delegated_models=tuple(sorted(trace.delegated_models)) if trace else (),
        trace_directory=trace_directory,
    )
    if trace is None:
        return _ClassifiedRun(record, frozenset())
    unexpected_tools = find_unexpected_tools(trace, EXPECTED_OFFERED_TOOLS)
    return _ClassifiedRun(record, unexpected_tools)
