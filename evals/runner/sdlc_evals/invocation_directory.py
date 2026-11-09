"""The invocation temp dir: the only place that the confined tree can write, one harness call's or
reading's directory at a time.
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path

from .levels import EffortLevel

DIRECTORY_PREFIX = "sdlc-evals-"


class UnsafeTemporaryRoot(Exception):
    """The temporary root would put results inside the working tree. Retrying won't help: set TMPDIR
    elsewhere.
    """


@dataclass(frozen=True)
class InvocationDirectory:
    """Holds a directory for each harness call and each reading, and the wrapper's own files where
    no confined process can write.
    """

    path: Path

    @classmethod
    def make(cls, temporary_root: Path, worktree: Path) -> InvocationDirectory:
        resolved_root = temporary_root.resolve()
        if resolved_root.is_relative_to(worktree):
            raise UnsafeTemporaryRoot(
                f"The temporary root must be outside the working tree (got {resolved_root})"
            )
        return cls(Path(tempfile.mkdtemp(prefix=DIRECTORY_PREFIX, dir=resolved_root)))

    @property
    def nono_state(self) -> Path:
        return self.path / "nono"

    @property
    def self_test(self) -> Path:
        return self.path / "self-test"

    @property
    def wrapper_sockets(self) -> Path:
        return self.path / "sockets"

    @property
    def manifest(self) -> Path:
        return self.path / "manifest.json"

    @property
    def summary(self) -> Path:
        return self.path / "summary.txt"

    def call(self, case_name: str, level: EffortLevel) -> ConfinedDirectory:
        # Each name is unique, since nono names a policy's profile after its writable directory.
        return ConfinedDirectory(
            self.path / "calls" / f"{case_name.replace('/', '--')}--{level.value}"
        )

    def reading(self, index: int) -> ConfinedDirectory:
        return ConfinedDirectory(self.path / "readings" / f"reading-{index}")

    def traces(self, level: EffortLevel) -> Path:
        return self.path / "traces" / level.value


@dataclass(frozen=True)
class ConfinedDirectory:
    """The home, configuration, temporary files, and results of one confined Claude Code process,
    whether a harness call or a reading, all writable by it.
    """

    path: Path

    @property
    def home(self) -> Path:
        return self.path / "home"

    @property
    def config(self) -> Path:
        return self.path / "config"

    @property
    def tmp(self) -> Path:
        return self.path / "tmp"

    @property
    def results(self) -> Path:
        return self.path / "results"

    def make(self) -> None:
        for directory in (self.home, self.config, self.tmp, self.results):
            directory.mkdir(mode=0o700, parents=True, exist_ok=False)
