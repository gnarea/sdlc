"""Tools that the harness offers to agents, by name."""

from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]


def read_file(path: str) -> str:
    """Return the contents of a file in the repository, given its path from the root."""
    resolved = (REPOSITORY / path).resolve()
    if not resolved.is_relative_to(REPOSITORY):
        raise ValueError(f"{path} is outside the repository")
    return resolved.read_text(encoding="utf-8")


TOOLS = {"read_file": read_file}
