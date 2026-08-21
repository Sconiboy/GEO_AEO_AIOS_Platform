# Manus Sprint 8.2 Strict Comparative Governance Review

**Reviewed commit:** `4390470`  
**Status:** **Automatic keyword promotion fixed; human-decision evidence binding incomplete.**  
**Date:** August 21, 2026

## What now works

| Control | Independent result |
|---|---|
| Automatic support | Removed. Verified excerpts now produce `candidate_for_human_semantic_review`, not automatic `supported`. |
| False-keyword case | Regression test covers the prior Rust false-positive case. |
| Comparative record digest | Expanded to include assessment and finding-basis content. |
| Renderer | Shows status and human-review framing. |
| Baseline | Independent run returned **89 tests passed** and **0 mypy issues**. |

## P0: a human decision can be replayed onto unrelated evidence

The comparator checks only whether a valid `HumanDecisionRecord` has a decision with the same `statement_id`. It does not validate that the human decision is bound to:

- the current observation ID and raw-answer hash;
- the current source ledger, query map, and manifest;
- the current evidence ID, source URL, snapshot, and quoted excerpt; or
- the current client/competitor evidence role.

Independent adversarial result:

```text
replayed_pep_decision_on_rust_evidence=supported
```

An immutable human decision approving a PEP 20 excerpt for a Python statement was passed with Rust Book evidence. The comparator marked the Rust evidence `supported` solely because `statement_id` matched.

That is an evidence-substitution flaw. Human review must be strict, but it must also be review of the **same claim against the same evidence in the same observation context**.

## Required Sprint 8.3

1. Before using a `HumanDecisionRecord`, compare every context binding to the current observation: observation ID, raw-answer SHA-256, source-ledger run/SHA-256, query-map SHA-256, and manifest SHA-256.
2. For each promoted assessment, require a quoted-evidence pair whose evidence ID, URL, snapshot hash, and exact quoted passage match the current selected evidence.
3. Bind the comparative role (`client_owned` or `competitor_owned`) into the per-assessment human decision application.
4. Reject a human decision that does not apply, rather than silently using it to promote unrelated evidence.
5. Add cross-observation, cross-evidence, cross-source-role, and altered-quoted-passage replay tests.

## Boundary

Sprint 8.2 correctly blocks automated semantic promotion. It does not yet safely allow human-governed comparative promotion. The current comparative output must remain an investigation record, not a supported evidence-gap finding or client/portfolio artifact.
