# Antigravity Final Comparative Provenance Closure

**Status:** Required before any real client or portfolio comparative report is called defensible.  
**Scope:** Narrow implementation closure only. Do not add dashboards, scoring, AI-provider integrations, or commercial recommendations.

## Why this remains open

The Sprint 8.5.2 matrix now proves many field mismatches fail closed. However, independent review found three trust boundaries still allow an internally consistent but non-authoritative artifact to enter a promoted comparative result:

1. `ForensicGapAnalyzer` derives findings from caller-supplied models even when raw artifact bytes are available.
2. A snapshot digest alone is accepted without reloading retained bytes and recomputing the digest.
3. `CollectionExecutionRecord.canonical_digest` is self-recomputable, and promotion does not prove its candidate was authorized for the current observation/query/manifest.

## Required implementation

| Boundary | Required control | Acceptance evidence |
| --- | --- | --- |
| Canonical artifacts | Parse raw ledger, profile, query-map, and manifest bytes inside the gap-analysis/comparative path. Use the parsed objects for all artifact-derived decisions, or reject supplied models unless their canonical serializations exactly equal the raw artifacts. | Tests reject a same-ID/same-run-ID altered model for each artifact type. |
| Retained snapshots | For `OPENED_VERIFIED` evidence eligible for comparative promotion, require a snapshot reference; load its retained bytes using an approved resolver and recompute SHA-256. Require equality with the evidence artifact, selected execution, and human quote snapshot digest. | Tests reject no snapshot reference, missing retained bytes, substituted bytes, and digest mismatch. |
| Execution authority | Resolve selected execution to an authoritative record created from an authorized collection candidate. Require `candidate_id` to exist in the current gap record, `target_query_id == observation.query_id`, exact candidate URL/query match in the current manifest, and approved target query in the parsed QueryMap. A self-recomputed execution digest is integrity evidence, not authority evidence. | Test rejects a self-consistent execution with `candidate_id="candidate-never-authorized"` or a foreign target query. |

## Non-negotiable constraints

The comparator must continue to parse the raw ledger itself, preserve the current six-field quote binding, fail closed rather than substitute `unknown`, and keep promotion human-governed. Keep the existing 99-test suite green, add focused adversarial tests for the cases above, run `pytest --cov=src tests/ && mypy src`, and update the task backlog with the exact test count.

> **Stop after this closure.** If it passes independent review, move straight to the first authorized, real comparative pre-pilot. Do not harden unrelated infrastructure.

## Related reviews

- `docs/MANUS_SPRINT852_REVIEW.md`
- `docs/MANUS_AUTOMATED_REVIEW_bd2ffaaf0e22162c1c1550e24ee33602316dde4b.md`
