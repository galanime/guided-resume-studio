#!/usr/bin/env python3
"""Render a grounded resume to LapisCV-style HTML/Markdown and approved PDF."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


TEMPLATE_ID = "lapiscv-professional-blue-one-page"
SAFE_BASENAME = re.compile(r"^[^/\\]+$")
EMPHASIS_KINDS = {"label", "metric", "result", "keyword"}


class RenderError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RenderError(f"expected a JSON object in {path}")
    return value


def require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RenderError(f"{field} must be a non-empty string")
    return value.strip()


def validate_resume(data: dict[str, Any]) -> None:
    if data.get("schema_version") != "1.0":
        raise RenderError("schema_version must be 1.0")
    if data.get("template_id") != TEMPLATE_ID:
        raise RenderError(f"template_id must be {TEMPLATE_ID}")
    if data.get("locale") not in {"zh-CN", "en"}:
        raise RenderError("locale must be zh-CN or en")
    basename = data.get("output_basename", "resume")
    if not isinstance(basename, str) or not SAFE_BASENAME.fullmatch(basename) or basename in {".", ".."}:
        raise RenderError("output_basename must be a safe filename without path separators")

    header = data.get("header")
    if not isinstance(header, dict):
        raise RenderError("header must be an object")
    for key in ("display_name", "headline", "summary"):
        require_text(header.get(key), f"header.{key}")
    contacts = header.get("contacts")
    if not isinstance(contacts, list) or not contacts:
        raise RenderError("header.contacts must contain at least one public contact")
    for index, contact in enumerate(contacts):
        require_text(contact, f"header.contacts[{index}]")

    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        raise RenderError("sections must contain at least one non-empty section")
    for section_index, section in enumerate(sections):
        if not isinstance(section, dict):
            raise RenderError(f"sections[{section_index}] must be an object")
        require_text(section.get("section_id"), f"sections[{section_index}].section_id")
        require_text(section.get("title"), f"sections[{section_index}].title")
        entries = section.get("entries")
        direct_bullets = section.get("bullets")
        if not entries and not direct_bullets:
            raise RenderError(f"sections[{section_index}] is empty; omit it instead of rendering an empty heading")
        if entries is not None:
            if not isinstance(entries, list) or not entries:
                raise RenderError(f"sections[{section_index}].entries must be a non-empty array")
            for entry_index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    raise RenderError(f"sections[{section_index}].entries[{entry_index}] must be an object")
                require_text(entry.get("title"), f"sections[{section_index}].entries[{entry_index}].title")
                validate_bullets(entry.get("bullets"), f"sections[{section_index}].entries[{entry_index}].bullets")
        if direct_bullets is not None:
            validate_bullets(direct_bullets, f"sections[{section_index}].bullets")


def validate_bullets(value: Any, field: str) -> None:
    if not isinstance(value, list) or not value:
        raise RenderError(f"{field} must be a non-empty array")
    for index, bullet in enumerate(value):
        prefix = f"{field}[{index}]"
        if not isinstance(bullet, dict):
            raise RenderError(f"{prefix} must be an object")
        text_value = require_text(bullet.get("text"), f"{prefix}.text")
        fact_ids = bullet.get("fact_ids")
        if not isinstance(fact_ids, list) or not fact_ids or any(not isinstance(item, str) or not item for item in fact_ids):
            raise RenderError(f"{prefix}.fact_ids must contain at least one fact id")
        emphasis = bullet.get("emphasis", [])
        if not isinstance(emphasis, list) or len(emphasis) > 3:
            raise RenderError(f"{prefix}.emphasis must contain at most three spans")
        locations: list[tuple[int, int]] = []
        emphasized_chars = 0
        for span_index, span in enumerate(emphasis):
            if not isinstance(span, dict):
                raise RenderError(f"{prefix}.emphasis[{span_index}] must be an object")
            span_text = require_text(span.get("text"), f"{prefix}.emphasis[{span_index}].text")
            if span.get("kind") not in EMPHASIS_KINDS:
                raise RenderError(f"{prefix}.emphasis[{span_index}].kind is invalid")
            if text_value.count(span_text) != 1:
                raise RenderError(f"{prefix}: emphasized text {span_text!r} must occur exactly once")
            start = text_value.index(span_text)
            end = start + len(span_text)
            if any(start < prior_end and end > prior_start for prior_start, prior_end in locations):
                raise RenderError(f"{prefix}: emphasis spans may not overlap")
            locations.append((start, end))
            emphasized_chars += len(span_text)
        if emphasis and emphasized_chars / len(text_value) > 0.36:
            raise RenderError(f"{prefix}: emphasized text exceeds about one third of the bullet")


def iter_bullets(data: dict[str, Any]):
    for section in data["sections"]:
        for entry in section.get("entries", []):
            yield from entry["bullets"]
        yield from section.get("bullets", [])


def validate_grounding(resume: dict[str, Any], profile: dict[str, Any], ats_map: dict[str, Any]) -> None:
    identity = profile.get("identity")
    facts = profile.get("facts")
    if not isinstance(identity, dict) or not isinstance(facts, list):
        raise RenderError("profile.json must contain identity and facts")
    if identity.get("display_name") != resume["header"]["display_name"]:
        raise RenderError("resume display name does not match profile.json")
    public_contacts = {item.get("value") for item in identity.get("contacts", []) if isinstance(item, dict) and item.get("public") is True}
    if not set(resume["header"]["contacts"]).issubset(public_contacts):
        raise RenderError("resume contains a contact not marked public in profile.json")

    fact_by_id: dict[str, dict[str, Any]] = {}
    for fact in facts:
        if not isinstance(fact, dict) or not isinstance(fact.get("fact_id"), str):
            raise RenderError("every profile fact must have a fact_id")
        if fact["fact_id"] in fact_by_id:
            raise RenderError(f"duplicate profile fact id: {fact['fact_id']}")
        fact_by_id[fact["fact_id"]] = fact
    experience_categories = {
        "education", "employment", "internship", "project", "research", "coursework",
        "campus", "volunteer", "freelance", "publication", "other",
    }
    if not any(fact.get("status") == "user_verified" and fact.get("category") in experience_categories for fact in facts):
        raise RenderError("minimum generation threshold not met: add one user-verified education or real-experience fact")

    keywords = ats_map.get("keywords")
    if ats_map.get("schema_version") != "1.0" or not isinstance(keywords, list):
        raise RenderError("ats-map.json must have schema_version 1.0 and a keywords array")
    keyword_by_id: dict[str, dict[str, Any]] = {}
    for keyword in keywords:
        if not isinstance(keyword, dict) or not isinstance(keyword.get("keyword_id"), str):
            raise RenderError("every ATS keyword must have a keyword_id")
        if keyword.get("status") not in {"covered", "gap"}:
            raise RenderError(f"ATS keyword {keyword['keyword_id']} has an invalid status")
        if keyword["keyword_id"] in keyword_by_id:
            raise RenderError(f"duplicate ATS keyword id: {keyword['keyword_id']}")
        keyword_by_id[keyword["keyword_id"]] = keyword

    for bullet in iter_bullets(resume):
        bullet_fact_ids = set(bullet["fact_ids"])
        for fact_id in bullet_fact_ids:
            fact = fact_by_id.get(fact_id)
            if fact is None:
                raise RenderError(f"bullet references unknown fact_id {fact_id}")
            if fact.get("status") != "user_verified":
                raise RenderError(f"bullet fact {fact_id} is not user_verified")
        for keyword_id in bullet.get("keyword_ids", []):
            keyword = keyword_by_id.get(keyword_id)
            if keyword is None:
                raise RenderError(f"bullet references unknown keyword_id {keyword_id}")
            if keyword.get("status") != "covered":
                raise RenderError(f"unsupported ATS keyword {keyword_id} is a gap and cannot enter the resume")
            support = set(keyword.get("fact_ids", []))
            if not support.intersection(bullet_fact_ids):
                raise RenderError(f"ATS keyword {keyword_id} is not supported by this bullet's fact_ids")


def emphasize_html(text_value: str, emphasis: list[dict[str, str]]) -> str:
    spans: list[tuple[int, int, str]] = []
    for item in emphasis:
        start = text_value.index(item["text"])
        spans.append((start, start + len(item["text"]), item["kind"]))
    result: list[str] = []
    cursor = 0
    for start, end, kind in sorted(spans):
        result.append(html.escape(text_value[cursor:start]))
        css_class = "emphasis-label" if kind == "label" else f"emphasis-{kind}"
        tag = "span" if kind == "label" else "strong"
        result.append(f'<{tag} class="{css_class}">{html.escape(text_value[start:end])}</{tag}>')
        cursor = end
    result.append(html.escape(text_value[cursor:]))
    return "".join(result)


def emphasize_markdown(text_value: str, emphasis: list[dict[str, str]]) -> str:
    spans: list[tuple[int, int]] = []
    for item in emphasis:
        start = text_value.index(item["text"])
        spans.append((start, start + len(item["text"])))
    result: list[str] = []
    cursor = 0
    for start, end in sorted(spans):
        result.extend((text_value[cursor:start], "**", text_value[start:end], "**"))
        cursor = end
    result.append(text_value[cursor:])
    return "".join(result)


def render_sections_html(sections: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for section in sections:
        chunks.append(f'<section class="resume-section" data-section-id="{html.escape(section["section_id"])}">')
        chunks.append(f'<h2 class="section-title">{html.escape(section["title"])}</h2>')
        for entry in section.get("entries", []):
            chunks.append('<div class="resume-entry">')
            chunks.append('<div class="entry-heading">')
            chunks.append(f'<h3 class="entry-title">{html.escape(entry["title"])}</h3>')
            if entry.get("meta"):
                chunks.append(f'<div class="entry-meta">{html.escape(entry["meta"])}</div>')
            chunks.append("</div>")
            if entry.get("summary"):
                chunks.append(f'<div class="entry-summary">{html.escape(entry["summary"])}</div>')
            chunks.append(render_bullets_html(entry["bullets"]))
            chunks.append("</div>")
        if section.get("bullets"):
            chunks.append(render_bullets_html(section["bullets"]))
        chunks.append("</section>")
    return "\n".join(chunks)


def render_bullets_html(bullets: list[dict[str, Any]]) -> str:
    body = ["<ul class=\"resume-bullets\">"]
    for bullet in bullets:
        fact_ids = " ".join(html.escape(item) for item in bullet["fact_ids"])
        keyword_ids = " ".join(html.escape(item) for item in bullet.get("keyword_ids", []))
        content = emphasize_html(bullet["text"], bullet.get("emphasis", []))
        body.append(f'<li data-fact-ids="{fact_ids}" data-keyword-ids="{keyword_ids}">{content}</li>')
    body.append("</ul>")
    return "\n".join(body)


def render_sections_markdown(sections: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for section in sections:
        chunks.append(f"## {section['title']}")
        for entry in section.get("entries", []):
            line = f"### {entry['title']}"
            if entry.get("meta"):
                line += f" <span class=\"entry-meta\">{entry['meta']}</span>"
            chunks.append(line)
            if entry.get("summary"):
                chunks.append(entry["summary"])
            chunks.extend(f"- {emphasize_markdown(b['text'], b.get('emphasis', []))}" for b in entry["bullets"])
        chunks.extend(f"- {emphasize_markdown(b['text'], b.get('emphasis', []))}" for b in section.get("bullets", []))
        chunks.append("")
    return "\n".join(chunks).rstrip()


def browser_candidates(explicit: str | None) -> list[Path]:
    values: list[str] = []
    if explicit:
        values.append(explicit)
    if os.environ.get("GUIDED_RESUME_CHROMIUM"):
        values.append(os.environ["GUIDED_RESUME_CHROMIUM"])
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
        located = shutil.which(name)
        if located:
            values.append(located)
    values.extend([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    ])
    return [Path(item).expanduser() for item in dict.fromkeys(values)]


def find_browser(explicit: str | None) -> Path:
    for candidate in browser_candidates(explicit):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    raise RenderError("Chrome, Edge, or Chromium was not found. Install one or set GUIDED_RESUME_CHROMIUM.")


def font_candidates(explicit: str | None, environment_name: str, bold: bool) -> list[Path]:
    values: list[str] = []
    if explicit:
        values.append(explicit)
    if os.environ.get(environment_name):
        values.append(os.environ[environment_name])
    suffix = "Bold" if bold else "Regular"
    values.extend([
        str(Path.home() / f"Library/Fonts/NotoSansCJKsc-{suffix}.ttf"),
        str(Path.home() / f"Library/Fonts/NotoSansCJKsc-{suffix}.otf"),
        str(Path.home() / f"Library/Fonts/Microsoft Yahei{' Bold' if bold else ''}.ttf"),
        f"/usr/share/fonts/truetype/noto/NotoSansCJKsc-{suffix}.ttf",
        f"C:/Windows/Fonts/msyh{'bd' if bold else ''}.ttc",
    ])
    if shutil.which("fc-match"):
        for query in (
            "Noto Sans CJK SC:style=Bold" if bold else "Noto Sans CJK SC:style=Regular",
            "PingFang SC:style=Semibold" if bold else "PingFang SC:style=Regular",
        ):
            completed = subprocess.run(
                ["fc-match", "-f", "%{file}\n", query], check=False, capture_output=True, text=True, timeout=10
            )
            matched = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
            if "Noto Sans" in query:
                values.extend(path for path in matched if Path(path).suffix.lower() in {".ttf", ".ttc"})
            else:
                values.extend(matched)
    values.extend([
        f"/usr/share/fonts/opentype/noto/NotoSansCJKsc-{suffix}.otf",
        f"/usr/share/fonts/opentype/source-han-sans/SourceHanSansCN-{suffix}.otf",
    ])
    return [Path(item).expanduser() for item in dict.fromkeys(values)]


def find_font(explicit: str | None, environment_name: str, bold: bool) -> Path:
    acceptable = ("notosanscjk", "notosanssc", "sourcehansans", "pingfang", "msyh", "microsoft yahei")
    for candidate in font_candidates(explicit, environment_name, bold):
        if candidate.is_file() and any(marker in candidate.name.lower() for marker in acceptable):
            return candidate.resolve()
    weight = "bold" if bold else "regular"
    raise RenderError(
        f"an approved {weight} CJK font file was not found; install Noto Sans CJK SC or set {environment_name}"
    )


def font_family(path: Path) -> str:
    lowered = path.name.lower()
    if "pingfang" in lowered:
        return "PingFang SC"
    if "sourcehan" in lowered:
        return "Source Han Sans CN"
    if "msyh" in lowered or "microsoft yahei" in lowered:
        return "Microsoft YaHei"
    return "Noto Sans CJK SC"


def expected_pdf_text(resume: dict[str, Any]) -> str:
    header = resume["header"]
    lines = [header["display_name"], header["headline"], " · ".join(header["contacts"]), header["summary"]]
    for section in resume["sections"]:
        lines.append(section["title"])
        for entry in section.get("entries", []):
            lines.append(entry["title"] + (f" {entry['meta']}" if entry.get("meta") else ""))
            if entry.get("summary"):
                lines.append(entry["summary"])
            lines.extend(f"· {bullet['text']}" for bullet in entry["bullets"])
        lines.extend(f"· {bullet['text']}" for bullet in section.get("bullets", []))
    return "\n".join(lines)


def repair_pdf_unicode(pdf_path: Path, resume: dict[str, Any]) -> dict[str, Any]:
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import NameObject
    except ImportError as exc:
        raise RenderError("pypdf is required to repair Chromium CJK ToUnicode maps") from exc

    reader = PdfReader(str(pdf_path))
    actual_text = "\n".join((page.extract_text() or "") for page in reader.pages)
    expected_text = expected_pdf_text(resume)
    actual_chars = [character for character in actual_text if not character.isspace()]
    expected_chars = [character for character in expected_text if not character.isspace()]
    if len(actual_chars) != len(expected_chars):
        raise RenderError(
            f"cannot safely repair PDF Unicode: extracted/source character counts differ ({len(actual_chars)} vs {len(expected_chars)})"
        )
    replacements: dict[str, str] = {}
    for actual, expected in zip(actual_chars, expected_chars):
        if actual == expected:
            continue
        prior = replacements.get(actual)
        if prior is not None and prior != expected:
            raise RenderError(f"cannot safely repair ambiguous PDF glyph mapping {actual!r}: {prior!r} vs {expected!r}")
        replacements[actual] = expected

    changed_streams = 0
    for page in reader.pages:
        resources = page.get("/Resources") or {}
        fonts = resources.get("/Font") or {}
        for font_reference in fonts.values():
            font = font_reference.get_object()
            to_unicode_reference = font.get("/ToUnicode")
            if to_unicode_reference is None:
                continue
            stream = to_unicode_reference.get_object()
            data = stream.get_data()
            updated = data
            for actual, expected in replacements.items():
                source_hex = actual.encode("utf-16-be").hex().upper().encode("ascii")
                target_hex = expected.encode("utf-16-be").hex().upper().encode("ascii")
                pattern = re.compile(rb"(<[0-9A-Fa-f]+>\s+)<" + source_hex + rb">")
                updated = pattern.sub(lambda match: match.group(1) + b"<" + target_hex + b">", updated)
            if updated != data:
                stream._data = updated
                stream.pop(NameObject("/Filter"), None)
                stream.pop(NameObject("/DecodeParms"), None)
                changed_streams += 1

    if replacements and not changed_streams:
        raise RenderError("PDF Unicode mappings need repair, but no ToUnicode stream could be updated")
    temporary = pdf_path.with_suffix(".unicode-repaired.tmp.pdf")
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    with temporary.open("wb") as handle:
        writer.write(handle)
    os.replace(temporary, pdf_path)

    repaired = PdfReader(str(pdf_path))
    repaired_text = "\n".join((page.extract_text() or "") for page in repaired.pages)
    repaired_chars = [character for character in repaired_text if not character.isspace()]
    if repaired_chars != expected_chars:
        raise RenderError("PDF Unicode repair did not reproduce the approved source text exactly")
    return {"replacements": replacements, "changed_streams": changed_streams}


def find_pypdf_python() -> Path:
    candidates = [Path(sys.executable)]
    candidates.extend(Path.home().glob(".cache/codex-runtimes/*/dependencies/python/bin/python3"))
    for candidate in candidates:
        if not candidate.is_file():
            continue
        completed = subprocess.run(
            [str(candidate), "-c", "import pypdf"], check=False, capture_output=True, text=True, timeout=10
        )
        if completed.returncode == 0:
            return candidate.resolve()
    raise RenderError("pypdf is unavailable; load the Codex workspace dependencies before formal PDF generation")


def repair_pdf_with_available_python(pdf_path: Path, input_path: Path) -> dict[str, Any]:
    python = find_pypdf_python()
    completed = subprocess.run(
        [str(python), str(Path(__file__).resolve()), "--unicode-repair-only", "--input", str(input_path), "--pdf", str(pdf_path)],
        check=False, capture_output=True, text=True, timeout=60,
    )
    if completed.returncode != 0:
        raise RenderError(f"PDF Unicode repair failed: {(completed.stderr or completed.stdout).strip()[-1000:]}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RenderError("PDF Unicode repair returned an invalid report") from exc


def browser_version(browser: Path) -> str:
    try:
        completed = subprocess.run([str(browser), "--version"], check=False, capture_output=True, text=True, timeout=10)
        return (completed.stdout or completed.stderr).strip()
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def print_pdf(browser: Path, html_path: Path, pdf_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="guided-resume-chrome-") as profile:
        command = [
            str(browser), "--headless=new", "--disable-gpu", "--no-sandbox",
            "--allow-file-access-from-files",
            f"--user-data-dir={profile}", "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri(),
        ]
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
        )
        deadline = time.monotonic() + 60
        previous_size = -1
        stable_checks = 0
        while process.poll() is None and time.monotonic() < deadline:
            size = pdf_path.stat().st_size if pdf_path.exists() else 0
            if size > 1000 and size == previous_size:
                stable_checks += 1
            else:
                stable_checks = 0
            previous_size = size
            if stable_checks >= 4:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait(timeout=3)
                break
            time.sleep(0.25)
        if process.poll() is None:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=3)
        stdout, stderr = process.communicate(timeout=3)
    if not pdf_path.exists() or pdf_path.stat().st_size < 1000:
        detail = (stderr or stdout).strip()[-1000:]
        raise RenderError(f"browser PDF generation failed or timed out: {detail}")


def approval_matches(approval: dict[str, Any], hashes: dict[str, str]) -> bool:
    return (
        approval.get("approved") is True
        and approval.get("template_id") == TEMPLATE_ID
        and approval.get("content_sha256") == hashes["content_sha256"]
        and approval.get("template_sha256") == hashes["template_sha256"]
        and approval.get("theme_sha256") == hashes["theme_sha256"]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="resume.json")
    parser.add_argument("--profile", type=Path, help="Verified knowledge/profile.json")
    parser.add_argument("--ats-map", type=Path, help="Grounded jobs/<job-id>/ats-map.json")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--approval", type=Path, help="Required for formal PDF generation")
    parser.add_argument("--preview-only", action="store_true", help="Write Markdown and HTML only")
    parser.add_argument("--chromium", help="Explicit browser executable")
    parser.add_argument("--font-regular", help="Explicit approved CJK regular font file")
    parser.add_argument("--font-bold", help="Explicit approved CJK bold font file")
    parser.add_argument("--asset-dir", type=Path, default=Path(__file__).resolve().parents[1] / "assets" / "lapiscv")
    parser.add_argument("--unicode-repair-only", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--pdf", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        if args.unicode_repair_only:
            if args.input is None or args.pdf is None:
                raise RenderError("--unicode-repair-only requires --input and --pdf")
            report = repair_pdf_unicode(args.pdf, load_json(args.input))
            print(json.dumps(report, ensure_ascii=False))
            return 0
        if args.input is None or args.profile is None or args.ats_map is None or args.output_dir is None:
            raise RenderError("normal rendering requires --input, --profile, --ats-map, and --output-dir")
        resume = load_json(args.input)
        validate_resume(resume)
        profile = load_json(args.profile)
        ats_map = load_json(args.ats_map)
        validate_grounding(resume, profile, ats_map)
        asset_dir = args.asset_dir.resolve()
        template_path = asset_dir / "template.md"
        main_css_path = asset_dir / "main.css"
        theme_css_path = asset_dir / "professional-blue.css"
        theme_json_path = asset_dir / "theme.json"
        for path in (template_path, main_css_path, theme_css_path, theme_json_path):
            if not path.is_file():
                raise RenderError(f"missing render asset: {path}")

        template_text = template_path.read_text(encoding="utf-8")
        main_css = main_css_path.read_text(encoding="utf-8")
        theme_css = theme_css_path.read_text(encoding="utf-8")
        theme_json = load_json(theme_json_path)
        font_regular = find_font(args.font_regular, "GUIDED_RESUME_FONT_REGULAR", bold=False)
        font_bold = find_font(args.font_bold, "GUIDED_RESUME_FONT_BOLD", bold=True)
        regular_family = font_family(font_regular)
        bold_family = font_family(font_bold)
        font_regular_hash = sha256_file(font_regular)
        font_bold_hash = sha256_file(font_bold)
        hashes = {
            "content_sha256": sha256_bytes(canonical_bytes(resume)),
            "template_sha256": sha256_bytes((template_text + "\n" + main_css).encode("utf-8")),
            "theme_sha256": sha256_bytes(
                canonical_bytes(theme_json) + theme_css.encode("utf-8")
                + regular_family.encode("utf-8") + bold_family.encode("utf-8")
                + font_regular_hash.encode("ascii") + font_bold_hash.encode("ascii")
                + b"chromium-cjk-unicode-repair-v1"
            ),
            "profile_sha256": sha256_bytes(canonical_bytes(profile)),
            "ats_map_sha256": sha256_bytes(canonical_bytes(ats_map)),
        }

        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        basename = resume.get("output_basename", "resume")
        header = resume["header"]
        md_sections = render_sections_markdown(resume["sections"])
        markdown = template_text
        markdown = markdown.replace("{{display_name}}", header["display_name"])
        markdown = markdown.replace("{{headline}}", header["headline"])
        markdown = markdown.replace("{{contact}}", " · ".join(header["contacts"]))
        markdown = markdown.replace("{{summary}}", header["summary"])
        markdown = markdown.replace("{{sections}}", md_sections)

        document_title = html.escape(resume.get("document_title") or f"{header['display_name']} - {header['headline']}")
        embedded_font_css = f"""
@font-face {{ font-family: 'Guided Resume CJK'; src: local('{regular_family}'), url('{font_regular.as_uri()}'); font-weight: 400; font-style: normal; }}
@font-face {{ font-family: 'Guided Resume CJK'; src: local('{bold_family}'), url('{font_bold.as_uri()}'); font-weight: 700; font-style: normal; }}
:root {{ --text-font: '{regular_family}', 'Noto Sans CJK SC', sans-serif; --title-font: '{bold_family}', 'Noto Sans CJK SC', sans-serif; }}
"""
        html_document = f"""<!doctype html>
<html lang=\"{html.escape(resume['locale'])}\">
<head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{document_title}</title><style>{main_css}\n{theme_css}\n{embedded_font_css}</style></head>
<body><main class=\"resume-page\">
<header class=\"resume-header\"><h1>{html.escape(header['display_name'])}</h1>
<div class=\"target-headline\">{html.escape(header['headline'])}</div>
<div class=\"contact-line\">{'<span class="contact-item"> · </span>'.join(html.escape(c) for c in header['contacts'])}</div>
<div class=\"profile-summary\">{html.escape(header['summary'])}</div></header>
{render_sections_html(resume['sections'])}
</main></body></html>"""

        md_path = output_dir / f"{basename}.md"
        html_path = output_dir / f"{basename}.html"
        json_path = output_dir / "resume.json"
        md_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
        html_path.write_text(html_document, encoding="utf-8")
        json_path.write_text(json.dumps(resume, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        approval_template = {
            "approved": False,
            "template_id": TEMPLATE_ID,
            **hashes,
            "approved_at": None,
            "approved_by": None,
        }
        preview_manifest = {
            "template_id": TEMPLATE_ID,
            **hashes,
            "files": {"markdown": md_path.name, "html": html_path.name, "resume_json": json_path.name},
            "fonts": {
                "regular": {"path": str(font_regular), "sha256": font_regular_hash},
                "bold": {"path": str(font_bold), "sha256": font_bold_hash}
            },
            "approval_template": approval_template,
        }
        (output_dir / "preview-manifest.json").write_text(
            json.dumps(preview_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        result: dict[str, Any] = {"mode": "preview", "output_dir": str(output_dir), "hashes": hashes}
        if not args.preview_only:
            if args.approval is None:
                raise RenderError("formal PDF generation requires --approval after the user approves the preview")
            approval = load_json(args.approval)
            if not approval_matches(approval, hashes):
                raise RenderError("approval is missing, false, or stale; regenerate the preview and obtain approval for its exact hashes")
            browser = find_browser(args.chromium)
            pdf_path = output_dir / f"{basename}.pdf"
            print_pdf(browser, html_path, pdf_path)
            unicode_repair = repair_pdf_with_available_python(pdf_path, args.input.resolve())
            build_report = {
                "status": "rendered_unverified",
                "pdf": pdf_path.name,
                "pdf_sha256": sha256_file(pdf_path),
                "browser": str(browser),
                "browser_version": browser_version(browser),
                "fonts": {
                    "regular": {"path": str(font_regular), "sha256": font_regular_hash},
                    "bold": {"path": str(font_bold), "sha256": font_bold_hash}
                },
                "approval": str(args.approval.resolve()),
                "unicode_repair": unicode_repair,
                **hashes,
            }
            (output_dir / "build-report.json").write_text(
                json.dumps(build_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            result.update({"mode": "formal-pdf", "pdf": str(pdf_path), "status": "rendered_unverified"})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except RenderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
