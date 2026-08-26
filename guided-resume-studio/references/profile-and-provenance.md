# Profile and provenance

## Canonical profile

Use `assets/profile.schema.json` and keep one `knowledge/profile.json`. Also maintain a human-readable `knowledge/profile.md` and append confirmed changes to `knowledge/fact-ledger.jsonl`.

Each fact needs a stable `fact_id`, category, raw description, status and source references. Preserve separate fields for date, organization, role, metrics and tags when they exist. Do not merge conflicting facts into one apparently certain value.

Allowed statuses:

- `user_verified`: the user explicitly confirmed the fact.
- `source_supported`: a readable source supports it, but the user has not yet confirmed a risky detail.
- `unverified`: imported or inferred but not confirmed.
- `conflicted`: two or more sources disagree.
- `do_not_disclose`: accurate or possible, but excluded from generated materials.

Only `user_verified` facts may support final claims. A `source_supported` fact can be promoted only after showing the source-bound value to the user and receiving confirmation.

## Import policy

Read only materials the user places in scope. PDF and DOCX import should use available document/PDF extraction tools and visual inspection when layout changes meaning. For directories, inventory likely career files first and ask before processing a very large or unrelated tree.

Do not copy an entire external knowledge base by default. `source-manifest.json` stores:

- `source_id`;
- local path or URL;
- media type;
- SHA-256 when local content is available;
- access/import time;
- short notes about the facts actually used.

For pasted text, save a minimal local snapshot because there is no stable external path. Never persist credentials, cookies, tokens, identity-document numbers or unrelated private records.

## Workspace

Use `scripts/init_workspace.py --root <current-workspace> --candidate-id <safe-id>`. It creates files only when missing and must not overwrite a profile or source manifest.

Expected structure:

```text
resume-workspace/<candidate-id>/
  knowledge/
  jobs/<job-id>/
  drafts/<job-id>/
  outputs/<job-id>/<timestamp>/
```

## Claim ledger

Every final bullet in `resume.json` carries `fact_ids` and optional `keyword_ids`. `change-map.md` must make the chain readable:

`source fact -> selected job requirement -> rewritten claim -> emphasis -> final section`

Unsupported keywords remain gaps. Do not create a fact record merely to justify text already drafted.

## Run snapshot

After PDF and QA pass, call `scripts/snapshot_run.py --profile <profile.json> --ats-report <ats-map.json> ...`. The provenance directory must include the exact verified profile snapshot, ATS map, renderer, template, CSS, theme, MIT license, approval, manifest and executable rebuild command. Treat provenance as private because it contains candidate data. Hash every delivered and rebuild-critical file. Do not claim deterministic rebuild across different Chromium versions; record the browser path and version reported by the renderer.
