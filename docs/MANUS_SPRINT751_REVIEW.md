# Manus Sprint 7.5.1 Collection Execution Provenance Review

**Reviewed commit:** `0246170`  
**Status:** **Rejected for controlled public-source collection pre-pilot.**  
**What is accepted:** complete pre-fetch candidate-context validation, immutable execution-record structure, and real local verifier/snapshot integration are material improvements.  
**Date:** August 21, 2026

## Controls independently verified

| Control | Result |
|---|---|
| Candidate record integrity | The collector now refuses a `ForensicGapAnalysisRecord` whose canonical digest fails. |
| Context binding | It compares observation ID/answer hash, ledger run/hash, query-map hash, manifest hash, profile ID/hash, and current raw artifact bytes before fetch. |
| Execution record | A frozen `CollectionExecutionRecord` binds candidate, observation, profile, manifest, query map, pre-fetch ledger, evidence, verifier run, snapshot hash, and timestamp. |
| Integration test direction | The submitted suite includes a real local HTTP source through the actual `SourceVerifier` and `SnapshotStore`, rather than only a verifier mock. |
| Baseline | Independent run returned **69 tests passed** and **0 mypy issues**. |

## P0: an inaccessible verifier result is recorded as a completed collection execution

The collector creates a `CollectionExecutionRecord` unconditionally after `verify_url()`. It does not require `OPENED_VERIFIED`, a verification artifact, or a retained snapshot before appending evidence and emitting collection provenance.

Independent controlled failure-path result:

| Check | Result |
|---|---|
| Verifier return | `INACCESSIBLE` evidence with an HTTP-status failure category |
| Failed evidence added to ledger | `true` |
| Collection execution records emitted | `1` |
| Execution snapshot hash | `unknown` |

This is not a completed evidence collection. The execution record’s schema and report presentation imply a candidate was successfully collected and snapshot-bound, but the source was inaccessible. It would corrupt the chain of custody and can mislead a later comparison stage.

## Required Sprint 7.5.2

1. Branch explicitly on `ev_record.verification_status` after `verify_url()`.
2. Create `CollectionExecutionRecord` only for `OPENED_VERIFIED` evidence with a valid verification artifact, snapshot ID, verifier run ID, and 64-character snapshot SHA-256.
3. For inaccessible, quote-mismatch, or policy-blocked results, create a separately typed **CollectionAttemptRecord** that records the failure category/reason, no evidence-success claim, and no snapshot-success fields.
4. Keep failed attempts visible in the source ledger, but do not remove the original collection candidate or treat the observed competitor URL as verified.
5. Add tests for every non-success verification status, asserting no success execution record is created.
6. Require renderer wording to distinguish **verified collection** from **failed collection attempt**.

## Pilot boundary

After Sprint 7.5.2 passes, one public approved competitor URL may be collected in a real pre-pilot. A successful source becomes verified competitor evidence; a failure remains an evidence-collection failure, not an equivalently valid result. No comparative conclusion follows either result until the required client and competitor evidence sets exist.
