# Automated Provenance Review — `bd2ffaaf0e22162c1c1550e24ee33602316dde4b`

**Reviewed repository:** `Sconiboy/GEO_AEO_AIOS_Platform`  
**Reviewed branch and commit:** `main` at `bd2ffaaf0e22162c1c1550e24ee33602316dde4b`  
**Reviewer:** Manus Review Bot  
**Date:** August 22, 2026  
**Verdict:** **REJECTED — validation completed, but approval-critical provenance controls remain falsifiable.**

## Decision

The supplied archive is authentic for the requested revision: its SHA-256 was recorded as `ab4fe06d0a466043917b1a3443c92f43ea310d442e4efa3840dc1f20c5ad1c53`; it exactly matched both an independently cloned working tree and a fresh Git archive generated from the requested commit, excluding only `.git` metadata. The remote `main` branch resolved to the requested commit at review time.

The automated gate correctly rejects a forged digest and rejects individually altered selected-execution fields for evidence ID, URL, verifier-run ID, snapshot digest, raw-ledger digest, observation ID, raw-answer digest, profile ID, profile digest, query-map digest, and manifest digest. It also prevents promotion when any of the six human-quote bindings is changed. [2] [4]

Approval is nevertheless not justified. A human-supported conclusion can still be produced from a nonexistent snapshot, from a gap record derived from a different same-run-ID ledger model, from foreign profile/query-map/manifest models supplied alongside current raw-byte hashes, and from a self-consistent but unauthorized collection execution. Those bypasses fail the Sprint 8.5 approval boundary and the required exact-current-context standard. [1] [2] [3] [4] [5]

> **Approval boundary:** Promotion requires a retrievable snapshot whose bytes hash to the quoted digest, a gap record and all inputs derived from the exact raw artifacts, and a selected collection execution whose origin as well as its fields are authenticated against the current collection context. A recomputable digest is tamper evidence, not proof that an untrusted execution was actually performed or authorized.

| Required approval control | Independent result | Status |
|---|---|---|
| Human quote binds exact evidence ID, URL, quoted text, snapshot SHA-256, verifier-run ID, and collection-execution ID | An authentic two-source decision promoted both assessments. Mutating each of the six client quote fields independently downgraded the client assessment to `candidate_for_human_semantic_review`. | **PASS** |
| Selected execution verifies its own integrity and current evidence/raw-ledger/observation/profile/query-map/manifest fields | Each individually altered field was blocked when its canonical digest was recomputed. A foreign-observation execution was also blocked. | **PASS, field-level only** |
| Selected execution is authentic and authorized for the current collection | A newly created record with a recomputed valid digest, `candidate_id="candidate-never-authorized"`, and `target_query_id="q-foreign-not-current"` was accepted and promoted when its other fields were current. No lookup binds `candidate_id` or `target_query_id` to an authoritative collection artifact/current query. | **FAIL** |
| Gap record ledger SHA-256 matches the exact raw ledger bytes | The authentic baseline gap record matched the supplied raw bytes; a deliberately altered gap hash was rejected. | **PASS** |
| Gap analysis is derived from the exact raw ledger artifact rather than a separately trusted model | An empty `AuditRun` with the authentic run ID, used with raw bytes containing two evidence records, produced an integrity-valid gap record with `total_sources_evaluated == 0` and still reached `supported` for both human-promoted assessments. | **FAIL** |
| Profile, query map, and manifest context are the exact current raw artifacts | Foreign in-memory models with changed profile entity, query-map ID, or manifest ID were accepted against unchanged raw-byte hashes. The foreign profile entity appeared in the promoted comparative record. | **FAIL** |
| Quoted snapshot is retained and hashes to the claimed SHA-256 | Both fixture snapshot digests had no corresponding file under either `.snapshots/<sha>.txt` or `data/snapshots/<sha>.txt`; both assessments nevertheless promoted to `supported`. | **FAIL** |

## Observed Commands and Results

| Command or review action | Observed result |
|---|---|
| `gh api repos/Sconiboy/GEO_AEO_AIOS_Platform/commits/bd2ffaaf0e22162c1c1550e24ee33602316dde4b` and `.../branches/main` | The requested commit existed and `main` resolved to `bd2ffaaf0e22162c1c1550e24ee33602316dde4b`. |
| `sha256sum review-context.tgz` | `ab4fe06d0a466043917b1a3443c92f43ea310d442e4efa3840dc1f20c5ad1c53`. |
| Fresh canonical checkout plus `git archive --format=tar bd2ffa...`, then `diff -ruN --no-dereference` against supplied export | Exact match; `DIFF_BYTES=0`. |
| `python3 -m pytest --cov=src tests/` | **99 passed** in 6.25 seconds; total coverage reported as 82%. |
| `python3 -m mypy src` | **Success: no issues found in 27 source files.** |
| `python3 -m src.cli audit --fixture data/fixtures/sample_audit.json --output ../ci_test_report.md` | Fixture loaded, ledger validation passed for one claim, and report exported. |
| Independent harness: `independent_adversarial_review.py` | Baseline and all six quote-field mutations behaved as stated above. It also reproduced the raw/model, absent-snapshot, foreign-model, and forged-execution bypasses described below. |

## Findings

### P0 — Retained snapshot proof is absent at promotion

The comparative gate only rejects a missing or `unknown` snapshot string and checks equality between the selected evidence, execution, and human quote. It does not load retained snapshot bytes or recompute their SHA-256. [2] The repository has a snapshot store capable of loading content-addressed bytes, but the promotion path does not use it. [5]

The independent harness found all four expected fixture paths absent—two locations for each selected digest—and nevertheless obtained `supported` assessments for both sources. This is a direct falsification of the requirement that the promoted quoted text bind to a **retained** snapshot, rather than merely to an unverified 64-hex claim.

### P0 — A gap record can be derived from a different ledger model than its raw ledger bytes

`ForensicGapAnalyzer.analyze_gaps()` iterates over the supplied `source_ledger` model while using `raw_ledger_bytes` only to calculate a digest. [3] The final comparator does parse the raw ledger before resolving the selected evidence, but it checks the upstream gap record only for the common run ID and raw hash. [2]

The harness supplied an empty `AuditRun` sharing the exact run ID of a raw two-evidence ledger. The resulting gap record was integrity-valid, reported `total_sources_evaluated == 0`, carried the raw ledger SHA-256, and still drove fully `supported` human promotion using the raw-ledger evidence. The hash is correct, but the gap analysis did not originate from the hashed artifact.

### P0 — Foreign profile, query-map, and manifest models are accepted beside current raw-byte hashes

The comparative gate hashes raw profile/query-map/manifest bytes but consumes the independently supplied profile model for ownership classification and result presentation; it neither parses nor canonically compares that model to `raw_profile_bytes`. [2] The gap analyzer likewise consumes supplied manifest and profile models while only hashing the raw bytes. [3]

A profile model with the same profile ID but the client entity changed to `Foreign Profile Entity` was accepted, and that foreign entity appeared in the promoted result. Independently changed query-map and manifest IDs were also accepted while the human decision and executions retained the original raw hashes. Therefore, the system has field-level execution hash comparisons but not proof that all consumed contextual models are the exact current artifacts.

### P0 — Self-consistent forged collection execution is treated as authentic

`CollectionExecutionRecord.verify_integrity()` only recomputes an unsigned deterministic SHA-256 over supplied fields. [4] The final gate requires a selected record whose `evidence_id` matches and checks several field equalities, but it does not bind `candidate_id` to an actual authorized candidate, require `target_query_id == observation.query_id`, or authenticate the execution’s origin independently of its self-calculated digest. [2]

The harness created a new execution with the current evidence, ledger, observation, profile, query-map, manifest, verifier-run, and snapshot fields, but with `candidate_id="candidate-never-authorized"` and `target_query_id="q-foreign-not-current"`. After recomputing its canonical digest and binding the human quote to its new execution ID, the gate promoted both assessments. This is a foreign/forged execution accepted as valid provenance.

### Controls That Held Under Falsification

The current commit does enforce useful partial controls. The harness confirmed that separately recomputed, integrity-valid executions with altered evidence ID, URL, verifier run, snapshot digest, ledger digest, observation ID, raw-answer digest, profile ID, profile digest, manifest digest, or query-map digest are rejected. The test suite also confirms the same pattern for several of these cases. [2] The six mandatory human-quote fields are present in the schema and are all checked against the selected evidence/execution before promotion. [2] [6]

## Next Action

Remediation must be narrow and demonstrated by new negative tests before another approval review.

1. **Make raw artifacts canonical inputs.** Parse `raw_ledger_bytes`, `raw_profile_bytes`, `raw_qm_bytes`, and `raw_manifest_bytes` inside the relevant promotion and gap-analysis paths, and either use only those parsed artifacts or reject supplied models unless a complete canonical comparison proves equality. A shared run ID or independent raw hash is insufficient.
2. **Enforce retained-snapshot verification.** Bind a content-addressed snapshot locator to the artifact/execution, load the bytes during promotion, and require the recomputed SHA-256 to equal the evidence artifact, selected execution, and human quote digest.
3. **Authenticate execution origin and authorization.** Require an execution to resolve to an authoritative candidate/execution ledger, verify its candidate and query against the current observation and manifest/query-map context, and use a trust mechanism stronger than a self-recomputable digest for records crossing a trust boundary.
4. **Add adversarial regression tests.** Reject an empty/altered same-run-ID source model; foreign profile/query-map/manifest models; absent or digest-mismatched snapshot bytes; and a self-consistent execution whose candidate or target query is unauthorized/foreign. Retain the existing field-mismatch and quote-mutation matrix.

No code, workflow, setting, or secret was changed in this review. This document is the only intended repository modification.

## References

[1]: [Sprint 8.5 Review Gate](https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/bd2ffaaf0e22162c1c1550e24ee33602316dde4b/docs/MANUS_SPRINT85_REVIEW.md)  
[2]: [Comparative promotion gate](https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/bd2ffaaf0e22162c1c1550e24ee33602316dde4b/src/collector/comparative_reconciler.py)  
[3]: [Gap-analysis ledger and context handling](https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/bd2ffaaf0e22162c1c1550e24ee33602316dde4b/src/collector/gap_analyzer.py)  
[4]: [Collection execution integrity contract](https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/bd2ffaaf0e22162c1c1550e24ee33602316dde4b/src/domain/candidate_collection.py)  
[5]: [Snapshot storage and retrieval](https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/bd2ffaaf0e22162c1c1550e24ee33602316dde4b/src/collector/snapshot.py)  
[6]: [Human quote evidence contract](https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/bd2ffaaf0e22162c1c1550e24ee33602316dde4b/src/domain/human_decision.py)
