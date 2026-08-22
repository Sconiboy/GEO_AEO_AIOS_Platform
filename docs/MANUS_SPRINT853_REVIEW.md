# Manus Sprint 8.5.3 Final Provenance Gate

**Status:** **REJECTED — final narrow implementation closure required.**  
**Applies after:** `bd2ffaa` (test matrix) and automated review `e63ee4a`.

Sprint 8.5.2 correctly added the adversarial field-mismatch matrix. The remaining issue is **artifact authority**, not additional feature work.

## Required changes

1. **Canonical artifact inputs:** Parse raw ledger, profile, query-map, and manifest bytes in both gap analysis and comparative promotion. Use only parsed artifacts for decisions, or fail if caller-supplied objects are not canonically equal to those bytes.
2. **Retained snapshot verification:** For every promotion-eligible `OPENED_VERIFIED` record, require a snapshot reference, reload retained bytes via an approved resolver, recompute SHA-256, and require equality with evidence artifact, execution record, and human quote.
3. **Authorized execution provenance:** Require the chosen execution to resolve to an authorized candidate in the current gap record; require candidate/query/URL consistency with the parsed manifest and approved QueryMap. A self-recomputed SHA-256 only proves self-consistency, not origin.

## Required negative tests

Reject: same-ID or same-run-ID substituted ledger/profile/query-map/manifest models; no snapshot reference; missing or substituted retained bytes; snapshot digest mismatch; self-consistent execution with an unauthorized candidate; and self-consistent execution with a foreign target query.

Keep the Sprint 8.5.2 matrix and all existing human-governed six-field quote controls. Run the full tests and `mypy` before pushing.

> **Stop after this closure.** On approval, the next task is the first real authorized comparative pre-pilot—not more infrastructure hardening.

## Supporting records

- `docs/MANUS_SPRINT852_REVIEW.md`
- `docs/MANUS_AUTOMATED_REVIEW_bd2ffaaf0e22162c1c1550e24ee33602316dde4b.md`
- `docs/ANTIGRAVITY_FINAL_PROVENANCE_TASK.md`
