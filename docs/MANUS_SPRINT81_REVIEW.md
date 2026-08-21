# Manus Sprint 8.1 Forensic Comparative Evidence Review

**Reviewed commit:** `338f121`  
**Status:** **Improved structure; comparative artifact not approved.**  
**Date:** August 21, 2026

## What improved

| Control | Independent result |
|---|---|
| Subject classification | Client and competitor relationships are derived from evidence URLs and `SubjectProfile`; mismatches reject. |
| Record context | Observation, profile, query map, manifest, ledger, evidence, verifier, snapshot, and execution references are modeled. |
| Client collection path | Runner now attempts candidate collection for both sides. |
| Rendering | Exporter calls comparative record integrity verification before render. |
| Baseline | Independent run returned **88 tests passed** and **0 mypy issues**. |

## P0: claim-to-excerpt support is still a keyword heuristic

`evaluate_claim_support()` marks a statement `SUPPORTED` when there are two matching words, or when the excerpt contains any broad token such as `python`, `rust`, `zen`, `readability`, `ownership`, or `book`.

Independent adversarial result:

```text
false_claim_assessment=supported
```

The statement *“Rust guarantees every application is secure and easy to maintain”* was marked supported by the excerpt *“The Rust Programming Language”*. That is not semantic assessment; it is a false-positive keyword match.

No comparative action hypothesis may be generated from this status.

## P1: record integrity still omits material decision fields

The canonical digest does not include:

- `finding_basis`;
- each assessment’s `statement_text`, `evidence_url`, or `opened_excerpt`; and
- several contextual fields used to explain the decision.

The “complete 9-hash” claim is therefore incomplete: artifact hashes are present, but a reviewer could alter material explanatory and source-linkage content without necessarily invalidating the comparative digest.

## P1: gap determination is not comparative

`evidence_gap_identified` is set solely by `gap_record.attribution_status == cited_competitor_observed`. It does not compare verified client and competitor claim assessments. A cited competitor is a signal for investigation, not proof that the client has an evidence gap.

## Required Sprint 8.2

1. Remove automatic `SUPPORTED` from lexical overlap. Automated claim evaluation may return only `not_assessable` or `candidate_for_human_semantic_review` unless a narrow, deterministic entailment rule is explicitly approved and tested.
2. Require a separate immutable human semantic decision to promote any comparative claim to `SUPPORTED`, `UNSUPPORTED`, or `CONTRADICTED`.
3. Bind assessment statement text, source URL, excerpt, finding basis, uncertainty, and every action-driving field into the canonical digest.
4. Compute evidence-gap status from explicit, human-reviewed comparative findings—not simply from competitor citation.
5. Add false-positive, swapped-excerpt, altered-finding-basis, and cited-competitor-with-complete-client-evidence adversarial tests.

## Boundary

Sprint 8.1 improves the engineering structure but does not yet produce a forensic evidence-gap conclusion. The citation-bearing observation and verified source records remain valuable. The generic comparative action hypothesis is not approved for any client, portfolio, or sales use.
