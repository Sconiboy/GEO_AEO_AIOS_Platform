# Automated Provenance Review — `87a984d6eaeaca482e1a91c8880c2ed3a1e473ae`

**Repository:** `Sconiboy/GEO_AEO_AIOS_Platform`
**Reviewed branch and commit:** `main` at `87a984d6eaeaca482e1a91c8880c2ed3a1e473ae`
**Reviewer:** Manus Review Bot
**Date:** August 22, 2026
**Verdict:** **REJECTED — validation is complete, but approval-critical provenance controls remain falsifiable.**

## Decision

The supplied archive was independently tied to the requested commit, and the required test suite and strict type check passed. The comparative gate correctly prevented human promotion after each individual alteration of the six promoted-quote bindings: **evidence ID, URL, snapshot SHA-256, verifier-run ID, collection-execution ID, and quoted text**. It also rejected altered or malformed collection-execution integrity and current-context bindings for evidence, URL, verifier run, snapshot, raw ledger, observation, answer, profile, manifest, and query map. [1]

Approval is nevertheless not justified. An independently constructed, self-consistent `CollectionExecutionRecord` with `candidate_id="candidate-never-authorized"` reached human-supported promotion. A second self-consistent execution with `target_query_id="q-foreign"` did the same. The final comparative gate verifies that an execution is internally consistent and agrees with selected evidence and supplied hashes, but does **not** prove that the execution belongs to an authorized current candidate, matches the observation query, matches the current manifest candidate, or maps to an approved query in the parsed QueryMap. [1] [2]

The current path also accepts caller-supplied models that differ from the corresponding raw artifact bytes. Independent cases used an empty same-run-ID ledger, a modified same-ID profile, a modified QueryMap, and a modified manifest while retaining the original raw bytes and hashes; all reached human-supported client promotion. `ForensicGapAnalyzer` hashes raw artifacts while deriving analysis context from its supplied models, and the comparative gate parses only the raw ledger—not the raw profile, query map, or manifest—for artifact-derived decisions. [1] [3]

Finally, a human-supported promotion occurred while `EvidenceRecord.snapshot_id` was absent and neither `data/snapshots/<snapshot-sha256>.txt` nor `.snapshots/<snapshot-sha256>.txt` existed. The gate checks a syntactically nonempty snapshot digest and equality among supplied records but never loads retained bytes or recomputes their SHA-256. The snapshot store already provides a content-addressed loader, but the promotion path does not invoke it. [1] [4]

> **Approval boundary:** A human-supported comparative result must fail closed unless every selected execution is both integrity-valid and authoritatively resolvable against the exact current raw ledger, observation, profile, QueryMap, manifest, and authorized collection candidate; and unless every promoted quote’s snapshot can be retrieved and rehashed from retained bytes.

## Archive identity and validation record

| Check | Observed result | Status |
| --- | --- | --- |
| Supplied archive SHA-256 | `08f40549537a1b157e59ebf397398b1822b7aa157948afd90828780fee0a7f4c` | **PASS** |
| Reconstructed archive tree | `891bdc4da7bcc921f596650cf505d4b23f247d1b` | **PASS** |
| Canonical GitHub commit tree | `891bdc4da7bcc921f596650cf505d4b23f247d1b` | **PASS** |
| Requested commit on `origin/main` | `87a984d6eaeaca482e1a91c8880c2ed3a1e473ae` | **PASS** |
| `pytest --cov=src tests/` | **99 passed** in 8.22 seconds; total coverage 82% | **PASS** |
| `mypy src` | `Success: no issues found in 27 source files` | **PASS** |
| Independent adversarial harness | 21 required controls held; 8 required controls were accepted | **FAIL** |

The first fresh-index reconstruction omitted the tracked `.coverage` file because the repository’s `.gitignore` excludes it. Re-adding that tracked file to the isolated reconstruction produced the canonical tree above; content and tracked modes then matched the specified commit exactly.

## Observed commands

| Command | Result |
| --- | --- |
| `sha256sum review-context.tgz`; `tar -tzf`; isolated extraction | Archive was readable and extracted without execution. |
| `git init`; `git add -A`; `git add -f .coverage`; `git write-tree` | Reconstructed tree matched the requested commit tree exactly. |
| `gh api .../git/commits/87a984...`; `git ls-remote --heads origin main` | Confirmed the canonical tree and that `main` pointed to the requested commit during review. |
| `pytest --cov=src tests/` | **99 passed**. |
| `mypy src` | **Success: no issues found in 27 source files**. |
| Independent reviewer harness `provenance_falsification_87a984d6.py` | Baseline human promotion passed; all six quote bindings and 12 tested execution/context bindings failed closed; eight required controls were bypassed. |

## Falsification matrix

| Approval control | Independent adversarial result | Status |
| --- | --- | --- |
| Human quote evidence ID, URL, snapshot SHA-256, verifier-run ID, execution ID, and text each bind promotion | Each individual altered quote remained `candidate_for_human_semantic_review`, not `supported`. | **PASS** |
| Selected execution canonical digest and exact evidence/URL/verifier/snapshot/raw-ledger/observation/answer/profile/manifest/query-map context bind promotion | Tampered digest and each recomputed altered field raised a blocking `ValueError`. | **PASS** |
| Gap-record ledger SHA-256 matches the exact raw-ledger bytes | A valid ledger byte sequence differing only by trailing newline was blocked by a digest mismatch. | **PASS** |
| Each selected execution is authoritative for the current collection candidate | A recomputed execution with `candidate_id="candidate-never-authorized"` reached `supported`. | **FAIL** |
| Each selected execution targets the observation’s approved current query and exact manifest candidate | A recomputed execution with `target_query_id="q-foreign"` reached `supported`. | **FAIL** |
| Gap analysis derives source-ledger context from exact raw ledger bytes | An empty supplied `AuditRun` with the same run ID as the raw two-record ledger reached `supported`. | **FAIL** |
| Profile, QueryMap, and manifest context are parsed from exact raw bytes or canonically proven equivalent | Each altered same-ID caller model reached `supported` against the unchanged raw artifact bytes. | **FAIL** |
| Promoted evidence has a retained, rehashed snapshot and a required snapshot reference | Promotion succeeded with `snapshot_id=None` and absent bytes at both recognized snapshot paths. | **FAIL** |

## Findings

### P0 — Execution integrity is not execution authority

`CollectionExecutionRecord.verify_integrity()` recomputes a digest over whatever candidate and target-query values it is given. At comparative promotion, the gate selects an execution by evidence ID and verifies its digest and field equality, but it does not look up `candidate_id` in `gap_record.collection_candidates`, require `target_query_id == observation.query_id`, re-check the exact `(query_id, URL)` manifest candidate, or resolve the target query as approved in a parsed QueryMap. [1] [2]

This is not a cosmetic distinction. The reviewed harness recomputed valid digests after substituting a foreign candidate ID and a foreign query ID. Both passed all final checks and returned a human-supported client assessment. The requested authority boundary is therefore absent from the promotion path.

### P0 — Raw artifact hashes do not establish model identity

`ForensicGapAnalyzer.analyze_gaps()` accepts `source_ledger`, `subject_profile`, `query_map`, and `manifest` models alongside raw bytes. It computes raw SHA-256 values but uses caller-supplied models to build provenance context and candidates. The final gate parses the ledger but trusts supplied profile and QueryMap values and does not parse the raw profile, QueryMap, or manifest at all. [1] [3]

The independent same-ID altered-model cases show why equality of IDs and raw hashes is insufficient: the promotion result can be internally consistent while context was derived from a different artifact than the one whose hash is bound into the result.

### P0 — Snapshot SHA-256 is asserted rather than proven from retained bytes

`VerificationArtifact` has a digest field and `EvidenceRecord.snapshot_id` is optional. The comparative gate checks that the digest is not missing or `unknown` and checks equality with the execution and quote, but it has no required snapshot locator and no retained-byte load/re-hash. [1] [4]

The independent baseline used a 64-character digest with no snapshot ID and no corresponding retained file, yet human-supported promotion occurred. The implementation cannot distinguish nonexistent or substituted retained bytes from valid retained evidence at promotion time.

## Next action

The remediation must remain narrow and testable. First, parse the raw ledger, profile, QueryMap, and manifest inside both gap analysis and final comparison, and derive all artifact-dependent decisions from those parsed objects. If caller models remain in the API, reject unless their canonical serialization exactly equals the parsed raw artifact.

Second, require a content-addressed snapshot reference for every promotion-eligible `OPENED_VERIFIED` evidence record. Resolve it through the approved snapshot store, recompute SHA-256 from retained bytes, and require equality with the evidence artifact, selected execution, and human quote.

Third, resolve each selected execution to the current authoritative candidate and policy context at final promotion: the candidate must exist in the current gap record; `target_query_id` must equal `observation.query_id`; candidate URL/query must exactly match the current parsed manifest; and the parsed QueryMap target query must be approved. A self-recomputed execution digest may remain integrity evidence, but it is not authority evidence.

Add focused adversarial tests that reject altered same-ID models for all four artifacts, missing snapshot reference, missing retained bytes, substituted retained bytes, digest mismatch, foreign candidate ID, and foreign query ID. Re-run `pytest --cov=src tests/ && mypy src` and obtain a new independent review before authorizing a real comparative pre-pilot. No code, workflow, setting, or secret was changed by this review.

## References

[1]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/87a984d6eaeaca482e1a91c8880c2ed3a1e473ae/src/collector/comparative_reconciler.py "Comparative promotion gate"
[2]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/87a984d6eaeaca482e1a91c8880c2ed3a1e473ae/src/domain/candidate_collection.py "Collection execution contract"
[3]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/87a984d6eaeaca482e1a91c8880c2ed3a1e473ae/src/collector/gap_analyzer.py "Gap-analysis artifact handling"
[4]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/87a984d6eaeaca482e1a91c8880c2ed3a1e473ae/src/collector/snapshot.py "Content-addressed snapshot store"
