"""The working tree under test: where it is, the Claude Code it pins, and the code it holds."""

import difflib
import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path, PurePosixPath

from .snapshot import SNAPSHOT_ENTRIES, is_in_snapshot

CLAUDE_CODE_PACKAGE = "@anthropic-ai/claude-code"
GIT_TIMEOUT = timedelta(seconds=30)
MAX_DIFFED_FILE_BYTES = 4 * 1024 * 1024
MIN_GIT_VERSION = (2, 44)
# The wrapper's code, then the project files that decide which Python and dependencies run it.
WRAPPER_PATHS = ("evals/runner", "pyproject.toml", "uv.lock")
_BYTECODE_DIRECTORY = "__pycache__"
# The repository's own configuration, which every worktree shares, can name commands for git to run
# (e.g., filters, external diffs, fsmonitor, and fetches from a promisor remote), so the wrapper
# only runs plumbing that runs none of them, and computes the diff itself.
_GIT_ENVIRONMENT = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "LANG": "C",
}
_GIT_OPTIONS = ("--no-pager", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null")


class CodeUnrecordable(Exception):
    """Git couldn't say which commit the working tree holds. Retrying won't help until git works
    in it.
    """


class ClaudeCodeUnavailable(Exception):
    """The installed Claude Code isn't the pinned one. Retrying won't help: run `npm ci` in the
    working tree.
    """


@dataclass(frozen=True)
class PinnedClaudeCode:
    version: str
    binary: Path


@dataclass(frozen=True)
class FilesRecord:
    """How a set of files differs from the commit (untracked files included), and a digest of
    those files.
    """

    diff: str
    sha256: str


@dataclass(frozen=True)
class CodeRecord:
    """The commit that the snapshot was taken from, and how the snapshot and the wrapper's own
    code differ from it.
    """

    commit: str
    snapshot: FilesRecord
    wrapper: FilesRecord


@dataclass(frozen=True)
class _TreeEntry:
    mode: str
    object_id: str
    size: int | None


def find_root() -> Path:
    """The working tree that holds this wrapper."""
    return Path(__file__).resolve().parents[3]


def find_pinned_claude_code(root: Path) -> PinnedClaudeCode:
    try:
        manifest = json.loads((root / "package.json").read_text(encoding="utf-8"))
        version = manifest["devDependencies"][CLAUDE_CODE_PACKAGE]
        package_directory = root / "node_modules" / CLAUDE_CODE_PACKAGE
        installed = json.loads((package_directory / "package.json").read_text(encoding="utf-8"))[
            "version"
        ]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ClaudeCodeUnavailable(
            f"Cannot find the pinned {CLAUDE_CODE_PACKAGE}: run `npm ci`"
        ) from error
    if installed != version:
        raise ClaudeCodeUnavailable(
            f"{CLAUDE_CODE_PACKAGE} must be at the pinned {version} (got {installed}): run `npm ci`"
        )
    binary = package_directory / "bin" / "claude.exe"
    if not binary.is_file():
        raise ClaudeCodeUnavailable(f"{CLAUDE_CODE_PACKAGE} has no native binary: run `npm ci`")
    return PinnedClaudeCode(version=version, binary=binary)


def record_code(worktree: Path, snapshot: Path) -> CodeRecord:
    """Record the commit, and how the snapshot taken from the worktree, and the wrapper that runs
    it, differ from that commit.
    """
    _require_git_version(worktree)
    commit = _git(worktree, ["rev-parse", "--verify", "HEAD^{commit}"]).decode("ascii").strip()
    committed = _read_tree(worktree, commit)
    contents = _read_blobs(worktree, [entry for entry in committed.values() if _is_diffable(entry)])
    snapshot_files = _read_files(snapshot, (snapshot,), is_in_snapshot)
    wrapper_roots = tuple(worktree / path for path in WRAPPER_PATHS)
    wrapper_files = _read_files(worktree, wrapper_roots, is_wrapper_file)
    return CodeRecord(
        commit=commit,
        snapshot=_compare(_select(committed, is_in_snapshot), contents, snapshot_files),
        wrapper=_compare(_select(committed, is_wrapper_file), contents, wrapper_files),
    )


def is_wrapper_file(path: PurePosixPath) -> bool:
    """Whether a path relative to the working tree's root is part of the wrapper: its code, and the
    project files that decide which Python and which dependencies run it.
    """
    if str(path) in WRAPPER_PATHS[1:]:
        return True
    return path.parts[:2] == ("evals", "runner") and _BYTECODE_DIRECTORY not in path.parts


def _require_git_version(worktree: Path) -> None:
    # Older releases ignore GIT_NO_LAZY_FETCH, so they could fetch from a promisor remote, which
    # runs the commands that the repository's configuration names for fetching.
    words = _git(worktree, ["--version"]).decode("ascii", "replace").split()
    numbers = words[2].split(".")[:2] if 2 < len(words) else []
    version = tuple(int(number) for number in numbers if number.isdigit())
    if len(version) != 2 or version < MIN_GIT_VERSION:
        raise CodeUnrecordable(
            f"git must be at least {'.'.join(map(str, MIN_GIT_VERSION))} (got {' '.join(words)})"
        )


def _read_tree(worktree: Path, commit: str) -> dict[PurePosixPath, _TreeEntry]:
    listing = _git(
        worktree,
        [
            "ls-tree",
            "-r",
            "-z",
            "-l",
            "--full-tree",
            commit,
            "--",
            *SNAPSHOT_ENTRIES,
            *WRAPPER_PATHS,
        ],
    )
    entries: dict[PurePosixPath, _TreeEntry] = {}
    for record in filter(None, listing.split(b"\0")):
        metadata, _, raw_path = record.partition(b"\t")
        mode, _, object_id, size = metadata.decode("ascii").split()
        path = PurePosixPath(raw_path.decode("utf-8", "surrogateescape"))
        entries[path] = _TreeEntry(mode, object_id, int(size) if size.isdigit() else None)
    return entries


def _select(
    entries: dict[PurePosixPath, _TreeEntry], is_selected: Callable[[PurePosixPath], bool]
) -> dict[PurePosixPath, _TreeEntry]:
    return {path: entry for path, entry in entries.items() if is_selected(path)}


def _read_files(
    base: Path, roots: tuple[Path, ...], is_selected: Callable[[PurePosixPath], bool]
) -> dict[PurePosixPath, bytes]:
    """Read files under the roots, without git, keyed by their paths relative to the base."""
    files: dict[PurePosixPath, bytes] = {}
    candidates = [
        path
        for root in roots
        for path in (root, *(root.rglob("*") if root.is_dir() else ()))
        if path.exists() or path.is_symlink()
    ]
    for path in candidates:
        relative = PurePosixPath(path.relative_to(base).as_posix())
        if not is_selected(relative):
            continue
        if path.is_symlink():
            files[relative] = os.readlink(path).encode("utf-8", "surrogateescape")
        elif path.is_file():
            files[relative] = path.read_bytes()
    return files


def _compare(
    committed: dict[PurePosixPath, _TreeEntry],
    contents: dict[str, bytes],
    current: dict[PurePosixPath, bytes],
) -> FilesRecord:
    diff = "".join(
        _diff_file(path, committed.get(path), contents, current.get(path))
        for path in sorted(set(committed) | set(current))
    )
    return FilesRecord(diff=diff, sha256=_digest(current))


def _is_diffable(entry: _TreeEntry) -> bool:
    return entry.size is not None and entry.size <= MAX_DIFFED_FILE_BYTES


def _read_blobs(worktree: Path, entries: list[_TreeEntry]) -> dict[str, bytes]:
    """Read committed blobs as stored, without any filter, which `cat-file --batch` never applies."""
    request = b"".join(f"{entry.object_id}\n".encode("ascii") for entry in entries)
    output = _git(worktree, ["cat-file", "--batch"], request)
    contents: dict[str, bytes] = {}
    position = 0
    for entry in entries:
        header_end = output.index(b"\n", position)
        header = output[position:header_end].decode("ascii").split()
        position = header_end + 1
        if len(header) != 3:
            raise CodeUnrecordable(f"git cat-file must return {entry.object_id} (got {header!r})")
        size = int(header[2])
        contents[entry.object_id] = output[position : position + size]
        position += size + 1
    return contents


def _diff_file(
    path: PurePosixPath,
    committed: _TreeEntry | None,
    contents: dict[str, bytes],
    current: bytes | None,
) -> str:
    before = contents.get(committed.object_id) if committed else b""
    after = b"" if current is None else current
    if committed is not None and current is not None and before == after:
        return ""
    old_name = f"a/{path}" if committed else "/dev/null"
    new_name = f"b/{path}" if current is not None else "/dev/null"
    if before is None or MAX_DIFFED_FILE_BYTES < len(after):
        return f"--- {old_name}\n+++ {new_name}\n(too large to show)\n"
    try:
        old_lines = before.decode("utf-8").splitlines(keepends=True)
        new_lines = after.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return f"Binary files {old_name} and {new_name} differ\n"
    return "".join(difflib.unified_diff(old_lines, new_lines, old_name, new_name))


def _digest(files: dict[PurePosixPath, bytes]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(f"{path}\0{hashlib.sha256(files[path]).hexdigest()}\n".encode())
    return digest.hexdigest()


def _git(worktree: Path, arguments: list[str], request: bytes = b"") -> bytes:
    git = shutil.which("git")
    if git is None:
        raise CodeUnrecordable("git must be on PATH to record the commit")
    try:
        completed = subprocess.run(
            [git, *_GIT_OPTIONS, *arguments],
            cwd=worktree,
            env=_GIT_ENVIRONMENT,
            input=request,
            capture_output=True,
            timeout=GIT_TIMEOUT.total_seconds(),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CodeUnrecordable(
            f"git {arguments[0]} failed to run ({error.__class__.__name__})"
        ) from error
    if completed.returncode != 0:
        raise CodeUnrecordable(f"git {arguments[0]} must succeed (exit {completed.returncode})")
    return completed.stdout
