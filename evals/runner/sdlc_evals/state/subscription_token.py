"""The subscription token from `claude setup-token`, which the store keeps until it's replaced or
expires.
"""

import contextlib
import re
import termios
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import BinaryIO, TextIO

from .store import StateStore, StateStoreUnusable

TOKEN_FILE_NAME = "subscription-token.json"
TOKEN_FORMAT_VERSION = 1
# `claude setup-token` issues tokens that last a year.
TOKEN_LIFETIME = timedelta(days=365)
MAX_TOKEN_INPUT_BYTES = 4096
# Only the token's characters are checked, since its format isn't documented and has changed.
_TOKEN_PATTERN = re.compile(r"[\x21-\x7e]{20,}")
# API keys (and admin keys, which must never be used) go through `--credential api-key`.
_API_KEY_PREFIXES = ("sk-ant-api", "sk-ant-admin")
_PROMPT = "Paste the token from `claude setup-token`, then press Enter twice (it won't be shown): "


class InvalidToken(Exception):
    """The text isn't a token from `claude setup-token`. Retrying with the same text won't help."""


@dataclass(frozen=True)
class SubscriptionToken:
    value: str = field(repr=False)
    stored_at: datetime

    def expires_at(self) -> datetime:
        return self.stored_at + TOKEN_LIFETIME


def read_token_input(stdin: BinaryIO, progress: TextIO) -> str:
    """Read the token as it's pasted at the terminal, without echoing it, or as it's piped in.

    Reading continues past line breaks, since a narrow terminal splits the token over several
    lines, and stops at the first empty line after the token or at the end of input. Empty lines
    before the token are skipped, so that a copy that starts with one doesn't leave the token for
    the shell.
    """
    if not stdin.isatty():
        return _read_up_to_empty_line(stdin)
    with _echo_disabled(stdin.fileno()):
        progress.write(_PROMPT)
        progress.flush()
        try:
            return _read_up_to_empty_line(stdin)
        finally:
            # The line break that ended the read wasn't echoed either.
            progress.write("\n")
            progress.flush()


def parse_token(text: str) -> str:
    """Validate a pasted or piped token, ignoring any whitespace in it (e.g., line breaks), without
    ever putting it in the message.
    """
    token = "".join(text.split())
    if token.startswith(_API_KEY_PREFIXES):
        raise InvalidToken(
            "That's an API key, not a token from `claude setup-token`: pass a standard API key "
            "with `--credential api-key` instead, and never an admin key"
        )
    if not _TOKEN_PATTERN.fullmatch(token):
        raise InvalidToken(
            "Expected the token from `claude setup-token`, with at least 20 printable ASCII "
            "characters. A narrow terminal may have split it over several lines, so copy all of them."
        )
    return token


def store_token(store: StateStore, token: str, now: datetime) -> SubscriptionToken:
    stored = SubscriptionToken(value=parse_token(token), stored_at=now)
    store.write(
        TOKEN_FILE_NAME, TOKEN_FORMAT_VERSION, {"token": stored.value, "stored_at": now.isoformat()}
    )
    return stored


def load_token(store: StateStore, now: datetime) -> SubscriptionToken | None:
    """Return the stored token, or None if there is none or it has expired."""
    document = store.read(TOKEN_FILE_NAME, TOKEN_FORMAT_VERSION)
    if document is None:
        return None
    try:
        stored = SubscriptionToken(
            value=parse_token(str(document["token"])),
            stored_at=datetime.fromisoformat(str(document["stored_at"])),
        )
    except (KeyError, ValueError, InvalidToken) as error:
        raise StateStoreUnusable(
            f"{TOKEN_FILE_NAME} must hold a valid token and the time it was stored"
        ) from error
    if stored.stored_at.tzinfo is None:
        raise StateStoreUnusable(
            f"{TOKEN_FILE_NAME} must record when it was stored, with a time zone"
        )
    if stored.expires_at() <= now:
        return None
    return stored


@contextlib.contextmanager
def _echo_disabled(terminal: int) -> Iterator[None]:
    original = termios.tcgetattr(terminal)
    silent = [*original[:3], original[3] & ~termios.ECHO, *original[4:]]
    termios.tcsetattr(terminal, termios.TCSANOW, silent)
    try:
        yield
    finally:
        # Flushing discards whatever the read left in the terminal's input, such as the rest of a
        # paste after an empty line, which the shell would otherwise run and record in its history.
        termios.tcsetattr(terminal, termios.TCSAFLUSH, original)


def _read_up_to_empty_line(stream: BinaryIO) -> str:
    token_input = bytearray()
    while True:
        line = stream.readline(MAX_TOKEN_INPUT_BYTES + 1 - len(token_input))
        if MAX_TOKEN_INPUT_BYTES < len(token_input) + len(line):
            raise InvalidToken(
                f"The input exceeds {MAX_TOKEN_INPUT_BYTES} bytes, far more than a token from `claude setup-token` takes"
            )
        if token_input.strip() and not line.strip():
            break
        token_input += line
        if not line.endswith(b"\n"):
            break
    return token_input.decode("utf-8", "replace")
