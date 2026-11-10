"""The snapshot of the plugin that an invocation checks and runs, so that both see the same files
throughout.

It also keeps the working tree's version-control store, and everything else in the tree, out of the
confinement's reach.
"""

import shutil
from pathlib import Path, PurePosixPath

SNAPSHOT_ENTRIES = (".claude-plugin", "agents", "skills", "evals")
# Neither the wrapper nor any results from running the harness directly are part of the plugin
# under test.
EXCLUDED_SUITE_ENTRIES = frozenset({"runner", "results"})


def snapshot_plugin(worktree: Path, destination: Path) -> Path:
    """Copy the plugin's components and cases, keeping symbolic links as links so that the code
    check sees them.
    """
    for entry in SNAPSHOT_ENTRIES:
        shutil.copytree(
            worktree / entry, destination / entry, symlinks=True, ignore=_make_ignore(worktree)
        )
    return destination


def is_in_snapshot(path: PurePosixPath) -> bool:
    """Whether a path relative to the working tree's root is one that the snapshot copies."""
    parts = path.parts
    if not parts or parts[0] not in SNAPSHOT_ENTRIES:
        return False
    return not (parts[0] == "evals" and 1 < len(parts) and parts[1] in EXCLUDED_SUITE_ENTRIES)


def _make_ignore(worktree: Path):  # noqa: ANN202 -- shutil.copytree's callback type isn't public.
    def ignore(directory: str, names: list[str]) -> set[str]:
        relative = PurePosixPath(Path(directory).relative_to(worktree).as_posix())
        return {name for name in names if not is_in_snapshot(relative / name)}

    return ignore
