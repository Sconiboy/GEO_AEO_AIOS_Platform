# Manus Automated Provenance Review — `a32f8868aae86116499a12582f00efb4a54b293f`

**Reviewed repository:** `Sconiboy/GEO_AEO_AIOS_Platform`  
**Reviewed branch and commit:** `main` at `a32f8868aae86116499a12582f00efb4a54b293f`  
**Reviewer:** Manus Review Bot  
**Date:** August 22, 2026  
**Verdict:** **APPROVED — the Sprint 8.5 provenance promotion gate passed independent validation and all attempted binding falsifications were blocked.**

## Review basis

The supplied `review-context.tgz` archive had SHA-256 `f47912ba0925dd78f16f779b7d662ba2588698660fd10c28240c498622945342`. It contained 154 regular repository files, excluding Git metadata. A fresh checkout of the required commit had the same 154-file SHA-256 manifest, with no content differences. The checked-out Git object was the `main` head at review time and had tree `4b6d35a1a9f8a19dc9e6f7b906019762799693a4`.

The current gate requires a human-supported conclusion to fail closed unless every selected source has evidence and execution provenance grounded in the exact raw artifacts. The decisive code paths parse the raw ledger, compare supplied artifact models with their parsed forms, validate selected execution records against current context, require trusted issuer attestations, and rehash retained snapshot bytes before human promotion. [1] [2] [3]

| Approval condition | Independent result | Status |
|---|---|---|
| Archive equals the requested `main` commit | Supplied archive and fresh commit checkout matched file-for-file by SHA-256 manifest. | **PASS** |
| Promoted human quote binds evidence ID, URL, quoted text, snapshot SHA-256, verifier-run ID, and collection-execution ID | A canonical, otherwise-valid human decision was recreated for each one-field mutation. All six mutations stayed non-promoted. | **PASS** |
| Each selected collection execution proves integrity and exact current context | Client and competitor executions were separately rehashed and issued before attacks against evidence ID, URL, verifier run, snapshot digest, raw-ledger digest, observation ID/raw-answer digest, profile ID/digest, query-map digest, and manifest digest. Every attack was blocked. | **PASS** |
| Execution provenance rejects forged or foreign records | A self-corrupted digest and an attacker-issued, internally valid record were both rejected before promotion. | **PASS** |
| Gap record is bound to exact raw-ledger bytes | A canonical gap record with a forged `source_ledger_sha256` was rejected; a same-run-ID but empty supplied ledger model was rejected by the gap analyzer. | **PASS** |
| Snapshot claim resolves to retained bytes | Missing retained bytes and retained bytes with a mismatching SHA-256 both blocked human promotion. | **PASS** |

## Observed commands and results

The validation was run against the extracted archive after installing only the dependencies declared in `pyproject.toml`. The first `pytest` attempt established that the runner was not preinstalled; it was not a repository test failure. After dependency installation, the prescribed checks completed successfully.

| Command | Observed result |
|---|---|
| `pytest` | **107 passed in 3.80s** |
| `mypy src` | **Success: no issues found in 28 source files** |
| `PYTHONPATH="$REPO" python3 /home/ubuntu/geo_aeo_aios_review_a32f886/provenance_falsification.py` | **35 independent cases completed: one authentic promoted baseline and 34 attack cases; every attack was blocked** |
| `git fetch origin main && git rev-parse HEAD && git rev-parse origin/main` | Both resolved to `a32f8868aae86116499a12582f00efb4a54b293f` before publication. |

## Independent falsification findings

The authentic baseline promoted only after the quote matched the selected client evidence ID, exact URL, retained-snapshot SHA-256, verifier-run ID, collection-execution ID, and verbatim excerpt. Rebuilding an internally valid human-decision record while mutating any one of those six fields did not yield `SUPPORTED`. This confirms the runtime match, rather than merely the human-decision schema, controls promotion. [1] [4]

The review then created new, self-consistent collection executions under the trusted issuer for each field-level context attack. Both selected roles—client and competitor—were tested independently. The gate rejected every changed evidence identifier, URL, verifier run, snapshot digest, raw-ledger SHA-256, observation ID, raw-answer SHA-256, profile ID, profile SHA-256, query-map SHA-256, and manifest SHA-256. A forged canonical digest was also rejected. [1] [3]

> **Foreign-execution result:** an execution signed by a separate attacker-controlled registry remained internally integrity-valid but was rejected because its issuer was not the configured trusted issuer. A rehashed record therefore cannot substitute for a collector-issued record. [3]

The former raw-model substitution failure was specifically retested. A supplied `AuditRun` with the same `run_id` but an empty evidence ledger was rejected because the analyzer parses `raw_ledger_bytes` and compares the supplied model to the parsed artifact. Separately, a canonically rebuilt gap record with a false ledger SHA-256 was rejected against the digest of the exact raw bytes. [1] [2]

The retained-snapshot control also held. Deleting the retained client snapshot and replacing its bytes with a distinct payload each caused promotion to fail. The reconciler requires the declared snapshot reference, reloads retained bytes, recomputes SHA-256, and verifies equality with both the evidence artifact and selected execution. [1]

## Decision and next action

**Approval is justified for this commit under the stated gate.** No attack produced a human-supported promotion with an altered quote binding, altered selected-execution context, forged or foreign execution, substituted same-run-ID ledger model, mismatched gap-ledger digest, missing retained snapshot, or tampered retained snapshot bytes.

The next action is to preserve these adversarial checks as required regression coverage. Any change to the comparative reconciler, gap analyzer, execution registry, snapshot store, human-decision contract, or their canonical serialization must repeat this review before a human-supported conclusion is relied upon.

No code, workflow, setting, or secret was changed. This review record is the only repository modification.

## References

[1]: ../src/collector/comparative_reconciler.py "Comparative promotion gate and selected-execution validation"
[2]: ../src/collector/gap_analyzer.py "Raw-artifact parsing and supplied-model equivalence"
[3]: ../src/collector/execution_registry.py "Trusted collector issuer registry"
[4]: ../src/domain/human_decision.py "Canonical human decision and quoted evidence contract"
[5]: ../tests/test_comparative_reconciler.py "Sprint 8.5 regression and adversarial coverage"
[6]: MANUS_SPRINT85_REVIEW.md "Current Sprint 8.5 review gate"
