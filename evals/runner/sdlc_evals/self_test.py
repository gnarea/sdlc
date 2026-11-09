"""The confinement self-test, which proves the policy before any run, without any model call."""

import json
import os
import secrets
import socket
import stat
from collections.abc import Callable, Iterator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from .code_check.suite import SCAFFOLD_SCRIPT, SCAFFOLD_SCRIPT_NAME
from .confinement import ConfinedResult, Confinement, Policy
from .working_tree import PinnedClaudeCode

PROBE_INTERPRETER = Path("/usr/bin/python3")
PROBE_SCRIPT = Path(__file__).with_name("self_test_probe.py")
ALLOWED_HOST = "api.anthropic.com"
REFUSED_HOST = "example.com"
SELF_TEST_TIMEOUT = timedelta(minutes=2)
MAX_RUNTIME_SOCKETS = 256
# Bash forks rather than execs a command that's followed by another, so the probe runs two levels
# below the root.
_LAUNCHER = 'bash -c \'"$@"; exit $?\' level-1 "$@"; exit $?'


@dataclass(frozen=True)
class CheckResult:
    check: str
    expectation: str
    outcome: str
    detail: str

    @property
    def is_passed(self) -> bool:
        return self.outcome == self.expectation


@dataclass(frozen=True)
class SelfTestReport:
    results: tuple[CheckResult, ...]
    problems: tuple[str, ...]

    @property
    def is_passed(self) -> bool:
        return not self.problems and all(result.is_passed for result in self.results)

    def failures(self) -> tuple[str, ...]:
        failed = tuple(
            f"{result.check}: expected {result.expectation}, got {result.outcome} {result.detail}".rstrip()
            for result in self.results
            if not result.is_passed
        )
        return self.problems + failed


@dataclass(frozen=True)
class SelfTestTargets:
    """What the probe must find denied, outside anything the policy grants."""

    operator_home: Path
    operator_config: tuple[Path, ...]
    worktree: Path
    temporary_root: Path
    invocation_directory: Path
    runtime_directory: Path | None


def run_self_test(
    confinement: Confinement,
    make_policy: Callable[[Path], Policy],
    writable_directory: Path,
    socket_directory: Path,
    targets: SelfTestTargets,
    claude: PinnedClaudeCode,
) -> SelfTestReport:
    if not PROBE_INTERPRETER.is_file():
        return SelfTestReport((), (f"The self-test needs {PROBE_INTERPRETER}",))
    _prepare_case(writable_directory)
    marker = f"sdlc-evals-self-test-{secrets.token_hex(8)}"
    with _listeners(socket_directory, marker) as listeners:
        policy = make_policy(writable_directory)
        spec = _make_spec(targets, listeners, policy.proxy_port, writable_directory, claude)
        result = _run_probe(confinement, policy, spec)
    return _make_report(result, spec)


@dataclass(frozen=True)
class _Listeners:
    other_port: int
    unix_socket: Path
    abstract_socket: str


def _make_spec(
    targets: SelfTestTargets,
    listeners: _Listeners,
    proxy_port: int,
    writable_directory: Path,
    claude: PinnedClaudeCode,
) -> dict[str, object]:
    runtime_sockets = _runtime_sockets(targets.runtime_directory)
    return {
        "denied_reads": [str(path) for path in _existing_reads(targets)],
        "denied_writes": [str(path) for path in _denied_writes(targets)],
        "marker": listeners.abstract_socket,
        "writable_directory": str(writable_directory),
        "other_port": listeners.other_port,
        "proxy_port": proxy_port,
        "allowed_host": ALLOWED_HOST,
        "refused_host": REFUSED_HOST,
        "unix_sockets": [str(listeners.unix_socket), *map(str, runtime_sockets)],
        "abstract_socket": listeners.abstract_socket,
        "scaffold_script": str(writable_directory / "case" / SCAFFOLD_SCRIPT_NAME),
        "workspace": str(writable_directory / "workspace"),
        "claude": str(claude.binary),
        "claude_version": claude.version,
    }


def _run_probe(confinement: Confinement, policy: Policy, spec: dict[str, object]) -> ConfinedResult:
    # The probe's source goes on the command line, since the policy grants nothing that holds the
    # wrapper.
    probe = PROBE_SCRIPT.read_text(encoding="utf-8")
    interpreter = [str(PROBE_INTERPRETER), "-I", "-c", probe, json.dumps(spec)]
    command = ["/usr/bin/bash", "-c", _LAUNCHER, "level-0", *interpreter]
    return confinement.run(policy, command, SELF_TEST_TIMEOUT, is_output_captured=True)


def _make_report(result: ConfinedResult, spec: dict[str, object]) -> SelfTestReport:
    results, problems = _parse_results(result.stdout)
    if result.is_timed_out:
        problems.append(f"The probe didn't finish within {SELF_TEST_TIMEOUT}")
    expected_count = _expected_check_count(spec)
    if len(results) != expected_count:
        problems.append(
            f"The probe reported {len(results)} of {expected_count} checks: "
            f"{result.stderr[-500:].strip()}"
        )
    return SelfTestReport(tuple(results), tuple(problems))


def find_runtime_directory(environment: Mapping[str, str]) -> Path | None:
    configured = environment.get("XDG_RUNTIME_DIR")
    candidate = Path(configured) if configured else Path("/run/user") / str(os.getuid())
    return candidate if candidate.is_dir() else None


def _prepare_case(writable_directory: Path) -> None:
    case = writable_directory / "case"
    (case / "fixture").mkdir(parents=True)
    (case / SCAFFOLD_SCRIPT_NAME).write_text(SCAFFOLD_SCRIPT, encoding="utf-8")
    (case / "fixture" / "copied.txt").write_text("copied\n", encoding="utf-8")
    (writable_directory / "workspace").mkdir()


@contextmanager
def _listeners(socket_directory: Path, marker: str) -> Iterator[_Listeners]:
    """Listen where a confined process must not reach: TCP on another port, and Unix sockets
    outside the policy.
    """
    socket_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    unix_path = socket_directory / "probe.sock"
    with ExitStack() as stack:
        tcp = stack.enter_context(socket.create_server(("127.0.0.1", 0)))
        unix = stack.enter_context(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM))
        unix.bind(str(unix_path))
        unix.listen()
        abstract = stack.enter_context(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM))
        abstract.bind("\0" + marker)
        abstract.listen()
        try:
            yield _Listeners(tcp.getsockname()[1], unix_path, marker)
        finally:
            unix_path.unlink(missing_ok=True)


def _existing_reads(targets: SelfTestTargets) -> list[Path]:
    home = targets.operator_home
    candidates = [
        home,
        home / ".claude",
        home / ".claude.json",
        home / ".ssh",
        *targets.operator_config,
        targets.worktree,
        *_first_file_in(targets.worktree),
        *find_git_metadata(targets.worktree),
    ]
    return [path for path in [*candidates, *_first_file_in(home / ".ssh")] if path.exists()]


def find_git_metadata(worktree: Path) -> tuple[Path, ...]:
    """The worktree's git metadata: its `.git` entry and, for a linked worktree, the directories
    it points to, found without running git.
    """
    dot_git = worktree / ".git"
    if not dot_git.is_file():
        return (dot_git,) if dot_git.exists() else ()
    found = [dot_git]
    pointer = dot_git.read_text(encoding="utf-8", errors="replace").strip()
    if pointer.startswith("gitdir:"):
        git_directory = (worktree / pointer.removeprefix("gitdir:").strip()).resolve()
        found.append(git_directory)
        common = git_directory / "commondir"
        if common.is_file():
            found.append((git_directory / common.read_text(encoding="utf-8").strip()).resolve())
    return tuple(found)


def _first_file_in(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    files = sorted(path for path in directory.iterdir() if path.is_file() and not path.is_symlink())
    return files[:1]


def _denied_writes(targets: SelfTestTargets) -> list[Path]:
    return [
        targets.worktree,
        targets.operator_home,
        targets.temporary_root,
        targets.invocation_directory,
    ]


def _runtime_sockets(runtime_directory: Path | None) -> list[Path]:
    if runtime_directory is None:
        return []
    found: list[Path] = []
    for root, directories, files in os.walk(runtime_directory, onerror=lambda _: None):
        for name in directories + files:
            path = Path(root) / name
            try:
                if stat.S_ISSOCK(path.lstat().st_mode):
                    found.append(path)
            except OSError:
                continue
        if MAX_RUNTIME_SOCKETS <= len(found):
            break
    return found[:MAX_RUNTIME_SOCKETS]


def _parse_results(stdout: str) -> tuple[list[CheckResult], list[str]]:
    results: list[CheckResult] = []
    problems: list[str] = []
    for line in stdout.splitlines():
        try:
            record = json.loads(line)
            results.append(
                CheckResult(
                    str(record["check"]),
                    str(record["expectation"]),
                    str(record["outcome"]),
                    str(record["detail"]),
                )
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            problems.append(f"The probe printed an unexpected line: {line[:200]!r}")
    return results, problems


def _expected_check_count(spec: dict[str, object]) -> int:
    per_item = sum(len(spec[key]) for key in ("denied_reads", "denied_writes", "unix_sockets"))  # type: ignore[arg-type]
    # The writable directory, two UDP families, another TCP port, two proxied hosts, the
    # abstract socket, and three programs.
    return per_item + 10
