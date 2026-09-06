# Job research and grounded rewriting

Before drafting, read [岗位族叙事策略库](narrative-strategy-library.md) and
[经历增强与无指标写法](experience-enhancement.md). The strategy changes language,
proof order and experience emphasis; the enhancement pass improves specificity without
changing the underlying fact boundary.

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
- narrative strategy selection (`primary`, `signals`, optional `secondary`);
- evidence enhancement notes (`evidence_ladder`, unresolved follow-ups and assumptions);
- uncertainty and gaps.

Give every requirement and keyword a stable ID so `resume.json` can point back to it.

## Mapping before writing

Build a requirement-to-fact matrix before drafting. Score relevance using evidence, recency, strength and repetition across official JDs. Do not treat keyword frequency as permission to claim a skill.

Select facts and section order from that matrix. Projects are optional. When there are no projects, use the strongest truthful combination of education, coursework, employment, research, campus, volunteer, freelance or other experience.

## Decision rules

Content selection is a ranking problem with a fixed order — do not re-ask the user for choices this ranking can settle. Decide autonomously and record the reasoning in `change-map.md`:

1. JD `must_have` requirement match beats everything else.
2. Fact strength: `user_verified` with quantified evidence beats unquantified.
3. Recency: newer experience beats older at equal strength.
4. Repetition: a capability repeated across several official JDs beats one mentioned once.

When one page runs out of room, cut from the bottom of this ranking, never from the top. Section order, bullet compression/merging/splitting, truthful synonym choice and emphasis spans are always autonomous decisions — present them in the review packet, do not ask about them in advance.

Ask the user only when:

- two sources conflict on a fact;
- a disclosure boundary is involved;
- a `source_supported` fact needs promotion;
- two mutually exclusive narrative directions are equally ranked (for example, a research-oriented vs. an engineering-oriented framing of the same experience).

When information is missing but a conservative default exists, take the default, record the assumption in `change-map.md`, and list it in the review packet instead of blocking.

## Rewrite policy

Derive presentation from the researched job and the selected narrative strategy:

- engineering: problem, mechanism, scope/quality evidence and result;
- product/operations: user or business problem, judgment/tradeoff, solution and result;
- research: question, method, contribution and validation;
- other roles: infer the recurring responsibility language from official JDs and state the selected pattern in `research.json`.

Run a separate language-quality pass after evidence enhancement and ATS mapping. Natural Chinese causality,
consistent ownership and explicit limitations outrank generic action verbs. A bullet
may be ATS-complete and still require rewriting when its tone or logic does not fit
the selected family.

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
