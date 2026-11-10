"""The processes that the wrapper starts, however they detach, so that none outlives its harness
call.

nono passes no signal on to the confined tree, and the harness's runs have process groups of their
own, so stopping nono alone would leave runs spending, possibly whilst the next harness call runs.
"""

import ctypes
import os
import signal
import subprocess
import time
from datetime import timedelta
from pathlib import Path

PR_SET_CHILD_SUBREAPER = 36
REAP_DEADLINE = timedelta(seconds=10)
_POLL_SECONDS = 0.05
_PROC = Path("/proc")


class SubreaperUnavailable(Exception):
    """The kernel refused to make the wrapper a subreaper, so orphaned processes could escape it.

    Retrying won't help: the suite needs Linux 3.4 or later.
    """


def configure_child_subreaper() -> None:
    """Have orphaned descendants re-parented to this process, rather than to init, so that they
    can still be found and stopped.
    """
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise SubreaperUnavailable(f"prctl(PR_SET_CHILD_SUBREAPER) failed ({os.strerror(error)})")


def find_descendants() -> frozenset[int]:
    """Every live process below this one."""
    children: dict[int, list[int]] = {}
    for entry in _PROC.iterdir():
        if not entry.name.isdigit():
            continue
        parent = _read_parent(entry)
        if parent is not None:
            children.setdefault(parent, []).append(int(entry.name))
    found: set[int] = set()
    pending = [os.getpid()]
    while pending:
        for child in children.get(pending.pop(), []):
            if child not in found:
                found.add(child)
                pending.append(child)
    return frozenset(found)


def stop_tree(root: subprocess.Popen[bytes], grace: timedelta) -> None:
    """Ask every descendant to stop, give them the grace period, then kill whatever remains."""
    _signal(find_descendants(), signal.SIGTERM)
    try:
        root.wait(timeout=grace.total_seconds())
    except subprocess.TimeoutExpired:
        # The root is reaped through its Popen, which would otherwise lose its exit status.
        root.kill()
        root.wait()
    kill_stragglers()


def kill_stragglers() -> None:
    """Kill every descendant still alive, and reap those that became this process's children."""
    deadline = time.monotonic() + REAP_DEADLINE.total_seconds()
    killed: set[int] = set()
    while (alive := find_descendants() - _zombies(killed)) and time.monotonic() < deadline:
        _signal(alive, signal.SIGKILL)
        killed |= alive
        time.sleep(_POLL_SECONDS)
        _reap(killed)
    _reap(killed)


def _read_parent(process: Path) -> int | None:
    try:
        status = (process / "stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    # The command name is in parentheses and may hold spaces, so the fields after it start at
    # the last closing parenthesis.
    fields = status[status.rindex(")") + 2 :].split()
    return int(fields[1]) if 1 < len(fields) else None


def _zombies(pids: set[int]) -> set[int]:
    zombies: set[int] = set()
    for pid in pids:
        try:
            status = (_PROC / str(pid) / "stat").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if status[status.rindex(")") + 2 :].startswith("Z"):
            zombies.add(pid)
    return zombies


def _signal(pids: frozenset[int] | set[int], signal_number: int) -> None:
    for pid in pids:
        try:
            os.kill(pid, signal_number)
        except ProcessLookupError:
            continue


def _reap(pids: set[int]) -> None:
    for pid in pids:
        try:
            os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            continue
