# Competitor Evidence Gap Report and 90-Day Catch-Up Plan

**Client / subject:** `[entity name]`  
**Category and geography:** `[defined category]`  
**Audit window:** `[start – end UTC]`  
**Decision status:** `[draft | preliminary hypothesis approved | client-ready]`  
**Prepared by:** `[operator]`  
**Evidence ledger version:** `[run ID and raw-ledger SHA-256]`

## 1. Decision Brief

This report answers a limited practical question: **what publicly verifiable evidence patterns appeared in the defined answer sample, what evidence is currently present for the subject, and what evidence should be collected or improved next?** It does not claim a universal AI ranking, causal mechanism, or market-wide demand estimate.

| Executive question | Evidence-grounded answer | Confidence | Required decision |
| --- | --- | --- | --- |
| Was the subject cited in the defined sample? | `[yes / no / insufficient sample]` | `[high / medium / low]` | `[continue / expand sample / stop]` |
| Which declared competitor entities were explicitly cited? | `[entities, exact URLs, and count]` | `[high / medium / low]` | `[collect more evidence / none]` |
| What is the highest-value evidence gap to investigate? | `[one bounded hypothesis]` | `[hypothesis only]` | `[approve next collection wave]` |

> **Executive guardrail:** An answer-surface observation is a sample, not a ranking. Recommendations below are evidence-collection or proof-improvement actions, never instructions to fabricate reviews, spam communities, or manipulate sources.

## 2. Audit Coverage and Limits

| Scope element | Approved definition | Delivered | Limitation |
| --- | --- | --- | --- |
| Query set | `[approved QueryMap ID / query count]` | `[count captured]` | `[coverage limitation]` |
| Model surfaces | `[provider and model labels]` | `[capture count by surface]` | `[access or login limitations]` |
| Competitor set | `[declared profiles]` | `[observed competitors]` | `[not a market census]` |
| Evidence sources | `[first-party / editorial / community / review]` | `[opened verified count]` | `[source-type imbalance]` |
| Audit window | `[UTC range]` | `[timestamps]` | `[time-bound results]` |

## 3. Observed Answer-Surface Evidence

For each captured answer, preserve the raw transcript, capture timestamp, provider/model, operator, query ID, and direct URLs. Do not substitute summaries for the artifact.

| Query | Surface | Capture timestamp | Explicit subject citations | Explicit competitor citations | Unverified cited URLs |
| --- | --- | --- | --- | --- | --- |
| `[query ID]` | `[provider / model]` | `[UTC]` | `[exact URLs or none]` | `[exact URLs and entity]` | `[URLs requiring approval]` |

## 4. Evidence Ecosystem Comparison

| Entity / source | Relationship | Source type | Verified passage | Snapshot / verifier reference | What it proves | What it does **not** prove |
| --- | --- | --- | --- | --- | --- | --- |
| `[competitor URL]` | Competitor-owned | `[type]` | `[verbatim excerpt]` | `[evidence ID / snapshot]` | `[narrow factual scope]` | `[no causal claim]` |
| `[subject URL]` | Subject-owned | `[type]` | `[verbatim excerpt]` | `[evidence ID / snapshot]` | `[narrow factual scope]` | `[no absence or ranking claim]` |
| `[third-party URL]` | Independent / community / review | `[type]` | `[verbatim excerpt]` | `[evidence ID / snapshot]` | `[narrow factual scope]` | `[no endorsement inference]` |

## 5. Preliminary Evidence-Gap Hypotheses

Each hypothesis must be human-reviewed. Use conditional language and link it to exact evidence.

| Hypothesis | Supporting observation | Counter-evidence / uncertainty | Status | Human decision |
| --- | --- | --- | --- | --- |
| `[e.g., category-specific proof appears more explicit on the competitor source than in the subject source sampled]` | `[observation and evidence IDs]` | `[sample limits and alternative explanations]` | `[candidate / approved / rejected]` | `[reviewer / timestamp]` |

## 6. 90-Day Catch-Up Plan

The plan is about **better proof and clearer public evidence**, not manipulation. No action becomes client-ready without an approved hypothesis and success condition.

| Window | Evidence-governed action | Owner | Acceptance evidence | Do not do |
| --- | --- | --- | --- | --- |
| Days 0–30 | `[inventory and verify existing category proof]` | `[owner]` | `[opened verified subject sources]` | `Do not publish thin AI-generated pages.` |
| Days 31–60 | `[create or improve one genuinely useful category-specific source]` | `[owner]` | `[source publishes, is accurate, and can be verified]` | `Do not claim model ranking outcomes.` |
| Days 61–90 | `[earn legitimate editorial, partner, or community references where appropriate]` | `[owner]` | `[independent source is real and non-incentivized]` | `Do not buy or fabricate reviews, citations, or forum posts.` |

## 7. Measurement Plan

| Metric | Defined measurement | Review cadence | Failure condition |
| --- | --- | --- | --- |
| Explicit citation presence | `[cited answers / approved captures]` | `[cadence]` | `Sample too small or surfaces inaccessible` |
| Verified subject evidence coverage | `[opened verified sources by evidence type]` | `[cadence]` | `Sources are generic, stale, or non-verifiable` |
| Hypothesis progression | `[approved / rejected / unresolved]` | `[cadence]` | `No human review or missing raw artifacts` |

## 8. Explicit Non-Claims

This report does **not** claim that:

1. a single model answer represents all users, prompts, or model versions;
2. an observed citation establishes causal ranking factors;
3. a competitor source is better merely because it was cited;
4. missing citation in the sample means the subject cannot be cited elsewhere; or
5. a recommended action will produce a model-answer outcome.

## 9. Approval Record

| Decision | Approver | Timestamp (UTC) | Scope of approval |
| --- | --- | --- | --- |
| `[approve / hold / reject]` | `[name]` | `[timestamp]` | `[hypothesis / next collection / client delivery]` |

## 10. Artifact Appendix

List the immutable artifacts required to replay this report: QueryMap, DatasetManifest, SubjectProfile, raw source ledger, raw answer transcript, AnswerObservation, gap-analysis record, collection executions, human decision records, and their SHA-256 digests.
