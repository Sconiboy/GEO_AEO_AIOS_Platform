# Manus Sprint 7.5 Candidate Collection Execution Review

**Reviewed commit:** `a22b7c126d400e478546b3f9ff48cba4ea91054f`  
**Status:** **Rejected for controlled competitor collection execution.**  
**What is accepted:** exact manifest/query authorization is rechecked and the existing secure verifier/policy is reused.  
**Date:** August 21, 2026

## Controls independently verified

| Control | Result |
|---|---|
| Candidate approval flag | Collection blocks when `requires_human_manifest_approval` is true. |
| Exact current manifest check | Collection requires an exact normalized URL and query ID in the reloaded manifest. |
| Query state | The executor checks `HumanApprovalState.APPROVED`. |
| Secure verification path | Collection uses `SourcePolicy` and `SourceVerifier`, retaining the prior HTTPS/SSRF/payload controls. |
| Baseline | Submitted test suite claims **67 passed** with a clean type check. |

## P0: the executor does not validate the collection candidate’s evidence context

`CandidateCollector.collect_candidate()` trusts any candidate found by ID in any supplied `ForensicGapAnalysisRecord`. It does **not**:

- call `gap_record.verify_integrity()`;
- compare the gap record’s observation ID/raw-answer hash with the supplied observation;
- compare its source-ledger run/hash, query-map hash, manifest hash, or profile hash with current raw artifacts; or
- require the candidate’s finding basis to match the supplied observation.

This permits a candidate generated for one observed answer to be replayed against a different answer/context when URL and query happen to overlap. The candidate ID itself is deterministic from query and URL, not observation context.

Execution-time manifest authorization is necessary, but it does not replace execution-time verification of the **observed-citation record** that created the collection request.

## P0: no candidate-to-evidence provenance is preserved

The new `EvidenceRecord` contains URL, snapshot, and verifier metadata, but its contract has no `candidate_id`, originating `observation_id`, answer hash, profile hash, manifest candidate identity, or collection timestamp binding. The executor merely appends the raw verifier output to the ledger.

After re-analysis, the collection candidate disappears because the URL is now verified. The system can infer a relationship from the same URL, but cannot prove which approved observed citation authorized the fetch.

The implementation summary’s claim that these bindings are appended to the `EvidenceRecord` is not true in the submitted schema or code.

## P1: the current “successful collection” test is mocked

The success test monkeypatches `SourceVerifier.verify_url()` and returns a hand-constructed evidence record with an all-`c` snapshot digest. That is acceptable as a unit test, but it does not prove an end-to-end retained snapshot or candidate-to-evidence chain. The existing secure-verifier tests cover retrieval separately; the new integration test must assert the full provenance contract.

## Required Sprint 7.5.1

1. Fail closed unless `gap_record.verify_integrity()` passes.
2. Revalidate all gap-record bindings against current raw observation, ledger, query map, manifest, and profile bytes before fetch.
3. Add immutable `CollectionExecutionProvenance` to collected evidence (or a separately canonicalized linked collection-execution record) containing candidate ID, originating observation ID, raw-answer hash, profile hash, manifest candidate URL/query ID, manifest hash, verifier run ID, evidence ID, snapshot ID/hash, and execution timestamp.
4. Link the execution record back to the candidate finding basis and include it in the updated ledger/analysis digest.
5. Add a non-mocked integration test using a local controlled HTTP fixture through the real `SourceVerifier` and `SnapshotStore`; assert the saved snapshot, evidence, candidate ID, and observation binding all agree.
6. Fail closed if any context artifact drifted since the candidate was issued.

## Pilot boundary

After Sprint 7.5.1 passes, the first controlled public-source collection pre-pilot can run. It will still be one exact URL, one exact approved query, one public non-client source, and no comparative conclusion until both client and competitor evidence chains are verified.
