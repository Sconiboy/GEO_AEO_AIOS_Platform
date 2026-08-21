# Manus Sprint 7.2 Forensic Provenance & Attribution Review

**Reviewed commit:** `75d27d5b8bc62ceee4d4fdf8eccecaab68b6b23d`  
**Status:** **Approved for evidence-provenance safeguards; not approved for competitor attribution or a real forensic pilot.**  
**Date:** August 21, 2026

## Controls independently verified

| Control | Result |
|---|---|
| Full profile binding | `profile_sha256` is now stored and included in the canonical analysis digest. |
| Human-decision replay defense | The analyzer compares all six human-decision bindings with the current observation, answer hash, ledger run/hash, query map, and manifest, failing closed on mismatch. |
| Three-way evidence state | Client-owned evidence now suppresses the previous false documentation gap; supported statements remain excluded. |
| No-citation safety | The PEP fixture, whose answer has no URL, returns `NO_ANSWER_CITATIONS_NOT_ASSESSABLE` and emits no catch-up action. |
| Baseline | Independent run returned **57 tests passed** and **0 mypy issues**. |

This is a material improvement. The current fixture now behaves conservatively rather than recommending documentation that already exists.

## P0: a direct competitor citation is misclassified if it is not in the source ledger

The core forensic input is an explicit competitor citation in the observed answer. I tested that exact case by adding `https://rust-lang.org` to the raw answer. Rust is a declared competitor in the supplied profile but is not present in the PEP-only source ledger.

Expected result: `CITED_COMPETITOR_OBSERVED`.  
Actual result: `CLIENT_ONLY_CITATIONS`.

The failure occurs because competitor relationship lookup uses `domain_relationships`, which is populated only from source-ledger records. It does not classify the domains extracted from the answer against the explicit `SubjectProfile`.

This blocks the product’s central scenario: a model can cite a competitor’s page even when that page was not part of the client/source collection run. The system must recognize the declared competitor from the **observed answer** first, then decide whether a separate authorized retrieval is needed to examine that competitor evidence.

## Sprint 7.3 required correction

1. Classify every `AnswerCitation.domain` directly with `classify_source_relationship()` against the profile, independent of source-ledger membership.
2. Expand each answer citation to include `source_relationship` and, when applicable, the declared competitor entity ID/name.
3. Derive `CITED_COMPETITOR_OBSERVED` from those classified answer citations—not from ledger lookup.
4. Preserve the distinction between **observed competitor citation** and **verified competitor source**. An observed link is not yet a verified source; verification requires a separate manifest-approved, policy-compliant collection step.
5. Add adversarial tests for a competitor URL present only in the answer, a neutral editorial URL, a client URL, an unknown URL, and a deceptive subdomain such as `notrust-lang.org`.
6. Do not issue an action plan just because a competitor URL is observed. The next action is an evidence-collection proposal, then a confidence-bounded comparison after verified client and competitor evidence are available.

## Pilot boundary

After Sprint 7.3, we can run the first honest forensic **pre-pilot**: a public non-client answer that explicitly cites a declared competitor, followed by an authorized source collection of cited competitor and client-owned pages. Only after that evidence exists should the platform produce a comparative catch-up hypothesis.
