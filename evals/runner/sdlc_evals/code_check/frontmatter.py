"""YAML frontmatter and YAML documents, read more strictly than Claude Code reads them.

Claude Code accepts YAML that this module refuses (e.g., anchors, tags, and duplicate keys), so
anything
that passes here means the same to both, and no key can hide from the allowlists.
"""

from dataclasses import dataclass
from pathlib import Path

import strictyaml

FRONTMATTER_DELIMITER = "---"
_FORBIDDEN_CHARACTERS = ("\r", "\ufeff")


@dataclass(frozen=True)
class Document:
    """A Markdown file split into its frontmatter and its body."""

    frontmatter: dict[str, object]
    body: str


class MalformedDocument(Exception):
    """The file isn't one that the code check can vouch for. Retrying won't help: fix the file."""


def read_exactly(path: Path) -> str:
    """Read a UTF-8 file without translating its line endings, which the checks must see as they
    are.
    """
    return path.read_bytes().decode("utf-8")


def parse_markdown(text: str) -> Document:
    """Split a Markdown file into its frontmatter (a YAML map) and its body."""
    _require_plain_text(text)
    lines = text.split("\n")
    if lines[0] != FRONTMATTER_DELIMITER:
        raise MalformedDocument(f"File must start with a {FRONTMATTER_DELIMITER} line")
    try:
        closing_line_index = lines.index(FRONTMATTER_DELIMITER, 1)
    except ValueError as error:
        raise MalformedDocument(
            f"Frontmatter must be closed with a {FRONTMATTER_DELIMITER} line"
        ) from error
    frontmatter = parse_yaml("\n".join(lines[1:closing_line_index]))
    body = "\n".join(lines[closing_line_index + 1 :])
    return Document(frontmatter=frontmatter, body=body)


def parse_yaml(text: str) -> dict[str, object]:
    """Parse a YAML map, refusing anything that strict YAML refuses."""
    _require_plain_text(text)
    if not text.strip():
        return {}
    try:
        data = strictyaml.dirty_load(text, allow_flow_style=True).data
    except strictyaml.YAMLError as error:
        raise MalformedDocument(
            f"Invalid or non-strict YAML ({error.__class__.__name__})"
        ) from error
    if not isinstance(data, dict):
        raise MalformedDocument(f"YAML must be a map (got {type(data).__name__})")
    return data


def _require_plain_text(text: str) -> None:
    for character in _FORBIDDEN_CHARACTERS:
        if character in text:
            raise MalformedDocument(f"File must not contain {character!r}")
