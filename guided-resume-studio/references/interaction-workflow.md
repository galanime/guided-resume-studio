# Interaction workflow

## State model

Treat the workflow as resumable states:

`INTAKE -> IMPORT_REVIEW -> FACT_CONFIRMATION -> TARGET_RESEARCH -> RESUME_PLAN -> CONTENT_REVIEW -> APPROVED -> RENDERED -> VERIFIED`

Record the current state in the task summary or workspace. Never skip a confirmation gate because the user asked for speed.

## Intake

Ask no more than three related questions in one round. Start with:

1. Display name.
2. At least one contact method intended for the resume.
3. Career stage, such as student, recent graduate, career changer or experienced hire.

Then ask whether the user will fill the supplied template, paste material, attach files, provide a local path, or use an available read-only knowledge connector. Ask for the preferred resume language only when it is not already clear; default to Chinese and support a separately reviewed English version.

## Fact confirmation

Normalize imported material, then show small batches of facts. Confirm dates, role/scope, quantitative results and disclosure boundaries. Highlight conflicts instead of resolving them by guesswork. The user must see every fact that changes from source-supported to user-verified.

Minimum profile before resume planning:

- non-blank display name;
- at least one contact method;
- at least one substantive education, employment, internship, project, research, course, campus, volunteer, freelance or other experience fact.

## One target per run

Ask for company, role, geography, seniority and JD/link when available. Reuse the verified profile for later jobs, but keep job research, ATS mapping, drafts, approval and output in separate job directories.

## Planning phase

If system Plan mode is active, use it. Otherwise explicitly say that the skill cannot change collaboration mode and run an internal planning conversation that covers:

- official job evidence;
- must-have, important and nice-to-have requirements;
- factual matches and gaps;
- proposed section order and omissions;
- rewrite strategy and ATS terminology;
- `lapiscv-professional-blue-one-page` output intent.

Ask whether the user wants to continue to a draft after presenting that plan.

## Final approval

Before PDF creation, present:

- complete Markdown content;
- professional-blue HTML preview;
- section order and omissions;
- exposed contacts and links;
- summary/headline;
- ATS hits and unsupported gaps;
- high-impact before/after rewrites;
- every emphasis span that will be blue or bold.

Ask for an explicit approval to generate the PDF. Create `approval.json` from the preview manifest only after that response. Copy the exact `content_sha256`, `template_sha256` and `theme_sha256`; set `approved` to true and record an ISO-8601 timestamp. Do not store the whole conversation transcript.

If content or presentation changes after approval, regenerate the preview manifest and request approval again.
