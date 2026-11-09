"""Allowlists for the case suite: its layout, its case keys, its graders, its fixtures, and the
fixture-copying step.
"""

import re
from datetime import timedelta
from pathlib import Path, PurePosixPath

from .frontmatter import MalformedDocument, parse_markdown, parse_yaml, read_exactly
from .model import Case, Finding

SUITE_DIRECTORY = "evals"
DELEGATION_PREFACE_FILE = "delegation-preface.md"
DELEGATION_PREFACE_AGENT_PLACEHOLDER = "(agent)"

# The harness passes the step no paths: it runs `bash <real path of the script>` from the run's
# workspace.
SCAFFOLD_SCRIPT_NAME = "scaffold.sh"
SCAFFOLD_SCRIPT = """\
#!/usr/bin/env bash
# Copies the case's fixture into the run's workspace, which is the working directory.
set -euo pipefail
cp -R -- "${0%/*}/fixture/." .
"""
CASE_SCHEMA_VERSION = "1.1"

PERMITTED_SUITE_ENTRIES = frozenset(
    {
        ".markdownlint-cli2.jsonc",
        "README.md",
        "architecture.md",
        "threat-model.md",
        DELEGATION_PREFACE_FILE,
        "runner",
        "results",
    }
)
PERMITTED_CASE_ENTRIES = frozenset(
    {"case.yaml", "prompt.md", SCAFFOLD_SCRIPT_NAME, "graders", "fixture"}
)
PERMITTED_CASE_YAML_KEYS = frozenset({"schema_version", "name", "context"})
PERMITTED_PROMPT_KEYS = frozenset(
    {
        "description",
        "tags",
        "runs",
        "max_turns",
        "timeout_seconds",
        "allowed_tools",
        "disallowed_tools",
    }
)
PERMITTED_TOOLS = frozenset({"Read", "Glob", "Grep", "Skill", "Agent", "Write", "Edit"})
# Every run is offered Write and Edit, which bring NotebookEdit with them, so a case can only
# withhold them.
WITHHOLDABLE_TOOLS = frozenset({"Write", "Edit", "NotebookEdit"})
REQUIRED_GRADERS = frozenset({"delegated", "request-passed-on"})
COMMON_GRADER_KEYS = frozenset({"type", "weight", "arm"})
PERMITTED_GRADER_KEYS = {
    "regex": frozenset({"target", "pattern", "flags", "match"}),
    "tool_used": frozenset({"tool", "input_match", "min", "max"}),
    "tool_order": frozenset({"before", "after"}),
    "file_exists": frozenset({"path", "exists"}),
    "llm": frozenset({"criteria", "focus"}),
}
# Claude Code configuration, and git metadata, which can make git run commands in the workspace.
FORBIDDEN_FIXTURE_NAMES = frozenset(
    name.casefold()
    for name in (
        ".claude",
        ".claude.json",
        ".claude-plugin",
        ".mcp.json",
        ".lsp.json",
        "CLAUDE.md",
        "CLAUDE.local.md",
        ".git",
    )
)
# The harness skips these directories when it looks for cases.
HARNESS_SKIPPED_DIRECTORIES = frozenset({".git", "node_modules", ".claude", "results", "mocks"})
CASE_MARKERS = frozenset({"prompt.md", "case.yaml"})

_SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
_RANGES = {"runs": (1, 50), "max_turns": (1, 200), "timeout_seconds": (1, 3600)}


def check_suite(root: Path, agents: tuple[str, ...]) -> tuple[tuple[Case, ...], list[Finding]]:
    """Return the suite's cases, and whatever the allowlists refuse."""
    suite_directory = root / SUITE_DIRECTORY
    preface_template, findings = _read_preface_template(suite_directory)
    findings += _check_suite_entries(suite_directory, agents)
    cases: list[Case] = []
    for case_directory in _find_cases(suite_directory):
        case, case_findings = _check_case(root, case_directory, agents, preface_template)
        findings += case_findings
        if case is not None and not case_findings:
            cases.append(case)
    return tuple(cases), findings


def render_preface(template: str, agent: str) -> str:
    """The preface that every prompt for this agent must start with."""
    return template.strip().replace(DELEGATION_PREFACE_AGENT_PLACEHOLDER, agent)


def _read_preface_template(suite_directory: Path) -> tuple[str, list[Finding]]:
    path = suite_directory / DELEGATION_PREFACE_FILE
    try:
        template = read_exactly(path)
    except (OSError, UnicodeDecodeError) as error:
        return "", [
            Finding(
                _relative(suite_directory.parent, path),
                f"Delegation preface must be readable UTF-8 ({error.__class__.__name__})",
            )
        ]
    if DELEGATION_PREFACE_AGENT_PLACEHOLDER not in template or "\n" in template.strip():
        return "", [
            Finding(
                _relative(suite_directory.parent, path),
                f"Delegation preface must be one line with the {DELEGATION_PREFACE_AGENT_PLACEHOLDER} placeholder",
            )
        ]
    return template, []


def _check_suite_entries(suite_directory: Path, agents: tuple[str, ...]) -> list[Finding]:
    return [
        Finding(
            _relative(suite_directory.parent, entry),
            "The suite's root may only hold permitted entries and one directory per agent",
        )
        for entry in sorted(suite_directory.iterdir())
        if entry.name not in PERMITTED_SUITE_ENTRIES
        and not (entry.is_dir() and entry.name in agents)
    ]


def _find_cases(suite_directory: Path) -> list[Path]:
    """Find every directory that the harness would take for a case, wherever it is."""
    cases: list[Path] = []
    pending = [suite_directory]
    while pending:
        directory = pending.pop()
        entries = sorted(directory.iterdir())
        if any(entry.name in CASE_MARKERS for entry in entries):
            cases.append(directory)
            continue
        pending += [
            entry
            for entry in entries
            if entry.is_dir()
            and not entry.is_symlink()
            and entry.name not in HARNESS_SKIPPED_DIRECTORIES
        ]
    return sorted(cases)


def _check_case(
    root: Path, case_directory: Path, agents: tuple[str, ...], preface_template: str
) -> tuple[Case | None, list[Finding]]:
    relative_path = _relative(root, case_directory)
    parts = relative_path.parts
    if len(parts) != 3 or parts[1] not in agents or not _SLUG.fullmatch(parts[2]):
        return None, [
            Finding(
                relative_path,
                f"Cases must be at {SUITE_DIRECTORY}/(agent)/(case), with a lowercase hyphenated name",
            )
        ]
    agent, case_slug = parts[1], parts[2]
    name = f"{agent}/{case_slug}"
    findings = _check_case_entries(root, case_directory)
    findings += _check_case_yaml(root, case_directory, name)
    findings += _check_scaffold_script(root, case_directory)
    findings += _check_graders(root, case_directory)
    findings += _check_fixture(root, case_directory)
    case, prompt_findings = _check_prompt(root, case_directory, name, agent, preface_template)
    return case, findings + prompt_findings


def _check_case_entries(root: Path, case_directory: Path) -> list[Finding]:
    names = {entry.name for entry in case_directory.iterdir()}
    findings = [
        Finding(_relative(root, case_directory / name), "Cases may only hold permitted entries")
        for name in sorted(names - PERMITTED_CASE_ENTRIES)
    ]
    return findings + [
        Finding(_relative(root, case_directory / name), "Every case must have this entry")
        for name in sorted(PERMITTED_CASE_ENTRIES - names)
    ]


def _check_case_yaml(root: Path, case_directory: Path, name: str) -> list[Finding]:
    path = case_directory / "case.yaml"
    relative_path = _relative(root, path)
    if not path.is_file():
        return []
    try:
        case_yaml = parse_yaml(read_exactly(path))
    except (OSError, UnicodeDecodeError) as error:
        return [Finding(relative_path, f"Must be readable UTF-8 ({error.__class__.__name__})")]
    except MalformedDocument as error:
        return [Finding(relative_path, f"Must be strict YAML ({error})")]
    findings = _keys_outside(relative_path, case_yaml, PERMITTED_CASE_YAML_KEYS, "Case key")
    expected = {
        "schema_version": CASE_SCHEMA_VERSION,
        "name": name,
        "context": {"scaffold_script": SCAFFOLD_SCRIPT_NAME},
    }
    for key, value in expected.items():
        if case_yaml.get(key) != value:
            findings.append(
                Finding(relative_path, f"{key} must be {value!r} (got {case_yaml.get(key)!r})")
            )
    return findings


def _check_scaffold_script(root: Path, case_directory: Path) -> list[Finding]:
    path = case_directory / SCAFFOLD_SCRIPT_NAME
    try:
        is_permitted = (
            path.is_file()
            and not path.is_symlink()
            and path.read_bytes() == SCAFFOLD_SCRIPT.encode()
        )
    except OSError:
        is_permitted = False
    if is_permitted:
        return []
    return [
        Finding(_relative(root, path), "Must be the permitted fixture-copying step, byte for byte")
    ]


def _check_prompt(
    root: Path, case_directory: Path, name: str, agent: str, preface_template: str
) -> tuple[Case | None, list[Finding]]:
    path = case_directory / "prompt.md"
    relative_path = _relative(root, path)
    if not path.is_file():
        return None, []
    try:
        document = parse_markdown(read_exactly(path))
    except (OSError, UnicodeDecodeError) as error:
        return None, [
            Finding(relative_path, f"Must be readable UTF-8 ({error.__class__.__name__})")
        ]
    except MalformedDocument as error:
        return None, [
            Finding(relative_path, f"Must be Markdown with strict YAML frontmatter ({error})")
        ]
    problems = _check_prompt_keys(document.frontmatter, agent)
    numbers, number_problems = _read_numbers(document.frontmatter)
    preface = render_preface(preface_template, agent)
    if preface_template and not document.body.lstrip("\n").startswith(preface + "\n"):
        problems.append(
            f"The prompt must start with the delegation preface, as a paragraph of its own: {preface!r}"
        )
    findings = [Finding(relative_path, problem) for problem in problems + number_problems]
    if findings:
        return None, findings
    case = Case(
        name=name,
        agent=agent,
        runs=numbers["runs"],
        allowed_tools=frozenset(document.frontmatter["allowed_tools"]),  # type: ignore[arg-type]
        timeout=timedelta(seconds=numbers["timeout_seconds"]),
    )
    return case, []


def _check_prompt_keys(frontmatter: dict[str, object], agent: str) -> list[str]:
    problems = [
        f"Case key is not permitted (got {key!r})"
        for key in sorted(frontmatter)
        if key not in PERMITTED_PROMPT_KEYS
    ]
    tags = frontmatter.get("tags")
    if not isinstance(tags, list) or agent not in tags:
        problems.append(f"tags must include {agent!r} (got {tags!r})")
    for key, permitted, default in (
        ("allowed_tools", PERMITTED_TOOLS, None),
        ("disallowed_tools", WITHHOLDABLE_TOOLS, []),
    ):
        tools = frontmatter.get(key, default)
        if not isinstance(tools, list) or not set(tools) <= permitted:
            problems.append(f"{key} must be a list drawn from {sorted(permitted)} (got {tools!r})")
    return problems


def _read_numbers(frontmatter: dict[str, object]) -> tuple[dict[str, int], list[str]]:
    numbers: dict[str, int] = {}
    problems: list[str] = []
    for key, (lower, upper) in _RANGES.items():
        value = frontmatter.get(key)
        if not (isinstance(value, str) and value.isdigit() and lower <= int(value) <= upper):
            problems.append(f"{key} must be an integer from {lower} to {upper} (got {value!r})")
            continue
        numbers[key] = int(value)
    return numbers, problems


def _check_graders(root: Path, case_directory: Path) -> list[Finding]:
    graders_directory = case_directory / "graders"
    if not graders_directory.is_dir():
        return []
    findings: list[Finding] = []
    names: set[str] = set()
    for entry in sorted(graders_directory.iterdir()):
        relative_path = _relative(root, entry)
        if not entry.is_file() or entry.suffix != ".md":
            findings.append(Finding(relative_path, "Graders must be Markdown files"))
            continue
        names.add(entry.stem)
        findings += _check_grader(relative_path, entry)
    findings += [
        Finding(
            _relative(root, graders_directory / f"{name}.md"), "Every case must have this grader"
        )
        for name in sorted(REQUIRED_GRADERS - names)
    ]
    return findings


def _check_grader(relative_path: PurePosixPath, path: Path) -> list[Finding]:
    try:
        frontmatter = parse_markdown(read_exactly(path)).frontmatter
    except (OSError, UnicodeDecodeError) as error:
        return [Finding(relative_path, f"Must be readable UTF-8 ({error.__class__.__name__})")]
    except MalformedDocument as error:
        return [Finding(relative_path, f"Must be Markdown with strict YAML frontmatter ({error})")]
    grader_type = frontmatter.get("type")
    if grader_type not in PERMITTED_GRADER_KEYS:
        return [
            Finding(
                relative_path,
                f"Grader type must be one of {sorted(PERMITTED_GRADER_KEYS)} (got {grader_type!r})",
            )
        ]
    permitted_keys = COMMON_GRADER_KEYS | PERMITTED_GRADER_KEYS[str(grader_type)]
    return _keys_outside(relative_path, frontmatter, permitted_keys, "Grader key")


def _check_fixture(root: Path, case_directory: Path) -> list[Finding]:
    fixture = case_directory / "fixture"
    if not fixture.is_dir() or fixture.is_symlink():
        return []
    findings: list[Finding] = []
    for path in sorted(fixture.rglob("*")):
        relative_path = _relative(root, path)
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            findings.append(
                Finding(relative_path, "Fixtures may only hold regular files and directories")
            )
        elif path.name.casefold() in FORBIDDEN_FIXTURE_NAMES:
            findings.append(
                Finding(
                    relative_path,
                    "Fixtures must not hold Claude Code configuration or git metadata",
                )
            )
    return findings


def _keys_outside(
    path: PurePosixPath, mapping: dict[str, object], permitted: frozenset[str], kind: str
) -> list[Finding]:
    return [
        Finding(path, f"{kind} is not permitted (got {key!r})")
        for key in sorted(mapping)
        if key not in permitted
    ]


def _relative(root: Path, path: Path) -> PurePosixPath:
    return PurePosixPath(path.relative_to(root).as_posix())
