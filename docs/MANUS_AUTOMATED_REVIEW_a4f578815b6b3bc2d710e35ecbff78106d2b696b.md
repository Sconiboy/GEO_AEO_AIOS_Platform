# Automated Provenance Review — `a4f578815b6b3bc2d710e35ecbff78106d2b696b`

**Repository:** `Sconiboy/GEO_AEO_AIOS_Platform`  
**Branch:** `main`  
**Reviewed commit:** `a4f578815b6b3bc2d710e35ecbff78106d2b696b`  
**Reviewer:** Manus Review Bot  
**Date:** 2026-08-22  
**Verdict:** **REJECTED — validation completed, but an approval-critical quoted-text-to-snapshot binding remains falsifiable.**

## Decision

The supplied archive was independently matched against a fresh Git archive of the requested commit. The review then ran the declared test and strict type-check commands, read `docs/MANUS_SPRINT85_REVIEW.md` as the current gate, and executed an independent adversarial harness outside the repository test suite. The harness exercised both selected evidence records, both quote records, all six promoted-quote fields, all collection-execution fields, raw-artifact byte bindings, model/raw equivalence, snapshot presence and digest integrity, observation integrity, and foreign/forged execution attacks.

The review **does not approve promotion**. The comparator confirms that a retained file hashes to the claimed snapshot SHA-256, and separately confirms that the human quote is a substring of `EvidenceRecord.opened_excerpt`. It does **not** prove that the human-promoted quoted text occurs in the retained snapshot bytes. An evidence record can therefore contain an authentic retained snapshot, an `OPENED_VERIFIED` status, matching execution context, and an `opened_excerpt` containing the quote, while the exact quote is absent from the hashed snapshot. That fixture promoted the client claim to `SUPPORTED`.

> **Approval boundary:** A promoted human quote must be demonstrably recoverable from the exact retained snapshot whose SHA-256 is bound to the evidence and collection execution. Co-hashing a quote field and a snapshot digest in separate records is not sufficient evidence of that relationship.

| Approval control | Independent result | Status |
|---|---|---:|
| Supplied archive is the exact requested Git tree | `175` supplied files and `175` fresh-archive files; `diff -r --brief` produced no differences; sorted file-hash manifests had identical SHA-256 `34aafd5643e79168d56111af449d7da9ec0d66574662be151d64a8ca7f3f642c`. | PASS |
| Gap-record ledger SHA-256 equals the exact raw-ledger bytes | The comparator recalculates `sha256(raw_ledger_bytes)` and rejects a different byte sequence; the gap analyzer rejects a same-run-ID model with a different ledger. | PASS |
| Selected execution integrity and exact current evidence/raw-ledger/observation/profile/query-map/manifest context | Both client and competitor execution records were independently mutated field-by-field. Canonical-digest, evidence ID, URL, verifier-run ID, snapshot SHA-256, raw-ledger SHA-256, observation ID, raw-answer SHA-256, profile ID/SHA-256, manifest SHA-256, query-map SHA-256, target query, and candidate mutations all failed closed. | PASS |
| Foreign or forged collection execution rejection | A self-consistent but unregistered execution and an execution attested by a different issuer both failed for each selected side. | PASS |
| Selected evidence is `OPENED_VERIFIED` with verifier provenance | A non-verified selected client record failed closed; evidence without the required verifier artifact/run is rejected by the comparator. | PASS |
| Retained snapshot availability and hash integrity | Missing retained bytes and deliberately substituted retained bytes both failed closed. | PASS |
| Six promoted-quote field bindings for both selected sources | Independent mutations to evidence ID, URL, snapshot SHA-256, verifier-run ID, collection-execution ID, and quoted text did not promote the altered source. | PASS |
| Promoted quoted text is evidenced by the retained snapshot bytes | A quote present in `opened_excerpt` but absent from the correctly hashed retained snapshot bytes promoted to `SUPPORTED`. | **FAIL** |

## Observed commands and results

| Command / operation | Result |
|---|---|
| `gh repo clone Sconiboy/GEO_AEO_AIOS_Platform ...`; `git rev-parse a4f5788^{commit}`; `git branch -r --contains a4f5788` | Resolved the requested commit and confirmed it is contained by `origin/main`. |
| `git archive --format=tar a4f5788 ...`; archive extraction; `diff -r --brief`; sorted `sha256sum` manifests | Exact 175-file tree match; archive SHA-256: `b58a21d41fca7f13663745d38a2e59ea61a7d5e68c077eb3e2b8fa16ad4cf1f8`. |
| `pytest` | **108 passed in 7.39s**. |
| `mypy src` | **Success: no issues found in 28 source files**. |
| Independent, fresh-registry adversarial harness | **54 controls held; 1 bypass**. The only bypass was `quote_snapshot_content_binding`: a promoted quote was absent from the retained, correctly hashed snapshot bytes. |

## Findings

### P0 — Promoted quote text is not bound to the retained snapshot content

`evaluate_claim_support()` accepts a human quote when its six fields equal selected-record metadata and its `quoted_passage` is a substring of `evidence.opened_excerpt`. It then calls `_verify_retained_snapshot()`, which checks that the retained snapshot exists and hashes to the evidence/execution digest. The path never searches the retained bytes for that same quote. [1]

The independent harness created a real content-addressed snapshot containing `independent retained client snapshot bytes`, with the exact SHA-256 recorded in both the verification artifact and trusted collection execution. It supplied an `opened_excerpt` and human quote of `Beautiful is better than ugly.`; that text was intentionally absent from the retained snapshot bytes. The comparator nevertheless returned `SUPPORTED` for the adjudicated client statement. This falsifies the required evidence binding between the promoted quoted text and the retained snapshot, despite the other ID, URL, digest, verifier-run, execution, and context controls holding.

This is approval-critical because a reviewer could promote a claim with a quote that exists only in a mutable/independent ledger field, not in the retained source artifact that the snapshot digest purports to authenticate.

## Controls that held

The reviewed commit closes the two failures documented in the current Sprint 85 gate: `ForensicGapAnalyzer.analyze_gaps()` parses every raw artifact and rejects a supplied model that differs from it, while `_verify_retained_snapshot()` requires a snapshot reference, reloads the snapshot, recomputes its SHA-256, and compares it to the evidence and execution record. [1] [2] The independent harness also confirmed rejection of malformed, foreign, rehashed, and attacker-issued collection executions on both selected sources. [1] [3]

## Next action

Restrict the remediation to the missing semantic provenance proof. During human promotion, derive a deterministic textual representation from the loaded retained snapshot bytes and require the exact `QuotedEvidencePassage.quoted_passage` to occur in those bytes before returning a promoted assessment. This verification must occur after loading and SHA-256-validating the snapshot and must apply to each selected quote. Add adversarial tests that use a valid retained snapshot whose bytes omit the promoted quote, for **both client and competitor** records; those tests must reject promotion. Retain the existing raw-model-equivalence, snapshot-digest, six-field quote, and trusted-issuer execution tests.

No code, workflow, setting, or secret was modified in this review. This document is the only intended repository modification.

## References

[1]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/a4f578815b6b3bc2d710e35ecbff78106d2b696b/src/collector/comparative_reconciler.py "Comparative promotion and retained-snapshot checks"
[2]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/a4f578815b6b3bc2d710e35ecbff78106d2b696b/src/collector/gap_analyzer.py "Raw-artifact authority and gap-record construction"
[3]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/a4f578815b6b3bc2d710e35ecbff78106d2b696b/src/collector/execution_registry.py "Trusted collection-execution issuer registry"
[4]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/a4f578815b6b3bc2d710e35ecbff78106d2b696b/src/domain/human_decision.py "Human quote decision contract"
[5]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/a4f578815b6b3bc2d710e35ecbff78106d2b696b/docs/MANUS_SPRINT85_REVIEW.md "Current Sprint 85 review gate"
