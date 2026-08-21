# Manus Sprint 2 Controlled Live-Collection Review

**Reviewed commit:** `d9ed20b`  
**Status:** **Approved as a non-client verification spike; conditionally approved for source-policy hardening, not yet for a client query map**  
**Date:** August 21, 2026

## Independent verification

The source-verification spike works as described on its approved non-client test URL. Independent review ran the full suite and static checks:

| Check | Result |
|---|---|
| Test suite | 17 passed |
| Coverage | 83% reported by `pytest-cov` |
| Static type check | `mypy src` passed with 0 issues |
| Exact quote verification | Returned `opened_verified`, stored a content-addressed snapshot, and returned a hash matching the actual persisted bytes |
| Quote mismatch | Returned `quote_mismatch` and exit code 1 while retaining the attempted snapshot and artifact |
| Inaccessible URL test | Returned `inaccessible` and blocked later evidence export |

The spike demonstrates an important property: a verification artifact can now be derived from actual fetched bytes and checked against a persisted content hash, rather than supplied only in fixture JSON.

## Why this is not yet client-ready

The collector is intentionally small, but it currently accepts arbitrary HTTP/HTTPS URLs and follows the platform default networking behavior. Before any client or user-provided URL reaches this code, implement source-policy and SSRF controls.

| Required hardening | Reason |
|---|---|
| Reject localhost, loopback, link-local, private, and reserved IP targets after DNS resolution and after redirects | Prevent server-side request forgery into internal services or cloud metadata endpoints. |
| Permit only `https` for live client collection; document narrow exceptions if needed | Avoid insecure transport. |
| Enforce maximum response size, accepted content types, redirect limit, final-URL recording, and explicit timeout policy | Prevent memory exhaustion, binary capture, redirect confusion, and unbounded collection. |
| Add domain-level allow/deny rules, rate limits, robots/terms policy, and request logging | Make collection legally and operationally governable. |
| Separate raw-byte snapshot from extracted evidence text | A match inside a hidden script, navigation, or unrelated page markup is not automatically meaningful evidence. Persist extraction method, content type, and exact text location. |
| Move generated snapshots and coverage databases out of Git tracking | Real source snapshots may create copyright, privacy, retention, and repository-growth problems. Use local/content-addressed artifact storage with retention policy; commit only safe fixtures. |
| Make unit tests hermetic | `httpbin.org` is a good integration smoke target, not a unit-test dependency. Mock HTTP responses or use a local test server for unit tests; isolate optional network integration tests. |

## Approval boundary

**Approved:** continue collector hardening and create a source-policy contract. Continue using `httpbin.org` or similarly permission-free public test endpoints for integration smoke checks only.

**Not approved:** select a client, accept arbitrary client URLs, crawl communities or review platforms, run broad collection, map AI answer surfaces, or activate paid model APIs yet.

## Next work package

Implement **Sprint 2.1: Safe Source Policy and Verifier Hardening** before a client query map:

1. Create a `SourcePolicy` contract with allowed schemes, redirect count, byte limit, content-type policy, domain allow/deny controls, and audit log fields.
2. Implement DNS/IP safety checks before request and on redirect targets.
3. Store final URL, HTTP status, response content type, content length, retrieval timing, and extraction method in the verification artifact.
4. Add hermetic tests for private/loopback destinations, unsafe redirects, oversized responses, unsupported content types, non-HTTPS URLs, and quote presence only in excluded markup.
5. Make generated snapshot storage an ignored runtime artifact with documented retention and deletion behavior.

After Sprint 2.1 passes, the platform can define a first **non-client, controlled query-map dataset**. A real client audit still requires a separate client-consent, source-policy, and answer-surface-observation decision.
