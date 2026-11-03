"""Validate every skill in a directory against the Agent Skills specification.

`skills-ref validate` rejects any frontmatter field that the specification
doesn't define, including those that Claude Code adds, so this script drops
Claude Code's fields before passing the frontmatter to `skills-ref`.
"""

import sys
from pathlib import Path

from skills_ref.errors import ParseError
from skills_ref.parser import find_skill_md, parse_frontmatter
from skills_ref.validator import validate_metadata

# https://code.claude.com/docs/en/skills#frontmatter-reference
CLAUDE_CODE_FRONTMATTER_FIELDS = frozenset(
    {
        "agent",
        "argument-hint",
        "arguments",
        "background",
        "context",
        "disable-model-invocation",
        "disallowed-tools",
        "effort",
        "hooks",
        "model",
        "paths",
        "shell",
        "user-invocable",
        "when_to_use",
    }
)


def main() -> int:
    errors_by_skill = _validate_skills(Path(sys.argv[1]))
    _report(errors_by_skill)
    return 1 if any(errors_by_skill.values()) else 0


def _validate_skills(skills_directory: Path) -> dict[Path, list[str]]:
    skill_directories = sorted(path for path in skills_directory.iterdir() if path.is_dir())
    return {skill_directory: _validate_skill(skill_directory) for skill_directory in skill_directories}


def _validate_skill(skill_directory: Path) -> list[str]:
    skill_md = find_skill_md(skill_directory)
    if skill_md is None:
        return ["Missing required file: SKILL.md"]

    try:
        frontmatter, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    except ParseError as error:
        return [str(error)]

    specification_fields = {
        field: value
        for field, value in frontmatter.items()
        if field not in CLAUDE_CODE_FRONTMATTER_FIELDS
    }
    errors = validate_metadata(specification_fields, skill_directory)
    errors.extend(_validate_fields_unchecked_by_skills_ref(specification_fields))
    return errors


def _validate_fields_unchecked_by_skills_ref(frontmatter: dict[str, object]) -> list[str]:
    errors = []
    if "allowed-tools" in frontmatter and not isinstance(frontmatter["allowed-tools"], str):
        errors.append("Field 'allowed-tools' must be a space-separated string")
    # `parse_frontmatter` converts every value in the map to a string, so only the map itself can be checked.
    if "metadata" in frontmatter and not isinstance(frontmatter["metadata"], dict):
        errors.append("Field 'metadata' must be a map from string keys to string values")
    return errors


def _report(errors_by_skill: dict[Path, list[str]]) -> None:
    for skill_directory, errors in errors_by_skill.items():
        if not errors:
            print(f"Valid skill: {skill_directory}")
            continue

        print(f"Validation failed for {skill_directory}:")
        for error in errors:
            print(f"  - {error}")


if __name__ == "__main__":
    sys.exit(main())
