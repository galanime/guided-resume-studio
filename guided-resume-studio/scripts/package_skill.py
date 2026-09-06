#!/usr/bin/env python3
"""Create a distributable .skill archive for guided-resume-studio."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from quick_validate import validate_skill


SKIP_NAMES = {".DS_Store"}
SKIP_PARTS = {"__pycache__", ".pytest_cache", "dist"}


def should_package(path: Path) -> bool:
    if path.name in SKIP_NAMES or path.suffix == ".skill":
        return False
    return not any(part in SKIP_PARTS for part in path.parts)


def package_skill(skill_dir: Path, output_dir: Path | None = None) -> Path:
    skill_dir = skill_dir.resolve()
    valid, message = validate_skill(skill_dir)
    if not valid:
        raise ValueError(message)

    destination_dir = output_dir.resolve() if output_dir else (skill_dir / "dist").resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    archive_path = destination_dir / f"{skill_dir.name}.skill"

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in skill_dir.rglob("*") if path.is_file() and should_package(path)):
            archive.write(file_path, file_path.relative_to(skill_dir.parent))
    return archive_path


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("Usage: package_skill.py <skill_directory> [output_directory]", file=sys.stderr)
        return 1
    skill_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) == 3 else None
    try:
        archive_path = package_skill(skill_dir, output_dir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(str(archive_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
