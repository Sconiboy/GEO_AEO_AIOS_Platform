# Manus Sprint 3.1 Policy-Completeness Review

**Reviewed commit:** `1123d50bf6c3104e760bf03b9b47e5b610c14f6b`  
**Status:** **Approved for a narrow, manual-capture answer-surface observation contract.**  
**Date:** August 21, 2026

## Independent verification

Sprint 3.1 resolves the policy-enforcement gaps that blocked the previous review. The runner now treats its declared policy fields as execution controls rather than descriptive metadata, and the query-map CLI produces a controlled source ledger instead of a commercial-style audit report.

| Acceptance condition | Independent result |
|---|---|
| Full test suite | 33 passed |
| Static type check | `mypy src` passed with 0 issues |
| Per-query source cap | Hermetic test confirms a cap of one causes one verifier/open call and records the next candidate as excluded. |
| Blocked-domain precedence | Hermetic test confirms a domain in both lists makes zero opener calls. |
| Non-client-only gate | `is_non_client_spike: false` raises before verifier construction. |
| Ledger completeness | Multiple blocked inputs now use query-and-URL-hash IDs and remain distinct. |
| CLI rendering | Controlled fixture run renders “Subject Entity,” verified sources, policy-filtered exclusions, snapshot hash, and verifier method—without client-domain, claim, or confidence-score language. |

The submitted source-ledger output contained an opened-and-verified record with a content-addressed snapshot and an excluded non-allowlisted URL. That is the right artifact at this stage: a factual record of source collection and policy decisions, not a visibility claim.

## Deferred, non-blocking cleanup

The controlled fixture calls `httpbin.org/html` `official_documentation` and marks it independent. Those labels are not credible provenance for that page. Correct the fixture to use a source type and independence label that reflect the actual publisher before using it as a demonstration artifact. This does not block the answer-observation contract because the fixture remains explicitly non-client and the source ledger displays its classification rather than deriving a commercial conclusion from it.

## Approved next work: Sprint 4 Manual Answer-Surface Observation Contract

Do **not** integrate an LLM API or automate model querying in Sprint 4. The objective is to create a verifiable import and review path for a human-authorized, manually captured response from exactly one named model and one approved query.

| Required contract element | Requirement |
|---|---|
| Query binding | Every observation must reference an `APPROVED` `TargetQuery` and its query-map/run identifiers. |
| Model provenance | Record provider, exact model label supplied by the operator, capture timestamp, locale/region when known, and capture method. Unknown fields must remain explicitly unknown—not inferred. |
| Immutable raw evidence | Store the exact raw answer, a SHA-256 digest, and an optional operator-provided capture reference. Do not silently normalize or rewrite the answer. |
| Source-ledger binding | Link the observation to the controlled source-ledger run that contextualizes any later extracted claim. |
| Claim treatment | Any extracted statement begins as an unverified proposal. It must not become a recommendation, visibility score, or client conclusion without source-ledger-backed verification and human review. |
| Renderer | Render an “Observation Record,” clearly separating raw response, machine-assisted extraction (if any), verification status, gaps, and human decision. |
| Privacy and spend | No client data, no paid model API, no unattended query execution, no background scheduler, and no model-specific connector. |

## Sprint 4 acceptance test

The implementation should use a synthetic/manual fixture response only. Its tests must prove that a proposed or rejected query cannot be imported; that modifying raw response text invalidates its hash; that unknown model provenance remains unknown; and that no output presents a recommendation, ranking, answer-share, or commercial audit result.

After the contract passes review, Manus may conduct one deliberately scoped manual observation for the existing public test entity. That observation remains an internal portfolio artifact, not a client audit.
