# Manus Sprint 7.4.1 Exact Manifest Authorization Review

**Reviewed commit:** `9f73b38cff1ff19af85a210ddff17849d443bfac`  
**Status:** **Approved for collection-candidate authorization.**  
**Not yet approved:** actual competitor source collection execution. That requires a separate execution-time gate.  
**Date:** August 21, 2026

## Independent results

| Control | Result |
|---|---|
| Cross-query authorization | A Rust candidate for `q-unrelated` no longer authorizes the same citation for `q-001`. |
| Same-domain/different-URL authorization | A candidate for `https://rust-lang.org/about` no longer authorizes `https://rust-lang.org/learn`. |
| Exact authorization | An exact normalized `https://rust-lang.org/learn` candidate for `q-001` correctly clears the approval flag. |
| Provenance | The authorized candidate stores its matched manifest query ID and protects it in the analysis digest. |
| Baseline | Independent run returned **64 tests passed** and **0 mypy issues**. |

The prior candidate-domain authorization bypass is closed. Candidate generation now reflects the correct boundary: collection requires an exact source candidate approved for the current buyer question.

## Remaining implementation boundary

Sprint 7.4.1 does not execute a fetch. It creates an analytical collection candidate only. The existing `QueryMapRunner` can fetch manifest candidates through the secure verifier, but it is not yet connected to the forensic candidate lifecycle.

Before any competitor URL is collected, the platform needs a separate execution procedure that:

1. reloads the current raw manifest and query map;
2. revalidates the exact normalized URL and `query_id` immediately before calling `SourceVerifier`;
3. validates the query is still human-approved, non-client, HTTPS, in allowed scope, and not blocked;
4. records which manifest candidate authorized the fetch and binds it to the observed-citation candidate;
5. stores the resulting snapshot/evidence record and links it back to the original answer; and
6. fails closed if the manifest or policy changed since the collection candidate was issued.

This is an execution-time authorization control, not another generic framework task. It is the final gate before the first controlled competitor evidence collection pre-pilot.

## Approved pre-pilot boundary

After the execution gate passes review, one public non-client URL may be collected only when all of the following are true:

- the AI answer explicitly cited it;
- the subject profile declares the cited domain a competitor;
- the exact URL is in a persisted manifest for the exact approved query;
- the secure source policy permits it; and
- the new evidence record and snapshot are bound back to the original observation.

No client domains, no automated expansion to other URLs, no competitor conclusion, and no catch-up recommendation beyond the verified evidence collection itself.
