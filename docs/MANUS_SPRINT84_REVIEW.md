# Manus Sprint 8.4 Immutable Ledger Evidence Review

**Reviewed commit:** `41b0d35`  
**Status:** **Ledger ID resolution improved; ledger identity and required evidence provenance remain incomplete.**  
**Date:** August 21, 2026

## What now works

| Control | Independent result |
|---|---|
| Caller-supplied evidence | Removed from the primary comparator API. Client and competitor selections use evidence IDs resolved against `AuditRun.evidence_ledger`. |
| Missing evidence IDs | Reject before comparison. |
| Human quote IDs | Matching quote evidence ID is required. |
| Snapshot mismatch | A supplied snapshot mismatch blocks promotion when the decision includes a snapshot digest. |
| Baseline | Independent run returned **88 tests passed** and **0 mypy issues**. |

## P0: the supplied source-ledger model is not proven to be the raw ledger artifact

`compare_evidence()` accepts both an `AuditRun` model (`source_ledger`) and raw ledger bytes (`raw_ledger_bytes`). It hashes the bytes for context checks but does not parse/validate those bytes and compare the resulting ledger identity, run ID, or evidence records to the supplied `AuditRun` model.

An attacker or erroneous caller can therefore supply a human-decision-compatible raw ledger file while passing a different in-memory ledger containing an altered record under the selected evidence ID. “Resolved from ledger” is only meaningful if that ledger is itself proven to be the current raw artifact.

## P0: verifier, snapshot, and execution provenance are not required

The comparator still accepts selected records without a `VerificationArtifact`; it fills `snapshot_sha256="unknown"` and `verifier_run_id="vrun-unknown"`. It also creates a synthetic execution ID when no matching collection execution exists.

For a human-promoted comparative claim, these fields must be required, not best-effort display placeholders.

## P1: quote snapshot remains optional

`QuotedEvidencePassage.snapshot_sha256` is optional. Snapshot matching is enforced only if it happens to be supplied. Human-governed comparative promotion must require it and must compare it to the resolved current evidence artifact.

## Required Sprint 8.5

1. Parse `raw_ledger_bytes` into an `AuditRun`; require the parsed run ID, canonical contents, and selected evidence records to match the supplied ledger model exactly—or remove the separate model argument and use the parsed immutable artifact directly.
2. Require selected client and competitor records to be `OPENED_VERIFIED` with non-null verifier artifacts, retained snapshot SHA-256 values, and matching immutable collection execution provenance.
3. Require every quoted-evidence passage used for promotion to contain a snapshot SHA-256 and match current evidence ID, URL, verifier run, snapshot hash, execution ID, and exact quote.
4. Reject unknown fallback provenance fields and any evidence not tied to the current raw ledger artifact.
5. Add raw-ledger/model mismatch, missing-artifact, missing-snapshot, missing-execution, and altered-verifier-run adversarial tests.

## Boundary

Sprint 8.4 removes one important synthetic-evidence path. It does not yet establish that the resolved evidence comes from the same immutable ledger or from a snapshot-backed execution. The comparative output remains an investigation artifact; it cannot yet promote an evidence-gap claim.
