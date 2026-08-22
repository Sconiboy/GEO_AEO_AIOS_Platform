# Manus Sprint 8.5 Provenance Review

**Reviewed repository:** `Sconiboy/GEO_AEO_AIOS_Platform`

**Reviewed branch and commit:** `main` at `63eef00ccad0924aad17db897d331a148ceb75c9`

**Review basis:** Supplied `review-context.tgz`, independently compared byte-for-byte with a fresh Git archive of the reviewed commit.

**Reviewer:** Manus Review Bot

**Date:** August 22, 2026
**Verdict:** **REJECTED — validation completed, but two approval-critical provenance controls remain falsifiable.**

## Decision

The reviewed comparator materially improves the previous controls. It parses `raw_ledger_bytes` directly into an `AuditRun`, resolves selected evidence from that parsed artifact, requires `OPENED_VERIFIED` status and verifier artifacts, verifies collection-execution digests and context fields, and blocks promotion when any of the six per-quote bindings is altered. [1] [2]

Approval is nevertheless not justified. The upstream gap-analysis API still accepts both a supplied `AuditRun` model and raw-ledger bytes without proving that they are equivalent. An independent harness supplied an **empty** model with the **same run ID** as a raw ledger containing the two selected records; it produced an integrity-valid gap record and then reached full human-supported comparative promotion. The reviewed code treats the common run ID and raw SHA-256 as sufficient, even though the gap analysis itself was derived from a different model. [3]

The retained-snapshot control is also not enforced. A 64-hex `snapshot_sha256` value with no corresponding file in either retained snapshot location was accepted through human-supported promotion. The comparator validates a non-empty digest string and equality across records; it never resolves retained snapshot bytes or recomputes their SHA-256. [1] [4]

> **Approval boundary:** A human-supported comparative conclusion must not be produced when the record that supplies its collection/provenance context was built from a different ledger model than the raw artifact, or when the claimed snapshot cannot be retrieved and hashed.

| Required approval control | Independent result | Evidence | Status |
|---|---|---|---|
| Raw bytes are parsed into `AuditRun` or supplied model is proven canonically equivalent | `ComparativeEvidenceReconciler` parses raw bytes, but `ForensicGapAnalyzer` still trusts a separate supplied model. A same-run-ID empty model reached full promotion against a raw two-record ledger. | `src/collector/comparative_reconciler.py`; `src/collector/gap_analyzer.py`; independent adversarial harness | **FAIL** |
| Both selected records are `OPENED_VERIFIED` | Unverified selected client evidence was blocked. | Independent harness; `src/collector/comparative_reconciler.py` | **PASS** |
| Both selected records have verifier-run provenance | Missing artifact and `vrun-unknown` were blocked; a recomputed execution with a wrong verifier run was blocked. | Independent harness; `src/collector/comparative_reconciler.py` | **PASS** |
| Both selected records have immutable collection-execution provenance | Missing execution, forged execution digest, and recomputed wrong URL/verifier/snapshot/ledger-digest executions were blocked. | Independent harness; `src/domain/candidate_collection.py`; `src/collector/comparative_reconciler.py` | **PASS** |
| Both selected records have a retained snapshot | A nonexistent 64-hex snapshot digest passed baseline human promotion. No retained-byte lookup or hash verification occurs at promotion. | Independent harness; `src/collector/comparative_reconciler.py`; `src/collector/snapshot.py` | **FAIL** |
| Every human-promoted quote binds exact evidence ID, URL, snapshot SHA-256, verifier-run ID, collection-execution ID, and quote text | Altering each of the six bindings independently prevented client promotion. | Independent harness; `src/domain/human_decision.py`; `src/collector/comparative_reconciler.py` | **PASS** |

## Observed commands and results

The archive contained 126 files and matched a fresh Git archive of the requested commit byte-for-byte. The embedded tar commit identifier was unavailable, so the identity conclusion rests on that complete tree comparison and Git object verification.

| Command | Result |
|---|---|
| `git -C repo.git archive ... 63eef00... | tar ...` followed by `diff -r --brief` against the extracted archive | **126 files vs. 126 files; exact tree match** |
| `pytest` | **89 passed** |
| `mypy src` | **Success: no issues found in 27 source files** |
| External adversarial harness (`/home/ubuntu/sprint85_review/sprint85_adversarial.py`) | Baseline authentic promotion passed; altered quote evidence ID, URL, snapshot, verifier run, execution ID, and text did not promote; missing artifact, non-verified evidence, absent execution, unknown verifier sentinel, and recomputed altered execution fields were blocked; raw/model mismatch and nonexistent snapshot retention were accepted. |

## Findings

### P0 — Raw/model identity is not enforced across the provenance pipeline

`ForensicGapAnalyzer.analyze_gaps()` derives verified URLs, evidence counts, collection candidates, and client-evidence state from its `source_ledger` parameter, while it only hashes `raw_ledger_bytes`; it does not parse and use those bytes or compare them to the model. [3] The final comparator only checks the resulting gap record's run ID and raw-ledger hash before parsing raw bytes for its own selected evidence lookup. [1]

The independent adversarial result is material: an empty supplied model with the same `run_id` as the raw two-record ledger generated an integrity-valid gap record with `total_sources_evaluated == 0`. That record, along with genuine executions and a correctly bound human decision for the raw ledger, reached `SUPPORTED` assessments for both sources. The control therefore does not establish that the upstream provenance context came from the immutable raw artifact.

### P0 — Snapshot SHA-256 is a claim, not proof of retained bytes

The selected-record gate rejects a missing or `unknown` digest but accepts any other 64-character digest. [1] `VerificationArtifact` contains only a digest; it does not bind a retained artifact location or content-addressed snapshot record. [4] The promotion path neither reads a snapshot nor recomputes a digest.

The independent harness set both selected evidence artifacts and their collection executions to a nonexistent `ff...ff` snapshot digest. There was no matching `.snapshots/<sha>.txt` or `data/snapshots/<sha>.txt` file. The final comparator nevertheless returned human-supported assessments. That directly falsifies the requirement for a **retained** snapshot rather than a syntactically valid hash string.

### Controls that held under falsification

The final comparative gate correctly failed closed for the following attempted bypasses: client evidence lacking `OPENED_VERIFIED` status, missing verification artifact, absent collection execution, `vrun-unknown`, and recomputed-but-altered execution URL, verifier run, snapshot digest, or source-ledger digest. [1] It also kept the client assessment non-promoted when any one of the required human-quote fields was changed: evidence ID, URL, snapshot SHA-256, verifier run ID, collection execution ID, or quote text. [1] [2]

## Next action

The next remediation must be limited and testable:

1. **Eliminate the separate trusted ledger model from `ForensicGapAnalyzer`, or parse `raw_ledger_bytes` there and use only the parsed ledger.** If an API model remains necessary, reject unless its canonical content and every relevant evidence record exactly match the parsed raw artifact; matching only `run_id` is insufficient.
2. **Make snapshot retention verifiable at promotion.** Bind a content-addressed snapshot locator or immutable snapshot record to `VerificationArtifact` and `CollectionExecutionRecord`; retrieve the retained bytes and require their recomputed SHA-256 to match the evidence, execution, and human quote bindings before a human-supported assessment is returned.
3. **Add adversarial tests for both failures.** At minimum, reject a same-run-ID but altered/empty supplied model when raw bytes differ, and reject a digest with no retained snapshot as well as retained bytes whose digest does not match. Keep the current six altered-quote and execution-field tests.

No code, workflow, setting, or secret was changed in this review; this document is the only intended repository modification.

## References

[1]: ../src/collector/comparative_reconciler.py "Comparative provenance gate"
[2]: ../src/domain/human_decision.py "Human quote evidence contract"
[3]: ../src/collector/gap_analyzer.py "Gap-analysis ledger input handling"
[4]: ../src/domain/models.py "Verification artifact contract"
