# Manus Sprint 7.1 Forensic Profile & Evidence-Gap Review

**Reviewed commit:** `6d3add7f94bb2f58e1efd630d70b67bfefc5ffb8`  
**Status:** **Rejected as a client/competitor forensic action-plan workflow.**  
**What is accepted:** explicit profile contracts, relationship classification, action-hypothesis framing, and expanded digest coverage are meaningful improvements.  
**Date:** August 21, 2026

## Improvements verified

| Control | Independent result |
|---|---|
| Explicit ownership model | Client and declared competitor profiles replace the earlier incorrect source-allowlist inference. |
| Relationship classification | `peps.python.org` is now correctly classified as client-owned for the controlled Python profile. |
| Supported-statement suppression | A statement marked `SUPPORTED` in the supplied human-decision record is excluded from the generic unsupported-statement list. |
| Action language | The output now uses **Hypothesis for Review** and includes ethical non-manipulation language. |
| Rendered-content integrity | The expanded digest now covers descriptions, counts, evidence basis, confidence explanation, action impact, and ethical notes. |
| Baseline | Independent run returned **58 tests passed** and **0 mypy issues**. |

## P0: it still produces a false client gap and generic action

The PEP fixture has a client-owned, `OPENED_VERIFIED` PEP 20 source. The human decision supports `stmt-001`. The remaining `stmt-002` is **unadjudicated**, not evidence of a missing client documentation gap.

Nevertheless, the report emits `MISSING_OFFICIAL_DOCS` for `stmt-002` and recommends publishing documentation on `python.org`. Its own finding basis points to the already-opened, client-owned PEP evidence record. This is still a generic “write documentation” conclusion, not a forensic gap.

The analyzer must distinguish at least:

| State | Correct output |
|---|---|
| Supported by current client-owned opened evidence | No documentation gap. |
| Evidence exists but semantic review is pending | `NOT_ASSESSABLE` / “needs semantic adjudication”; no catch-up action. |
| No relevant client-owned evidence after scoped collection | Candidate evidence gap, subject to confidence and action-hypothesis rules. |

## P0: no competitor attribution is possible without answer citations

The observed Python answer contains no explicit URL. The report renders that fact correctly as no answer citations, but it still labels source-ledger domains as a citation pattern. The ledger’s PEP source is client-owned; it is not a competitor citation.

When the answer surface does not expose cited URLs or source references, competitor attribution must be explicit **`NOT_ASSESSABLE`**. The tool may still summarize source-ledger coverage, but it must not claim a competitor pattern or issue a competitor-driven catch-up plan.

## P0: the full profile artifact is not bound

`raw_profile_bytes` is received and hashed in the analyzer, but that SHA-256 is discarded. The record contains only `profile_id`.

Independent check: changing the profile’s offering category while retaining `profile_id` left the forensic analysis digest unchanged. A client/competitor profile is an upstream decision input; its raw SHA-256 must be a record field and part of the canonical digest. `profile_id` alone is not a content-addressed binding.

## P0: a valid human decision can be replayed from another context

The CLI checks a supplied human decision’s own digest but does not compare its observation ID, raw-answer digest, ledger run ID/hash, query-map hash, or manifest hash against the current artifacts. A valid decision with the same statement ID from another context could suppress a gap in this run. Require exact six-binding equality before using any decision for supported-statement suppression.

## Required Sprint 7.2

1. Add `profile_sha256` to `ForensicGapAnalysisRecord` and its complete canonical digest. Validate the raw profile bytes before report generation.
2. Bind and validate any supplied human decision against the current observation, raw answer, ledger run/hash, query map, and manifest before using it.
3. Add explicit result states for **answer-citation attribution** and **evidence-gap assessment**. When citations are absent, competitor attribution is `NOT_ASSESSABLE` and no competitor action plan may be created.
4. Replace “not currently supported” with a three-way evaluation: `client_evidence_present`, `semantic_review_pending`, or `candidate_evidence_gap`. Only the third may create a documented action hypothesis.
5. Require each competitor pattern/action to cite actual answer-level citation IDs/domains and ownership relationships. No ledger domain may be called a competitor citation unless it is explicitly classified competitor-owned and observed in the answer.
6. Add adversarial tests for profile-content mutation, replayed human decision, client-owned evidence with pending review, no answer citations, and a neutral editorial source.

## Product boundary

Sprint 7.1 is much closer to the correct data model. Do not add another dashboard or generic prompt tracker. Implement these narrow state-and-provenance corrections, then run the first honest non-client forensic pilot with a real explicit competitor and observed answer citations.
