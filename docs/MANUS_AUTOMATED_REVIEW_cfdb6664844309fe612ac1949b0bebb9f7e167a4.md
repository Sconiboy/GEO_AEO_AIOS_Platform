# Automated Provenance Review — `cfdb6664844309fe612ac1949b0bebb9f7e167a4`

**Reviewed repository:** `Sconiboy/GEO_AEO_AIOS_Platform`  
**Reviewed branch and commit:** `main` at `cfdb6664844309fe612ac1949b0bebb9f7e167a4`  
**Reviewer:** Manus Review Bot  
**Review date:** August 22, 2026  
**Verdict:** **APPROVED — the requested provenance-promotion gate was independently validated.**

## Decision

The supplied `review-context.tgz` was extracted in an isolated review directory. Its archive SHA-256 was `05e7eb2640761952042a094e240bc125be1b2f46637d76f13986f9f0413ae551`. The archive contains no embedded Git metadata, so identity was independently established against a fresh checkout of `Sconiboy/GEO_AEO_AIOS_Platform`: all **201** file paths and Git blob object IDs match the authoritative tree of `cfdb6664844309fe612ac1949b0bebb9f7e167a4`, with no extracted symlinks. The requested commit is the current `main` ref at review time.

The current Sprint 85 document records the prior rejection criteria: a raw/model identity bypass and a syntactically plausible but unretained snapshot digest. This review evaluated the requested commit rather than inheriting that historical verdict. The requested commit parses and compares raw artifacts before analysis, resolves promoted evidence from raw ledger bytes, requires a trusted execution registry, validates execution integrity and current context on both selected sources, and reloads retained snapshot bytes before human promotion. [1] [2] [3]

> **Approval scope:** This is an approval of the specified commit for the provenance conditions in this review. It is not an approval for unreviewed operational, security, product, or live-collection behavior.

## Required-Control Results

| Required approval control | Independent result | Verdict |
|---|---|---|
| Promoted human quotes bind exact evidence ID, URL, quoted text, snapshot SHA-256, verifier-run ID, and collection-execution ID | An authentic two-source decision promoted. Each of the six bindings was then recomputed with a forged value independently for both client and competitor quotes; every altered quote remained non-promoted. | **PASS** |
| Each selected collection execution verifies integrity | A corrupt canonical digest was rejected for each selected execution. | **PASS** |
| Each selected execution binds the current evidence, raw ledger, observation, profile, query map, and manifest | Self-consistently recomputed mutations of evidence ID, URL, verifier run, snapshot digest, raw-ledger digest, observation ID, raw-answer digest, profile ID, profile digest, manifest digest, query-map digest, target query, and candidate were rejected for both selected executions. | **PASS** |
| Foreign or forged collection executions cannot be substituted | A valid foreign-issuer execution, an altered attestation, and an unsigned self-consistent execution were rejected. | **PASS** |
| Gap-record ledger SHA-256 matches the exact raw ledger bytes | A self-consistent gap record with a forged source-ledger SHA-256 was rejected against the caller-supplied raw bytes. | **PASS** |
| A same-run-ID but different supplied ledger model cannot affect gap analysis | An empty `AuditRun` with the authentic run ID was rejected because it did not canonically match the parsed raw ledger artifact. | **PASS** |
| Promoted selected evidence has retained, hashable snapshots | Missing client bytes, missing competitor bytes, and substituted retained bytes for either source were rejected. | **PASS** |

The final comparator requires all six per-quote fields to match the resolved `EvidenceRecord`, performs trusted issuer-registry verification, and verifies the snapshot bytes before returning a human-supported assessment. [1] The upstream analyzer parses the raw profile, query map, manifest, and ledger; it rejects a caller-supplied model that differs from those artifacts and uses the parsed versions for analysis. [2] The execution contract hashes the required execution fields, while registry verification compares the exact caller-supplied record against the trusted, durable issued record and its HMAC attestation. [3] [4]

## Observed Commands and Results

| Command or procedure | Observed result |
|---|---|
| `sha256sum review-context.tgz`; isolated extraction; archive file manifest compared with `git ls-tree -r cfdb666...` using Git blob IDs | Archive SHA-256 recorded above; **201 / 201** paths and blob IDs matched; no symlinks were present. |
| Fresh Git retrieval of `Sconiboy/GEO_AEO_AIOS_Platform`; `git show`; `git merge-base --is-ancestor cfdb666... origin/main` | Commit exists, is reachable from `main`, and `origin/main` resolved to `cfdb6664844309fe612ac1949b0bebb9f7e167a4`. |
| `mypy src` | **Success: no issues found in 28 source files.** |
| `pytest --cov=src tests/` | **108 passed** in 4.97 seconds; total coverage reported as 83%. |
| Independent external adversarial harness | **50 cases**: one authentic two-source promotion plus 49 attempted falsifications. Every falsification was blocked or remained non-promoted. The harness was written outside the repository and did not modify repository source, settings, workflows, or secrets. |

## Findings

No approval-critical provenance failure was reproduced. The independent harness established a baseline with two `OPENED_VERIFIED` evidence records, exact human quotes, reloadable snapshot bytes, two issued execution records, and a canonically bound human-decision record. Both source assessments promoted to `SUPPORTED` only under that authentic baseline.

The review then tried to falsify every requested quote binding separately for **each** selected source. For every forged value—evidence ID, evidence URL, snapshot SHA-256, verifier-run ID, collection-execution ID, and quoted text—the affected source fell back to `CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW`; it did not promote. The other, unaltered source could remain supported, which is the expected per-source behavior rather than a bypass.

The execution tests were deliberately self-consistent where possible: altered execution fields were accompanied by recomputed execution digests, and altered gap records were accompanied by recomputed gap digests. These attempts still failed due to exact equality checks against the current raw artifacts, candidate authorization, and trusted durable registry state. This matters because a digest check alone would not reject an attacker who can recompute an unsigned digest. [1] [3] [4]

## Next Action

No remediation is required for this narrow approval boundary. Preserve the existing adversarial coverage and rerun the same provenance review whenever changes affect `comparative_reconciler.py`, `gap_analyzer.py`, `candidate_collection.py`, `execution_registry.py`, the human-decision contract, or snapshot retention. Any later review must again use the exact raw artifact bytes and a registry configuration that is separate from caller-controlled inputs.

## References

[1]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/cfdb6664844309fe612ac1949b0bebb9f7e167a4/src/collector/comparative_reconciler.py "Comparative promotion gate"
[2]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/cfdb6664844309fe612ac1949b0bebb9f7e167a4/src/collector/gap_analyzer.py "Raw-artifact canonicality enforcement"
[3]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/cfdb6664844309fe612ac1949b0bebb9f7e167a4/src/domain/candidate_collection.py "Collection execution integrity contract"
[4]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/cfdb6664844309fe612ac1949b0bebb9f7e167a4/src/collector/execution_registry.py "Trusted execution registry"
[5]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/cfdb6664844309fe612ac1949b0bebb9f7e167a4/docs/MANUS_SPRINT85_REVIEW.md "Current Sprint 85 review gate"
[6]: https://github.com/Sconiboy/GEO_AEO_AIOS_Platform/blob/cfdb6664844309fe612ac1949b0bebb9f7e167a4/pyproject.toml "Strict type-check configuration"
