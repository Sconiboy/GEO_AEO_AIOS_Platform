# Manus Sprint 6.2 Live Source-Ledger Pipeline Review

**Reviewed commit:** `951de2e8acaf4cbb2337d11ec18bf681cbbfa1c3`  
**Status:** **Secure source retrieval accepted; end-to-end demonstration not approved.** Manifest provenance is broken and the automatic support heuristic is unsafe.  
**Date:** August 21, 2026

## What worked

The actual secure collection components worked. `QueryMapRunner` invoked `SourceVerifier` for the PEP 20 candidate and produced an emitted ledger with a real `OPENED_VERIFIED` record. Independent checks confirmed that the retained snapshot file exists, its bytes hash to the emitted `snapshot_sha256`, and it contains the verified PEP 20 quote.

| Control | Independent result |
|---|---|
| URL retrieval | Opened through the secured verifier. |
| Visible-text match | Passed for `Explicit is better than implicit. Simple is better than complex.` |
| Snapshot | Retained under `snap-1e2b8d7404d38ac6`; SHA-256 matches emitted artifact. |
| Ledger binding | Emitted ledger SHA-256 matches the emitted observation and persisted reconciliation. |
| Source classification | Correctly `official_documentation`, not independent, non-client. |
| Regression baseline | 47 tests passed; `mypy src` reported 0 issues. |

This proves the platform can perform secured live source retrieval and create a source-ledger record without manually transcribing verifier fields.

## P0: the emitted PEP 20 source was not approved by the persisted manifest bound to the observation

The emitted observation declares manifest hash `ac7f4d…`, which is the raw hash of `data/fixtures/controlled_dataset_manifest.json`. That persisted manifest contains only `httpbin.org` and an intentionally unapproved test domain; it contains no PEP 20 candidate.

The PEP 20 manifest was built in an inline local script but was never persisted. The final observation therefore binds to one manifest while the source was collected under a different, ephemeral manifest. That breaks the human-approval trail.

> A source cannot be described as manifest-approved if the persisted manifest attached to the final observation does not contain it.

## P0: automatic `SUPPORTED` is a broad keyword false positive

`evaluate_semantic_support` marks a statement supported when it contains **any** one of `readability`, `simplicity`, `design`, `zen of python`, or `pep 20` and the evidence excerpt contains **any** one of `readability`, `simple`, `explicit`, `beautiful`, `complex`, `pep 20`, or `zen of python`.

Independent adversarial check showed the function returns `true` for:

> “Python design guarantees that every program is easy to learn.”

against:

> “Beautiful is better than ugly.”

That source does not establish the claim. A keyword overlap heuristic cannot award `SUPPORTED` status. It may identify a candidate for review, but it is not semantic verification.

## Additional qualification

The emitted ledger is still labeled `is_synthetic_fixture: true`, and the retained snapshot is not versioned in Git. That is honest for a controlled test run, but it is not yet a portable, durable demonstration artifact.

## Sprint 6.3 acceptance criteria

1. Persist `live_pep20_manifest.json` containing the PEP 20 URL, exact candidate excerpt, source classification, non-client approval, and any scope decision. Bind the emitted observation to that exact raw manifest hash.
2. Explicitly add or verify `peps.python.org` under the query-map source scope; test subdomain matching rather than relying on an implicit assumption.
3. Replace auto-`SUPPORTED` keyword logic. The default result after a live match must be `NOT_ASSESSABLE` or `proposed_for_human_review`; a human-reviewed, immutable decision record may subsequently mark it `SUPPORTED` with a precise rationale and cited excerpt.
4. Add false-positive tests, including the adversarial claim above, and fixture tests proving emitted observation manifest hash points to the persisted live manifest.
5. Persist the snapshot in the platform’s durable artifact store or explicitly state that the controlled run is non-portable. A snapshot hash without retained accessible bytes is insufficient for a portfolio artifact.

## Boundary

Do not present the two PEP 20 statements as verified `SUPPORTED` results yet. The source collection is real; the approval trail and semantic decision are not sufficiently trustworthy. No client work, scores, rankings, or commercial claims before Sprint 6.3 passes.
