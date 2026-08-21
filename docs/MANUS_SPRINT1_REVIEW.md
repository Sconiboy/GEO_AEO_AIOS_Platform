# Manus Sprint 1 Implementation Review

**Reviewed commit:** `e391879`  
**Status:** **Conditionally approved as an early local prototype; not approved for any live audit or client-facing report**  
**Date:** August 21, 2026

## What is good

The core architectural correction has been implemented in code, not merely copied into a planning document. The repository now has typed domain models, runtime validation before report export, a local fixture runner, a Markdown exporter, and negative-path tests for missing evidence, missing ledger records, and inaccessible evidence.

The `ClaimRecord` to `EvidenceRecord` relationship is the right starting point. The report exporter calls runtime validation before rendering, which is the correct enforcement location. Hermes has not been added as a final authority, and no external model API has been introduced prematurely.

## Blocking finding: the sample evidence is not trustworthy

The current fixture labels three records as `opened_verified` and renders a **HIGH 0.90** confidence conclusion for Searchbloom. At least two cited records fail direct source checks:

| Fixture record | Current fixture claim | Direct review result | Required change |
|---|---|---|---|
| `ev-001` TechCrunch | Opened, independent editorial source supporting GEO leadership | The referenced URL could not be retrieved during review. It cannot remain `opened_verified` without a stored source snapshot and a successful verifier result. | Mark inaccessible/unverified or replace with a verifiable fixture source. |
| `ev-002` Reddit | r/SEO discussion recommending Searchbloom for AEO | The URL resolves to a deleted 14-year-old **r/Maplestory** collector thread, not an r/SEO AEO-agency discussion. | Remove immediately; retain as an adversarial invalid-URL fixture. |
| `ev-003` G2 | Review content specifically supports technical SEO, JSON-LD entity graphs, and clear ROI tracking | The G2 page exists, but the cited excerpt must be matched to a stored opened excerpt. Current direct page content supports general SEO/marketing claims, not the fixture’s precise language as written. | Replace with a verbatim excerpt and snapshot, or reduce/remove the claim. |

This does not invalidate the architecture. It proves why the architecture needs a real verifier. But the generated report must not be described as an audited example or shown to a client.

## Blocking finding: the project is not reproducible from GitHub

The repository currently has no `pyproject.toml`, `requirements.txt`, lock file, virtual-environment setup instructions, or CI workflow. The claimed `pytest` and `mypy` run could not be independently reproduced from a fresh clone because neither test dependency is declared or installed by the repository.

Also, “9/9 tests passing” is not “100% test coverage.” The latter is a measurable coverage statistic and should not be claimed without a coverage tool and threshold.

## Validation gaps to fix before live data

1. A claim with one valid evidence ID and one invalid or missing evidence ID currently passes because the validator only fails when **no** valid evidence remains. Require all referenced supporting evidence IDs to be valid, or explicitly model optional/context evidence separately.
2. Missing or invalid counter-evidence IDs are silently ignored. Counter-evidence must either validate, create a visible validation failure, or be explicitly recorded as unresolved.
3. `url` is currently an unconstrained string despite importing `HttpUrl`. Validate URL syntax and canonicalize it before persistence.
4. `opened_verified`, `is_independent`, `is_syndicated_duplicate`, and `snapshot_id` are currently self-asserted fixture fields. Add a separate verification artifact with method, verifier run ID, verifier timestamp, snapshot path/hash, and limitations.
5. Confidence is deterministic but still arbitrary. The current 0.90 score comes from three fixture labels and does not evaluate source recency, exact quote alignment, actual source quality, unique root domains, verified snapshot existence, or source dependence. Treat it as a development placeholder, not an audit-grade score.
6. The report must visibly label all fixture output **SAMPLE / SYNTHETIC / NOT CLIENT EVIDENCE**. Do not use real-brand claims in synthetic test fixtures unless every source is real, verified, and the report is clearly non-client internal testing.

## Required remediation gate

Before adding a live query connector, Hermes parser, scraper, or paid API, complete the following:

| Priority | Required change | Acceptance condition |
|---|---|---|
| P0 | Add reproducible dependency management and CI | A fresh clone installs, runs tests, runs mypy, and runs the fixture CLI from documented commands. |
| P0 | Replace or relabel the current fixture | No client-facing report can be produced from fabricated or unverified source facts. |
| P0 | Tighten supporting/counter-evidence validation | New tests cover mixed valid/invalid support IDs, missing counter IDs, quote mismatch, circular source, stale source, and zero evidence. |
| P1 | Add a verification artifact contract | Each opened/verified source has a snapshot hash, timestamp, verifier, method, quote-alignment result, and limitations. |
| P1 | Make confidence explainable | The report exposes each score input and labels the scoring model as provisional until evaluated. |
| P1 | Add fixture/report safety labels | Synthetic or fixture reports cannot be confused with live client audit evidence. |

## Approval outcome

**Approved:** Continue Sprint 1 hardening. The evidence-led design is correct and the local prototype has a useful spine.

**Not approved:** Do not define a first live audit target, call external models, scrape sources, present the report to a client, or claim an audited confidence score until the P0 remediation gate passes.

When the remediation commit is pushed, Manus will re-review the code and then help define the first controlled live audit.
