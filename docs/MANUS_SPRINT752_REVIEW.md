# Manus Sprint 7.5.2 Failed Collection Attempt Review

**Reviewed commit:** `64d2fa2`  
**Status:** **Approved for one controlled public competitor-source collection pre-pilot.**  
**Date:** August 21, 2026

## Independent results

| Control | Result |
|---|---|
| Success/failure branching | `OPENED_VERIFIED` evidence with a real verifier artifact produces a `CollectionExecutionRecord`; non-success states produce a `CollectionAttemptRecord`. |
| False snapshot prevention | Failed attempts have no success snapshot hash or verifier-run success claim. |
| Candidate preservation | An unsuccessful result remains unverified, so the candidate is regenerated in the updated analysis while its typed attempt record is retained. |
| Failure provenance | Attempt records bind status, failure category, reason, candidate, observation, profile, manifest, query map, and pre-fetch ledger artifacts. |
| Renderer | Successful collections and failed attempts are rendered in separate sections with distinct language. |
| Baseline | Independent run returned **70 tests passed** and **0 mypy issues**. |

Sprint 7.5.2 correctly fixes the false-success condition identified in Sprint 7.5.1. A failed source retrieval is now auditable without being misrepresented as verified competitor evidence.

## Approved collection pre-pilot boundary

One collection may proceed only when all conditions are met:

1. The raw observed answer explicitly contains the public competitor URL.
2. The subject profile declares that domain a competitor.
3. The exact normalized URL appears in the persisted manifest for the exact human-approved query.
4. The reloaded source policy permits the URL at execution time.
5. The candidate record and every bound upstream artifact pass integrity verification immediately before fetch.
6. The secure verifier retains a snapshot and creates an `OPENED_VERIFIED` evidence record, or the system records a typed failed attempt instead.

The initial pre-pilot is limited to one public non-client URL and one approved query. It may prove collection provenance only. It may **not** generate a comparative performance claim, a visibility score, or a client-facing catch-up recommendation.

## Next product milestone

If that single collection succeeds, the next work is not more generic security hardening. It is a bounded comparative-evidence workflow: collect one matching client-owned public source under the same approved question, compare the two verified evidence sets, and produce a carefully worded **hypothesis for human review**. The platform must still avoid claiming causal certainty about why an LLM chose a competitor.
