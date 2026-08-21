# Manus Sprint 2.2 Secure Fetch Review

**Reviewed commit:** `2a678d5`  
**Status:** **Approved to prepare a small controlled non-client query-map dataset; not approved for client collection or model-answer harvesting**  
**Date:** August 21, 2026

## Independent verification

Sprint 2.2 closes the immediate redirect and hidden-markup defects identified in the prior review. Independent execution reproduced the claimed baseline:

| Check | Result |
|---|---|
| Test suite | 24 passed |
| Coverage | 82% reported by `pytest-cov` |
| Static type check | `mypy src` passed with 0 issues |
| HTTPS public source | Returned `opened_verified` with `PARSED_VISIBLE_TEXT_BS4` and a content-addressed snapshot hash |
| HTTP source | Rejected under default HTTPS-only policy with exit code 1 |
| Script-only quote | Hermetic test rejects it as `QUOTE_NOT_FOUND` |
| Tracked generated artifacts | Removed; only `.gitkeep` anchors remain tracked |

The manual redirect loop is a material improvement: every redirect target is passed through URL and DNS/IP policy validation before the next request is made. HTML quote verification now matches parsed visible text instead of raw HTML markup.

## Residual constraints

This is sufficient to begin **query-map preparation**, but not broad live collection.

| Item | Status | Required handling |
|---|---|---|
| DNS rebinding containment | Residual risk | Hostname is checked before `urllib` resolves and connects. The project must document this limitation and use a curated domain allowlist for the next non-client dataset; a stronger pinned-resolution transport remains future hardening. |
| Operator policy profiles | Missing | CLI currently uses defaults and cannot load an approved domain list, locale, source scope, retention rule, or per-run policy profile. Add this before collection beyond a one-source smoke check. |
| Failure labels | Needs refinement | A blocked `http` URL is currently reported as `ssrf_blocked`, even though it is a scheme-policy rejection. Separate transport/scheme, domain-policy, DNS, and IP-safety categories. |
| HTTP success semantics | Needs test | Require a documented successful status range, and add hermetic tests for non-200/non-2xx final responses. |
| JSON evidence | Deferred | Raw JSON matching is acceptable only after an approved field-extraction rule exists; do not treat arbitrary serialized JSON as visible source evidence. |

## Approved next work: Sprint 3 Query-Map Contract and Controlled Dataset

Do not add model adapters yet. Build the input contract for an audit first:

1. Define `QueryMap`, `Query`, `SourceScope`, and `CollectionPolicyProfile` contracts.
2. Require client/entity name, offer, target buyer, geography, locale, query intent, and approved source domains.
3. Store each proposed query with a reason it exists and a human approval state.
4. Require an explicit non-client dataset manifest naming a small set of permission-free or clearly public test URLs; use a curated `allowed_domains` list.
5. Add CLI support to load the policy profile and reject sources outside the manifest.
6. Collect a small source set, generate verification artifacts, and render a source ledger—not a client conclusion or LLM visibility score.

## Approval boundary

**Approved:** build the query-map and policy-profile contracts, and collect a small, curated, non-client source dataset under a strict allowlist.

**Not approved:** client URLs, customer data, broad community/review scraping, arbitrary URL collection, LLM recommendation/share claims, paid model APIs, or commercial reports.

The next review should validate the query-map contract, approved-source enforcement, manifest integrity, and the resulting source-ledger artifact.
