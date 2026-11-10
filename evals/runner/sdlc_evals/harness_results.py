"""What the confined harness leaves behind for one harness call: its aggregate result, each run's
trace, and the sandboxes.

Everything here was written inside the confinement, so it's validated before use and bounded in
size.
"""

import json
import math
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .invocation_directory import ConfinedDirectory
from .state.ledger import WeeklyUtilisation

AGGREGATE_RESULT_FILE = "aggregate-result.json"
MAX_AGGREGATE_RESULT_BYTES = 64 * 1024 * 1024
# The harness kills a run whose output exceeds 64 MiB, so no trace can be larger.
MAX_TRACE_BYTES = 64 * 1024 * 1024
SANDBOX_PREFIX = "claude-eval-"


class HarnessResultUnreadable(Exception):
    """The harness left no aggregate result that the wrapper can read, so the call's runs are
    inconclusive.
    """


@dataclass(frozen=True)
class GraderVerdict:
    name: str
    passed: bool
    explanation: str


@dataclass(frozen=True)
class HarnessRun:
    """A run as the harness reported it."""

    case: str
    index: int
    passed: bool
    cost_usd: float
    error: str | None
    trace_path: Path | None
    started_at: str
    graders: tuple[GraderVerdict, ...]


@dataclass(frozen=True)
class HarnessResult:
    claude_version: str
    cost_usd: float
    partial_reason: str | None
    runs: tuple[HarnessRun, ...]


@dataclass(frozen=True)
class ToolCall:
    name: str
    input: dict[str, object]
    is_delegated: bool


@dataclass(frozen=True)
class Trace:
    """The facts that classification needs from one run's trace and session transcripts, and
    that a reading of the weekly utilisation needs from its own trace.
    """

    offered_tools: frozenset[str]
    tool_calls: tuple[ToolCall, ...]
    error_tool_results: tuple[str, ...]
    result_subtype: str | None
    is_api_error: bool
    main_models: frozenset[str]
    delegated_models: frozenset[str]
    main_session_efforts: frozenset[str]
    delegated_session_efforts: frozenset[str]
    utilisations: tuple[WeeklyUtilisation, ...]


def read_harness_result(directory: ConfinedDirectory) -> HarnessResult:
    path = directory.results / AGGREGATE_RESULT_FILE
    try:
        if MAX_AGGREGATE_RESULT_BYTES < path.stat().st_size:
            raise HarnessResultUnreadable(
                f"{AGGREGATE_RESULT_FILE} exceeds {MAX_AGGREGATE_RESULT_BYTES} bytes"
            )
        document = json.loads(path.read_text(encoding="utf-8"))
        return _decode_result(document)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise HarnessResultUnreadable(
            f"The harness left no readable {AGGREGATE_RESULT_FILE} ({error.__class__.__name__})"
        ) from error


def _decode_result(raw: object) -> HarnessResult:
    document = _mapping(raw)
    runs: list[HarnessRun] = []
    for case in map(_mapping, _list(document["cases"])):
        for index, run in enumerate(_list(_mapping(case["arms"])["with"]), start=1):
            runs.append(_decode_run(str(case["name"]), index, _mapping(run)))
    partial_reason = document.get("partialReason")
    return HarnessResult(
        claude_version=str(document["claudeVersion"]),
        cost_usd=_non_negative(document["costUsd"]),
        partial_reason=str(partial_reason) if partial_reason is not None else None,
        runs=tuple(runs),
    )


def _decode_run(case: str, index: int, run: dict[str, object]) -> HarnessRun:
    trace_path = run.get("tracePath")
    error = run.get("error")
    graders = tuple(
        GraderVerdict(
            name=str(grader["name"]),
            passed=grader["passed"] is True,
            explanation=str(grader.get("explanation", "")),
        )
        for grader in map(_mapping, _list(run.get("graders", [])))
    )
    return HarnessRun(
        case=case,
        index=index,
        passed=run["passed"] is True,
        cost_usd=_non_negative(run["costUsd"]),
        error=str(error) if error is not None else None,
        trace_path=Path(str(trace_path)) if trace_path else None,
        started_at=str(run.get("startedAt", "")),
        graders=graders,
    )


def collect_sandboxes(
    directory: ConfinedDirectory, result: HarnessResult | None, traces: Path
) -> dict[tuple[str, int], Path]:
    """Copy each run's trace and session transcripts out of its sandbox, then delete every sandbox.

    Returns where each run's copy went. A sandbox that no run claims is copied under its own name.
    """
    traces.mkdir(mode=0o700, parents=True, exist_ok=True)
    copies: dict[tuple[str, int], Path] = {}
    claimed: set[Path] = set()
    for run in result.runs if result else ():
        sandbox = _sandbox_of(directory, run.trace_path)
        if sandbox is None:
            continue
        destination = traces / run.case.replace("/", "--") / f"run-{run.index}"
        _copy_run_records(sandbox, destination)
        copies[(run.case, run.index)] = destination
        claimed.add(sandbox)
    for sandbox in _sandboxes(directory):
        if sandbox not in claimed:
            _copy_run_records(sandbox, traces / "unclaimed" / sandbox.name)
        _delete_sealed(sandbox)
    return copies


def measure_bytes(path: Path) -> int:
    """The space that a directory takes, unsealing any directory that the harness sealed so that it
    can be read.
    """
    total = 0
    for root, directories, files in _walk_unsealing(path):
        for name in directories + files:
            total += os.lstat(os.path.join(root, name)).st_blocks * 512
    return total


def _walk_unsealing(path: Path):  # noqa: ANN202 -- os.walk's own result type.
    os.chmod(path, 0o700, follow_symlinks=False)
    for root, directories, files in os.walk(path):
        for name in directories:
            # The harness seals a kept sandbox with mode 000, which the walk must undo
            # before it can descend.
            os.chmod(os.path.join(root, name), 0o700, follow_symlinks=False)
        yield root, directories, files


def read_trace(directory: Path) -> Trace:
    """Read a run's copied trace and transcripts. Anything malformed in them is left out, never
    trusted.
    """
    records = list(_read_json_lines(directory / "trace.jsonl"))
    init = next(
        (
            record
            for record in records
            if record.get("type") == "system" and record.get("subtype") == "init"
        ),
        {},
    )
    result = next((record for record in reversed(records) if record.get("type") == "result"), None)
    main_efforts, delegated_efforts = _read_transcript_efforts(directory / "projects")
    if isinstance(init.get("effort"), str):
        main_efforts |= {str(init["effort"])}
    return Trace(
        offered_tools=frozenset(str(tool) for tool in _list_or_empty(init.get("tools"))),
        tool_calls=tuple(_tool_calls(records)),
        error_tool_results=tuple(_error_tool_results(records)),
        result_subtype=str(result["subtype"]) if result and "subtype" in result else None,
        is_api_error=bool(
            result
            and result.get("is_error") is True
            and isinstance(result.get("api_error_status"), int)
        ),
        main_models=frozenset(_models(records, is_delegated=False)),
        delegated_models=frozenset(_models(records, is_delegated=True)),
        main_session_efforts=frozenset(main_efforts),
        delegated_session_efforts=frozenset(delegated_efforts),
        utilisations=tuple(_utilisations(records)),
    )


def _sandbox_of(directory: ConfinedDirectory, trace_path: Path | None) -> Path | None:
    if trace_path is None:
        return None
    sandbox = trace_path.parent.parent
    # A trace path that points anywhere else came from somewhere the wrapper doesn't control.
    if (
        sandbox.parent != directory.tmp
        or not sandbox.name.startswith(SANDBOX_PREFIX)
        or sandbox.is_symlink()
    ):
        return None
    return sandbox


def _sandboxes(directory: ConfinedDirectory) -> list[Path]:
    return sorted(
        path
        for path in directory.tmp.iterdir()
        if path.name.startswith(SANDBOX_PREFIX) and path.is_dir() and not path.is_symlink()
    )


def _copy_run_records(sandbox: Path, destination: Path) -> None:
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    trace = sandbox / "out" / "trace.jsonl"
    if trace.is_file() and not trace.is_symlink():
        shutil.copyfile(trace, destination / "trace.jsonl")
    projects = sandbox / "config" / "projects"
    if projects.is_dir() and not projects.is_symlink():
        shutil.copytree(projects, destination / "projects", symlinks=True, dirs_exist_ok=True)


def unseal(path: Path) -> None:
    """Undo the harness's sealing of the sandboxes it keeps, so that the operator can delete
    them.
    """
    for _ in _walk_unsealing(path):
        pass


def _delete_sealed(sandbox: Path) -> None:
    unseal(sandbox)
    shutil.rmtree(sandbox)


def _read_json_lines(path: Path):  # noqa: ANN202 -- a generator of decoded records.
    if not path.is_file() or path.is_symlink() or MAX_TRACE_BYTES < path.stat().st_size:
        return
    with path.open(encoding="utf-8", errors="replace") as file:
        for line in file:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def _tool_calls(records: list[dict[str, object]]):  # noqa: ANN202
    for record in records:
        if record.get("type") != "assistant":
            continue
        for block in _content_blocks(record):
            if block.get("type") == "tool_use" and isinstance(block.get("input"), dict):
                yield ToolCall(
                    name=str(block.get("name", "")),
                    input=block["input"],  # type: ignore[arg-type]
                    is_delegated=record.get("parent_tool_use_id") is not None,
                )


def _error_tool_results(records: list[dict[str, object]]):  # noqa: ANN202
    for record in records:
        if record.get("type") != "user":
            continue
        for block in _content_blocks(record):
            if block.get("type") == "tool_result" and block.get("is_error") is True:
                yield _text_of(block.get("content"))


def _models(records: list[dict[str, object]], *, is_delegated: bool):  # noqa: ANN202
    for record in records:
        if (
            record.get("type") != "assistant"
            or (record.get("parent_tool_use_id") is not None) != is_delegated
        ):
            continue
        model = _mapping_or_empty(record.get("message")).get("model")
        if isinstance(model, str) and not model.startswith("<"):
            yield model


def _utilisations(records: list[dict[str, object]]):  # noqa: ANN202
    for record in records:
        if record.get("type") != "rate_limit_event":
            continue
        windows = _mapping_or_empty(
            _mapping_or_empty(record.get("rate_limit_info")).get("unifiedWindows")
        )
        seven_day = _mapping_or_empty(windows.get("seven_day"))
        fraction, resets_at = seven_day.get("utilization"), seven_day.get("resetsAt")
        if (
            isinstance(fraction, bool)
            or not isinstance(fraction, (int, float))
            or not (math.isfinite(fraction) and 0 <= fraction)
            or isinstance(resets_at, bool)
            or not isinstance(resets_at, int)
        ):
            continue
        try:
            reset_time = datetime.fromtimestamp(resets_at, UTC)
        except (OverflowError, OSError, ValueError):
            continue
        yield WeeklyUtilisation(fraction=float(fraction), resets_at=reset_time)


def _read_transcript_efforts(projects: Path) -> tuple[set[str], set[str]]:
    main: set[str] = set()
    delegated: set[str] = set()
    if not projects.is_dir():
        return main, delegated
    for path in sorted(projects.rglob("*.jsonl")):
        efforts = delegated if "subagents" in path.relative_to(projects).parts else main
        for record in _read_json_lines(path):
            if record.get("type") != "assistant":
                continue
            for effort in (
                record.get("effort"),
                _mapping_or_empty(record.get("message")).get("effort"),
            ):
                if isinstance(effort, str):
                    efforts.add(effort)
    return main, delegated


def _content_blocks(record: dict[str, object]) -> list[dict[str, object]]:
    content = _mapping_or_empty(record.get("message")).get("content")
    return [block for block in _list_or_empty(content) if isinstance(block, dict)]


def _text_of(content: object) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(
        str(block.get("text", "")) for block in _list_or_empty(content) if isinstance(block, dict)
    )


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object (got {type(value).__name__})")
    return value


def _mapping_or_empty(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"Expected a JSON array (got {type(value).__name__})")
    return value


def _list_or_empty(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _non_negative(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"Expected a non-negative number (got {value!r})")
    return float(value)
