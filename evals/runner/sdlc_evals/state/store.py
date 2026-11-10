"""The operator state store: a directory that only the operator's account can read, outside the
confinement.
"""

import fcntl
import json
import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

STORE_DIRECTORY_NAME = "sdlc-evals"
DIRECTORY_MODE = 0o700
FILE_MODE = 0o600
MAX_FILE_BYTES = 1024 * 1024
LOCK_FILE_NAME = "invocation.lock"


class StateStoreUnusable(Exception):
    """The store can't be trusted to hold the budget and the trust answers.

    Retrying won't help: fix the store's ownership or permissions, or restore the file, as the
    message says.
    """


class InvocationLockHeld(Exception):
    """Another invocation holds the lock. Retry once it has finished."""

    def __init__(self, holder: str) -> None:
        super().__init__(f"Another invocation is running ({holder})")
        self.holder = holder


@dataclass(frozen=True)
class StateStore:
    """A directory whose files are JSON documents, each with a format version."""

    directory: Path

    @classmethod
    def init(cls, account_home: Path) -> StateStore:
        """Open the store in the account's default XDG state directory, creating it if need be.

        It ignores `XDG_STATE_HOME` and `HOME`, which can differ between the invocations that
        agents start, so that every invocation under the account shares one lock and one ledger.
        """
        if not account_home.is_absolute():
            raise StateStoreUnusable(f"The account's home must be absolute (got {account_home})")
        directory = account_home / ".local" / "state" / STORE_DIRECTORY_NAME
        directory.mkdir(mode=DIRECTORY_MODE, parents=True, exist_ok=True)
        _require_private(directory.lstat(), directory.name, is_directory=True)
        return cls(directory)

    def read(self, name: str, *format_versions: int) -> dict[str, object] | None:
        """Return the document, which must have one of the format versions, or None if it doesn't
        exist yet.
        """
        try:
            descriptor = os.open(self.directory / name, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        except OSError as error:
            raise StateStoreUnusable(f"Cannot read {name} ({error.__class__.__name__})") from error
        with os.fdopen(descriptor, "rb") as file:
            _require_private(os.fstat(descriptor), name, is_directory=False)
            content = file.read(MAX_FILE_BYTES + 1)
        if MAX_FILE_BYTES < len(content):
            raise StateStoreUnusable(f"{name} exceeds {MAX_FILE_BYTES} bytes")
        try:
            document = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise StateStoreUnusable(f"{name} is not valid JSON") from error
        if not isinstance(document, dict) or document.get("format_version") not in format_versions:
            expected = " or ".join(str(version) for version in format_versions)
            raise StateStoreUnusable(f"{name} must have format version {expected}")
        return document

    def write(self, name: str, format_version: int, document: Mapping[str, object]) -> None:
        """Replace the document atomically, so that a crash leaves either the old or the new one."""
        content = json.dumps(
            {"format_version": format_version, **document}, indent=2, sort_keys=True
        )
        temporary_path = self.directory / f".{name}.{os.getpid()}.tmp"
        descriptor = os.open(
            temporary_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, FILE_MODE
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.directory / name)
        finally:
            temporary_path.unlink(missing_ok=True)
        _fsync_directory(self.directory)

    def lock_invocation(self, holder: str) -> InvocationLock:
        """Take the lock that only one invocation at a time can hold, or raise naming whoever holds
        it.
        """
        path = self.directory / LOCK_FILE_NAME
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, FILE_MODE)
        try:
            _require_private(os.fstat(descriptor), LOCK_FILE_NAME, is_directory=False)
        except StateStoreUnusable:
            os.close(descriptor)
            raise
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            current_holder = (
                os.pread(descriptor, 4096, 0).decode("utf-8", "replace").strip() or "unknown"
            )
            os.close(descriptor)
            raise InvocationLockHeld(current_holder) from error
        os.ftruncate(descriptor, 0)
        os.pwrite(descriptor, holder.encode("utf-8"), 0)
        return InvocationLock(descriptor)


class InvocationLock:
    """The invocation lock, which the operating system releases if the process dies."""

    def __init__(self, descriptor: int) -> None:
        self._descriptor = descriptor

    def release(self) -> None:
        os.ftruncate(self._descriptor, 0)
        fcntl.flock(self._descriptor, fcntl.LOCK_UN)
        os.close(self._descriptor)

    def __enter__(self) -> InvocationLock:
        return self

    def __exit__(self, *_: object) -> None:
        self.release()


def _require_private(status: os.stat_result, name: str, *, is_directory: bool) -> None:
    expected_type = stat.S_ISDIR if is_directory else stat.S_ISREG
    if not expected_type(status.st_mode):
        raise StateStoreUnusable(
            f"{name} must be a {'directory' if is_directory else 'regular file'}"
        )
    if status.st_uid != os.getuid() or status.st_mode & 0o077:
        raise StateStoreUnusable(
            f"{name} must be owned by, and only accessible to, the operator's account"
        )


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
