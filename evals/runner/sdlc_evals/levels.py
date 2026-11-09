"""The effort levels under test."""

import enum


class EffortLevel(enum.StrEnum):
    """An effort level, as Claude Code names it, at which both the delegating session and the agent
    run.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
