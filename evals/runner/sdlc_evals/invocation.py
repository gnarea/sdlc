"""An invocation: everything the wrapper does from the operator's command to the exit status."""

import functools
import json
import os
import secrets
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import TextIO

from .code_check import Refused, Suite, check_plugin_snapshot
from .confinement import Confinement, NonoBinary, NonoUnavailable, Policy
from .credentials import Credential, CredentialUnavailable, load_credential
from .egress_proxy import EgressProxy
from .exit_status import ExitStatus
from .harness import CaseSelection, InvalidSelection
from .harness_call import CallContext, run_harness_call
from .invocation_calls import CallPlan, run_calls
from .invocation_directory import InvocationDirectory, UnsafeTemporaryRoot
from .levels import EffortLevel
from .process_tree import SubreaperUnavailable, configure_child_subreaper
from .records import (
    InvocationRecord,
    decide_exit_status,
    render_brief,
    render_manifest,
    render_summary,
)
from .self_test import (
    SelfTestTargets,
    find_git_metadata,
    find_runtime_directory,
    run_self_test,
)
from .snapshot import snapshot_plugin
from .spend import ApiKeyChoice, SubscriptionChoice
from .state.ledger import find_provisional_charges
from .state.store import InvocationLockHeld, StateStore, StateStoreUnusable
from .state.trust import ConfirmedTrust, confirm_trust
from .terminal_status import end_status
from .utilisation_reading import take_reading
from .working_tree import (
    ClaudeCodeUnavailable,
    CodeRecord,
    CodeUnrecordable,
    PinnedClaudeCode,
    find_pinned_claude_code,
    find_root,
    record_code,
)

ALLOWED_HOSTS = frozenset({"api.anthropic.com"})
# What the confined tree finds on its PATH: bash and cp for the fixture-copying step, and git for
# the harness.
CONFINED_SEARCH_PATH = "/usr/bin:/bin"
DEFAULT_TEMPORARY_ROOT = Path("/tmp")
# Until the pilot measures the space a run takes, each is assumed to take this much whilst its
# harness call lasts.
SPACE_PER_RUN_ESTIMATE_BYTES = 4 * 1024 * 1024
# Left free for the other sessions that share the temporary root.
FREE_SPACE_RESERVE_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class InvocationOptions:
    agents: tuple[str, ...] | None
    levels: tuple[EffortLevel, ...]
    case_names: frozenset[str] | None
    runs_per_case: int | None
    credential: SubscriptionChoice | ApiKeyChoice


@dataclass(frozen=True)
class Operator:
    """The operator's side of the invocation: their environment, their clock, and their terminal."""

    environment: Mapping[str, str]
    account_home: Path
    now: Callable[[], datetime]
    open_terminal: Callable[[], TextIO]
    progress: TextIO


class StartRefused(Exception):
    """The wrapper refuses to start. The message says why, and what would let it start."""


_REFUSAL_CAUSES = (
    SubreaperUnavailable,
    StateStoreUnusable,
    InvocationLockHeld,
    ClaudeCodeUnavailable,
    NonoUnavailable,
    CredentialUnavailable,
    UnsafeTemporaryRoot,
    CodeUnrecordable,
    InvalidSelection,
)


def run_invocation(options: InvocationOptions, operator: Operator) -> ExitStatus:
    try:
        configure_child_subreaper()
        store = StateStore.init(operator.account_home)
        worktree = find_root()
        with store.lock_invocation(
            f"pid {os.getpid()}, worktree {worktree}, since {operator.now().isoformat()}"
        ):
            return _run_locked(options, operator, store, worktree)
    except (*_REFUSAL_CAUSES, StartRefused) as error:
        operator.progress.write(f"Refused to start: {error}\n")
        return ExitStatus.REFUSED


def _run_locked(
    options: InvocationOptions, operator: Operator, store: StateStore, worktree: Path
) -> ExitStatus:
    prepared = _prepare(options, operator, store, worktree)
    with EgressProxy.start(ALLOWED_HOSTS, now=operator.now) as proxy:
        variable = prepared.credential.environment_variable
        context = CallContext(
            confinement=prepared.confinement,
            claude=prepared.claude.binary,
            plugin=prepared.plugin,
            trust=prepared.trust,
            directory=prepared.directory,
            proxy_url=proxy.url,
            make_policy=lambda writable, environment: prepared.policy_base.make(
                writable, proxy.port, environment, (variable,)
            ),
            progress=operator.progress,
        )
        invocation_id = secrets.token_hex(8)
        outcome = run_calls(
            CallPlan(prepared.selection, options.levels, options.credential),
            store,
            invocation_id,
            run_call=functools.partial(run_harness_call, context),
            take_reading=lambda index: take_reading(context, index, operator.now),
            has_room_for=functools.partial(_has_room_for, prepared.directory),
            now=operator.now,
        )
        record = InvocationRecord(
            invocation_id=invocation_id,
            started_at=prepared.started_at,
            finished_at=operator.now(),
            directory=prepared.directory.path,
            worktree=worktree,
            code=prepared.code,
            claude_code_version=prepared.claude.version,
            credential_source=prepared.credential.source,
            selection=prepared.selection,
            levels_requested=options.levels,
            self_test_checks=prepared.self_test_checks,
            allowed_hosts=ALLOWED_HOSTS,
            calls=outcome.calls,
            readings=outcome.readings,
            spend=outcome.spend,
            budget=outcome.budget,
            proxy_refusals=proxy.refusals(),
            proxy_failures=proxy.upstream_failures(),
            stop_reason=outcome.stop_reason,
        )
    return _write_records(record, prepared.directory, operator.progress)


@dataclass(frozen=True)
class _Prepared:
    """Everything that's settled before the first harness call: what runs, under which policy, and
    why.
    """

    started_at: datetime
    claude: PinnedClaudeCode
    credential: Credential
    directory: InvocationDirectory
    plugin: Path
    selection: CaseSelection
    trust: ConfirmedTrust
    code: CodeRecord
    confinement: Confinement
    policy_base: _PolicyBase
    self_test_checks: int


def _prepare(
    options: InvocationOptions, operator: Operator, store: StateStore, worktree: Path
) -> _Prepared:
    """Take every step that can refuse the invocation, in the order the architecture sets."""
    started_at = operator.now()
    claude = find_pinned_claude_code(worktree)
    nono = NonoBinary.locate(operator.environment.get("PATH", ""))
    credential = load_credential(
        options.credential.source, store, operator.environment, started_at
    )
    _require_unblocked_budget(options.credential, store, started_at)
    directory = InvocationDirectory.make(_temporary_root(operator.environment), worktree)
    operator.progress.write(f"Invocation directory: {directory.path}\n")
    plugin = snapshot_plugin(worktree, directory.path / "plugin")
    # Recorded from the snapshot, at once, so that the record matches what the runs read.
    code = record_code(worktree, plugin)
    selection = CaseSelection.make(
        _require_code_check(worktree, plugin),
        options.agents,
        options.case_names,
        options.runs_per_case,
    )
    trust = confirm_trust(store, worktree, operator.now(), operator.open_terminal)
    if trust is None:
        raise StartRefused(f"The operator didn't confirm trust in {worktree} at its terminal")
    secrets_by_variable = {credential.environment_variable: credential.value}
    confinement = Confinement(nono, directory.nono_state, CONFINED_SEARCH_PATH, secrets_by_variable)
    policy_base = _PolicyBase(
        readable=(plugin, claude.binary.parent.parent), denied=_denied_paths(operator, worktree)
    )
    self_test_checks = _require_self_test(
        confinement, policy_base, directory, worktree, claude, operator
    )
    return _Prepared(
        started_at=started_at,
        claude=claude,
        credential=credential,
        directory=directory,
        plugin=plugin,
        selection=selection,
        trust=trust,
        code=code,
        confinement=confinement,
        policy_base=policy_base,
        self_test_checks=self_test_checks,
    )


def _require_unblocked_budget(
    credential: SubscriptionChoice | ApiKeyChoice, store: StateStore, now: datetime
) -> None:
    if not isinstance(credential, SubscriptionChoice):
        return
    charges = find_provisional_charges(store, now)
    if not charges:
        return
    holders = ", ".join(
        f"{charge.invocation_id} (since {charge.recorded_at:%Y-%m-%d %H:%M %Z})"
        for charge in charges
    )
    raise StartRefused(
        f"A provisional charge holds the subscription's weekly budget for the evals ({holders}): "
        "the owner must check the usage, then clear it with the clear-charge command"
    )


def _has_room_for(directory: InvocationDirectory, runs: int) -> bool:
    needed = runs * SPACE_PER_RUN_ESTIMATE_BYTES + FREE_SPACE_RESERVE_BYTES
    return needed <= shutil.disk_usage(directory.path).free


def _require_code_check(worktree: Path, plugin: Path) -> Suite:
    result = check_plugin_snapshot(worktree, plugin)
    if isinstance(result, Refused):
        findings = "\n".join(f"  {finding}" for finding in result.findings)
        raise StartRefused(f"The code check refused {len(result.findings)} item(s):\n{findings}")
    return result


@dataclass(frozen=True)
class _PolicyBase:
    readable: tuple[Path, ...]
    denied: tuple[Path, ...]

    def make(
        self,
        writable: Path,
        proxy_port: int,
        environment: Mapping[str, str],
        inherited: tuple[str, ...],
    ) -> Policy:
        return Policy(
            readable_directories=self.readable,
            writable_directory=writable,
            proxy_port=proxy_port,
            denied_paths=self.denied,
            environment=dict(environment),
            inherited_variables=inherited,
        )


def _require_self_test(
    confinement: Confinement,
    policy_base: _PolicyBase,
    directory: InvocationDirectory,
    worktree: Path,
    claude: PinnedClaudeCode,
    operator: Operator,
) -> int:
    environment = operator.environment
    configured = environment.get("CLAUDE_CONFIG_DIR")
    targets = SelfTestTargets(
        operator_home=operator.account_home,
        operator_config=(Path(configured),) if configured else (),
        worktree=worktree,
        temporary_root=directory.path.parent,
        invocation_directory=directory.path,
        runtime_directory=find_runtime_directory(environment),
    )
    directory.self_test.mkdir(mode=0o700)
    # The self-test has a proxy of its own, so that the refusal it provokes isn't reported as
    # the runs'.
    with EgressProxy.start(ALLOWED_HOSTS) as proxy:
        report = run_self_test(
            confinement=replace(confinement, inherited_environment={}),
            make_policy=lambda writable: policy_base.make(
                writable,
                proxy.port,
                {"HOME": str(writable), "TMPDIR": str(writable), "LANG": "C.UTF-8"},
                (),
            ),
            writable_directory=directory.self_test,
            socket_directory=directory.wrapper_sockets,
            targets=targets,
            claude=claude,
        )
    if not report.is_passed:
        failures = "\n".join(f"  {failure}" for failure in report.failures())
        raise StartRefused(f"The confinement self-test failed:\n{failures}")
    return len(report.results)


def _denied_paths(operator: Operator, worktree: Path) -> tuple[Path, ...]:
    """Paths that nono must refuse to grant, should any grant ever cover them."""
    home = operator.account_home
    candidates = [home / ".claude", home / ".claude.json", home / ".ssh", home / ".gnupg"]
    candidates += find_git_metadata(worktree)
    if configured := operator.environment.get("CLAUDE_CONFIG_DIR"):
        candidates.append(Path(configured))
    if runtime_directory := find_runtime_directory(operator.environment):
        candidates.append(runtime_directory)
    return tuple(path for path in candidates if path.exists())


def _temporary_root(environment: Mapping[str, str]) -> Path:
    configured = environment.get("TMPDIR")
    return Path(configured) if configured else DEFAULT_TEMPORARY_ROOT


def _write_records(
    record: InvocationRecord, directory: InvocationDirectory, progress: TextIO
) -> ExitStatus:
    exit_status = decide_exit_status(record)
    directory.manifest.write_text(
        json.dumps(render_manifest(record, exit_status), indent=2) + "\n", encoding="utf-8"
    )
    summary = render_summary(record, exit_status)
    directory.summary.write_text(summary, encoding="utf-8")
    end_status(progress)
    progress.write(render_brief(record, exit_status, directory.summary))
    return exit_status


def self_test_only(operator: Operator) -> ExitStatus:
    """Check the confinement without any model call, any spend, or any trust answer."""
    try:
        configure_child_subreaper()
        worktree = find_root()
        claude = find_pinned_claude_code(worktree)
        nono = NonoBinary.locate(operator.environment.get("PATH", ""))
        directory = InvocationDirectory.make(_temporary_root(operator.environment), worktree)
        plugin = snapshot_plugin(worktree, directory.path / "plugin")
        confinement = Confinement(nono, directory.nono_state, CONFINED_SEARCH_PATH)
        policy_base = _PolicyBase(
            readable=(plugin, claude.binary.parent.parent),
            denied=_denied_paths(operator, worktree),
        )
        checks = _require_self_test(confinement, policy_base, directory, worktree, claude, operator)
    except (*_REFUSAL_CAUSES, StartRefused) as error:
        operator.progress.write(f"{error}\n")
        return ExitStatus.REFUSED
    operator.progress.write(
        f"The confinement self-test passed all {checks} checks ({directory.path}).\n"
    )
    return ExitStatus.THRESHOLD_MET


__all__ = [
    "InvocationOptions",
    "Operator",
    "StartRefused",
    "run_invocation",
    "self_test_only",
]
