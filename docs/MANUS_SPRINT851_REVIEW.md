# Manus Sprint 8.5.1 Comparative Provenance Review

**Reviewed implementation commit:** `63eef00ccad0924aad17db897d331a148ceb75c9`  
**Review context:** `origin/main` at `e5620c5`  
**Status:** **REJECTED — implementation controls appear materially complete, but the required adversarial test matrix is not present.**  
**Date:** August 22, 2026

## Independent validation

| Check | Observed result |
| --- | --- |
| Full test suite | `89 passed` in `8.32s`; total coverage reported as 82%. |
| Static typing | `mypy src` completed with **no issues** across 27 source files. |
| Integrated comparative pre-pilot | Completed with `PYTHONPATH=.`; produced a comparative record with verified canonical digest. |
| Focused test inventory | The comparative reconciler module contains five test functions: positive execution, missing verification artifact, forged execution digest, mismatched quote execution ID, and authentic promotion. [1] |

The new code is substantially better. It makes each quote field mandatory, checks all six bindings before promotion, validates collection-execution digest and context, and compares the gap-record ledger digest to the raw ledger bytes. [2] [3] The rejection concerns **proof completeness**, not a claim that those controls are absent.

## Controls now implemented

`QuotedEvidencePassage` now requires `evidence_id`, `evidence_url`, `snapshot_sha256`, `verifier_run_id`, `collection_execution_id`, and `quoted_passage`; the canonical decision digest includes each value. [3] The reconciler matches each value against parsed-ledger evidence and the selected execution before a human decision can promote a claim. [2]

The comparator also verifies the collection execution’s own digest and checks its URL, verifier-run ID, snapshot digest, ledger digest, observation, raw-answer digest, profile, manifest, and query-map context. It rejects a gap record whose ledger digest differs from the raw ledger bytes before resolving any evidence. [2]

## Remaining approval blocker: adversarial matrix is too narrow

The prior review explicitly required negative tests for every missing or mismatched quote and execution binding. The focused module adds only two new negative cases: a forged execution digest and a mismatched quote execution ID. [1] That does not prove that the remaining implemented comparisons are actually wired to the blocking path.

| Required adversarial proof | Current focused test coverage | Required completion |
| --- | --- | --- |
| Forged execution digest | Present | Retain. |
| Same-evidence-ID foreign execution with valid own digest | Absent | Prove failure when URL, observation/profile/artifact context, or ledger differs. |
| Wrong execution URL | Absent | Prove failure. |
| Wrong execution verifier run | Absent | Prove failure. |
| Wrong execution snapshot digest | Absent | Prove failure. |
| Wrong execution ledger digest | Absent | Prove failure. |
| Raw gap-record ledger digest versus raw bytes | Absent | Prove failure. |
| Missing mandatory quote field | Absent | Prove model construction fails for URL, snapshot, verifier run, and execution ID. |
| Mismatched quote URL, snapshot, or verifier run | Absent | Prove each leaves the assessment non-promoted. |
| Authentic six-binding promotion | Present | Retain. |

This matrix is not bureaucratic padding. The test suite is the only regression proof that a later refactor cannot silently weaken one comparison while leaving the happy path green. Until these tests exist, the platform cannot honestly say the Sprint 8.5.1 promotion gate is fully defended.

## Required Sprint 8.5.2 remediation

Add the missing adversarial cases above without weakening the current validators. Preserve the current positive six-binding promotion test. The review will approve the comparative provenance gate when all required negative cases fail closed, the existing full suite and static type check remain clean, and the integrated pre-pilot continues to emit only human-reviewed hypotheses.

> No real client or portfolio comparative artifact should yet be described as provenance-complete. The system is close, but the proof suite has not caught up with the implementation.

## References

[1]: ../tests/test_comparative_reconciler.py "Sprint 8.5.1 focused comparative tests"
[2]: ../src/collector/comparative_reconciler.py "Sprint 8.5.1 comparative reconciler"
[3]: ../src/domain/human_decision.py "Sprint 8.5.1 human-decision contract"
