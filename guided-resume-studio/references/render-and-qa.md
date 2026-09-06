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
- refined typography floor: 8.9 pt body text and 1.39 line height;
- contact separator: `｜`; only the `作品集：` label is blue and bold;
- standard and contextual ligatures are disabled so source strings such as `Diff` remain extractable.

Keep LapisCV geometry and dynamic sections. Do not add an empty section, a second theme or automatic two-page mode. Do not reduce the configured text size to force fit. If output exceeds one page, follow the page-fit ladder below before any approval request.

## Page-fit ladder

The default deliverable is exactly one well-filled A4 page. Never present a preview or PDF that obviously overflows or is visibly under-filled.

1. **Measure early.** Run `render_lapiscv.py --fit-check --input <resume.json>` before writing the preview. It reports `fits`, `borderline`, `overflow` or `underfilled` with an estimated usage ratio and the longest bullets as trim candidates. The estimate carries ±8% tolerance; `validate_resume.py` page-count remains the hard check. Every preview manifest also embeds the same `fit_check`.
2. **Overflow — resolve in this order:**
   a. trim or merge the lowest-priority bullets per the decision rules in [Job research and grounded rewriting](research-and-rewrite.md);
   b. compress wording without losing grounded facts;
   c. drop an entire low-priority section or entry;
   d. only if content is already minimal, typography is already at the 8.9 pt / 1.39 floor and may not go lower — instead go back to step a.
3. **Underfilled — resolve in this order:**
   a. pull the strongest unused `user_verified` facts from the knowledge pool (`jobs/<job-id>/selection.json`) and re-rank them against this JD;
   b. expand high-priority bullets with grounded detail already in the fact ledger;
   c. never pad with unverified content.
4. **Still unresolved after the ladder:** ask the user exactly one question with a concrete proposal — a specific cut list or addition list with reasons — then apply the answer in one round. Do not iterate blindly.
5. Re-run `--fit-check` after each adjustment round. Request preview approval only when the status is `fits`, or `borderline` with a written justification in the review packet.

## Amendments and re-rendering

Post-approval changes follow the amendment policy in [Interaction workflow](interaction-workflow.md). Class M (typo-level) amendments skip the user approval round but never skip verification: fresh preview hashes, updated `approval.json` with an `amendment` record, formal re-render, full structural QA, PNG inspection and an `amendments.jsonl` entry. Class S changes require a single compact-diff confirmation. A class M amendment never changes template, CSS, theme, fonts or layout, so it does not require a new visual approval beyond the standard PNG inspection.

The renderer must reject a mismatch between `theme.json` and the CSS values for page margins, body size, line height and heading sizes. Use the effective CSS value as the source of visual truth, then update the metadata to match before generating a preview.

## Structural validation

Run `validate_resume.py --pdf ... --content ... --report ... --png-dir ...`. It must check:

- exactly one page;
- A4 media box within tolerance;
- extractable name, headline, section titles, entry titles and bullet text;
- no replacement characters;
- no known decorative fallback fonts;
- an acceptable CJK font when Chinese text is present;
- rendered PNG exists.

The first validation intentionally reports visual review as pending. Open every generated page image and inspect at 100% zoom. A local correction never authorizes a local-only review: regenerate the whole page and inspect every section and every repeated selector before approval.

Any change to template assets, CSS, theme metadata, font features, contact rendering or layout text requires a fresh whole-page preview and a whole-page review note. Re-check repeated selectors everywhere they appear; do not sign off based only on the region the user highlighted.

Treat wrapping as follows:

- Normal wrapping stays inside the content box, preserves the bullet hanging indent, keeps every glyph visible and does not overlap a date or adjacent element. Natural Chinese line wrapping is not an error.
- Abnormal wrapping includes clipping, horizontal overflow, a detached label or bullet, a date collision, an orphan heading, or a forced break that materially damages meaning.

The `--visual-note` must explicitly record clipping, overlap, missing glyphs, date collisions, orphan headings, whether natural wrapping is acceptable, and the consistency of the header, indentation and page whitespace. Only then rerun with `--visual-approved`.

Any content, CSS, theme, template, font-feature or contact-rendering change invalidates prior approval hashes. Browser zoom and preview URL query parameters do not.

## Finalization

Do not mark the PDF final until `qa-report.json` has `passed: true` and `visual_review: approved`. The fixed sequence is preview approval, formal render, structural QA, inspection of every PNG, `--visual-approved`, then provenance snapshot. The provenance rebuild command must also re-run structural QA on the rebuilt PDF and record that result. Keep HTML and PNG as QA/provenance material, but the default user deliverables are PDF, Markdown, resume JSON, ATS report and provenance package.
