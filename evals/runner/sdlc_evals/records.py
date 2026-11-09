"""What an invocation leaves for the operator: the manifest, the summary, and the exit status."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .classification import Outcome
from .confinement import NONO_VERSION
from .credentials import CredentialSource
from .egress_proxy import Refusal, UpstreamFailure
from .exit_status import ExitStatus
from .harness import JUDGE_MODEL, MODEL, CaseSelection
from .harness_call import CallRecord
from .invocation_calls import StopReason
from .levels import EffortLevel
from .spend import WEEKLY_BUDGET_POINTS, ApiKeyBudget, SubscriptionBudget, week_charge_points
from .state.ledger import LedgerEntry, WeeklyUtilisation
from .working_tree import CodeRecord, FilesRecord

MANIFEST_FORMAT_VERSION = 2
# A case meets the threshold at a level when this share of its completed runs passed.
PASS_THRESHOLD = 1.0
_EXIT_STATUS_BY_STOP_REASON = {
    StopReason.INTERRUPTED: ExitStatus.INTERRUPTED,
    StopReason.NO_SPACE: ExitStatus.REFUSED,
    StopReason.READING_FAILED: ExitStatus.SPEND_UNMEASURED,
    StopReason.WEEKLY_BUDGET: ExitStatus.SPEND_CAP,
    StopReason.SPEND_CAP: ExitStatus.SPEND_CAP,
}


@dataclass(frozen=True)
class InvocationRecord:
    invocation_id: str
    started_at: datetime
    finished_at: datetime
    directory: Path
    worktree: Path
    code: CodeRecord
    claude_code_version: str
    credential_source: CredentialSource
    selection: CaseSelection
    levels_requested: tuple[EffortLevel, ...]
    self_test_checks: int
    allowed_hosts: frozenset[str]
    calls: tuple[CallRecord, ...]
    readings: tuple[WeeklyUtilisation, ...]
    spend: LedgerEntry | None
    budget: SubscriptionBudget | ApiKeyBudget | None
    proxy_refusals: tuple[Refusal, ...]
    proxy_failures: tuple[UpstreamFailure, ...]
    stop_reason: StopReason | None


@dataclass(frozen=True)
class CaseLevelCount:
    case: str
    level: EffortLevel
    passed: int
    completed: int
    inconclusive: int

    @property
    def is_below_threshold(self) -> bool:
        return 0 < self.completed and self.passed / self.completed < PASS_THRESHOLD


def count_passes(calls: tuple[CallRecord, ...]) -> tuple[CaseLevelCount, ...]:
    counts: list[CaseLevelCount] = []
    for call in calls:
        outcomes = Counter(run.classification.outcome for run in call.runs)
        passed, failed = outcomes[Outcome.PASSED], outcomes[Outcome.FAILED]
        counts.append(
            CaseLevelCount(
                call.case, call.level, passed, passed + failed, outcomes[Outcome.INCONCLUSIVE]
            )
        )
    return tuple(counts)


def decide_exit_status(record: InvocationRecord) -> ExitStatus:
    if record.stop_reason in _EXIT_STATUS_BY_STOP_REASON:
        return _EXIT_STATUS_BY_STOP_REASON[record.stop_reason]
    counts = count_passes(record.calls)
    if any(count.is_below_threshold for count in counts):
        return ExitStatus.BELOW_THRESHOLD
    if record.stop_reason is not None or any(
        count.inconclusive or not count.completed for count in counts
    ):
        return ExitStatus.INCONCLUSIVE
    return ExitStatus.THRESHOLD_MET


def render_manifest(record: InvocationRecord, exit_status: ExitStatus) -> dict[str, object]:
    return {
        "format_version": MANIFEST_FORMAT_VERSION,
        "invocation_id": record.invocation_id,
        "started_at": record.started_at.isoformat(),
        "finished_at": record.finished_at.isoformat(),
        "worktree": str(record.worktree),
        "code": {
            "commit": record.code.commit,
            "snapshot": _encode_files(record.code.snapshot),
            "wrapper": _encode_files(record.code.wrapper),
        },
        "claude_code_version": record.claude_code_version,
        "nono_version": NONO_VERSION,
        "model": MODEL,
        "judge_model": JUDGE_MODEL,
        "credential_source": record.credential_source.value,
        "subset": {
            "agents": list(record.selection.agents),
            "levels": [level.value for level in record.levels_requested],
            "case": record.selection.case_name,
            "runs_per_case": record.selection.runs_per_case,
        },
        "self_test": {"passed": True, "checks": record.self_test_checks},
        "proxy": {
            "allowed_hosts": sorted(record.allowed_hosts),
            "refusals": [_encode_refusal(refusal) for refusal in record.proxy_refusals],
            "upstream_failures": [
                {"time": failure.time.isoformat(), "host": failure.host, "error": failure.error}
                for failure in record.proxy_failures
            ],
        },
        "readings": [_encode_utilisation(reading) for reading in record.readings],
        "spend": _encode_spend(record),
        "calls": [_encode_call(call) for call in record.calls],
        "stop_reason": record.stop_reason.value if record.stop_reason else None,
        "exit_status": int(exit_status),
    }


def render_summary(record: InvocationRecord, exit_status: ExitStatus) -> str:
    lines = [
        f"Agent eval suite, invocation {record.invocation_id}",
        f"Results: {record.directory}",
        f"Code: {record.code.commit}{_describe_changes(record.code)}",
        f"Claude Code {record.claude_code_version}, {MODEL} (judge {JUDGE_MODEL}), credential: {record.credential_source}",
        "",
        "Pass counts (completed runs):",
    ]
    counts = count_passes(record.calls)
    lines += [
        f"  {count.case}  {count.level}  {count.passed}/{count.completed}"
        + (f"  ({count.inconclusive} inconclusive)" if count.inconclusive else "")
        for count in counts
    ] or ["  none"]
    lines += ["", "Inconclusive runs:"]
    lines += [
        f"  {run.case}  {call.level}  run {run.index}: {run.classification.cause} ({run.classification.detail})"
        for call in record.calls
        for run in call.runs
        if run.classification.outcome is Outcome.INCONCLUSIVE
    ] or ["  none"]
    runs = [run for call in record.calls for run in call.runs]
    confirmed = sum(1 for run in runs if run.classification.is_effort_confirmed)
    lines += ["", f"Effort level confirmed for {confirmed} of {len(runs)} run(s)."]
    lines += ["", "Proxy refusals:"]
    refusals = Counter(
        f"{refusal.host or '(none)'} ({refusal.reason})" for refusal in record.proxy_refusals
    )
    lines += [f"  {target} × {count}" for target, count in sorted(refusals.items())] or ["  none"]
    lines += ["", "Spend:", *_describe_spend(record)]
    if record.stop_reason:
        lines += ["", _describe_stop(record)]
    lines += ["", f"Exit status: {int(exit_status)} ({exit_status.name.lower().replace('_', ' ')})"]
    return "\n".join(lines) + "\n"


def render_brief(record: InvocationRecord, exit_status: ExitStatus, summary: Path) -> str:
    """What the terminal shows at the end: the cases that failed, the tally of runs, and where
    the summary is.
    """
    by_case: dict[str, list[CaseLevelCount]] = {}
    for count in count_passes(record.calls):
        by_case.setdefault(count.case, []).append(count)
    lines = [
        f"{case}: "
        + ", ".join(f"{count.level} {count.passed}/{count.completed}" for count in counts)
        for case, counts in by_case.items()
        if any(count.passed < count.completed for count in counts)
    ]
    outcomes = Counter(run.classification.outcome for call in record.calls for run in call.runs)
    causes = Counter(
        str(run.classification.cause)
        for call in record.calls
        for run in call.runs
        if run.classification.outcome is Outcome.INCONCLUSIVE
    )
    tally = (
        f"{outcomes[Outcome.PASSED]} of {outcomes.total()} runs passed, "
        f"{outcomes[Outcome.FAILED]} failed, {outcomes[Outcome.INCONCLUSIVE]} inconclusive"
    )
    if causes:
        tally += " (" + ", ".join(f"{cause} × {n}" for cause, n in sorted(causes.items())) + ")"
    lines.append(tally)
    if record.stop_reason:
        lines.append(_describe_stop(record))
    lines.append(
        f"Exit status {int(exit_status)} ({exit_status.name.lower().replace('_', ' ')}). "
        f"Details: {summary}"
    )
    return "\n".join(lines) + "\n"


def _describe_spend(record: InvocationRecord) -> list[str]:
    usd_by_level: dict[EffortLevel, float] = {}
    for call in record.calls:
        usd_by_level[call.level] = usd_by_level.get(call.level, 0.0) + call.spend_usd
    lines = [f"  {level}: ${usd:.2f} at list price" for level, usd in usd_by_level.items()]
    entry, budget = record.spend, record.budget
    if entry is None or budget is None:
        return lines or ["  none"]
    if isinstance(budget, ApiKeyBudget):
        return lines + [
            f"  Charged ${budget.spent_usd:.2f} of the invocation's ${budget.cap_usd:.2f} cap."
        ]
    for index, week in enumerate(entry.weeks):
        start = f"{week.first_fraction:.0%}" if index == 0 else "0% at the reset"
        lines.append(
            f"  Weekly utilisation {start} → {week.last_fraction:.0%} (week resetting "
            f"{week.resets_at:%Y-%m-%d %H:%M %Z}): charged "
            f"{_format_points(week_charge_points(entry, index))}"
        )
    if budget.provisional_invocations:
        holders = ", ".join(budget.provisional_invocations)
        return lines + [f"  This week's budget is held by the provisional charge of {holders}."]
    return lines + [
        f"  This week's eval invocations have used {budget.spent_points:g} of their "
        f"{WEEKLY_BUDGET_POINTS:g} points."
    ]


def _describe_stop(record: InvocationRecord) -> str:
    levels_by_case: dict[str, set[EffortLevel]] = {}
    for call in record.calls:
        levels_by_case.setdefault(call.case, set()).add(call.level)
    covered = sum(
        1 for levels in levels_by_case.values() if set(record.levels_requested) <= levels
    )
    description = (
        f"Stopped early: {record.stop_reason}. {covered} of {len(record.selection.cases)} "
        "case(s) ran at every level."
    )
    if record.spend is not None and record.spend.is_provisional:
        description += (
            " Its provisional charge blocks the subscription until the owner checks the usage "
            "and clears it with the clear-charge command."
        )
    return description


def _format_points(points: float) -> str:
    return f"{points:g} point{'' if points == 1 else 's'}"


def _encode_spend(record: InvocationRecord) -> dict[str, object] | None:
    entry, budget = record.spend, record.budget
    if entry is None or budget is None:
        return None
    encoded: dict[str, object] = {
        "list_price_usd": entry.list_price_usd,
        "is_provisional": entry.is_provisional,
        "weeks": [
            {
                "resets_at": week.resets_at.isoformat(),
                "first_fraction": week.first_fraction,
                "last_fraction": week.last_fraction,
                "charged_points": week_charge_points(entry, index),
            }
            for index, week in enumerate(entry.weeks)
        ],
    }
    if isinstance(budget, ApiKeyBudget):
        return encoded | {"cap_usd": budget.cap_usd}
    return encoded | {
        "week_spent_points": budget.spent_points,
        "weekly_budget_points": WEEKLY_BUDGET_POINTS,
        "provisional_invocations": list(budget.provisional_invocations),
    }


def _encode_call(call: CallRecord) -> dict[str, object]:
    return {
        "case": call.case,
        "level": call.level.value,
        "environment": call.command.environment,
        "inherited_variables": list(call.inherited_variables),
        "argv": list(call.command.argv),
        "cap_usd": call.cap_usd,
        "spend_usd": call.spend_usd,
        "harness_exit_code": call.harness_exit_code,
        "is_harness_timed_out": call.is_harness_timed_out,
        "harness_version": call.harness_version,
        "harness_partial_reason": call.harness_partial_reason,
        "space_bytes": call.space_bytes,
        "unexpected_tools": sorted(call.unexpected_tools),
        "runs": [
            {
                "case": run.case,
                "index": run.index,
                "outcome": run.classification.outcome.value,
                "cause": run.classification.cause.value if run.classification.cause else None,
                "detail": run.classification.detail,
                "is_effort_confirmed": run.classification.is_effort_confirmed,
                "cost_usd": run.cost_usd,
                "models": {"main": list(run.main_models), "delegated": list(run.delegated_models)},
                "trace": str(run.trace_directory) if run.trace_directory else None,
            }
            for run in call.runs
        ],
    }


def _encode_files(files: FilesRecord) -> dict[str, object]:
    return {"differs_from_commit": bool(files.diff), "diff": files.diff, "sha256": files.sha256}


def _describe_changes(code: CodeRecord) -> str:
    changed = [
        name for name, files in (("plugin", code.snapshot), ("wrapper", code.wrapper)) if files.diff
    ]
    if not changed:
        return f" (snapshot {code.snapshot.sha256[:12]})"
    return f", with uncommitted changes to the {' and the '.join(changed)} (snapshot {code.snapshot.sha256[:12]})"


def _encode_refusal(refusal: Refusal) -> dict[str, object]:
    return {
        "time": refusal.time.isoformat(),
        "reason": refusal.reason.value,
        "host": refusal.host,
        "port": refusal.port,
    }


def _encode_utilisation(utilisation: WeeklyUtilisation) -> dict[str, object]:
    return {"fraction": utilisation.fraction, "resets_at": utilisation.resets_at.isoformat()}
