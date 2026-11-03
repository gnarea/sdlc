"""Validate every skill in a directory against the Agent Skills specification.

`skills-ref validate` rejects any frontmatter field that the specification
doesn't define, including those that Claude Code adds, so this script drops
Claude Code's fields before passing the frontmatter to `skills-ref`.
"""

import sys
from pathlib import Path

import strictyaml
from skills_ref.validator import ALLOWED_FIELDS, validate_metadata

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

FRONTMATTER_DELIMITER = "---"


def main() -> int:
    skills_directory = Path(sys.argv[1])
    errors_by_skill = _validate_skills(skills_directory)
    _report(skills_directory, errors_by_skill)
    return 0 if errors_by_skill and not any(errors_by_skill.values()) else 1


def _validate_skills(skills_directory: Path) -> dict[Path, list[str]]:
    skill_directories = sorted(path for path in skills_directory.iterdir() if path.is_dir())
    return {directory: _validate_skill(directory) for directory in skill_directories}


def _validate_skill(skill_directory: Path) -> list[str]:
    skill_md = skill_directory / "SKILL.md"
    if not skill_md.is_file():
        return ["Missing required file: SKILL.md"]

    try:
        skill_md_content = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        return [f"SKILL.md must be encoded in UTF-8 ({error})"]

    frontmatter, errors = _parse_frontmatter(skill_md_content)
    if errors:
        return errors

    frontmatter = _drop_claude_code_fields(frontmatter)
    return validate_metadata(frontmatter, skill_directory) + _validate_optional_fields(frontmatter)


def _parse_frontmatter(skill_md_content: str) -> tuple[dict[str, object], list[str]]:
    lines = skill_md_content.splitlines()
    if not lines or lines[0] != FRONTMATTER_DELIMITER:
        return {}, [f"SKILL.md must start with YAML frontmatter ({FRONTMATTER_DELIMITER})"]
    if FRONTMATTER_DELIMITER not in lines[1:]:
        return {}, [f"SKILL.md frontmatter must be closed with {FRONTMATTER_DELIMITER}"]

    closing_line_index = lines.index(FRONTMATTER_DELIMITER, 1)
    frontmatter_yaml = "\n".join(lines[1:closing_line_index])
    try:
        frontmatter = strictyaml.dirty_load(frontmatter_yaml, allow_flow_style=True).data
    except strictyaml.YAMLError as error:
        return {}, [f"Invalid YAML in frontmatter: {error}"]

    if not isinstance(frontmatter, dict):
        return {}, [f"SKILL.md frontmatter must be a map (got {type(frontmatter).__name__})"]
    return frontmatter, []


def _drop_claude_code_fields(frontmatter: dict[str, object]) -> dict[str, object]:
    # A field that the specification adopts from Claude Code must then observe the specification.
    return {
        field: value
        for field, value in frontmatter.items()
        if field in ALLOWED_FIELDS or field not in CLAUDE_CODE_FRONTMATTER_FIELDS
    }


def _validate_optional_fields(frontmatter: dict[str, object]) -> list[str]:
    errors = []
    if "license" in frontmatter and not isinstance(frontmatter["license"], str):
        errors.append(
            f"Field 'license' must be a string (got {type(frontmatter['license']).__name__})"
        )
    if frontmatter.get("compatibility") == "":
        errors.append("Field 'compatibility' must not be empty")
    if "metadata" in frontmatter:
        errors.extend(_validate_metadata_field(frontmatter["metadata"]))
    if "allowed-tools" in frontmatter and not isinstance(frontmatter["allowed-tools"], str):
        errors.append(
            "Field 'allowed-tools' must be a space-separated string "
            f"(got {type(frontmatter['allowed-tools']).__name__})"
        )
    return errors


def _validate_metadata_field(metadata: object) -> list[str]:
    if not isinstance(metadata, dict):
        return [f"Field 'metadata' must be a map (got {type(metadata).__name__})"]
    return [
        f"Field 'metadata' must map '{key}' to a string (got {type(value).__name__})"
        for key, value in metadata.items()
        if not isinstance(value, str)
    ]


def _report(skills_directory: Path, errors_by_skill: dict[Path, list[str]]) -> None:
    if not errors_by_skill:
        print(f"No skills found in {skills_directory}")

    for skill_directory, errors in errors_by_skill.items():
        if not errors:
            print(f"Valid skill: {skill_directory}")
            continue

        print(f"Validation failed for {skill_directory}:")
        for error in errors:
            print(f"  - {error}")


if __name__ == "__main__":
    sys.exit(main())
