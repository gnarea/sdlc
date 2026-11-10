"""Tests of what the wrapper prepares before anything runs: the policy, the binaries, the snapshot, and the code record."""

import contextlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from sdlc_evals.cli import parse_command
from sdlc_evals.confinement import NonoBinary, NonoUnavailable, Policy
from sdlc_evals.credentials import (
    CredentialSource,
    CredentialUnavailable,
    load_credential,
)
from sdlc_evals.invocation_directory import InvocationDirectory, UnsafeTemporaryRoot
from sdlc_evals.levels import EffortLevel
from sdlc_evals.snapshot import snapshot_plugin
from sdlc_evals.spend import ApiKeyChoice, SubscriptionChoice
from sdlc_evals.state.store import StateStore
from sdlc_evals.working_tree import (
    ClaudeCodeUnavailable,
    find_pinned_claude_code,
    record_code,
)

POLICY = Policy(
    readable_directories=(Path("/inv/plugin"),),
    writable_directory=Path("/inv/calls/programmer--review-implied--low"),
    proxy_port=4242,
    denied_paths=(Path("/home/operator/.ssh"),),
    environment={"HOME": "/inv/calls/programmer--review-implied--low/home"},
    inherited_variables=("CLAUDE_CODE_OAUTH_TOKEN",),
)


class PolicyTest(unittest.TestCase):
    def test_renders_a_profile_that_denies_everything_it_does_not_name(self) -> None:
        profile = POLICY.render()

        self.assertIn("system_write_linux", profile["groups"]["exclude"])  # type: ignore[index]
        filesystem = profile["filesystem"]
        self.assertIn("/inv/plugin", filesystem["read"])  # type: ignore[index]
        self.assertEqual(filesystem["allow"], ["/inv/calls/programmer--review-implied--low"])  # type: ignore[index]
        self.assertEqual(filesystem["deny"], ["/home/operator/.ssh"])  # type: ignore[index]
        self.assertEqual(profile["network"], {"block": True, "connect_port": [4242]})
        self.assertEqual(profile["linux"]["af_unix_mediation"], "pathname")  # type: ignore[index]
        self.assertEqual(profile["open_urls"], {"allow_origins": [], "allow_localhost": False})
        self.assertEqual(
            profile["environment"],
            {
                "allow_vars": ["LANG", "CLAUDE_CODE_OAUTH_TOKEN"],
                "set_vars": {"HOME": "/inv/calls/programmer--review-implied--low/home"},
            },
        )

    def test_refuses_values_that_nono_would_expand(self) -> None:
        policy = Policy((), Path("/w"), 1, (), {"HOME": "$HOME/x"})

        with self.assertRaisesRegex(ValueError, "HOME"):
            policy.render()


class NonoBinaryTest(unittest.TestCase):
    def test_refuses_a_missing_or_unpinned_binary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(NonoUnavailable, "must be on PATH"):
                NonoBinary.locate(directory)
            impostor = Path(directory) / "nono"
            impostor.write_text("#!/bin/sh\necho nono 0.81.0\n", encoding="utf-8")
            os.chmod(impostor, 0o755)

            with self.assertRaisesRegex(NonoUnavailable, "release binary"):
                NonoBinary.locate(directory)


class InvocationDirectoryTest(unittest.TestCase):
    def test_refuses_a_temporary_root_inside_the_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as worktree:
            with self.assertRaises(UnsafeTemporaryRoot):
                InvocationDirectory.make(Path(worktree) / "tmp", Path(worktree))

    def test_makes_a_private_directory_under_the_temporary_root(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as worktree:
            directory = InvocationDirectory.make(Path(root), Path(worktree))

            self.assertEqual(directory.path.parent, Path(root).resolve())
            self.assertEqual(directory.path.stat().st_mode & 0o777, 0o700)
            self.assertEqual(
                directory.call("programmer/review-implied", EffortLevel.HIGH).path,
                directory.path / "calls" / "programmer--review-implied--high",
            )
            self.assertEqual(
                directory.reading(0).path, directory.path / "readings" / "reading-0"
            )


class SnapshotTest(unittest.TestCase):
    def test_copies_the_plugin_without_the_wrapper_or_results_and_keeps_links_as_links(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            worktree, destination = Path(directory) / "tree", Path(directory) / "snapshot"
            for relative_path in (
                ".claude-plugin/plugin.json",
                "agents/a.md",
                "skills/s/SKILL.md",
                "evals/x/y/prompt.md",
                "evals/runner/m.py",
                "evals/results/r.json",
                "README.md",
            ):
                (worktree / relative_path).parent.mkdir(parents=True, exist_ok=True)
                (worktree / relative_path).write_text("x", encoding="utf-8")
            os.symlink("/etc/passwd", worktree / "agents" / "link.md")

            snapshot_plugin(worktree, destination)

            copied = sorted(
                str(path.relative_to(destination))
                for path in destination.rglob("*")
                if not path.is_dir()
            )
            self.assertEqual(
                copied,
                [
                    ".claude-plugin/plugin.json",
                    "agents/a.md",
                    "agents/link.md",
                    "evals/x/y/prompt.md",
                    "skills/s/SKILL.md",
                ],
            )
            self.assertTrue((destination / "agents" / "link.md").is_symlink())


class WorkingTreeTest(unittest.TestCase):
    def test_requires_the_installed_claude_code_to_be_the_pinned_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                json.dumps({"devDependencies": {"@anthropic-ai/claude-code": "2.1.317"}}),
                encoding="utf-8",
            )
            package = root / "node_modules" / "@anthropic-ai" / "claude-code"
            (package / "bin").mkdir(parents=True)
            (package / "package.json").write_text(
                json.dumps({"version": "2.1.312"}), encoding="utf-8"
            )

            with self.assertRaisesRegex(ClaudeCodeUnavailable, "pinned 2.1.317 \\(got 2.1.312\\)"):
                find_pinned_claude_code(root)

            (package / "package.json").write_text(
                json.dumps({"version": "2.1.317"}), encoding="utf-8"
            )
            (package / "bin" / "claude.exe").write_text("", encoding="utf-8")
            self.assertEqual(find_pinned_claude_code(root).binary, package / "bin" / "claude.exe")

    def test_records_how_the_snapshot_and_the_wrapper_differ_from_the_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, snapshot = Path(directory) / "tree", Path(directory) / "snapshot"
            _commit(
                root,
                {
                    "agents/a.md": "one\n",
                    "agents/gone.md": "gone\n",
                    "README.md": "x\n",
                    "pyproject.toml": "[project]\n",
                    "uv.lock": "version = 1\n",
                    "evals/runner/main.py": "print(1)\n",
                },
            )
            (root / "agents" / "a.md").write_text("two\n", encoding="utf-8")
            (root / "agents" / "gone.md").unlink()
            (root / "evals" / "new.md").write_text("new\n", encoding="utf-8")
            (root / "evals" / "runner" / "added.py").write_text("print(2)\n", encoding="utf-8")
            (root / "evals" / "runner" / "__pycache__").mkdir()
            (root / "evals" / "runner" / "__pycache__" / "main.pyc").write_bytes(b"cached")
            (root / "uv.lock").write_text("version = 2\n", encoding="utf-8")
            (root / "README.md").write_text("y\n", encoding="utf-8")
            for entry in (".claude-plugin", "skills"):
                (root / entry).mkdir()
            snapshot_plugin(root, snapshot)

            record = record_code(root, snapshot)
            unchanged = record_code(root, snapshot)

        self.assertEqual(len(record.commit), 40)
        self.assertIn("-one\n+two", record.snapshot.diff)
        self.assertIn("--- a/agents/gone.md\n+++ /dev/null", record.snapshot.diff)
        self.assertIn("--- /dev/null\n+++ b/evals/new.md", record.snapshot.diff)
        self.assertNotIn("runner", record.snapshot.diff)
        self.assertIn("--- /dev/null\n+++ b/evals/runner/added.py", record.wrapper.diff)
        self.assertIn("-version = 1\n+version = 2", record.wrapper.diff)
        self.assertNotIn("main.py", record.wrapper.diff)
        self.assertNotIn("__pycache__", record.wrapper.diff)
        for files in (record.snapshot, record.wrapper):
            self.assertNotIn("README", files.diff)
            self.assertEqual(len(files.sha256), 64)
        self.assertEqual(unchanged, record)

    def test_runs_no_command_that_the_repository_configuration_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, snapshot = Path(directory) / "tree", Path(directory) / "snapshot"
            marker = Path(directory) / "ran"
            _commit(
                root, {"agents/a.md": "one\n", ".gitattributes": "* filter=planted diff=planted\n"}
            )
            for key, value in (
                ("filter.planted.clean", f"touch {marker}; cat"),
                ("filter.planted.smudge", f"touch {marker}; cat"),
                ("filter.planted.process", f"touch {marker}"),
                ("diff.planted.textconv", f"touch {marker}; cat"),
                ("diff.planted.command", f"touch {marker}"),
                ("core.fsmonitor", f"touch {marker}"),
                ("core.pager", f"touch {marker}"),
            ):
                subprocess.run(["git", "config", key, value], cwd=root, check=True)
            (root / "agents" / "a.md").write_text("two\n", encoding="utf-8")
            for entry in (".claude-plugin", "skills", "evals"):
                (root / entry).mkdir()
            snapshot_plugin(root, snapshot)

            record = record_code(root, snapshot)

            self.assertFalse(marker.exists())
        self.assertIn("-one\n+two", record.snapshot.diff)


def _commit(root: Path, files: dict[str, str]) -> None:
    environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "a",
        "GIT_AUTHOR_EMAIL": "a@a",
        "GIT_COMMITTER_NAME": "a",
        "GIT_COMMITTER_EMAIL": "a@a",
    }
    for relative_path, content in files.items():
        (root / relative_path).parent.mkdir(parents=True, exist_ok=True)
        (root / relative_path).write_text(content, encoding="utf-8")
    for command in (["init", "-q"], ["add", "."], ["commit", "-qm", "x"]):
        subprocess.run(["git", *command], cwd=root, env=environment, check=True)


class CredentialTest(unittest.TestCase):
    def test_takes_only_a_standard_api_key_from_the_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore.init(Path(directory))
            key = "sk-ant-api03-" + "k" * 64
            credential = load_credential(
                CredentialSource.API_KEY, store, {"ANTHROPIC_API_KEY": key}, None
            )  # type: ignore[arg-type]

            self.assertEqual(
                (credential.environment_variable, credential.value), ("ANTHROPIC_API_KEY", key)
            )
            self.assertNotIn(key, repr(credential))
            for invalid in ("", "sk-ant-admin01-" + "k" * 64):
                with self.subTest(invalid=invalid[:14]):
                    with self.assertRaises(CredentialUnavailable):
                        load_credential(
                            CredentialSource.API_KEY, store, {"ANTHROPIC_API_KEY": invalid}, None
                        )  # type: ignore[arg-type]


class OptionsTest(unittest.TestCase):
    def _options(self, *arguments: str):  # noqa: ANN202
        command, options = parse_command(["run", *arguments])
        self.assertEqual(command, "run")
        return options

    def test_takes_no_options_for_other_commands(self) -> None:
        self.assertEqual(parse_command(["self-test"]), ("self-test", None))
        self.assertEqual(parse_command(["store-token"]), ("store-token", None))
        self.assertEqual(parse_command(["clear-charge"]), ("clear-charge", None))

    def test_defaults_to_every_agent_at_low_effort_on_the_subscription(self) -> None:
        options = self._options()

        self.assertEqual(
            (options.agents, options.levels, options.case_names, options.credential),
            (None, (EffortLevel.LOW,), None, SubscriptionChoice()),
        )

    def test_takes_a_subset_and_an_api_key_cap(self) -> None:
        options = self._options(
            "--agent",
            "programmer",
            "--level",
            "high",
            "--level",
            "low",
            "--level",
            "high",
            "--case",
            "programmer/review-implied",
            "--case",
            "programmer/domain",
            "--case",
            "programmer/review-implied",
            "--runs",
            "1",
            "--credential",
            "api-key",
            "--max-cost-usd",
            "5",
        )

        self.assertEqual(options.agents, ("programmer",))
        self.assertEqual(options.levels, (EffortLevel.HIGH, EffortLevel.LOW))
        self.assertEqual(
            options.case_names, frozenset({"programmer/review-implied", "programmer/domain"})
        )
        self.assertEqual((options.runs_per_case, options.credential), (1, ApiKeyChoice(5.0)))

    def test_refuses_an_ambiguous_or_missing_cap(self) -> None:
        for arguments in (
            ["--credential", "api-key"],
            ["--credential", "api-key", "--max-cost-usd", "0"],
            ["--max-cost-usd", "5"],
            ["--runs", "4"],
        ):
            with self.subTest(arguments=arguments):
                with (
                    self.assertRaises(SystemExit) as raised,
                    open(os.devnull, "w") as devnull,
                    contextlib.redirect_stderr(devnull),
                ):
                    self._options(*arguments)
                self.assertEqual(raised.exception.code, 4)
