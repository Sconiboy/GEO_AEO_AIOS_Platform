# Manus Sprint 4.1 Evidence-Integrity Review

**Reviewed commit:** `ac37afcaeeea2cae2d93e15750058b8f8fb4ddbd`  
**Status:** **Not approved for a live manual observation. One focused statement-status remediation remains.**  
**Date:** August 21, 2026

## What independently passed

Sprint 4.1 closes most of the meaningful evidence-integrity gaps from Sprint 4. The observation CLI now reads only local artifacts, and the observation binds to the exact raw bytes of the query map, manifest, and frozen ledger. The raw response model is frozen and the renderer rechecks its answer digest before producing output.

| Control | Independent result |
|---|---|
| Test suite | 37 passed |
| Static type check | `mypy src` passed with 0 issues |
| Raw-answer immutability | Direct mutation is rejected by the frozen Pydantic model. |
| Raw-answer integrity | Import and rendering re-verify the SHA-256 digest. |
| Explicit provenance | Capture timestamp is required; absent locale/region render as `Unknown`; fixture uses `synthetic_fixture_import`. |
| Frozen artifact binding | Query-map, manifest, and frozen-ledger digests are recalculated from local raw bytes and compared to the observation. |
| Offline observation CLI | Loads four local JSON artifacts and performs no collection/network request. |
| Linked-source quality | Linked evidence must exist and have `OPENED_VERIFIED` status. |

The resulting output is now a truthful **Observation Record**: it displays a synthetic fixture as synthetic, retains unknown provenance as unknown, shows a raw-answer digest, and makes no commercial visibility, recommendation, ranking, or client-audit claim.

## Remaining P0: imported statement status is forgeable

Sprint 4.1 did not fully implement the approved “proposal-only import” rule. If an input statement references any `OPENED_VERIFIED` evidence record, the importer preserves an input-provided `source_verified` or `human_approved` status. An independent adversarial import changed the fixture statement to `human_approved`, linked it to `ev-httpbin-001`, and the importer returned `human_approved`.

That source record only proves that a page was opened and a quoted excerpt was found. It does **not** prove the model statement is supported by that page, nor does it prove that a human approved it. Allowing the raw import payload to assign either status destroys the separation between observation, verification, and human judgment.

| Required Sprint 4.2 remediation | Acceptance condition |
|---|---|
| Force initial status | Every imported extracted statement must be returned as `proposed_unverified`, including statements that carry a linked evidence ID. |
| Preserve only contextual linkage | An optional evidence link may survive import only if its record is `OPENED_VERIFIED`; it must not elevate status. |
| Reserve transitions | Do not add a status-transition workflow in this sprint. A later reviewed decision model must own verification/human-approval transitions, with actor, timestamp, rationale, and supporting-evidence trace. |
| Add adversarial test | A payload containing `source_verified` or `human_approved` plus valid opened evidence must import as `proposed_unverified` (or be rejected). |
| Keep renderer honest | Observation Record must show imported statements only as proposals. |

## Approval boundary

**Approved foundation:** immutable observation artifacts, frozen local artifact binding, explicit provenance, and an offline import/render path.

**Still blocked:** the first real manual observation. Sprint 4.2 should be a small correction, not another architecture round. Once this one status-escalation path is closed and independently retested, the first permitted activity is exactly one manually captured response for the public Python test entity and the approved `q-001` query.

That record remains an internal evidence artifact. It is not an LLM-ranking result, recommendation, client report, comparative claim, paid API integration, or customer-data workflow.
