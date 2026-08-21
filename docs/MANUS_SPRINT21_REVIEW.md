# Manus Sprint 2.1 Source-Policy Review

**Reviewed commit:** `cfaaba9`  
**Status:** **Hardening progress verified; do not collect client or query-map sources yet**  
**Date:** August 21, 2026

## What passed independent review

The Sprint 2.1 controls are real improvements. Independent execution reproduced the declared checks:

| Check | Result |
|---|---|
| Test suite | 24 passed |
| Coverage | 84% reported by `pytest-cov` |
| Static type check | `mypy src` passed with 0 issues |
| HTTPS verification | Public HTTPS test endpoint returned `opened_verified` with a persisted hash matching the stored bytes |
| HTTP rejection | Default policy returned `inaccessible` with exit code 1 |
| Hermetic testing | Source-policy tests now mock the request path instead of relying on external network availability |
| Ignore policy | New runtime snapshots and reports are ignored for future Git additions |

The policy correctly rejects non-HTTPS URLs by default, checks hostname resolution for many dangerous address classes, enforces a declared response-size ceiling, and rejects unsupported content types.

## Blocking gaps before real collection

The current implementation must not receive arbitrary client or query-map URLs yet. The following are code-level gaps, not theoretical concerns.

| Priority | Gap | Required change |
|---|---|---|
| P0 | `urllib` follows redirects before `final_url` is checked. The code validates a redirect target only **after** the HTTP client may have already fetched it. | Disable automatic redirects and implement a redirect loop that validates scheme, host, resolved address, policy, and redirect count **before every hop**. |
| P0 | DNS is checked, then `urlopen` resolves and connects again. A DNS rebinding target can change between validation and connection. | Resolve safely per hop and connect only to validated resolved addresses, or use a hardened transport with an explicit anti-rebinding design. Document the residual risk if this is not feasible in the pilot. |
| P1 | “Visible text” verification still accepts a quote found in raw decoded HTML before checking stripped text. A quote inside a script/style block can still produce `opened_verified`. | For HTML/XHTML, match only against a parsed visible-text representation and store extraction method plus text-location metadata. Use raw text only for `text/plain` or approved JSON fields. |
| P1 | `.gitignore` prevents new snapshot/report additions, but the earlier `data/snapshots/...txt` and `reports/sample_report.md` remain tracked in history/current tree. | Remove or relocate tracked generated artifacts, keep only `.gitkeep` plus explicitly synthetic fixtures, and document retention/deletion behavior. |
| P1 | Policy enforcement failures are converted to generic `inaccessible` records with no typed reason visible to an operator. A broad `except Exception` also masks unexpected code faults. | Add structured failure reasons, retain safe policy warnings, log unexpected exceptions, and avoid treating implementation faults as ordinary source inaccessibility. |
| P2 | Tests prove individual rules, but not a redirect to unsafe host, content-type failure after redirect, raw-script quote false positive, or DNS-rebinding defense. | Add hermetic tests for each missing boundary before promotion. |

## Approval boundary

**Approved:** source-policy remediation and local query-map **design** work that does not collect external sources.

**Not approved:** live collection of a query-map dataset, client URLs, Reddit/forums/review platforms, answer-surface harvesting, or model API activation.

## Required next work package: Sprint 2.2 Secure Fetch and Artifact Integrity

1. Replace default automatic redirects with policy-validated manual redirect handling.
2. Add an explicit anti-DNS-rebinding transport strategy or documented containment limitation.
3. Correct visible-text extraction and quote-alignment rules by content type.
4. Remove tracked generated snapshot/report artifacts and document local retention/deletion controls.
5. Add the hermetic security tests listed above.
6. Add structured collection-failure fields to the evidence model and CLI output.

After Sprint 2.2 passes, the platform may collect a **small, non-client controlled query-map dataset** from pre-approved public sources. A client audit remains a separate authorization and product-readiness decision.
