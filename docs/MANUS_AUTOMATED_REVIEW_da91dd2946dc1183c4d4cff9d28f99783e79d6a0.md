# Manus Automated Provenance Review

| Review item | Observed value |
|---|---|
| Repository | `Sconiboy/GEO_AEO_AIOS_Platform` |
| Reviewed branch and commit | `main` at `da91dd2946dc1183c4d4cff9d28f99783e79d6a0` |
| Supplied archive | `review-context.tgz`; SHA-256 `ff3da82bcbab2da7c65962dd81b8e35e0ee10a7bc51e60f32c564378fe557013` |
| Review gate | [`docs/MANUS_SPRINT85_REVIEW.md`][1] |
| Reviewer | Manus Review Bot |
| Date | August 22, 2026 |
| Verdict | **REJECTED — validation completed, but approval-critical provenance remains falsifiable.** |

## Decision

The supplied archive did not contain a `.git` directory, so it did not embed a commit identifier. I extracted it into an isolated directory, fetched the requested Git object from the stated repository, and compared the extracted tree byte-for-byte against a detached checkout of `da91dd2946dc1183c4d4cff9d28f99783e79d6a0`. The comparison returned exit status `0` with no differences. The archive is therefore the exact requested tree.

The implementation correctly rejects the six direct quote-field mutations, raw-artifact/model substitutions, raw-ledger byte changes, and most execution-context mutations. It also rejects a self-consistent but unregistered execution, an execution attested by a foreign issuer, and an execution with a tampered canonical digest. [2] [3] [4]

Approval is nevertheless not justified. A decision-targeted human-supported claim was promoted when the retained snapshot bytes existed and hashed to the declared SHA-256, but **neither promoted quoted passage was present in those bytes**. The final gate checks a quote only against `EvidenceRecord.opened_excerpt`; it reloads and hashes the snapshot, but never proves that the promoted quote is recoverable from the retained snapshot. A hash of unrelated retained bytes is not evidence for quoted text. [2] [3] [5]

A second falsification shows that candidate authority remains self-asserted inside the caller-supplied gap record. An issued execution whose `candidate_id` was changed, paired with a self-consistent gap-record candidate having the current query, URL, and manifest authorization, was accepted. The test did **not** forge an issuer signature: it used the controlled harness's valid issuer to isolate the final gate's candidate-origin validation. The acceptance shows that the gate proves membership in a self-hashed gap record, but does not prove that the candidate was derived from the current observation's actual citation set. [2] [4] [6]

> **Approval boundary:** A promoted human quote must be reproducible from retained, hash-verified snapshot bytes under a specified extraction/normalization rule. A selected execution's candidate must also be proven to arise from the current observation and authorized raw artifacts, not merely appear in a recomputed gap-record payload.

## Observed commands and results

| Command or procedure | Result |
|---|---|
| `tar -tzf /home/ubuntu/upload/review-context.tgz` and path screening | No absolute or traversal member paths detected. |
| Extracted archive compared with a fresh detached checkout of `da91dd2946dc1183c4d4cff9d28f99783e79d6a0` using `diff -qr --exclude=.git` | **Exact match**; comparison exit status `0`. |
| Initial `pytest` invocation | Tool unavailable in the base environment; no test result claimed from this attempt. |
| `sudo pip3 install -e '.[dev]' && pytest` | **108 passed** in 3.87 seconds. |
| `mypy src` | **Success: no issues found in 28 source files.** |
| Isolated external harness: `python3 /home/ubuntu/independent_provenance_review.py` | Completed the independent mutation matrix; two approval-critical falsifications were accepted as detailed below. |

The review was performed against the extracted archive. The external harness and its JSON result artifact were stored outside the repository; this review document is the only repository modification.

## Binding-falsification matrix

| Control tested | Independent mutation or condition | Observed result | Status |
|---|---|---|---|
| Human quote evidence ID | Freshly digested human decision with a foreign evidence ID | Client assessment fell closed to `candidate_for_human_semantic_review`. | **PASS** |
| Human quote URL | Freshly digested decision with a foreign URL | Client assessment fell closed. | **PASS** |
| Human quote snapshot SHA-256 | Freshly digested decision with a different 64-hex digest | Client assessment fell closed. | **PASS** |
| Human quote verifier-run ID | Freshly digested decision with another verifier run | Client assessment fell closed. | **PASS** |
| Human quote collection-execution ID | Freshly digested decision with another execution ID | Client assessment fell closed. | **PASS** |
| Human quote text | Freshly digested decision with text absent from `opened_excerpt` | Client assessment fell closed. | **PASS** |
| Quote text versus retained snapshot bytes | Snapshot bytes existed and their SHA-256 matched evidence and execution, but contained neither decision-targeted quote | Both decision-targeted assessments were `supported`. | **FAIL** |
| Gap record ledger digest | The raw ledger received one trailing newline while the record retained the old SHA-256 | Comparator rejected the exact-byte SHA-256 mismatch. | **PASS** |
| Gap analyzer raw-model authority | Substituted `AuditRun`, profile, query map, and manifest models, each differing from the supplied raw bytes | Analyzer rejected all four canonical-artifact mismatches. | **PASS** |
| Execution evidence ID, query, URL, verifier, snapshot, raw-ledger, observation, raw-answer, profile, manifest, and query-map bindings | Recomputed execution for each individual mutation, then obtained a controlled valid issuer attestation | Comparator rejected every listed mismatch. | **PASS** |
| Selected execution candidate origin | Changed `candidate_id`; supplied a self-consistent gap-record candidate matching the current URL/query/manifest and a valid issued execution | Comparator accepted the altered candidate provenance. | **FAIL** |
| Self-consistent unregistered execution | Recomputed digest and claimed the trusted issuer ID without a registry attestation | Rejected for missing issuer attestation. | **PASS** |
| Foreign issuer execution | Execution issued by a distinct attacker-controlled registry | Rejected as untrusted. | **PASS** |
| Tampered execution canonical digest | Replaced the digest without recomputation | Rejected for failed execution integrity. | **PASS** |

## Findings

### P0 — Retained snapshot bytes do not prove the promoted quoted text

`evaluate_claim_support()` accepts a human quote when its six fields match the evidence and when the quoted passage is contained in `opened_excerpt`. It then calls `_verify_retained_snapshot()`, which verifies only that the retained bytes hash to the artifact and execution digest. The function does not search or otherwise derive the quote from those bytes. [2] The `VerificationArtifact.quote_exact_match` field is an asserted Boolean rather than a recomputed proof over the stored material. [5]

The independent harness constructed two `OPENED_VERIFIED` records whose snapshot references and SHA-256 values were valid. It retained bytes under the correct content-addressed names, deliberately made those bytes unrelated to the ledger excerpts, constructed a valid human decision with all six direct quote bindings, and used valid issuer-attested executions. The comparator returned `supported` for both decision-targeted claims. The promoted quote is therefore not bound to evidence content, only to a separate mutable ledger excerpt and a digest of other bytes.

### P0 — Candidate authority can be injected into a self-consistent gap record

`_validate_execution_authority()` resolves a candidate by identifier from the supplied `gap_record` and validates URL/query/manifest consistency. It does not prove that the candidate is present in the current observation's explicit answer citations or was generated from the raw artifacts. [2] `ForensicGapAnalysisRecord.verify_integrity()` recomputes a public SHA-256 over the supplied payload; it is an integrity check, not an authenticity attestation. [6]

The independent harness changed an execution's candidate ID, recomputed its digest, issued it through the controlled trusted registry, and supplied a corresponding candidate in a rehashed gap record. The forged candidate was internally coherent with the current manifest, query map, URL, observation ID, and evidence selection, yet it did not have to derive from the observation's citation set. The final comparator accepted it. This is not evidence of a broken issuer signature; it is evidence that final candidate-origin validation is incomplete.

## Next action

The next remediation should be limited to the two failed proof boundaries and accompanied by adversarial tests.

1. **Bind quote text to retained bytes.** At promotion, load the content-addressed snapshot, verify its SHA-256, apply the verifier's declared deterministic extraction/normalization rule, and reject unless the exact `quoted_passage` is reproducible from that result. If byte-level quote searching is unsuitable for HTML, bind a normalized extracted-text artifact and its digest into the verification artifact and execution record.
2. **Make candidate origin independently verifiable.** Regenerate the authorized candidate set from the parsed current observation, profile, query map, manifest, and raw ledger, or make the gap-analysis artifact issuer-attested. The comparator must reject a candidate that is merely inserted into a self-recomputed gap record, even if URL and query match the manifest.
3. **Add end-to-end negative tests.** Reject hash-valid retained bytes that omit the promoted quote, including normalization edge cases. Reject a valid issuer-attested execution whose candidate appears only in a rehashed gap record and is absent from the observation-derived candidate set. Retain the existing six quote-field, raw-artifact, execution-context, self-consistent, and foreign-issuer tests.

No code, workflow, setting, or secret was changed in this review. This document is the only intended repository modification.

## References

[1]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/da91dd2946dc1183c4d4cff9d28f99783e79d6a0/docs/MANUS_SPRINT85_REVIEW.md "Sprint 8.5 provenance review gate"
[2]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/da91dd2946dc1183c4d4cff9d28f99783e79d6a0/src/collector/comparative_reconciler.py "Comparative reconciliation and human-promotion gate"
[3]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/da91dd2946dc1183c4d4cff9d28f99783e79d6a0/src/domain/human_decision.py "Human decision quote-binding contract"
[4]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/da91dd2946dc1183c4d4cff9d28f99783e79d6a0/src/collector/execution_registry.py "Collector execution issuer registry"
[5]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/da91dd2946dc1183c4d4cff9d28f99783e79d6a0/src/domain/models.py "Evidence and verification-artifact contract"
[6]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/da91dd2946dc1183c4d4cff9d28f99783e79d6a0/src/domain/gap_analysis.py "Gap-record canonical integrity calculation"
