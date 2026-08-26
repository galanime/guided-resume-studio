# Job research and grounded rewriting

## Source priority

1. Exact official job page supplied by the user.
2. Current official company career page for the same requisition.
3. Three to five current official job descriptions representing the requested role, geography and seniority.

Use third-party job boards only to locate an official source or to label uncertainty. Record URLs, page status, access date and published date when available. Prefer paraphrased findings and short necessary snippets, not copies of whole pages.

## Research output

Write `research.json` with:

- job identity and source records;
- requirements classified as `must_have`, `important` or `nice_to_have`;
- ATS terms and truthful synonyms;
- responsibility priorities;
- recommended narrative pattern;
- uncertainty and gaps.

Give every requirement and keyword a stable ID so `resume.json` can point back to it.

## Mapping before writing

Build a requirement-to-fact matrix before drafting. Score relevance using evidence, recency, strength and repetition across official JDs. Do not treat keyword frequency as permission to claim a skill.

Select facts and section order from that matrix. Projects are optional. When there are no projects, use the strongest truthful combination of education, coursework, employment, research, campus, volunteer, freelance or other experience.

## Rewrite policy

Derive presentation from the researched job:

- engineering: action, mechanism, scale/quality and result;
- product/operations: user or business problem, judgment/tradeoff, solution and result;
- research: question, method, contribution and validation;
- other roles: infer the recurring responsibility language from official JDs and state the selected pattern in `research.json`.

Permitted changes: selection, ordering, compression, splitting, merging, truthful synonym choice, exact ATS terminology when equivalent, and changing emphasis.

Forbidden changes: invented metrics, upgraded ownership, changed dates, renamed employers, unsupported tools, implied production use, fabricated team size or unverified business impact.

## ATS coverage

Create `ats-map.json` with supported hits, unsupported gaps and synonyms. A keyword may enter a bullet only when at least one `fact_id` supports the same capability. Gaps must remain visible even if that reduces the coverage score.

Use this stable machine-readable shape so the renderer can enforce grounding:

```json
{
  "schema_version": "1.0",
  "keywords": [
    {"keyword_id": "kw-001", "term": "用户研究", "status": "covered", "fact_ids": ["fact-001"]},
    {"keyword_id": "kw-002", "term": "SQL", "status": "gap", "fact_ids": []}
  ]
}
```

Allowed statuses are `covered` and `gap`. Every `keyword_id` used by `resume.json` must be `covered`, and its supporting fact IDs must overlap the same bullet's verified fact IDs. A `gap` is report-only and must never appear in resume claims.

## Emphasis semantics

Every emphasis span is explicit in `resume.json` and has a kind:

- `label`: a short narrative label such as `交付结果｜`; rendered professional blue and bold.
- `metric`: a grounded quantitative result; rendered dark and bold.
- `result`: a grounded high-value outcome; rendered dark and bold.
- `keyword`: a small number of grounded must-have terms; rendered dark and bold.

Use at most three spans in one bullet and keep emphasized characters at or below one third of the bullet. Do not emphasize whole sentences, contact information or ordinary dates. The renderer validates spans; it never guesses from number patterns.
