# Manus Sprint 8.5 Comparative Provenance Review

**Reviewed implementation commit:** `81c2db8`  
**Review context:** `origin/main` at `27753f8`  
**Status:** **REJECTED — raw-ledger parsing is corrected, but human quote and collection-execution provenance remain insufficient for comparative promotion.**  
**Date:** August 22, 2026

## Independent validation

| Check | Observed result |
| --- | --- |
| Full test suite | `87 passed` in `8.60s`; total coverage reported as 82%. |
| Static typing | `mypy src` completed with **no issues** across 27 source files. |
| Comparative pre-pilot | Completed after setting `PYTHONPATH=.`; it created a comparative record and verified its canonical digest. |
| Raw-ledger path | The reconciler now parses `raw_ledger_bytes` into an `AuditRun` and resolves selected evidence only from that parsed record. [1] |

The green suite demonstrates that the submitted implementation is internally consistent with its current tests. It does **not** prove that a human-promoted comparative finding is bound to the exact verifier and collection execution that produced the selected evidence.

## What Sprint 8.5 fixed

The separate caller-provided `AuditRun` argument is gone. `compare_evidence()` parses the raw ledger artifact directly, checks the parsed run ID against the gap record, and resolves both selected evidence IDs from that parsed ledger. This closes the prior raw-bytes versus in-memory-ledger substitution path. [1]

The comparator also rejects selected evidence that is not `OPENED_VERIFIED`, lacks a verification artifact, lacks a snapshot digest, lacks a verifier-run ID, or lacks a collection-execution object with the same evidence ID. The new omitted-snapshot test correctly shows that a quote lacking `snapshot_sha256` cannot promote a claim. [1] [2]

## P0: a human-promoted quote still lacks four required bindings

`QuotedEvidencePassage` contains only `evidence_id`, `quoted_passage`, and an **optional** `snapshot_sha256`. It has no evidence URL, verifier-run ID, or collection-execution ID. [3] The comparator consequently promotes a human decision after checking only evidence ID, text containment, and snapshot-digest equality. [1]

This fails the required Sprint 8.5 control. A promoted quote must always bind the exact current **evidence ID, URL, snapshot SHA-256, verifier-run ID, collection-execution ID, and quoted text**. The model cannot represent four of those bindings, so no test can prove them. A record with the right evidence ID and snapshot digest but a wrong execution or verifier would currently still promote.

## P0: collection execution is selected by evidence ID but not proven authentic or current

The reconciler locates a collection execution with `next(... if ce.evidence_id == selected_evidence_id)` and then copies its `execution_id` into the output. It does not call `CollectionExecutionRecord.verify_integrity()` and does not compare the execution's URL, verifier-run ID, snapshot SHA-256, source-ledger digest, observation, profile, manifest, or query-map context to the selected evidence and current artifacts. [1] [4]

`ForensicGapAnalysisRecord.verify_integrity()` only verifies its own digest over the child execution’s stored `canonical_digest` field. It does not verify that the child digest is valid, nor that the child’s fields belong to the current raw ledger. [4] Therefore a forged or foreign execution record with the selected evidence ID can satisfy the current existence check and be represented as provenance.

## P0: the gap record’s ledger digest is not bound to the raw ledger used for selection

The reconciler compares the parsed raw ledger’s `run_id` to the gap record, but it does not compare `gap_record.source_ledger_sha256` to `sha256(raw_ledger_bytes)`. The raw digest is calculated later, and only an optional human-decision record is compared against it. [1] This leaves the collection executions in the gap record able to claim a different ledger artifact that happens to reuse the same run ID.

## Required Sprint 8.5.1 remediation

| Required change | Acceptance condition |
| --- | --- |
| Expand the quote contract | Make `evidence_url`, `verifier_run_id`, and `collection_execution_id` required `QuotedEvidencePassage` fields. Include them in the human-decision canonical digest. |
| Validate quote provenance at promotion | Compare every quoted field exactly against the parsed evidence and its selected, validated execution. A missing, unknown, or mismatched value must return the non-promoted assessment. |
| Validate execution provenance | Require `CollectionExecutionRecord.verify_integrity()` and exact equality for evidence ID, URL, verifier-run ID, snapshot digest, raw-ledger digest, observation, profile, manifest, and query-map bindings. |
| Bind the gap record to raw ledger bytes | Reject when `gap_record.source_ledger_sha256` differs from `sha256(raw_ledger_bytes)`, in addition to the existing run-ID check. |
| Add adversarial tests | Prove rejection for forged execution digest, same-evidence-ID foreign execution, wrong execution URL, wrong verifier run, wrong execution snapshot, wrong execution ledger hash, and each missing or mismatched quote binding. |

> The implementation may continue to create an investigation record with non-promoted assessments. It must not issue a human-supported comparative evidence-gap conclusion until every binding above is enforced and adversarially tested.

## Decision boundary

Sprint 8.5 makes a meaningful correction to raw-ledger identity and removes the snapshot-optional promotion path. It does **not** yet establish that a human adjudication references the real verifier and collection execution responsible for the selected ledger evidence. Approval would overstate the provenance available in the current contracts.

## References

[1]: ../src/collector/comparative_reconciler.py "Sprint 8.5 comparative reconciler"
[2]: ../tests/test_comparative_reconciler.py "Focused comparative reconciler tests"
[3]: ../src/domain/human_decision.py "Human decision and quoted evidence contracts"
[4]: ../src/domain/candidate_collection.py "Collection execution integrity contract"
