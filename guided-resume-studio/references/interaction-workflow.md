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

At intake, tell the user plainly: the knowledge base keeps every confirmed fact, including material not used in the current resume; unused facts are not deleted and can be reused for later target jobs; nothing leaves the local workspace.

## Decision autonomy

Apply the decision rules in [Job research and grounded rewriting](research-and-rewrite.md): selection, ordering, compression and emphasis are autonomous; only conflicts, disclosure boundaries, fact promotion and equally-ranked narrative directions go to the user. Do not turn rankable content choices into questions.

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

If content or presentation changes after approval, follow the amendment policy below instead of automatically re-running the full approval.

## Amendment policy after approval

Classify every post-approval change before touching anything:

- **Minor (class M)**: typo fixes, punctuation, whitespace and wording polish that change no fact, metric, date, entity, ATS keyword mapping, emphasis span, section order or layout parameter. Apply directly without a new user approval round: edit the content, rerun the preview to obtain fresh hashes, copy them into `approval.json` and add an `amendment` object (`{"class": "M", "summary": "...", "previous_content_sha256": "..."}`), re-render the PDF, re-run structural QA and inspect the PNG. Append every before/after pair to `drafts/<job-id>/amendments.jsonl` and show the diff at delivery. The hash trail keeps the change auditable; the classification rules keep it honest.
- **Substantive (class S)**: anything else — new or deleted facts or bullets, changed metrics, emphasis changes, section reordering, layout or typography changes. Show only a compact diff of the affected lines plus the hashes that will change, and ask a single yes/no question. Do not re-present the whole packet.

Batching rule: collect all pending feedback first and apply it in one round with one regeneration. Never loop "regenerate, re-confirm, regenerate" over one-character fixes. When unsure whether a change is class M, treat it as class S — but a typo is always class M.
