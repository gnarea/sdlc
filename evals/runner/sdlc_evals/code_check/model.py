"""What the code check finds: the suite it vouches for, or why it refuses one."""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import PurePosixPath


@dataclass(frozen=True)
class Finding:
    """Something in the working tree that the code check refuses, with its path from the tree's
    root.
    """

    path: PurePosixPath
    problem: str

    def __str__(self) -> str:
        return f"{self.path}: {self.problem}"


@dataclass(frozen=True)
class Case:
    """A case that passed the code check, with the names of its prohibitions of the trace: the
    graders of the trace that only forbid something, which a run cut short can fail for good.
    """

    name: str
    agent: str
    runs: int
    allowed_tools: frozenset[str]
    timeout: timedelta
    trace_prohibitions: frozenset[str]


@dataclass(frozen=True)
class Suite:
    """The plugin's agents and the cases that test them, all of which passed the code check."""

    agents: tuple[str, ...]
    cases: tuple[Case, ...]


@dataclass(frozen=True)
class Refused:
    """The code check's findings, which are never empty."""

    findings: tuple[Finding, ...]
