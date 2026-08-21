# Manus Sprint 5 Claim-Reconciliation Review

**Reviewed commit:** `c7631e1ae310a0e5b7218ac49bdfcebe50bf0280`  
**Status:** **First decision content accepted; Sprint 5 implementation not approved as a durable reconciliation artifact until Sprint 5.1 integrity remediation.**  
**Date:** August 21, 2026

## What independently passed

The first reconciliation’s substantive conclusion is correct. The frozen ledger does not contain relevant evidence about Python’s design philosophy or PEP 20. The system correctly returns `NOT_ASSESSABLE` for both statements instead of treating an opened `httpbin.org` Moby-Dick excerpt as proof of a Python claim.

| Check | Independent result |
|---|---|
| Test suite | 43 passed |
| Static type check | `mypy src` passed with 0 issues |
| First decision content | Both statements render as `NOT_ASSESSABLE` with appropriate limitations. |
| Decision statuses | Reconciliation enum allows the approved four outcomes only. |
| Evidence-reference gate | Manual decisions reject missing or non-`OPENED_VERIFIED` evidence IDs. |
| Non-commercial boundary | Renderer avoids rank, visibility score, recommendation, and client-audit assertions. |

This is the right product behavior: a source being retrievable and quote-verified does not mean it semantically supports an LLM statement.

## Why Sprint 5 is not yet a durable decision artifact

The reconciliation path drops the raw frozen-ledger provenance at the point it matters most. The observation binds to the actual raw ledger artifact hash (`76a7ec…`), and the CLI validates that binding before reconciliation. But `ClaimReconciler` then computes a different hash from `str(source_ledger.model_dump(...))` and writes that noncanonical digest into `ObservationReconciliation` without comparing it to the observation-bound artifact hash.

Consequently, the resulting record cannot independently prove which exact ledger file it evaluated. That is an evidence-integrity failure, even though the current decision content happens to be correct.

| Priority | Finding | Required remediation |
|---|---|---|
| P0 | Reconciliation does not preserve or verify the raw source-ledger artifact hash. | Pass the raw ledger bytes into the reconciler; assert their SHA-256 equals `observation.source_ledger_sha256`; copy that exact digest into the reconciliation record. |
| P0 | Reconciliation digest hashes only the list of decisions, not its bindings/metadata. | Hash one canonical payload containing run ID, observation ID, raw-answer hash, source-ledger run ID/hash, and every reconciliation decision; exclude only the digest field itself. |
| P0 | Reconciliation renderer does not call `verify_integrity()` before output. | Recheck full reconciliation integrity and observation raw-answer integrity in the renderer; fail closed on mismatch. |
| P1 | CLI reads frozen raw bytes but does not carry them into reconciliation. | Preserve raw ledger bytes through `run_cli_reconcile` into `ClaimReconciler.reconcile_observation`. |
| P1 | No tamper tests cover ledger bytes, reconciliation metadata, or renderer refusal. | Add hermetic tests proving each change invalidates import/render or produces a hard failure. |
| P2 | Reconciliation enums exist both in `domain/enums.py` and `domain/reconciliation.py`. | Select one canonical source and import it everywhere to prevent future status drift. |

## Sprint 5.1 acceptance criteria

1. A reconciliation run uses and records the exact SHA-256 of the frozen ledger file that the observation already binds.
2. A raw-ledger hash mismatch fails before any decision is generated.
3. The reconciliation digest is canonical and covers all decision bindings and metadata.
4. Modifying any decision, reconciliation run metadata, or artifact hash makes `verify_integrity()` fail.
5. The renderer fails closed if either the reconciliation or raw observation fails integrity verification.
6. The first Python reconciliation still yields `NOT_ASSESSABLE` for both statements.
7. Tests remain hermetic, `pytest` passes, and `mypy src` remains clean.

## Boundary

No new observations, models, clients, paid APIs, or scoring features. Sprint 5.1 is a small integrity correction. After it passes, the platform will have its first genuinely traceable end-to-end decision artifact: raw model answer → frozen evidence ledger → immutable semantic reconciliation.
