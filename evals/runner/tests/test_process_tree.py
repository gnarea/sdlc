import os
import subprocess
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from sdlc_evals.process_tree import (
    configure_child_subreaper,
    find_descendants,
    kill_stragglers,
    stop_tree,
)
from sdlc_evals.self_test import find_git_metadata

# A shell that leaves one sleeper in a session of its own, as the harness's runs are, and one in
# its own process group, then waits.
DETACHING_SHELL = "setsid sleep 300 & sleep 300 & echo ready; wait"


def is_running(pid: int) -> bool:
    try:
        status = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    return not status[status.rindex(")") + 2 :].startswith("Z")


class ProcessTreeTest(unittest.TestCase):
    def setUp(self) -> None:
        configure_child_subreaper()

    def _start(self, script: str) -> tuple[subprocess.Popen[bytes], frozenset[int]]:
        root = subprocess.Popen(["bash", "-c", script], stdout=subprocess.PIPE)
        self.addCleanup(kill_stragglers)
        assert root.stdout is not None
        self.addCleanup(root.stdout.close)
        self.assertEqual(root.stdout.readline(), b"ready\n")
        return root, find_descendants()

    def test_stops_every_descendant_however_it_detached(self) -> None:
        root, descendants = self._start(DETACHING_SHELL)

        stop_tree(root, timedelta(seconds=2))

        self.assertIn(root.pid, descendants)
        self.assertLessEqual(3, len(descendants))
        self.assertEqual([pid for pid in descendants if is_running(pid)], [])
        self.assertIsNotNone(root.returncode)
        self.assertEqual(find_descendants(), frozenset())

    def test_kills_what_outlives_its_parent(self) -> None:
        root, _ = self._start("setsid sleep 300 & echo ready")
        root.wait()
        orphans = find_descendants()

        kill_stragglers()

        self.assertEqual(len(orphans), 1)
        self.assertEqual([pid for pid in orphans if is_running(pid)], [])
        self.assertEqual(find_descendants(), frozenset())


class GitMetadataTest(unittest.TestCase):
    def test_follows_a_linked_worktree_to_its_git_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            git_directory = root / "main" / ".git" / "worktrees" / "tree"
            git_directory.mkdir(parents=True)
            (git_directory / "commondir").write_text("../..\n", encoding="utf-8")
            worktree = root / "tree"
            worktree.mkdir()
            (worktree / ".git").write_text(f"gitdir: {git_directory}\n", encoding="utf-8")

            found = find_git_metadata(worktree)

        self.assertEqual(found, (worktree / ".git", git_directory, root / "main" / ".git"))

    def test_finds_a_plain_repository_and_nothing_outside_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()

            self.assertEqual(find_git_metadata(root), (root / ".git",))
            os.rmdir(root / ".git")
            self.assertEqual(find_git_metadata(root), ())
