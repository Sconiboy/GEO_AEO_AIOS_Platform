# Automated Provenance Review — `939b4cb6d8717633bb544417e2a19ccad29fe8a2`

**Reviewed repository:** `Sconiboy/GEO_AEO_AIOS_Platform`  
**Reviewed branch and commit:** `main` at `939b4cb6d8717633bb544417e2a19ccad29fe8a2`  
**Reviewer:** Manus Review Bot  
**Review date:** August 22, 2026  
**Verdict:** **APPROVED — the Sprint 8.5 provenance gate is satisfied for the reviewed implementation.**

## Decision

The supplied archive was independently compared with a fresh checkout of the requested `main` commit. The extracted archive contains **146 files**, has the same paths and file bytes as the authoritative tree, and has the same normalized file-manifest SHA-256: `5caa82a0d39eee03eab4d6d20cd3b94f89374fba8eb1a4050a4ea1fa0e9e1cab`. The archive file SHA-256 was `c56debeecffee26545957c135ba7be31aae334ee1e37a84891264bab72065667`; the authoritative Git tree is `5ff1b483d1c9764156cf5bcea14e4b85c08fde9b`.

The prior Sprint 8.5 review rejected the predecessor state because a separate same-run-ID ledger model could influence gap analysis and because promotion did not retrieve and hash retained snapshot bytes. [1] The reviewed implementation parses the raw ledger as an `AuditRun`, rejects any differing supplied ledger model, validates the gap record’s ledger digest against the exact raw bytes, and requires reloadable snapshot bytes whose recomputed SHA-256 agrees with both selected evidence and its execution. [2] [3]

> **Approval boundary:** This approval concerns the implemented provenance gate. The newly committed `data/prepilot/initial_source_ledger.json` is explicitly labeled a controlled, non-client synthetic dataset spike and is not a human-supported commercial-audit conclusion. [10]

| Required approval control | Independent result | Status |
|---|---|---|
| A promoted human quote binds the exact evidence ID, URL, quote text, snapshot SHA-256, verifier-run ID, and collection-execution ID | The immutable decision digest includes all six fields, and the promotion path requires exact equality for the first five plus verbatim quote containment in the selected evidence excerpt. An independent harness altered each field separately; each altered quote remained non-promoted. [4] [2] | **PASS** |
| Selected evidence is verified and has verifier provenance | The reconciler requires `OPENED_VERIFIED` status, a verification artifact, a non-sentinel verifier-run ID, and a snapshot digest before selection. [2] | **PASS** |
| Each selected collection execution proves its own integrity and exact current evidence, ledger, observation, profile, query-map, and manifest context | The execution digest covers candidate, query, URL, observation/raw-answer, profile ID/hash, manifest hash, query-map hash, raw-ledger hash, evidence ID, verifier run, snapshot digest, timestamp, and issuer. The reconciler verifies its integrity and checks every relevant selected-execution field against the current raw artifacts and selected evidence. [5] [2] | **PASS** |
| Foreign or forged collection executions cannot pass | The trusted registry requires a configured issuer, a registered byte-identical execution, and a valid issuer attestation. The independent harness rejected self-rehashed foreign executions for all execution bindings and rejected an execution attested by an attacker registry. [6] [2] | **PASS** |
| Gap record’s ledger SHA-256 matches the exact raw ledger bytes | The reconciler computes SHA-256 from `raw_ledger_bytes` and rejects a gap record with any other `source_ledger_sha256`. The independent harness rehashed a gap record with `00…00` and it was rejected. [2] | **PASS** |
| Gap analysis itself cannot be derived from a substituted ledger model | `ForensicGapAnalyzer` parses all raw artifacts, compares the supplied `AuditRun` with the parsed raw ledger, then uses the parsed ledger for findings. A same-run-ID empty model was rejected by the independent harness. [3] | **PASS** |
| A snapshot digest represents retained bytes, not an unsupported claim | Human promotion requires an evidence snapshot reference, a provided snapshot store, retained bytes at the digest-addressed location, recomputation of the bytes’ SHA-256, and equality with the selected execution snapshot digest. The independent harness rejected the absent-snapshot case. [2] [7] | **PASS** |

## Observed Commands and Results

| Command | Result |
|---|---|
| `sha256sum review-context.tgz`; safe archive-path validation; extraction without preserving ownership or permissions | Archive SHA-256: `c56debeecffee26545957c135ba7be31aae334ee1e37a84891264bab72065667`; extraction completed; archive did not contain an embedded `.git` directory. |
| `gh repo clone Sconiboy/GEO_AEO_AIOS_Platform … --branch main --single-branch`; `git rev-parse 939b4cb…^{commit}` | The requested commit resolved, and the checkout `HEAD` was exactly `939b4cb6d8717633bb544417e2a19ccad29fe8a2`. |
| Path-list comparison and `diff -r --brief --exclude=.git` between extracted archive and fresh authoritative checkout | **146 vs. 146 files; paths identical; content identical.** |
| `pytest --cov=src tests/` | **106 passed** in 5.75 seconds; total coverage reported as 83%. A first piped-output wrapper returned a shell-status error after all tests had passed, so that result was not accepted; the clean rerun above is the validation result. |
| `mypy src` | **Success: no issues found in 28 source files.** |
| Independent external harness: `adversarial_provenance_review.py` | **25 attempted bypasses rejected or rendered non-promoted; baseline fully bound promotion succeeded.** The attempted bypasses covered six quote bindings, absent retained snapshots, same-run-ID substituted ledger model, rehashed gap-record ledger digest, 14 self-rehashed collection-execution fields, and attacker-issued execution. |

## Findings

The implementation fixes both prior P0 failures rather than merely adding tests. In gap analysis, raw profile, query map, manifest, and ledger bytes are parsed before the supplied models are compared; subsequent analysis uses only the parsed models. [3] This closes the prior same-run-ID model-substitution path. In comparative promotion, the gap record’s `source_ledger_sha256` must equal the SHA-256 of the exact `raw_ledger_bytes`, after which selected evidence is resolved directly from the parsed raw ledger. [2]

The selected collection-execution checks are appropriately layered. A valid canonical digest alone is insufficient: the record must also be tied to an authorized candidate, approved query, current manifest URL/query entry, trusted issuer identity, issued registry bytes, and issuer attestation. [2] [6] This is material because a foreign execution can be self-consistent and correctly rehashed; it still fails either current-context checking or issuer-registry verification.

The promoted-quote path is similarly fail-closed. A complete `HumanDecisionRecord` context digest binds the observation, raw-answer digest, ledger run and SHA-256, query-map SHA-256, manifest SHA-256, decision metadata, and six-field quoted evidence passages. [4] A selected quote cannot promote until its execution is trusted and the referenced snapshot is present and hashes to the exact expected SHA-256. [2]

No code, workflow, setting, or secret was changed during this review. This document is the only intended repository modification.

## Next Action

Proceed only with the next bounded operational stage: use a protected configured trusted issuer and durable snapshot store, retain the exact raw artifacts, and rerun the same provenance checks before any human-supported commercial conclusion. Do **not** treat the committed controlled non-client pre-pilot ledger as client evidence or as a promoted human decision. [10]

## References

[1]: MANUS_SPRINT85_REVIEW.md "Sprint 8.5 provenance gate and prior rejection"
[2]: ../src/collector/comparative_reconciler.py "Comparative promotion and selected-execution validation"
[3]: ../src/collector/gap_analyzer.py "Raw-artifact parsing and canonical-model comparison"
[4]: ../src/domain/human_decision.py "Human-decision and six-field quote bindings"
[5]: ../src/domain/candidate_collection.py "Collection execution canonical integrity contract"
[6]: ../src/collector/execution_registry.py "Trusted issuer registry and byte-identical execution verification"
[7]: ../src/collector/snapshot.py "Content-addressed retained snapshot store"
[8]: ../tests/test_comparative_reconciler.py "Repository adversarial provenance regression tests"
[9]: ../README.md "Stated test and static type-check commands"
[10]: ../data/prepilot/initial_source_ledger.json "Controlled non-client pre-pilot ledger notice"
