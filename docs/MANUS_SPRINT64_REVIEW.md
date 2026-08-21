# Manus Sprint 6.4 Human Decision Review

**Reviewed commit:** `94afcda4dbfdcb4d284310df6cd4bfb8b40aa541`  
**Status:** **Rejected for supported-result promotion.** The implementation has good structure, but it does not yet protect the core provenance claims of a human decision.  
**Date:** August 21, 2026

## What is solid

The new `HumanDecisionRecord` separates a human adjudication from the raw observation and automated reconciliation. It is immutable at the model level and binds the observation ID, raw-answer digest, source-ledger run ID/digest, query-map digest, and manifest digest. The command validates that a target statement exists and that each cited evidence ID is `OPENED_VERIFIED`.

The submitted baseline is also healthy: 52 tests pass and `mypy src` reports 0 issues.

## P0: a fabricated quotation can create a `SUPPORTED` human decision

The CLI accepts every `--quote` string without checking it against the cited `EvidenceRecord.opened_excerpt` or retained snapshot. Independent execution supplied:

> “This fabricated quotation does not occur in the source.”

with the legitimate PEP 20 evidence ID, a `SUPPORTED` status, and a valid rationale. The command exited successfully and wrote a decision artifact.

Valid evidence IDs are not enough. A human decision’s quoted passage is supposed to show why the claim was adjudicated. If it can be fabricated, the rendered decision record can present false provenance while every hash remains valid.

## P0: timestamp tampering does not invalidate the decision record

`HumanStatementDecision.decision_timestamp` and `reconciliation_method` are omitted from `compute_canonical_digest`. Independent modification of the committed decision timestamp to `2099-01-01T00:00:00Z` left `verify_integrity()` true.

The timestamp is a core human-governance field. It must be protected by the digest, not treated as mutable decoration.

## P1: reviewer identity is self-asserted

Any caller may pass `--auditor-identity` or accept the default “Lead Systems Architect & Auditor.” This is an offline prototype, so full identity infrastructure is not required now, but the output must say **declared reviewer identity**, not imply authenticated human authorization. A later production workflow needs authenticated actors or a signed attestation.

## Required Sprint 6.4.1 remediation

1. Require each quoted passage to be a normalized substring of the exact `opened_excerpt` for one of the cited evidence records, or of the durable retained snapshot when a storage key is available. Reject fabricated or mismatched quotes.
2. Include `decision_timestamp` and `reconciliation_method` in the canonical digest. Add a tamper test for each.
3. Require at least one quote-evidence pair; preserve which evidence ID each quote came from rather than a loose list of IDs and passages.
4. Change output terminology to **declared reviewer identity** until an authenticated actor or signed attestation is implemented.
5. Add an adversarial CLI test that attempts the exact fabricated PEP 20 quote above and expects failure.
6. Add the durable snapshot storage key/reference to the decision record or block portable supported decisions until it exists.

## Boundary

The PEP 20 `SUPPORTED` record in this commit is a wiring demonstration only. It is not approved as an evidence-governed human decision, portfolio artifact, or client-facing conclusion.
