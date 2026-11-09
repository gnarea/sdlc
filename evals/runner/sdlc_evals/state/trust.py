"""The operator's trust answers: one per worktree, confirmed in person at the terminal.

An answer holds for the worktree it was given for, rather than for its path, so a worktree that
replaces a removed one at the same path is asked about afresh.
"""

import ctypes
import errno
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TextIO

from ..controlling_terminal import ask_in_person
from .store import StateStore, StateStoreUnusable

TRUST_FILE_NAME = "trust.json"
TRUST_FORMAT_VERSION = 1
# From <linux/stat.h> and <fcntl.h>: struct statx is 256 bytes, with stx_mask at offset 0, stx_ino
# at 32, stx_btime at 80, and stx_dev_major and stx_dev_minor at 136 and 140.
_STATX_SIZE = 256
_STATX_INO = 0x100
_STATX_BTIME = 0x800
_STATX_WANTED = _STATX_INO | _STATX_BTIME
_AT_FDCWD = -100
_AT_SYMLINK_NOFOLLOW = 0x100


@dataclass(frozen=True)
class ConfirmedTrust:
    """Proof that the operator trusts the worktree, which only `confirm_trust` makes."""

    worktree: Path


@dataclass(frozen=True)
class _Answer:
    identity: str
    confirmed_at: str


def confirm_trust(
    store: StateStore, worktree: Path, now: datetime, open_terminal: Callable[[], TextIO]
) -> ConfirmedTrust | None:
    """Return the operator's trust in the worktree, asking them in person if they haven't confirmed
    it before.
    """
    if is_worktree_trusted(store, worktree):
        return ConfirmedTrust(worktree)
    explanation = (
        f"The suite has not run in {worktree} before.\n"
        "Its agents, skills, cases, and fixtures will run under confinement, but only the code "
        "check keeps other code from reading the credential. Review the change first."
    )
    if not ask_in_person(explanation, "trust this worktree", open_terminal):
        return None
    record_trust(store, worktree, now)
    return ConfirmedTrust(worktree)


def is_worktree_trusted(store: StateStore, worktree: Path) -> bool:
    """Whether the operator has confirmed trust in this worktree, forgetting answers for
    worktrees that no longer exist, or that another one has replaced.
    """
    answers = _read_answers(store)
    current = {
        path: answer
        for path, answer in answers.items()
        if Path(path).is_dir() and answer.identity == _identify(Path(path))
    }
    if current != answers:
        _write_answers(store, current)
    return str(worktree) in current


def record_trust(store: StateStore, worktree: Path, now: datetime) -> None:
    identity = _identify(worktree)
    if identity is None:
        # Without an identity, the answer couldn't be told from one for a later worktree at the
        # same path, so the operator is asked every time instead.
        return
    answers = _read_answers(store)
    answers[str(worktree)] = _Answer(identity=identity, confirmed_at=now.isoformat())
    _write_answers(store, answers)


def _identify(worktree: Path) -> str | None:
    """Name the worktree by the inode and birth time of its root and of its `.git` entry, which a
    new worktree at the same path gets afresh. Inodes alone won't do, since ext4 reuses them at
    once.

    Returns None where the filesystem can't tell when they were born.
    """
    identities = []
    for path in (worktree, worktree / ".git"):
        identity = _identify_file(path)
        if identity is None:
            return None
        identities.append(identity)
    return "/".join(identities)


def _identify_file(path: Path) -> str | None:
    # Python's os.stat doesn't report birth times on Linux, so this asks statx(2) through libc.
    buffer = ctypes.create_string_buffer(_STATX_SIZE)
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.statx(_AT_FDCWD, os.fsencode(path), _AT_SYMLINK_NOFOLLOW, _STATX_WANTED, buffer)
    if result != 0:
        return "absent" if ctypes.get_errno() == errno.ENOENT else None
    raw = buffer.raw
    if not int.from_bytes(raw[0:4], "little") & _STATX_BTIME:
        return None
    inode = int.from_bytes(raw[32:40], "little")
    born_seconds = int.from_bytes(raw[80:88], "little", signed=True)
    born_nanoseconds = int.from_bytes(raw[88:92], "little")
    device = (int.from_bytes(raw[136:140], "little"), int.from_bytes(raw[140:144], "little"))
    return f"{device[0]}.{device[1]}:{inode}:{born_seconds}.{born_nanoseconds:09d}"


def _read_answers(store: StateStore) -> dict[str, _Answer]:
    document = store.read(TRUST_FILE_NAME, TRUST_FORMAT_VERSION)
    if document is None:
        return {}
    worktrees = document.get("worktrees")
    if not isinstance(worktrees, dict):
        raise StateStoreUnusable(f"{TRUST_FILE_NAME} must map worktree paths to answers")
    answers: dict[str, _Answer] = {}
    for path, answer in worktrees.items():
        if not (isinstance(answer, dict) and set(answer) == {"identity", "confirmed_at"}):
            raise StateStoreUnusable(
                f"{TRUST_FILE_NAME} must hold an identity and a time per answer"
            )
        answers[str(path)] = _Answer(str(answer["identity"]), str(answer["confirmed_at"]))
    return answers


def _write_answers(store: StateStore, answers: dict[str, _Answer]) -> None:
    encoded = {
        path: {"identity": answer.identity, "confirmed_at": answer.confirmed_at}
        for path, answer in answers.items()
    }
    store.write(TRUST_FILE_NAME, TRUST_FORMAT_VERSION, {"worktrees": encoded})
