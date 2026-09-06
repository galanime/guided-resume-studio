#!/usr/bin/env python3
"""Validate one-page A4 resume PDFs and render a PNG for visual inspection."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def squash_whitespace(value: str) -> str:
    return re.sub(r"\s+", "", value)


def cjk_present(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def visual_note_complete(note: str, locale: str) -> tuple[bool, list[str]]:
    groups = {
        "clipping": ("裁切", "clipping"),
        "overlap": ("重叠", "overlap"),
        "glyphs": ("缺字", "missing glyph"),
        "dates": ("日期", "date"),
        "orphan headings": ("孤立标题", "orphan heading"),
        "natural wrapping": ("自然断行", "natural wrap"),
        "header": ("页眉", "header"),
        "indentation": ("缩进", "indent"),
        "whitespace": ("留白", "whitespace"),
    }
    lowered = note.lower()
    missing = [label for label, terms in groups.items() if not any(term.lower() in lowered for term in terms)]
    return not missing, missing


def expected_texts(resume: dict[str, Any]) -> list[str]:
    values = [resume["header"]["display_name"], resume["header"]["headline"]]
    values.extend(resume["header"].get("contacts", []))
    values.append(resume["header"]["summary"])
    for section in resume.get("sections", []):
        values.append(section["title"])
        for entry in section.get("entries", []):
            values.append(entry["title"])
            if entry.get("summary"):
                values.append(entry["summary"])
            values.extend(item["text"] for item in entry.get("bullets", []))
        values.extend(item["text"] for item in section.get("bullets", []))
    return [compact(value) for value in values if isinstance(value, str) and value.strip()]


def walk_font_names(value: Any, found: set[str], seen: set[int]) -> None:
    identity = id(value)
    if identity in seen:
        return
    seen.add(identity)
    try:
        from pypdf.generic import DictionaryObject, IndirectObject
    except ImportError:
        return
    if isinstance(value, IndirectObject):
        try:
            walk_font_names(value.get_object(), found, seen)
        except Exception:
            return
    elif isinstance(value, DictionaryObject):
        for key in ("/BaseFont", "/FontName", "/FontFamily"):
            font_name = value.get(key)
            if font_name:
                found.add(str(font_name).lstrip("/"))
        for item in value.values():
            walk_font_names(item, found, seen)
    elif isinstance(value, (list, tuple)):
        for item in value:
            walk_font_names(item, found, seen)


def find_pdftoppm(explicit: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("GUIDED_RESUME_PDFTOPPM"):
        candidates.append(Path(os.environ["GUIDED_RESUME_PDFTOPPM"]).expanduser())
    located = shutil.which("pdftoppm")
    if located:
        candidates.append(Path(located))
    candidates.extend(Path.home().glob(".cache/codex-runtimes/*/dependencies/bin/override/pdftoppm"))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--content", type=Path, required=True, help="Approved resume.json")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--png-dir", type=Path, required=True)
    parser.add_argument("--pdftoppm")
    parser.add_argument("--visual-approved", action="store_true", help="Set only after inspecting the rendered PNG")
    parser.add_argument("--visual-note", default="")
    args = parser.parse_args()

    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        from pypdf import PdfReader
    except ImportError:
        print("error: pypdf is required for PDF validation", file=sys.stderr)
        return 2

    try:
        resume = json.loads(args.content.read_text(encoding="utf-8"))
        reader = PdfReader(str(args.pdf))
    except Exception as exc:
        print(f"error: cannot open validation inputs: {exc}", file=sys.stderr)
        return 2

    page_count = len(reader.pages)
    checks.append({"id": "page_count", "passed": page_count == 1, "actual": page_count, "expected": 1})
    if page_count != 1:
        errors.append(f"PDF must be exactly one page; found {page_count}")

    extracted = "\n".join((page.extract_text() or "") for page in reader.pages)
    normalized_extracted = compact(extracted)
    whitespace_free_extracted = squash_whitespace(extracted)
    no_replacement = "\ufffd" not in extracted
    checks.append({"id": "no_replacement_characters", "passed": no_replacement})
    if not no_replacement:
        errors.append("PDF text contains Unicode replacement characters")

    if page_count:
        width = float(reader.pages[0].mediabox.width)
        height = float(reader.pages[0].mediabox.height)
        a4 = abs(width - 595.28) <= 3 and abs(height - 841.89) <= 3
        checks.append({"id": "a4_page_size", "passed": a4, "actual_points": [round(width, 2), round(height, 2)]})
        if not a4:
            errors.append(f"PDF is not A4: {width:.2f} x {height:.2f} points")

    missing: list[str] = []
    for value in expected_texts(resume):
        if squash_whitespace(value) not in whitespace_free_extracted:
            missing.append(value)
    text_ok = bool(normalized_extracted) and not missing
    checks.append({"id": "approved_text_extractable", "passed": text_ok, "missing": missing})
    if not normalized_extracted:
        errors.append("PDF has no extractable text")
    elif missing:
        errors.append(f"PDF is missing {len(missing)} approved text fragment(s)")

    contacts = resume.get("header", {}).get("contacts", [])
    separator_expected = max(0, len(contacts) - 1)
    separator_actual = extracted.count("｜")
    expected_contact_line = "｜".join(contacts)
    separator_ok = (
        separator_actual >= separator_expected
        and (not expected_contact_line or squash_whitespace(expected_contact_line) in whitespace_free_extracted)
    )
    checks.append({
        "id": "contact_separator_extractable",
        "passed": separator_ok,
        "expected_minimum": separator_expected,
        "actual": separator_actual,
        "contact_line": expected_contact_line,
    })
    if not separator_ok:
        errors.append("PDF contact line is missing one or more extractable ｜ separators")

    build_path = args.pdf.resolve().parent / "build-report.json"
    theme_consistency = None
    if build_path.is_file():
        try:
            theme_consistency = json.loads(build_path.read_text(encoding="utf-8")).get("theme_consistency")
        except (OSError, json.JSONDecodeError):
            theme_consistency = None
    theme_ok = isinstance(theme_consistency, dict) and theme_consistency.get("passed") is True
    checks.append({"id": "theme_css_consistency", "passed": theme_ok, "details": theme_consistency})
    if not theme_ok:
        errors.append("build-report.json does not prove theme.json and CSS configuration consistency")

    fonts: set[str] = set()
    for page in reader.pages:
        walk_font_names(page.get("/Resources"), fonts, set())
    font_blob = " ".join(sorted(fonts)).lower()
    forbidden = [name for name in ("wawa", "xingkai", "kaiti", "comic") if name in font_blob]
    cjk_required = resume.get("locale") == "zh-CN" and any(cjk_present(item) for item in expected_texts(resume))
    cjk_font_markers = ("notosanscjk", "sourcehan", "pingfang", "yahei")
    cjk_font_ok = not cjk_required or any(marker in font_blob for marker in cjk_font_markers)
    font_ok = bool(fonts) and not forbidden and cjk_font_ok
    checks.append({
        "id": "font_embedding_and_fallback",
        "passed": font_ok,
        "fonts": sorted(fonts),
        "forbidden_matches": forbidden,
        "cjk_font_required": cjk_required,
    })
    if not fonts:
        errors.append("No embedded font resources were detected")
    if forbidden:
        errors.append(f"Forbidden/decorative font detected: {', '.join(forbidden)}")
    if not cjk_font_ok:
        errors.append("Chinese content does not use an approved CJK font fallback")

    png_dir = args.png_dir.resolve()
    png_dir.mkdir(parents=True, exist_ok=True)
    pdftoppm = find_pdftoppm(args.pdftoppm)
    png_path: Path | None = None
    render_ok = False
    if pdftoppm:
        prefix = png_dir / args.pdf.stem
        completed = subprocess.run(
            [str(pdftoppm), "-png", "-r", "144", "-singlefile", str(args.pdf.resolve()), str(prefix)],
            check=False, capture_output=True, text=True, timeout=60,
        )
        png_path = prefix.with_suffix(".png")
        render_ok = completed.returncode == 0 and png_path.is_file() and png_path.stat().st_size > 1000
        if not render_ok:
            errors.append(f"Poppler could not render the PDF: {(completed.stderr or completed.stdout).strip()[-500:]}")
    else:
        errors.append("pdftoppm was not found; install Poppler or set GUIDED_RESUME_PDFTOPPM")
    checks.append({"id": "poppler_png_render", "passed": render_ok, "png": str(png_path) if png_path else None})

    structural_passed = not errors
    visual_status = "approved" if args.visual_approved else "pending"
    note = args.visual_note.strip()
    note_complete, missing_note_topics = visual_note_complete(note, str(resume.get("locale", "")))
    if args.visual_approved and not note:
        errors.append("--visual-note is required when --visual-approved is set")
    elif args.visual_approved and not note_complete:
        errors.append("--visual-note is missing whole-page review topics: " + ", ".join(missing_note_topics))
    checks.append({
        "id": "visual_inspection",
        "passed": args.visual_approved and bool(note) and note_complete,
        "status": visual_status,
        "note": note,
        "missing_note_topics": missing_note_topics if args.visual_approved else [],
        "required_checks": [
            "no clipping", "no overlap", "no missing glyphs", "no date collision", "no orphan heading",
            "natural wrapping confirmed", "consistent header", "consistent indentation", "balanced whitespace",
        ],
    })
    passed = structural_passed and args.visual_approved and bool(note) and note_complete
    report = {
        "schema_version": "1.0",
        "passed": passed,
        "status": "final" if passed else ("visual_review_pending" if structural_passed else "failed"),
        "visual_review": visual_status,
        "pdf": str(args.pdf.resolve()),
        "checks": checks,
        "errors": errors,
        "extracted_text_characters": len(extracted),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if passed:
        return 0
    if structural_passed:
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
