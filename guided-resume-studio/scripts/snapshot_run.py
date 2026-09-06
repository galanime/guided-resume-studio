#!/usr/bin/env python3
"""Seal an approved, QA-passed resume output with a reproducible provenance bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
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


def squash_whitespace(value: str) -> str:
    return "".join(value.split())


def expected_texts(resume: dict[str, Any]) -> list[str]:
    header = resume["header"]
    values = [header["display_name"], header["headline"], *header.get("contacts", []), header["summary"]]
    for section in resume.get("sections", []):
        values.append(section["title"])
        for entry in section.get("entries", []):
            values.append(entry["title"])
            if entry.get("summary"):
                values.append(entry["summary"])
            values.extend(item["text"] for item in entry.get("bullets", []))
        values.extend(item["text"] for item in section.get("bullets", []))
    return [item for item in values if isinstance(item, str) and item.strip()]


def validate_rebuilt_pdf(pdf: Path, resume: dict[str, Any]) -> dict[str, Any]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SnapshotError("pypdf is required for the provenance rebuild smoke test") from exc
    reader = PdfReader(str(pdf))
    if len(reader.pages) != 1:
        raise SnapshotError(f"rebuilt PDF must contain one page; found {len(reader.pages)}")
    width = float(reader.pages[0].mediabox.width)
    height = float(reader.pages[0].mediabox.height)
    if abs(width - 595.28) > 3 or abs(height - 841.89) > 3:
        raise SnapshotError(f"rebuilt PDF is not A4: {width:.2f} x {height:.2f} points")
    extracted = "\n".join((page.extract_text() or "") for page in reader.pages)
    compact = squash_whitespace(extracted)
    missing = [item for item in expected_texts(resume) if squash_whitespace(item) not in compact]
    if missing:
        raise SnapshotError(f"rebuilt PDF is missing {len(missing)} approved text fragment(s)")
    return {"passed": True, "page_count": 1, "a4_points": [round(width, 2), round(height, 2)], "missing": []}


def validate_asset_dir(asset_dir: Path) -> tuple[str, ...]:
    required = ("LICENSE", "main.css", "professional-blue.css", "template.md", "theme.json")
    missing = tuple(name for name in required if not (asset_dir / name).is_file())
    if missing:
        raise SnapshotError("template asset directory is incomplete: " + ", ".join(missing))
    return required


def validate_rebuild_qa_report(report: dict[str, Any]) -> dict[str, Any]:
    checks = report.get("checks")
    if not isinstance(checks, list):
        raise SnapshotError("rebuilt QA report is missing its checks array")
    failed = [
        str(check.get("id"))
        for check in checks
        if check.get("id") != "visual_inspection" and check.get("passed") is not True
    ]
    if failed:
        raise SnapshotError("rebuilt structural QA failed: " + ", ".join(failed))
    status = report.get("status")
    visual_review = report.get("visual_review")
    if status not in {"visual_review_pending", "final"}:
        raise SnapshotError(f"rebuilt QA report has an unexpected status: {status!r}")
    if visual_review not in {"pending", "approved"}:
        raise SnapshotError(f"rebuilt QA report has an unexpected visual_review state: {visual_review!r}")
    return {
        "status": status,
        "visual_review": visual_review,
        "failed_checks": failed,
    }


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
    parser.add_argument("--validator", type=Path, default=Path(__file__).resolve().with_name("validate_resume.py"))
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
        if build.get("theme_consistency", {}).get("passed") is not True:
            raise SnapshotError("build-report.json does not prove theme.json and CSS consistency")
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
        if sha256_file(rendered_pdf) != sha256_file(canonical_pdf):
            raise SnapshotError("named PDF and canonical resume.pdf hashes differ after copying")
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
        copy_file(args.validator, provenance / "validate_resume.py")
        assets_destination = provenance / "lapiscv-template"
        if assets_destination.exists():
            shutil.rmtree(assets_destination)
        asset_dir = args.asset_dir.resolve()
        validate_asset_dir(asset_dir)
        shutil.copytree(asset_dir, assets_destination)
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
            "  --output-dir \"$OUTPUT_DIR/rebuilt\"\n"
            "set +e\n"
            "\"$PYTHON_BIN\" \"$PROVENANCE_DIR/validate_resume.py\" \\\n"
            f"  --pdf \"$OUTPUT_DIR/rebuilt/{rendered_pdf_name}\" \\\n"
            "  --content \"$OUTPUT_DIR/resume.json\" \\\n"
            "  --report \"$OUTPUT_DIR/rebuilt/rebuilt-qa-report.json\" \\\n"
            "  --png-dir \"$OUTPUT_DIR/rebuilt/rebuilt-qa-png\"\n"
            "QA_EXIT=$?\n"
            "set -e\n"
            "if [ \"$QA_EXIT\" -ne 0 ] && [ \"$QA_EXIT\" -ne 3 ]; then\n"
            "  exit \"$QA_EXIT\"\n"
            "fi\n",
            encoding="utf-8",
        )
        rebuild.chmod(rebuild.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        rebuild_env = os.environ.copy()
        rebuild_env["PYTHON_BIN"] = sys.executable
        completed = subprocess.run(
            [str(rebuild)], check=False, capture_output=True, text=True, timeout=120, env=rebuild_env
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-1200:]
            raise SnapshotError(f"provenance rebuild command failed: {detail}")
        rebuilt_pdf = output_dir / "rebuilt" / rendered_pdf_name
        if not rebuilt_pdf.is_file():
            raise SnapshotError(f"provenance rebuild did not create the expected PDF: {rebuilt_pdf}")
        rebuild_smoke = validate_rebuilt_pdf(rebuilt_pdf, content)
        rebuilt_qa_report_path = output_dir / "rebuilt" / "rebuilt-qa-report.json"
        if not rebuilt_qa_report_path.is_file():
            raise SnapshotError("provenance rebuild did not record rebuilt structural QA")
        rebuilt_qa = validate_rebuild_qa_report(load_json(rebuilt_qa_report_path))

        tracked: list[Path] = [
            canonical_pdf, canonical_md, canonical_json, output_dir / "ats-report.json",
            output_dir / "qa-report.json", build_path, provenance / "approval.json",
            provenance / "profile.json", provenance / "ats-map.json",
            provenance / "render_lapiscv.py", provenance / "validate_resume.py", rebuild,
        ]
        tracked.append(rebuilt_qa_report_path)
        rebuilt_png_dir = output_dir / "rebuilt" / "rebuilt-qa-png"
        tracked.extend(sorted(path for path in rebuilt_png_dir.rglob("*") if path.is_file()))
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
            "canonical_pdf_sha256": sha256_file(canonical_pdf),
            "named_pdf_sha256": sha256_file(rendered_pdf),
            "rebuild_smoke": rebuild_smoke,
            "rebuild_structural_qa": rebuilt_qa,
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
