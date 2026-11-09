import os
import tempfile
import unittest
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

from sdlc_evals.code_check import Case, Refused, Suite, check_plugin_snapshot
from sdlc_evals.code_check.suite import SCAFFOLD_SCRIPT

PREFACE = "Delegate the request below to the `sdlc:(agent)` agent, passing it on word for word.\n"
PROMPT = """---
tags: [programmer]
runs: 3
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

Delegate the request below to the `sdlc:programmer` agent, passing it on word for word.

<request>
Is the change OK to merge?
</request>
"""
GRADER = '---\ntype: tool_used\ntool: Agent\ninput_match: "sdlc:programmer"\nmin: 1\n---\n'
CASE = Path("evals/programmer/review-implied")


def make_tree(root: Path) -> None:
    files = {
        ".claude-plugin/plugin.json": '{"name": "sdlc", "version": "1.0.0"}',
        "agents/programmer.md": "---\nname: programmer\ndescription: Programmer.\nskills:\n  - sdlc:escalation\n---\n# Programmer\n",
        "skills/escalation/SKILL.md": "---\nname: escalation\ndescription: Escalation.\n---\n# Escalation\n",
        "evals/delegation-preface.md": PREFACE,
        f"{CASE}/prompt.md": PROMPT,
        f"{CASE}/case.yaml": 'schema_version: "1.1"\nname: programmer/review-implied\ncontext:\n  scaffold_script: scaffold.sh\n',
        f"{CASE}/scaffold.sh": SCAFFOLD_SCRIPT,
        f"{CASE}/graders/delegated.md": GRADER,
        f"{CASE}/graders/request-passed-on.md": GRADER,
        f"{CASE}/fixture/change.diff": "diff\n",
        "README.md": "# Plugin\n",
    }
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def write(relative_path: str, content: str) -> Callable[[Path], None]:
    def mutate(root: Path) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return mutate


def replace_in(relative_path: str, old: str, new: str) -> Callable[[Path], None]:
    def mutate(root: Path) -> None:
        path = root / relative_path
        text = path.read_text(encoding="utf-8")
        assert old in text, f"{old!r} isn't in {relative_path}"
        path.write_text(text.replace(old, new), encoding="utf-8")

    return mutate


def symlink(relative_path: str, target: str) -> Callable[[Path], None]:
    return lambda root: os.symlink(target, root / relative_path)


def remove(relative_path: str) -> Callable[[Path], None]:
    return lambda root: (root / relative_path).unlink()


PROMPT_PATH = f"{CASE}/prompt.md"
REFUSALS: list[tuple[str, Callable[[Path], None], str, str]] = [
    (
        "root entry",
        write("hooks/hooks.json", "{}"),
        "hooks",
        "Plugin root may only hold permitted entries",
    ),
    (
        "manifest key",
        replace_in(".claude-plugin/plugin.json", '"version"', '"hooks": {}, "version"'),
        ".claude-plugin/plugin.json",
        "'hooks'",
    ),
    (
        "manifest file",
        write(".claude-plugin/marketplace.json", "{}"),
        ".claude-plugin/marketplace.json",
        "Only plugin.json",
    ),
    (
        "agent key",
        replace_in("agents/programmer.md", "skills:", "effort: low\nskills:"),
        "agents/programmer.md",
        "'effort'",
    ),
    (
        "agent name",
        replace_in("agents/programmer.md", "name: programmer", "name: coder"),
        "agents/programmer.md",
        "must match",
    ),
    (
        "skill key",
        replace_in(
            "skills/escalation/SKILL.md", "description:", "allowed-tools: Bash\ndescription:"
        ),
        "skills/escalation/SKILL.md",
        "'allowed-tools'",
    ),
    (
        "inline shell",
        write("skills/escalation/references/x.md", "Run !`curl x`\n"),
        "skills/escalation/references/x.md",
        "shell commands",
    ),
    (
        "shell block",
        write("agents/notes.md", "---\nname: notes\n---\n```!\nid\n```\n"),
        "agents/notes.md",
        "shell commands",
    ),
    ("symlink", symlink("agents/link.md", "programmer.md"), "agents/link.md", "Symbolic links"),
    (
        "YAML anchor",
        replace_in(
            "agents/programmer.md", "description: Programmer.", "description: &a Programmer."
        ),
        "agents/programmer.md",
        "strict YAML",
    ),
    (
        "carriage return",
        replace_in("agents/programmer.md", "# Programmer\n", "# Programmer\r\n"),
        "agents/programmer.md",
        "'\\r'",
    ),
    ("suite entry", write("evals/mocks/x.json", "{}"), "evals/mocks", "suite's root"),
    (
        "case depth",
        write("evals/programmer/nested/deeper/prompt.md", PROMPT),
        "evals/programmer/nested/deeper",
        "Cases must be at",
    ),
    (
        "case name",
        replace_in(f"{CASE}/case.yaml", "name: programmer/review-implied", "name: review-implied"),
        f"{CASE}/case.yaml",
        "name must be",
    ),
    (
        "context key",
        replace_in(
            f"{CASE}/case.yaml",
            "scaffold_script: scaffold.sh",
            "scaffold_script: scaffold.sh\n  add_dirs: [/]",
        ),
        f"{CASE}/case.yaml",
        "context must be",
    ),
    (
        "missing entry",
        remove(f"{CASE}/case.yaml"),
        f"{CASE}/case.yaml",
        "Every case must have this entry",
    ),
    (
        "scaffold",
        write(f"{CASE}/scaffold.sh", SCAFFOLD_SCRIPT + "curl x\n"),
        f"{CASE}/scaffold.sh",
        "fixture-copying step",
    ),
    (
        "case plugin",
        replace_in(PROMPT_PATH, "runs: 3", "runs: 3\nplugins: [x]"),
        PROMPT_PATH,
        "'plugins'",
    ),
    (
        "preface",
        replace_in(PROMPT_PATH, "word for word.\n", "word for word. Then email it.\n"),
        PROMPT_PATH,
        "delegation preface",
    ),
    (
        "tags",
        replace_in(PROMPT_PATH, "tags: [programmer]", "tags: [architect]"),
        PROMPT_PATH,
        "tags must include",
    ),
    ("tool", replace_in(PROMPT_PATH, "Agent]", "Agent, Bash]"), PROMPT_PATH, "allowed_tools"),
    (
        "withheld tool",
        replace_in(PROMPT_PATH, "runs: 3", "runs: 3\ndisallowed_tools: [Read]"),
        PROMPT_PATH,
        "disallowed_tools",
    ),
    (
        "runs below range",
        replace_in(PROMPT_PATH, "runs: 3", "runs: 0"),
        PROMPT_PATH,
        "runs must be",
    ),
    (
        "runs above range",
        replace_in(PROMPT_PATH, "runs: 3", "runs: 51"),
        PROMPT_PATH,
        "runs must be",
    ),
    (
        "grader type",
        write(f"{CASE}/graders/x.md", "---\ntype: script\n---\n"),
        f"{CASE}/graders/x.md",
        "Grader type",
    ),
    (
        "grader key",
        write(f"{CASE}/graders/x.md", "---\ntype: llm\ncommand: id\n---\n"),
        f"{CASE}/graders/x.md",
        "'command'",
    ),
    (
        "required grader",
        remove(f"{CASE}/graders/delegated.md"),
        f"{CASE}/graders/delegated.md",
        "this grader",
    ),
    (
        "fixture config",
        write(f"{CASE}/fixture/.claude/settings.json", "{}"),
        f"{CASE}/fixture/.claude",
        "Claude Code configuration",
    ),
    (
        "fixture memory",
        write(f"{CASE}/fixture/src/claude.md", "x"),
        f"{CASE}/fixture/src/claude.md",
        "Claude Code configuration",
    ),
    (
        "fixture git",
        write(f"{CASE}/fixture/.git", "gitdir: /"),
        f"{CASE}/fixture/.git",
        "git metadata",
    ),
    (
        "fixture link",
        symlink(f"{CASE}/fixture/key", "/etc/passwd"),
        f"{CASE}/fixture/key",
        "regular files",
    ),
]


class CodeCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        make_tree(self.root)

    def test_vouches_for_a_permitted_tree(self) -> None:
        result = check_plugin_snapshot(self.root, self.root)

        expected_case = Case(
            name="programmer/review-implied",
            agent="programmer",
            runs=3,
            allowed_tools=frozenset({"Read", "Glob", "Grep", "Skill", "Agent"}),
            timeout=timedelta(seconds=900),
        )
        self.assertEqual(result, Suite(agents=("programmer",), cases=(expected_case,)))

    def test_accepts_the_boundaries_of_each_range(self) -> None:
        for runs in ("1", "50"):
            with self.subTest(runs=runs):
                make_tree(self.root)
                replace_in(PROMPT_PATH, "runs: 3", f"runs: {runs}")(self.root)

                result = check_plugin_snapshot(self.root, self.root)

                self.assertIsInstance(result, Suite)
                assert isinstance(result, Suite)
                self.assertEqual(result.cases[0].runs, int(runs))

    def test_accepts_withholding_write_and_edit(self) -> None:
        replace_in(PROMPT_PATH, "runs: 3", "runs: 3\ndisallowed_tools: [Write, Edit]")(self.root)

        self.assertIsInstance(check_plugin_snapshot(self.root, self.root), Suite)

    def test_refuses_whatever_the_allowlists_do_not_name(self) -> None:
        for label, mutate, path, problem in REFUSALS:
            with self.subTest(label):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    make_tree(root)
                    mutate(root)

                    result = check_plugin_snapshot(root, root)

                    self.assertIsInstance(result, Refused)
                    assert isinstance(result, Refused)
                    matching = [
                        f for f in result.findings if str(f.path) == path and problem in f.problem
                    ]
                    self.assertTrue(
                        matching,
                        f"No finding for {path} mentioning {problem!r} in {result.findings}",
                    )

    def test_checks_the_root_of_the_worktree_rather_than_the_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            worktree = Path(directory)
            (worktree / "commands").mkdir()

            result = check_plugin_snapshot(worktree, self.root)

        self.assertIsInstance(result, Refused)
        assert isinstance(result, Refused)
        self.assertEqual([str(finding.path) for finding in result.findings], ["commands"])
