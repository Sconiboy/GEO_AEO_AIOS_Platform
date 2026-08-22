# Automated Provenance Review — `6ddf46c98947f8b60670de74b349263c92f9a295`

**Reviewed repository:** `Sconiboy/GEO_AEO_AIOS_Platform`
**Reviewed ref:** `main` at `6ddf46c98947f8b60670de74b349263c92f9a295`
**Review basis:** Supplied `review-context.tgz`, independently extracted and compared with the exact Git tree of the reviewed commit.
**Reviewer:** Manus Review Bot
**Date:** August 22, 2026
**Verdict:** **APPROVED — the stated provenance-promotion gate is satisfied for the reviewed commit.**

## Decision

The supplied archive was independently verified as the exact file tree of commit `6ddf46c98947f8b60670de74b349263c92f9a295`. The current `docs/MANUS_SPRINT85_REVIEW.md` was treated as the governing control specification despite its header referring to an earlier reviewed commit. The two prior P0 failure modes described there—an independent in-memory ledger model and an unverified retained-snapshot claim—were specifically re-tested against this commit and failed closed. [1]

Approval is limited to the tested promotion path and synthetic review fixtures. It is not a validation of any live collection, production issuer configuration, or external evidence content.

| Approval-critical control | Independent result | Status |
|---|---|---|
| Promoted human quotes bind exact evidence ID, URL, quoted text, snapshot SHA-256, verifier-run ID, and collection-execution ID | An authentic decision promoted the adjudicated statement for both selected sources. Each of the six client quote fields was independently mutated, the decision digest recomputed, and client promotion was withheld every time. The human-decision canonical digest includes each quoted field. [2] [3] | **PASS** |
| Each selected execution verifies its own integrity and exact current evidence/raw-ledger/observation/profile/query-map/manifest context | Both baseline executions verified. A forged digest was rejected. Each field mutation below was self-rehashed before substitution and was still rejected against current context: evidence ID, URL, verifier-run ID, snapshot SHA-256, raw-ledger SHA-256, observation ID, raw-answer SHA-256, profile ID, profile SHA-256, query-map SHA-256, manifest SHA-256, candidate ID, and target query ID. [2] [4] | **PASS** |
| Selected executions cannot be foreign, forged, self-rehashed, or unauthorized | A new self-rehashed execution ID failed registry resolution. An execution attested by an attacker-controlled issuer failed trusted-issuer verification. An unauthorized candidate and foreign target-query mutation both failed execution-authority validation. [2] [5] | **PASS** |
| Retained snapshot is retrievable and hash-verified before promotion | Missing retained bytes and deliberately corrupted retained bytes were both rejected. The promotion gate reloads snapshot bytes by digest and compares their recomputed SHA-256 with both evidence and execution bindings. [2] [6] | **PASS** |
| Gap record ledger SHA-256 equals the exact raw ledger bytes | The baseline gap record matched SHA-256 of the exact raw-ledger bytes. An integrity-valid, rehashed gap record carrying a substituted ledger SHA-256 was rejected. A same-run-ID `AuditRun` model with an empty evidence ledger was rejected against the genuine raw ledger. [2] [7] | **PASS** |

## Observed Commands and Results

| Command | Result |
|---|---|
| `sha256sum review-context.tgz`; extract archive; compare extracted tree with a detached checkout of `6ddf46c98947f8b60670de74b349263c92f9a295` using `diff -qr` | Archive SHA-256: `dabfa7e42c91b22bdb61fd0dd3d1565d3089bacdb67b98ad878883e9321dc250`; no file differences. The reviewed tree object was `8940a0e7afbe61cc928118f2111226fe58c54c15`. |
| `pytest` | **108 passed** in 5.31 seconds. |
| `mypy src` | **Success: no issues found in 28 source files.** |
| Independent harness, `adversarial_review.py`, run against the extracted tree | **44/44 checks passed.** The harness created a real trusted registry and content-addressed snapshot store, verified a baseline promotion, then attempted the six quote substitutions, thirteen rehashed execution-context substitutions, a forged digest, self-rehashed unregistered execution, foreign issuer, unauthorized candidate, foreign target query, same-run-ID ledger substitution, gap-ledger digest substitution, missing snapshot, and corrupted snapshot. |

## Findings

The reviewed comparator parses the raw ledger and canonical artifacts from caller-provided bytes, rejects supplied models that do not equal those parsed artifacts, and resolves the selected evidence from the parsed ledger. It separately recomputes the raw-ledger SHA-256 and requires the gap record and each selected execution to carry that exact value. [2] [7]

The human-promotion path checks every required per-quote field against the parsed evidence and selected execution, requires a trusted issuer-backed registry record rather than a self-computed digest, and loads retained snapshot bytes for hash verification before returning a human-promoted assessment. [2] [3] [5] [6]

> **Approval boundary:** This verdict applies only to commit `6ddf46c98947f8b60670de74b349263c92f9a295` and the promotion behavior exercised above. Any change to the comparator, gap analysis, execution registry, snapshot store, canonical contracts, or relevant test fixtures requires a new independent provenance review.

## Next Action

Approve this commit for the stated provenance gate. Preserve the adversarial checks as mandatory regression coverage, and require a new review before promoting any revision that changes provenance binding, collection-execution authority, trusted-issuer behavior, raw-artifact parsing, or retained-snapshot handling.

## References

[1]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/6ddf46c98947f8b60670de74b349263c92f9a295/docs/MANUS_SPRINT85_REVIEW.md "Sprint 8.5 provenance-review gate"
[2]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/6ddf46c98947f8b60670de74b349263c92f9a295/src/collector/comparative_reconciler.py "Comparative promotion and execution-context gate"
[3]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/6ddf46c98947f8b60670de74b349263c92f9a295/src/domain/human_decision.py "Human quote binding contract"
[4]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/6ddf46c98947f8b60670de74b349263c92f9a295/src/domain/candidate_collection.py "Collection-execution canonical integrity contract"
[5]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/6ddf46c98947f8b60670de74b349263c92f9a295/src/collector/execution_registry.py "Trusted issuer execution registry"
[6]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/6ddf46c98947f8b60670de74b349263c92f9a295/src/collector/snapshot.py "Content-addressed retained snapshot store"
[7]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/6ddf46c98947f8b60670de74b349263c92f9a295/src/collector/gap_analyzer.py "Canonical raw-artifact parsing and gap-record binding"
