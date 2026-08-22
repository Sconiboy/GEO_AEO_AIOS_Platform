# Manus Sprint 8.5.2 Comparative Provenance Review

**Reviewed implementation commit:** `bd2ffaaf0e22162c1c1550e24ee33602316dde4b`  
**Status:** **REJECTED — the requested 13-point adversarial matrix is now present, but the gate still cannot prove analysis used the raw ledger throughout or that the quoted snapshot bytes are retained.**  
**Date:** August 22, 2026

## Independent validation

| Check | Observed result |
| --- | --- |
| Full test suite | `99 passed` in `8.59s`; total coverage reported as 82%. |
| Static typing | `mypy src` completed with **no issues** across 27 source files. |
| Focused test inventory | The comparative suite now includes foreign-execution, execution URL/verifier/snapshot/ledger mismatch, raw gap-record ledger-digest mismatch, required quote-field validation, quote URL/snapshot/verifier/execution mismatch, and authentic-promotion cases. [1] |
| Product-code delta | This commit changes the focused tests and task documentation; it does not change `ForensicGapAnalyzer`, `SnapshotStore`, `SourceVerifier`, or comparative promotion code. |

## What is now proven

The prior narrow test gap is closed. The focused matrix now exercises the six quote bindings and the major execution substitutions required by the Sprint 8.5.1 review. The reconciler implementation therefore has substantially better regression proof for its current checks. [1] [2]

## Remaining P0: gap analysis still trusts a caller-supplied ledger model

`ForensicGapAnalyzer.analyze_gaps()` accepts both `source_ledger: AuditRun` and `raw_ledger_bytes`, hashes the raw bytes, but derives verified URLs, domain patterns, client evidence, statement evidence state, and later analysis output from the supplied `source_ledger.evidence_ledger`. [3] A matching run ID and a separately recorded byte digest do not prove that the model used for those calculations equals the raw ledger artifact.

The later comparator reparses raw bytes for selected evidence, which reduces risk at that narrow stage. It does **not** repair already-created gap-analysis patterns, candidate outputs, or action hypotheses that may be rendered or consumed before comparative reconciliation. The analyzer must either parse `raw_ledger_bytes` itself and use that parsed ledger for every ledger-derived operation, or canonicalize and compare the supplied model to the same raw artifact before proceeding.

## Remaining P0: retained snapshot bytes are not verified at promotion

`SourceVerifier` does save raw response bytes and emits both `snapshot_id` and `snapshot_sha256` into a newly collected `EvidenceRecord`. [4] However, `snapshot_id` remains optional on the domain record, while the comparative reconciler validates only digest strings and never reloads retained snapshot bytes through `SnapshotStore` or a durable snapshot resolver. [2] [5]

This means a promoted quote can be bound to a digest that has no retained bytes available at review time. The system proves that a digest value is internally consistent with other metadata; it does not prove the actual evidence snapshot still exists or hashes to that digest. That falls short of the explicit retained-snapshot requirement for a portable, client-facing forensic artifact.

## Required final remediation

| Required change | Acceptance condition |
| --- | --- |
| Raw-ledger-only gap analysis | Parse `raw_ledger_bytes` in `ForensicGapAnalyzer` and use only the parsed `AuditRun` for all ledger-derived findings, or prove strict canonical equality with a supplied model. |
| Retained-snapshot proof | Require an immutable snapshot reference for `OPENED_VERIFIED` comparative evidence. Reload retained bytes through an approved resolver and require the recomputed SHA-256 to match the evidence artifact, execution record, and human quote before promotion. |
| Adversarial proof | Reject a same-run-ID altered supplied ledger, missing snapshot reference, missing retained file/object, substituted retained bytes, and retained bytes whose SHA-256 mismatches the recorded digest. |

> The matrix is now strong. The remaining work is not more test volume; it is two small but essential implementation boundaries. After those are closed, stop hardening and move into the first real, authorized comparative pre-pilot.

## References

[1]: ../tests/test_comparative_reconciler.py "Sprint 8.5.2 focused adversarial matrix"
[2]: ../src/collector/comparative_reconciler.py "Comparative promotion and provenance gate"
[3]: ../src/collector/gap_analyzer.py "Gap-analysis ledger input handling"
[4]: ../src/collector/verifier.py "Evidence snapshot persistence during verification"
[5]: ../src/domain/models.py "Evidence and verification-artifact contracts"
