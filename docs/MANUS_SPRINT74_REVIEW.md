# Manus Sprint 7.4 Collection Candidate & Manifest Authorization Review

**Reviewed commit:** `19c31c4d92ee146ffbcbfdb665d9cf8e1bbec6ec`  
**Status:** **Rejected for evidence-collection pilot authorization.**  
**What is accepted:** typed observed-citation candidates, exact ledger URL matching, candidate digest coverage, and orphan-action separation are materially correct.  
**Date:** August 21, 2026

## Controls independently verified

| Control | Result |
|---|---|
| Observed citation candidate | An unverified `https://rust-lang.org/learn` citation emits an immutable candidate with Rust Foundation linkage. |
| Default approval boundary | Against the current PEP-only manifest, the candidate correctly has `requires_human_manifest_approval=true`. |
| Evidence state | The candidate remains separate from `prioritized_actions`; no generic action or verified evidence claim is emitted. |
| URL verification | The code compares normalized full URLs/final URLs rather than treating a matching domain as verified. |
| Integrity | Candidate fields participate in the canonical digest and the direct check passed integrity verification. |
| Baseline | Independent run returned **62 tests passed** and **0 mypy issues**. |

## P0: one manifest candidate authorizes every URL on its domain, including another query

The manifest contract is explicitly candidate- and query-specific: each `ManifestSourceCandidate` has a `query_id` and `url`. However, Sprint 7.4 derives `manifest_candidate_domains` from every candidate URL and authorizes an observed citation when either its exact URL **or its domain** appears in that set. It does not check the candidate query ID.

Independent adversarial result:

| Input | Result |
|---|---|
| Observed URL | `https://rust-lang.org/learn` for `q-001` |
| Existing manifest candidate | `https://rust-lang.org/about` for `q-unrelated` |
| Candidate result | `requires_human_manifest_approval=false` |

That is a scope bypass. An approval of one URL for one question must not silently authorize a different URL for a different question.

## Required Sprint 7.4.1

1. Make authorization require an **exact normalized URL match and matching `query_id`** to a persisted manifest candidate.
2. If broad domain authorization is ever wanted, add an explicit `approved_domain_scopes` contract with its own query binding, rationale, expiry, and human approval state. Never derive it implicitly from an individual candidate URL.
3. Bind the matched manifest candidate ID and its raw manifest SHA-256 to a candidate when authorization is granted.
4. Add tests for same-domain/different-path, same-URL/different-query, redirect/final-URL behavior, and explicit domain-scope authorization.
5. Do not initiate a verifier fetch until exact candidate authorization is proven at execution time—not merely when a candidate report was generated.

## Pilot boundary

The observed-citation layer is now usable for **proposing** competitor evidence collection. It is not yet safe to execute that collection. After the exact URL/query authorization correction, the first collection-approval pilot may fetch one public, human-approved competitor URL under the existing secure verifier and link its snapshot back to the observation.
