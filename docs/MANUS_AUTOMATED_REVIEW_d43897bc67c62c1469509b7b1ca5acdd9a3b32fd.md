# Automated Provenance Review — `d43897bc67c62c1469509b7b1ca5acdd9a3b32fd`

**Repository:** `Sconiboy/GEO_AEO_AIOS_Platform`
**Reviewed ref:** `main` at `d43897bc67c62c1469509b7b1ca5acdd9a3b32fd`
**Reviewer:** Manus Review Bot
**Review date:** August 22, 2026
**Verdict:** **REJECTED — validation completed, but promoted quote text is not proven against the retained snapshot bytes.**

## Decision

The supplied `review-context.tgz` was safely extracted and independently matched against a fresh Git archive of the requested commit. The documented test suite and strict static type check both passed. The implementation also held against the requested attacks on the six visible human-quote fields, raw-ledger/model substitution, unavailable or substituted snapshots, self-forged executions, foreign-attested executions, and every selected-execution context field.

Approval is nevertheless not justified under the stated gate. A human-supported assessment can still be promoted when the human quote is absent from the retained snapshot bytes. The gate checks that the quote is a substring of the ledger's `opened_excerpt`, and independently checks that retained bytes match the snapshot digest. It does **not** prove that `opened_excerpt`, and therefore the promoted `quoted_passage`, occurs in those retained bytes. [1] [2]

> **Approval boundary:** A promoted human quote must be demonstrated verbatim in the retained, SHA-256-verified snapshot bytes—not only in a caller-provided ledger excerpt bearing the same snapshot digest.

| Required control | Independent result | Status |
|---|---|---|
| Exact archive identity | Archive SHA-256: `ba18731df8aaef2b03b2cdabd01c09837d48bbb9aeb6a140e37a65ed6598d4dd`; 185 files; fresh Git archive file-manifest SHA-256 was identical (`a95ea9c7bdf24b2762d0910ac93063810c4cac2f569b8a8b520649322539a3fb`); content difference count was zero. | **PASS** |
| Declared validation | `pytest --cov=src tests/`: **108 passed**; `mypy src`: **Success: no issues found in 28 source files**. | **PASS** |
| Authentic human promotion | A fully bound record with retained client and competitor snapshots promoted to `SUPPORTED`. | **PASS** |
| Six quote fields | Independent alteration of evidence ID, URL, snapshot SHA-256, verifier-run ID, collection-execution ID, or quote text did not promote the client claim. | **PASS** |
| Quote text is actually in retained bytes | A fabricated ledger excerpt and matching human quote, both absent from the retained snapshot, still promoted to `SUPPORTED` when all identifiers, digests, and trusted execution bindings were self-consistent. | **FAIL** |
| Raw-ledger model identity and gap-record ledger SHA-256 | A same-run-ID, empty supplied `AuditRun` was rejected against unchanged raw bytes. The selected execution’s source-ledger SHA-256 mismatch was also rejected. [1] [3] | **PASS** |
| Retained snapshot availability and bytes | Missing retained bytes and substituted retained bytes were rejected before promotion. [1] | **PASS** |
| Selected execution integrity and full context | Independently rehashed mutations to evidence ID, URL, verifier-run ID, snapshot SHA-256, raw-ledger SHA-256, observation ID, raw-answer SHA-256, profile ID/SHA-256, manifest SHA-256, query-map SHA-256, candidate ID, and target query were blocked. [1] [4] | **PASS** |
| Forged or foreign executions | A self-consistent but unissued execution and an attacker-attested execution were rejected by the configured trusted issuer registry. [1] [4] | **PASS** |

## Observed Commands and Results

| Command or procedure | Observed result |
|---|---|
| `sha256sum review-context.tgz`; `tar -tzf`; safe path/type checks | Archive had one safe top-level directory, 206 entries, no traversal paths, symbolic links, hard links, or embedded `.git` metadata. |
| Fresh clone, detached checkout of `d43897bc67c62c1469509b7b1ca5acdd9a3b32fd`, and `git archive` extraction | Requested object resolved exactly; `origin/main` was the same commit at review start. |
| SHA-256 file-manifest comparison and `diff -qr` between the supplied extraction and fresh Git archive | 185 files on each side, identical deterministic manifests, zero content differences. |
| `.venv/bin/pytest --cov=src tests/` | Exit `0`; **108 passed in 4.90s**; 83% aggregate coverage. |
| `.venv/bin/mypy src` | Exit `0`; **Success: no issues found in 28 source files**. |
| Independent isolated adversarial harness | 28 checks run: 27 passed and one approval-critical falsification succeeded. The successful bypass used a valid snapshot digest and retained bytes, but a fabricated `opened_excerpt`/human quote absent from those bytes. |

## Finding

### P0 — Promoted quote text has no retained-byte proof

`evaluate_claim_support()` accepts a quote when its six declared fields match the selected evidence and execution and when `quoted_passage` is found in `evidence.opened_excerpt`. [1] It subsequently invokes `_verify_retained_snapshot()`, which loads the snapshot and recomputes its SHA-256, but it never tests either `opened_excerpt` or `quoted_passage` against `retained_bytes`. [1] The quote contract makes `quoted_passage` non-empty and digest-binds it into the human decision, but it likewise does not bind the text to retained content. [2]

The independent harness therefore constructed a ledger in which the client evidence retained its authentic `snapshot_id`, authentic snapshot SHA-256, verifier-run ID, trusted collection execution, and all current profile/query-map/manifest/observation/raw-ledger bindings. It changed only the raw-ledger `opened_excerpt` to:

> `Fabricated claim that does not occur in retained snapshot bytes.`

The human decision quoted precisely that fabricated text. The supplied snapshot store contained the original bytes, whose SHA-256 matched the evidence and collection execution. The comparator returned `SUPPORTED`. This directly falsifies the required **quoted-text-to-snapshot** binding.

The other controls were materially effective. The analyzer parses raw artefacts and rejects a same-run-ID model substitution; the comparator resolves selected evidence from raw ledger bytes, compares selected execution fields to current raw contexts, verifies authorized candidate/query/URL context, and asks the protected registry to resolve the exact issued record. [1] [3] [4]

## Next Action

Remediate the single P0 gap before another approval review. During human promotion, after retained bytes are loaded and their digest is verified, require `quoted_passage` to occur verbatim in those bytes under a defined, documented decoding/normalization policy. If the ledger retains an `opened_excerpt`, require that excerpt to be derived from or verified against the same retained bytes as well. Add an adversarial end-to-end test that preserves valid evidence ID, URL, snapshot digest, verifier-run ID, trusted execution, raw-ledger SHA-256, observation, profile, query map, and manifest while substituting only a ledger excerpt/quote not present in the snapshot; it must not promote.

No code, workflow, setting, secret, or repository content other than this review record was intentionally changed.

## References

[1]: ../src/collector/comparative_reconciler.py "Comparative promotion, retained snapshot, and execution-binding enforcement"
[2]: ../src/domain/human_decision.py "Human quote contract and canonical digest"
[3]: ../src/collector/gap_analyzer.py "Raw-artifact authority and gap-record construction"
[4]: ../src/collector/execution_registry.py "Trusted execution issuer and registry verification"
