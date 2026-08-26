#!/usr/bin/env python3
"""Seal an approved, QA-passed resume output with a reproducible provenance bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TEMPLATE_ID = "lapiscv-professional-blue-one-page"


class SnapshotError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SnapshotError(f"expected a JSON object in {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def copy_file(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source == destination.resolve(strict=False):
        return
    shutil.copy2(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--content", type=Path, required=True, help="Approved resume.json")
    parser.add_argument("--profile", type=Path, required=True, help="Verified profile.json used for grounding")
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--qa-report", type=Path, required=True)
    parser.add_argument("--ats-report", type=Path)
    parser.add_argument("--research", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--renderer", type=Path, default=Path(__file__).resolve().with_name("render_lapiscv.py"))
    parser.add_argument("--asset-dir", type=Path, default=Path(__file__).resolve().parents[1] / "assets" / "lapiscv")
    args = parser.parse_args()

    try:
        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        content = load_json(args.content)
        profile = load_json(args.profile)
        approval = load_json(args.approval)
        qa = load_json(args.qa_report)
        build_path = output_dir / "build-report.json"
        build = load_json(build_path)

        if content.get("template_id") != TEMPLATE_ID:
            raise SnapshotError(f"content template_id must be {TEMPLATE_ID}")
        if approval.get("approved") is not True:
            raise SnapshotError("approval.json does not record explicit user approval")
        for key in ("content_sha256", "template_sha256", "theme_sha256"):
            if not approval.get(key) or approval.get(key) != build.get(key):
                raise SnapshotError(f"approval {key} does not match the rendered build")
        if qa.get("passed") is not True or qa.get("status") != "final" or qa.get("visual_review") != "approved":
            raise SnapshotError("qa-report.json must pass structural and visual validation before snapshotting")
        if build.get("profile_sha256") != canonical_json_sha256(profile):
            raise SnapshotError("profile.json no longer matches the grounded render")

        rendered_pdf_name = build.get("pdf")
        if not isinstance(rendered_pdf_name, str) or Path(rendered_pdf_name).name != rendered_pdf_name:
            raise SnapshotError("build-report.json contains an unsafe or missing PDF filename")
        rendered_pdf = output_dir / rendered_pdf_name
        if not rendered_pdf.is_file():
            raise SnapshotError(f"rendered PDF is missing: {rendered_pdf}")
        if build.get("pdf_sha256") != sha256_file(rendered_pdf):
            raise SnapshotError("rendered PDF hash no longer matches build-report.json")

        canonical_pdf = output_dir / "resume.pdf"
        canonical_json = output_dir / "resume.json"
        canonical_md = output_dir / "resume.md"
        copy_file(rendered_pdf, canonical_pdf)
        copy_file(args.content, canonical_json)
        source_md = output_dir / f"{content.get('output_basename', 'resume')}.md"
        if not source_md.is_file():
            raise SnapshotError(f"rendered Markdown is missing: {source_md}")
        copy_file(source_md, canonical_md)
        copy_file(args.qa_report, output_dir / "qa-report.json")
        if args.ats_report:
            copy_file(args.ats_report, output_dir / "ats-report.json")
        elif not (output_dir / "ats-report.json").is_file():
            raise SnapshotError("an ATS report is required for the final output")
        ats_report = load_json(output_dir / "ats-report.json")
        if build.get("ats_map_sha256") != canonical_json_sha256(ats_report):
            raise SnapshotError("ATS report no longer matches the grounded render")

        provenance = output_dir / "provenance"
        provenance.mkdir(parents=True, exist_ok=True)
        copy_file(args.approval, provenance / "approval.json")
        copy_file(args.profile, provenance / "profile.json")
        copy_file(output_dir / "ats-report.json", provenance / "ats-map.json")
        copy_file(args.renderer, provenance / "render_lapiscv.py")
        assets_destination = provenance / "lapiscv-template"
        if assets_destination.exists():
            shutil.rmtree(assets_destination)
        shutil.copytree(args.asset_dir.resolve(), assets_destination)
        if args.research:
            copy_file(args.research, provenance / "research.json")
        if args.source_manifest:
            copy_file(args.source_manifest, provenance / "source-manifest.json")

        rebuild = provenance / "rebuild.sh"
        rebuild.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "PROVENANCE_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
            "OUTPUT_DIR=\"$(dirname \"$PROVENANCE_DIR\")\"\n"
            "PYTHON_BIN=\"${PYTHON_BIN:-python3}\"\n"
            "\"$PYTHON_BIN\" \"$PROVENANCE_DIR/render_lapiscv.py\" \\\n"
            "  --input \"$OUTPUT_DIR/resume.json\" \\\n"
            "  --profile \"$PROVENANCE_DIR/profile.json\" \\\n"
            "  --ats-map \"$PROVENANCE_DIR/ats-map.json\" \\\n"
            "  --approval \"$PROVENANCE_DIR/approval.json\" \\\n"
            "  --asset-dir \"$PROVENANCE_DIR/lapiscv-template\" \\\n"
            "  --output-dir \"$OUTPUT_DIR/rebuilt\"\n",
            encoding="utf-8",
        )
        rebuild.chmod(rebuild.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        tracked: list[Path] = [
            canonical_pdf, canonical_md, canonical_json, output_dir / "ats-report.json",
            output_dir / "qa-report.json", build_path, provenance / "approval.json",
            provenance / "profile.json", provenance / "ats-map.json",
            provenance / "render_lapiscv.py", rebuild,
        ]
        tracked.extend(sorted(path for path in assets_destination.rglob("*") if path.is_file()))
        for optional in (provenance / "research.json", provenance / "source-manifest.json"):
            if optional.is_file():
                tracked.append(optional)

        manifest = {
            "schema_version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "template_id": TEMPLATE_ID,
            "approval": {
                "approved": True,
                "approved_at": approval.get("approved_at"),
                "approved_by": approval.get("approved_by"),
                "content_sha256": approval["content_sha256"],
                "template_sha256": approval["template_sha256"],
                "theme_sha256": approval["theme_sha256"],
            },
            "browser": build.get("browser"),
            "browser_version": build.get("browser_version"),
            "files": [
                {"path": path.relative_to(output_dir).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size}
                for path in tracked
            ],
            "rebuild_command": "PYTHON_BIN=python3 ./provenance/rebuild.sh",
        }
        manifest_path = provenance / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "final", "output_dir": str(output_dir), "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
        return 0
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
