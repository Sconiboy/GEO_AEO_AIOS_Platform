# Automated Provenance Review — `b2ac3a789555014c40b042eccb89567eb2221591`

**Reviewed repository:** `Sconiboy/GEO_AEO_AIOS_Platform`
**Reviewed branch and commit:** `main` at `b2ac3a789555014c40b042eccb89567eb2221591`
**Review basis:** Supplied `review-context.tgz`, independently re-extracted and canonical-tree-compared with the requested commit.
**Archive SHA-256:** `45e0322325e7b417010265e60b1310adac84a309e6e620d3d53c909a4c9ffa6c`
**Reviewer:** Manus Review Bot
**Date:** August 22, 2026
**Verdict:** **APPROVED**

## Decision

Approval is justified. The supplied archive reconstructs the exact canonical Git tree of the reviewed commit, and the provenance gate resisted every independent falsification attempt. A promoted human assessment required a quote binding the exact evidence ID, URL, quoted text, snapshot SHA-256, verifier-run ID, and collection-execution ID. It also required content-addressed retained snapshot bytes and a selected collection execution issued by the configured trusted registry. [1] [2] [3]

The independent harness first produced a valid human-supported promotion for both selected sources using the complete context. It then ran **26 negative cases**. Each altered human-quote field, missing or substituted retained snapshot, raw-ledger byte alteration, same-run-ID substituted ledger model, forged execution digest, self-consistent unregistered execution, and execution attested by a foreign registry was rejected or left the assessment unpromoted. [1] [2] [3] [4]

> **Approval boundary:** This verdict applies only to the exact commit and archive fingerprint above. Any change to evidence, raw-ledger bytes, observation, profile, query map, manifest, execution registry, snapshot store, or human-decision contract requires a new provenance review.

| Required control | Independent result | Status |
|---|---|---:|
| Supplied archive is the requested commit | The archive reconstructed tree `ed3c765b395f99be66bad006cc0fc3bde4e25aa0`, equal to the requested commit tree; both contained 199 tracked entries. The tracked-but-ignored `.coverage` blob was explicitly included in the reconstruction and matched (`cb07bb38f748790ef8dfacfe051f0a5a65a10656`). | **PASS** |
| Promoted quote binds exact evidence ID, URL, snapshot SHA-256, verifier-run ID, collection-execution ID, and quoted text | The baseline promoted. Independent mutations of all six fields left the client assessment at `candidate_for_human_semantic_review`. | **PASS** |
| Quote text is verbatim evidence | A non-present quoted passage did not promote. The decision contract also requires a non-empty quoted passage. | **PASS** |
| Selected execution integrity and current evidence context | Rehashed mutations of cited URL, verifier run, snapshot digest, source-ledger digest, observation ID, raw-answer digest, profile ID/digest, manifest digest, query-map digest, target query, candidate, and evidence ID were blocked. A forged canonical digest was also blocked. | **PASS** |
| Selected execution is authorized and trusted, not merely self-consistent | An unauthorized candidate was blocked. A locally integrity-valid execution with a new ID but no registry record was rejected; an execution issued by an attacker-controlled registry was rejected as untrusted. | **PASS** |
| Gap-record ledger SHA-256 binds exact raw bytes | Appending one ASCII space to otherwise parseable raw ledger bytes changed the computed SHA-256 and blocked comparison. | **PASS** |
| Gap analysis cannot use a substituted same-run-ID ledger model | An empty `AuditRun` model bearing the baseline run ID but not equal to the raw bytes was rejected before analysis. | **PASS** |
| Snapshot retention is proved at promotion | Human promotion was blocked when retained bytes were absent and when bytes existed under the claimed digest but hashed differently. | **PASS** |

## Observed Commands and Results

| Command | Result |
|---|---|
| `sha256sum /home/ubuntu/upload/review-context.tgz` | Archive SHA-256: `45e0322325e7b417010265e60b1310adac84a309e6e620d3d53c909a4c9ffa6c`. |
| Safe archive member listing and extraction | Completed with no absolute or traversal archive path accepted. |
| `gh repo clone Sconiboy/GEO_AEO_AIOS_Platform …` followed by `git checkout --detach b2ac3a…` | Checked out exact commit. `origin/main` resolved to `b2ac3a789555014c40b042eccb89567eb2221591`. |
| Canonical Git-tree reconstruction from fresh archive extraction | Archive tree `ed3c765b395f99be66bad006cc0fc3bde4e25aa0` equaled commit tree `ed3c765b395f99be66bad006cc0fc3bde4e25aa0`; 199 tracked entries each. |
| `pytest` in the extracted archive | **108 passed**. |
| `mypy src` in the extracted archive | **Success: no issues found in 28 source files**. |
| `pytest` in authoritative checkout | **108 passed**. |
| `mypy src` in authoritative checkout | **Success: no issues found in 28 source files**. |
| Isolated independent provenance harness | **1 authentic full-binding promotion; 26 adversarial attempts blocked**. The harness and result ledger were outside the repository and were not committed. |

## Findings

The comparator parses the raw ledger directly, computes the SHA-256 from the supplied bytes, resolves selected evidence from that parsed artifact, and cross-checks the supplied profile and query map against their raw bytes. It validates the gap record’s ledger digest before evidence resolution. [1]

For human promotion, the comparator requires all six quote bindings to match and requires the quote to occur in the opened excerpt. The data contract requires every binding field and rejects an empty quoted passage. The promotion path additionally reloads retained snapshot bytes, recomputes SHA-256, and requires equality with both evidence and execution digests. [1] [3]

Each selected collection execution is integrity-verified and checked against the current evidence URL, verifier-run ID, snapshot SHA-256, raw ledger, observation, profile, query map, manifest, and authorized candidate. The trusted execution registry rejects a record absent from its append-only registry and rejects attestation from a different issuer. [1] [2]

## Next Action

The commit is approved for the reviewed provenance gate. Preserve the immutable artifact set used for any production human-supported conclusion and require a new independent review for changes to the reviewed contracts or their enforcement paths.

No source code, workflow, setting, or secret was modified by this review. This document is the only intended repository modification.

## References

[1]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/b2ac3a789555014c40b042eccb89567eb2221591/src/collector/comparative_reconciler.py "Comparative provenance gate"
[2]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/b2ac3a789555014c40b042eccb89567eb2221591/src/collector/execution_registry.py "Trusted execution registry"
[3]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/b2ac3a789555014c40b042eccb89567eb2221591/src/domain/human_decision.py "Human decision and quoted evidence contracts"
[4]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/b2ac3a789555014c40b042eccb89567eb2221591/src/collector/gap_analyzer.py "Gap-analysis raw artifact verification"
