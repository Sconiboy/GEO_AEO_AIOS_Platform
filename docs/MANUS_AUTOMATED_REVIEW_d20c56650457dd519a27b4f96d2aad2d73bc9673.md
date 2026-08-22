# Automated Provenance Review — `d20c56650457dd519a27b4f96d2aad2d73bc9673`

**Repository:** `Sconiboy/GEO_AEO_AIOS_Platform`  
**Branch / reviewed commit:** `main` at `d20c56650457dd519a27b4f96d2aad2d73bc9673`  
**Reviewer:** Manus Review Bot  
**Date:** August 22, 2026  
**Verdict:** **REJECTED — validation completed, but a selected foreign collection execution can enter a comparative record without trusted-issuer verification.**

## Decision

The supplied `review-context.tgz` matched a fresh Git archive of the requested commit exactly: **135 files versus 135 files, with no byte-level tree differences**. The reviewed branch also resolved to the requested commit. The repository’s declared validation completed successfully: `pytest` reported **105 passed**, and `mypy src` reported **no issues in 28 source files**. [1] [2]

The Sprint 8.5 gate nevertheless is not satisfied. The comparator validates the canonical digest and current evidence, ledger, observation, profile, query-map, manifest, candidate, query, and URL bindings of both selected executions. It calls the protected trusted-issuer registry only inside `evaluate_claim_support()` after finding a matching human quote for that particular evidence record. [3] [4]

An independent harness constructed an attacker-issued competitor execution whose public canonical digest was valid and whose evidence, raw-ledger, observation, profile, query-map, manifest, candidate, query, URL, verifier-run, and snapshot fields all matched the current artifacts. The comparator accepted that foreign execution into the comparative summary when no human decision existed. It also accepted it when a valid human quote promoted the client assessment but the foreign competitor execution had no matching quote. The selected competitor summary therefore carries a foreign execution ID without trusted-issuer verification. [3] [4]

> **Approval boundary:** Every selected collection execution must be authenticated by the protected trusted issuer before the comparator returns any comparative record. Valid public hashing and matching context fields prove self-consistency; they do not prove platform authority.

## Required approval controls

| Required control | Independent result | Status |
|---|---|---|
| Archive is the requested commit | Supplied archive exactly matched `git archive d20c56650457dd519a27b4f96d2aad2d73bc9673`; authoritative `main` resolved to the same commit. | **PASS** |
| Promoted quotes bind exact evidence ID, URL, quoted text, snapshot SHA-256, verifier-run ID, and execution ID | Each of the six altered quote fields produced `candidate_for_human_semantic_review`, not `SUPPORTED`. A valid human quote promoted both authentic records. | **PASS** |
| Retained snapshot is proved at promotion | Authentic promotion required stored snapshot bytes whose recomputed SHA-256 matched the evidence and execution. The implementation fails closed for unavailable or substituted snapshot bytes. | **PASS** |
| Gap record ledger SHA-256 matches exact raw-ledger bytes | Altering the raw ledger byte stream caused the comparator to reject the gap-record ledger hash; same-run-ID substituted ledger model was rejected upstream. | **PASS** |
| Selected executions bind current evidence, ledger, observation, profile, query-map, manifest, candidate, query, and URL | Rehashed mutations of each tested binding were rejected: URL, verifier run, snapshot SHA-256, ledger SHA-256, observation ID, raw-answer SHA-256, profile ID/SHA-256, manifest SHA-256, query-map SHA-256, and target query. | **PASS** |
| **Every selected execution is authorized, including foreign executions** | An attacker-issued competitor execution with valid self-consistency and current-context bindings was selected into a non-promoted comparative record. The same foreign peer remained selected when a valid client quote promoted the client assessment. | **FAIL** |

## Observed commands and results

| Command or procedure | Result |
|---|---|
| `tar -xzf review-context.tgz` followed by a fresh `git archive` of `d20c566...` and `diff -r --brief` | **Exact tree match; 135 files on each side.** |
| `git -C audit_remote rev-parse main` | `d20c56650457dd519a27b4f96d2aad2d73bc9673` |
| `pytest` | **105 passed in 4.85s** |
| `mypy src` | **Success: no issues found in 28 source files** |
| Independent harness outside the repository | **24 controls passed; 2 foreign-execution bypasses reproduced.** |

The independent harness first established an authentic control with two registry-issued executions, persisted snapshots, and fully bound human quotes; both assessments were `SUPPORTED` and the comparative record verified its canonical digest. It then recomputed valid human-decision digests while independently altering each required quote field. Every altered quote failed to promote the client assessment.

For collection context, the harness recomputed self-consistent execution digests after independently changing each relevant field. The comparator rejected URL, verifier-run, snapshot, source-ledger SHA-256, observation ID, raw-answer SHA-256, profile ID, profile SHA-256, manifest SHA-256, query-map SHA-256, and target-query substitutions. It also rejected a same-run-ID empty `AuditRun` substituted for the raw ledger and rejected a gap record whose claimed ledger SHA-256 no longer matched the supplied raw bytes.

## P0 finding — trusted execution authority is conditional on a matching human quote

`compare_evidence()` validates every selected execution’s public canonical digest and current-artifact field equality before adding it to the comparative source summaries. [3] However, it does not call `CollectorExecutionRegistry.verify_issued()` in that selection path. The registry check occurs only in `evaluate_claim_support()` when a decision contains a matching quote for the evidence being evaluated. [3] [4]

This creates two reproducible bypasses. First, an attacker-registry-issued competitor execution can be selected into a record that has no human decision at all. Second, a human decision with a fully valid, trusted client quote promotes the client assessment while an unquoted attacker-issued competitor execution is still selected in the returned record. The comparator’s competitor assessment remains a candidate rather than a human-promoted conclusion, but its foreign execution has nevertheless passed the selected-execution gate. That fails the requested condition that **each selected collection execution** be independently verified, including foreign or forged executions.

The gate document’s displayed reviewed-commit identifier is an earlier `63eef00...` commit, while this archive and review are for `d20c566...`. This discrepancy did not affect the review’s use of the gate’s stated approval criteria, but the gate document should be updated in a subsequent documentation-only correction. [1]

## Next action

Move trusted-issuer verification out of the quote-promotion branch and into `compare_evidence()` immediately after each selected execution passes integrity and current-context checks. Require `self._trusted_execution_registry` to be configured, then call `verify_issued(client_exec)` and `verify_issued(comp_exec)` before constructing either comparative summary or evaluating any human decision. Add negative tests that use a foreign but self-consistent execution both with no human decision and with only the other source quoted. Re-run the full suite and `mypy src` before a new review.

No code, workflow, setting, or secret was changed by this review. This file is the only repository modification.

## References

[1]: ./MANUS_SPRINT85_REVIEW.md "Sprint 8.5 approval gate"
[2]: ../pyproject.toml "Declared test and strict mypy configuration"
[3]: ../src/collector/comparative_reconciler.py "Comparative selection, quote-promotion, and issuer-verification paths"
[4]: ../src/collector/execution_registry.py "Trusted collector issuer registry"
