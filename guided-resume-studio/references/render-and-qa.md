# LapisCV professional-blue rendering and QA

## Two-stage rendering

1. Preview: run `render_lapiscv.py --input <resume.json> --profile <profile.json> --ats-map <ats-map.json> --output-dir <dir> --preview-only`. It writes Markdown, HTML and `preview-manifest.json`, but never a PDF.
2. Final: after explicit user approval, create `approval.json` with the exact preview hashes and run the same command with `--approval <approval.json>` instead of `--preview-only`.

The renderer rejects missing, false or stale approval, non-public contacts, non-verified fact IDs, and ATS keywords marked as gaps. It locates Chrome, Edge or Chromium through `--chromium`, `GUIDED_RESUME_CHROMIUM`, `PATH` and common installation paths. Do not silently fall back to a different PDF engine.

Chromium/Skia may outline CJK OTF glyphs as Type3 fonts and choose compatibility ideographs in the generated `ToUnicode` map. After Chromium prints, the renderer uses the approved source text to repair only those Unicode mappings, verifies an exact source-to-extracted-text match, and records the replacements in `build-report.json`. This requires `pypdf`; in Codex Desktop, load the bundled workspace dependencies. Stop if the mapping is ambiguous or character counts differ. Do not normalize the candidate's source text or replace the Chrome-generated page geometry.

## Fixed design

- template: `lapiscv-professional-blue-one-page`;
- A4, 13 mm top/bottom and 15 mm left/right margins;
- accent `#1a56db`;
- heading `#1e293b`;
- body `#334155`;
- muted `#64748b`;
- rule `#e2e8f0`;
- CJK font preference: Noto Sans CJK SC, Source Han Sans CN, PingFang SC, Microsoft YaHei, sans-serif.

Keep LapisCV geometry and dynamic sections. Do not add an empty section, a second theme or automatic two-page mode. Do not reduce the configured text size to force fit. If output exceeds one page, revise content and obtain a new approval.

## Structural validation

Run `validate_resume.py --pdf ... --content ... --report ... --png-dir ...`. It must check:

- exactly one page;
- A4 media box within tolerance;
- extractable name, headline, section titles, entry titles and bullet text;
- no replacement characters;
- no known decorative fallback fonts;
- an acceptable CJK font when Chinese text is present;
- rendered PNG exists.

The first validation intentionally reports visual review as pending. Open every generated page image and inspect at 100% zoom. Check clipping, overlap, missing glyphs, awkward wrapping, over-dense emphasis, dates colliding with titles and large unexplained blank areas. Only then rerun with `--visual-approved`.

## Finalization

Do not mark the PDF final until `qa-report.json` has `passed: true` and `visual_review: approved`. Keep HTML and PNG as QA/provenance material, but the default user deliverables are PDF, Markdown, resume JSON, ATS report and provenance package.
