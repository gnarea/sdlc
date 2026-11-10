"""The controlling terminal, where the wrapper asks the operator in person, so that a process that
only controls standard input can't answer.
"""

import errno
import io
from collections.abc import Callable
from typing import TextIO

CONFIRMATION = "yes"
CONTROLLING_TERMINAL = "/dev/tty"
# What opening the controlling terminal fails with when the process has none.
_NO_TERMINAL_ERRORS = frozenset({errno.ENXIO, errno.ENOENT})


def ask_in_person(explanation: str, action: str, open_terminal: Callable[[], TextIO]) -> bool:
    """Explain what's at stake at the controlling terminal, and return whether the operator
    confirmed the action.

    Returns False when there is no terminal to ask at.
    """
    try:
        terminal = open_terminal()
    except OSError as error:
        if error.errno not in _NO_TERMINAL_ERRORS:
            raise
        return False
    with terminal:
        terminal.write(f"{explanation}\nType {CONFIRMATION!r} to {action}: ")
        terminal.flush()
        return terminal.readline().strip() == CONFIRMATION


def open_controlling_terminal() -> TextIO:
    """Open the controlling terminal to read and write, with a descriptor for each, since a
    terminal can't seek and `open(..., "r+")` therefore refuses it.
    """
    reader = io.FileIO(CONTROLLING_TERMINAL, "r")
    try:
        writer = io.FileIO(CONTROLLING_TERMINAL, "w")
    except BaseException:
        reader.close()
        raise
    return io.TextIOWrapper(io.BufferedRWPair(reader, writer), encoding="utf-8")
