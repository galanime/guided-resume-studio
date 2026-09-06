#!/usr/bin/env python3
"""Lightweight structural validation for guided-resume-studio packaging."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_TOP_LEVEL_KEYS = {"name", "description"}
ALLOWED_TOP_LEVEL_KEYS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}
REQUIRED_PATHS = (
    "SKILL.md",
    "README.md",
    "install.sh",
    "references/interaction-workflow.md",
    "references/profile-and-provenance.md",
    "references/research-and-rewrite.md",
    "references/render-and-qa.md",
    "scripts/init_workspace.py",
    "scripts/quick_validate.py",
    "scripts/package_skill.py",
    "scripts/render_lapiscv.py",
    "scripts/validate_resume.py",
    "scripts/snapshot_run.py",
    "assets/lapiscv/LICENSE",
    "assets/lapiscv/main.css",
    "assets/lapiscv/professional-blue.css",
    "assets/lapiscv/template.md",
    "assets/lapiscv/theme.json",
    "assets/profile.schema.json",
    "assets/resume.schema.json",
)


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    content = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", content, re.S)
    if not match:
        raise ValueError("SKILL.md must begin with YAML frontmatter delimited by ---")
    frontmatter = match.group(1)
    keys: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if not line or line[:1].isspace() or line.lstrip().startswith("#"):
            continue
        key_match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if key_match:
            keys[key_match.group(1)] = key_match.group(2).strip()
    return keys


def validate_skill(skill_dir: Path) -> tuple[bool, str]:
    skill_dir = skill_dir.resolve()
    if not skill_dir.is_dir():
        return False, f"skill directory not found: {skill_dir}"

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return False, "SKILL.md not found"

    try:
        frontmatter = parse_frontmatter(skill_md)
    except (OSError, ValueError) as exc:
        return False, str(exc)

    top_level_keys = set(frontmatter)
    missing_keys = sorted(REQUIRED_TOP_LEVEL_KEYS - top_level_keys)
    if missing_keys:
        return False, "missing frontmatter key(s): " + ", ".join(missing_keys)

    unexpected = sorted(top_level_keys - ALLOWED_TOP_LEVEL_KEYS)
    if unexpected:
        return False, "unexpected frontmatter key(s): " + ", ".join(unexpected)

    name = frontmatter.get("name", "")
    if not re.fullmatch(r"[a-z0-9-]{1,64}", name) or name.startswith("-") or name.endswith("-") or "--" in name:
        return False, "frontmatter name must be kebab-case and at most 64 characters"

    description = frontmatter.get("description", "")
    if not description or len(description) > 1024 or "<" in description or ">" in description:
        return False, "frontmatter description must be non-empty, <=1024 chars, and must not contain angle brackets"

    missing_paths = [relative for relative in REQUIRED_PATHS if not (skill_dir / relative).is_file()]
    if missing_paths:
        return False, "missing required skill file(s): " + ", ".join(missing_paths)

    return True, "Skill is valid"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: quick_validate.py <skill_directory>", file=sys.stderr)
        return 1
    valid, message = validate_skill(Path(sys.argv[1]))
    stream = sys.stdout if valid else sys.stderr
    print(message, file=stream)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
