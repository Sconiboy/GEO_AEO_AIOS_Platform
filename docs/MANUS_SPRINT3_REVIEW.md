# Manus Sprint 3 Query-Map Review

**Reviewed commit:** `decf13693e506fc1a3e61c3fdc46e300cebf13a8`  
**Status:** **Not approved for answer-surface observation. Accept the design direction; remediate the policy-enforcement gaps below first.**  
**Date:** August 21, 2026

## What independently passed

Sprint 3 introduces the right high-level boundaries. `TargetQuery`, `QueryMap`, `SourceScope`, and `CollectionPolicyProfile` are typed, and approval state is centrally represented by `HumanApprovalState`. The runner filters to `APPROVED` queries and performs its manifest-domain check before calling the verifier.

| Verification | Independent result |
|---|---|
| Test suite | 27 passed |
| Static type check | `mypy src` passed with 0 issues |
| Public controlled fixture CLI | Completed and produced a verification-artifact-backed ledger |
| Unapproved query path | Skipped without a verifier call |
| Out-of-allowlist source | Recorded as inaccessible before a verifier call |
| Existing secure-fetch controls | Still applied through the constructed `SourcePolicy` |

The source ledger correctly excludes the out-of-allowlist candidate from supporting evidence. The real fixture run verified the `httpbin.org/html` excerpt, wrote a content-addressed snapshot hash, and did not create a claim from the proposed query.

## Why this is not yet approved

The work describes a policy profile, but several declared policy controls are not applied by `QueryMapRunner`. That is an important distinction. A client-facing audit cannot claim controlled collection when a manifest can silently exceed its configured cap or circumvent its non-client boundary.

| Priority | Finding | Evidence | Required remediation |
|---|---|---|---|
| P0 | `max_sources_per_query` is declared but never enforced. | The runner iterates every manifest candidate and has no counter or cap check. | Enforce a deterministic per-query cap before fetch; retain an auditable skip record or explicit run metadata for excluded candidates. |
| P0 | `blocked_domains` is declared but is not passed to, or checked by, the runner’s `SourcePolicy`. | Only `allowed_domains` is used when the policy is constructed. | Wire `blocked_domains` into collection policy and test that a domain appearing in both lists is blocked without a request. |
| P0 | `is_non_client_spike` is informational, not an execution gate. | A manifest marked `false` validates; the runner never rejects it. | Require `is_non_client_spike is True` until a separately approved client-audit mode exists. |
| P1 | Multiple blocked candidates for the same query overwrite one another. | All blocked entries use `ev-blocked-{query_id}` as the ledger key. | Add a stable per-candidate ID or URL hash so every input and policy decision is retained. |
| P1 | Tests do not cover the new CLI, declared cap, blocked-domain list, or false non-client flag. | Only three new runner tests exist; CLI coverage remains 31% overall. | Add hermetic tests for each P0/P1 control and a CLI success/failure test. |
| P1 | The rendered output still looks like a commercial audit. | It labels the test entity as a “Client Domain,” calls ledger entries “Claims,” and calculates a MEDIUM confidence score. | Add a true `source-ledger` render mode: no client-domain wording, no recommendation/share conclusion, and no score presented as an audit result. |
| P2 | Fixture provenance is internally inconsistent. | `httpbin.org` is marked `official_documentation` and `is_independent: true`; the report calls a live public source a “synthetic fixture.” | Correct the source type/independence labels and separate live controlled-source runs from synthetic test fixtures. |

## Narrow remediation sprint: Sprint 3.1

Sprint 3.1 must complete the enforcement work above. The acceptance test is not another attractive report; it is a hermetic policy proof:

1. A cap of one results in at most one verifier call for an approved query with two allowable manifest candidates.
2. A blocked domain takes precedence over an allowlist match and makes zero verifier calls.
3. A manifest with `is_non_client_spike: false` exits nonzero before any verifier is constructed or network call occurs.
4. Two blocked candidates for one query result in two distinct ledger records.
5. The `query-map` CLI has dedicated passing and failing tests and renders a source ledger rather than a client audit.
6. The existing tests, the new policy tests, and `mypy src` pass from a clean checkout.

## Approval boundary

**Still allowed:** offline contract work, hermetic testing, and the existing one-source controlled smoke fixture.

**Still blocked:** client URLs, customer data, broader live source collection, any LLM answer-surface observation, recommendation-share claims, paid model APIs, or commercial reports.

Answer-surface observation becomes eligible only after Sprint 3.1 passes. When it does, the next milestone should capture raw answers from one explicitly approved model and one controlled query set, with no scoring or recommendation until those raw observations are cross-checked against the source ledger.
