"""What's running, shown in place on a terminal, so that a full run doesn't fill it."""

from typing import TextIO

_CLEAR_LINE = "\r\x1b[K"


def show_status(progress: TextIO, text: str) -> None:
    """Replace the status on a terminal, or else write it as a line of its own."""
    progress.write(f"{_CLEAR_LINE}{text}" if progress.isatty() else f"{text}\n")
    progress.flush()


def end_status(progress: TextIO) -> None:
    """Clear the status on a terminal, so that what follows starts on a clean line."""
    if progress.isatty():
        progress.write(_CLEAR_LINE)
