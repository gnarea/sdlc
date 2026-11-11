"""Allowlists for the plugin under test: its root, its manifest, and its agents' and skills' metadata.

A kind of plugin component that these lists don't name is refused, so that one that a new Claude
Code brings
in can't run code until a reviewed change to the suite allows it.
"""

import json
import re
from pathlib import Path, PurePosixPath

from .frontmatter import MalformedDocument, parse_markdown, read_exactly
from .model import Finding

PERMITTED_ROOT_ENTRIES = frozenset(
    {
        ".claude-plugin",
        ".cspell.jsonc",
        ".git",
        ".github",
        ".gitignore",
        ".markdownlint-cli2.jsonc",
        ".venv",
        "CLAUDE.md",
        "LICENSE",
        "README.md",
        "agents",
        "evals",
        "node_modules",
        "package-lock.json",
        "package.json",
        "pyproject.toml",
        "skills",
        "uv.lock",
    }
)
PERMITTED_MANIFEST_KEYS = frozenset({"name", "description", "version", "author"})
PERMITTED_AGENT_KEYS = frozenset({"name", "description", "skills"})
PERMITTED_SKILL_KEYS = frozenset({"name", "description"})

_INLINE_SHELL_COMMAND = re.compile(r"!`")
_SHELL_COMMAND_BLOCK = re.compile(r"^\s*(`{3,}|~{3,})!", re.MULTILINE)
_MANIFEST_PATH = PurePosixPath(".claude-plugin/plugin.json")


def check_root(worktree: Path) -> list[Finding]:
    """Refuse any entry at the plugin's root that the allowlist doesn't name, since Claude Code
    loads components from there.
    """
    return [
        Finding(PurePosixPath(entry.name), "Plugin root may only hold permitted entries")
        for entry in sorted(worktree.iterdir())
        if entry.name not in PERMITTED_ROOT_ENTRIES
    ]


def check_plugin(root: Path) -> tuple[tuple[str, ...], list[Finding]]:
    """Return the plugin's agent names, and whatever the allowlists refuse."""
    findings = _check_manifest(root) + _check_symlinks(root)
    agents, agent_findings = _check_agents(root)
    findings += agent_findings + _check_skills(root)
    for directory in ("agents", "skills"):
        findings += _check_shell_commands(root, directory)
    return agents, findings


def _check_manifest(root: Path) -> list[Finding]:
    plugin_directory = root / ".claude-plugin"
    findings = [
        Finding(PurePosixPath(".claude-plugin") / entry.name, "Only plugin.json is permitted here")
        for entry in sorted(plugin_directory.iterdir())
        if entry.name != "plugin.json"
    ]
    try:
        manifest = json.loads((root / _MANIFEST_PATH).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return findings + [
            Finding(_MANIFEST_PATH, f"Manifest must be readable JSON ({error.__class__.__name__})")
        ]
    if not isinstance(manifest, dict):
        return findings + [
            Finding(
                _MANIFEST_PATH, f"Manifest must be a JSON object (got {type(manifest).__name__})"
            )
        ]
    return findings + [
        Finding(
            _MANIFEST_PATH,
            f"Manifest may only declare metadata, so that only the default agents and skills directories hold components (got key {key!r})",
        )
        for key in sorted(manifest)
        if key not in PERMITTED_MANIFEST_KEYS
    ]


def _check_symlinks(root: Path) -> list[Finding]:
    return [
        Finding(
            PurePosixPath(path.relative_to(root).as_posix()), "Symbolic links are not permitted"
        )
        for directory in (".claude-plugin", "agents", "skills", "evals")
        for path in sorted((root / directory).rglob("*"))
        if path.is_symlink()
    ]


def _check_agents(root: Path) -> tuple[tuple[str, ...], list[Finding]]:
    agents: list[str] = []
    findings: list[Finding] = []
    for entry in sorted((root / "agents").iterdir()):
        relative_path = PurePosixPath("agents") / entry.name
        if not entry.is_file() or entry.suffix != ".md":
            findings.append(
                Finding(relative_path, "The agents directory may only hold Markdown files")
            )
            continue
        frontmatter, problem = _read_frontmatter(entry)
        if problem is not None:
            findings.append(Finding(relative_path, problem))
            continue
        findings += _check_keys(relative_path, frontmatter, PERMITTED_AGENT_KEYS, "Agent metadata")
        if frontmatter.get("name") != entry.stem:
            findings.append(
                Finding(
                    relative_path,
                    f"Agent name must match its file name (got {frontmatter.get('name')!r})",
                )
            )
        agents.append(entry.stem)
    return tuple(agents), findings


def _check_skills(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for entry in sorted((root / "skills").iterdir()):
        relative_path = PurePosixPath("skills") / entry.name / "SKILL.md"
        if not entry.is_dir() or not (entry / "SKILL.md").is_file():
            findings.append(
                Finding(relative_path.parent, "Each skill must be a directory with a SKILL.md")
            )
            continue
        frontmatter, problem = _read_frontmatter(entry / "SKILL.md")
        if problem is not None:
            findings.append(Finding(relative_path, problem))
            continue
        findings += _check_keys(relative_path, frontmatter, PERMITTED_SKILL_KEYS, "Skill metadata")
    return findings


def _read_frontmatter(path: Path) -> tuple[dict[str, object], str | None]:
    try:
        return parse_markdown(read_exactly(path)).frontmatter, None
    except (OSError, UnicodeDecodeError) as error:
        return {}, f"Must be readable UTF-8 ({error.__class__.__name__})"
    except MalformedDocument as error:
        return {}, f"Must be Markdown with strict YAML frontmatter ({error})"


def _check_keys(
    path: PurePosixPath, frontmatter: dict[str, object], permitted: frozenset[str], kind: str
) -> list[Finding]:
    return [
        Finding(path, f"{kind} may only use permitted keys (got {key!r})")
        for key in sorted(frontmatter)
        if key not in permitted
    ]


def _check_shell_commands(root: Path, directory: str) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted((root / directory).rglob("*")):
        if not path.is_file():
            continue
        relative_path = PurePosixPath(path.relative_to(root).as_posix())
        try:
            text = read_exactly(path)
        except (OSError, UnicodeDecodeError):
            findings.append(Finding(relative_path, "Agent and skill files must be UTF-8 text"))
            continue
        if _INLINE_SHELL_COMMAND.search(text) or _SHELL_COMMAND_BLOCK.search(text):
            findings.append(
                Finding(relative_path, "Agents and skills must not embed shell commands")
            )
    return findings
