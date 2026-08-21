# Manus Sprint 8.3 Human Governance Binding Review

**Reviewed commit:** `1a56ffd`  
**Status:** **Context replay protection improved; comparative evidence resolution is still incomplete.**  
**Date:** August 21, 2026

## What now works

| Control | Independent result |
|---|---|
| Observation and artifact context | Current observation ID, raw-answer hash, ledger run/hash, query-map hash, and manifest hash are checked before applying a human decision. |
| Cross-evidence ID replay | PEP decision cannot directly promote Rust evidence with a different evidence ID. |
| Quote text | Quoted passage must appear inside the currently supplied opened excerpt. |
| Automatic promotion | Still correctly disabled. |
| Baseline | Independent run returned **89 tests passed** and **0 mypy issues**. |

## P0: the comparator trusts caller-supplied evidence instead of resolving current ledger evidence

The promotion gate accepts a caller-supplied `EvidenceRecord` if its `evidence_id` and quote text match the human decision. It does not establish that the supplied record is the current evidence object from the immutable source ledger, nor does it require the human decision’s quoted snapshot SHA-256 to match the selected evidence verifier artifact.

Independent adversarial result:

```text
substituted_evidence_assessment=supported
```

I constructed a synthetic `OPENED_VERIFIED` evidence object carrying the PEP evidence ID and quote but no original snapshot/verifier provenance. The comparative evaluator promoted it to `supported`.

Human governance must bind the **same evidence artifact**, not merely an evidence ID and quoted string that a caller can recreate.

## Required Sprint 8.4

1. Resolve client and competitor evidence by evidence ID from the current immutable source ledger inside the comparator, rather than trusting caller-supplied `EvidenceRecord` objects.
2. Verify selected evidence is `OPENED_VERIFIED`, has a verifier artifact, and has a retained snapshot SHA-256.
3. Require each promoted quoted-evidence entry to match current evidence ID, URL, snapshot SHA-256, verifier run ID, and exact quoted passage.
4. Bind the resolved evidence object and collection execution ID to the comparative record; reject any mismatch or absent ledger membership.
5. Add synthetic-record, altered-snapshot, altered-verifier-run, and cross-role evidence-substitution tests.

## Boundary

Sprint 8.3 is a meaningful control improvement, but it does not yet safely permit a human decision to promote a comparative claim. The report remains an investigation artifact and must not present a supported client/competitor evidence-gap conclusion.
