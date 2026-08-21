# Manus Sprint 7.3 Answer-Level Competitor Citation Review

**Reviewed commit:** `5332d38fa220aa54ed02568ea3f350b91e9dd7be`  
**Status:** **Approved for direct observed-competitor classification; not approved for evidence-collection authorization or a comparative forensic pre-pilot.**  
**Date:** August 21, 2026

## Controls independently verified

| Control | Result |
|---|---|
| Direct answer citation classification | A raw `https://rust-lang.org` URL is now correctly classified `COMPETITOR_OWNED` from the declared profile even though it is absent from the PEP source ledger. |
| Attribution status | The same test correctly returns `CITED_COMPETITOR_OBSERVED`. |
| Entity linkage | The observed citation carries `Rust Foundation` from the declared competitor profile. |
| Domain boundary matching | Exact-domain/subdomain comparison prevents simple deceptive strings such as `notrust-lang.org` and `rust-lang.org.evil.com` from matching. |
| Baseline | Independent run returned **59 tests passed** and **0 mypy issues**. |

This is the capability Sprint 7.2 lacked: the platform can now recognize that an answer actually named or linked a declared competitor before a competitor evidence collection exists.

## P0: the collection proposal falsely says an unapproved URL is manifest-approved

The source profile and observed answer identify `rust-lang.org`, but the current manifest does **not** contain a Rust candidate or allow it as a collection source.

Independent check output:

| Check | Result |
|---|---|
| Attribution status | `cited_competitor_observed` |
| Rust URL present in persisted manifest | `false` |
| Emitted collection action | Says “Execute **authorized manifest-approved** evidence collection” |

An observed competitor URL must not be treated as approved for retrieval. The action must instead be a **collection-candidate proposal** requiring human approval and a newly persisted manifest/policy revision before the verifier may fetch anything.

## P0: the collection proposal is orphaned from a real analysis finding

The emitted action uses `gap-pat-q-001`, but no `ClientEvidenceGap` with that ID exists. The action is not bound to an explicit observed-citation finding; it appears as a generic `PrioritizedActionPlan` with no valid parent gap.

Collection-candidate proposals need their own typed finding/decision category, with the observed URL, classified relationship, competitor entity, observation ID, and exact raw-answer anchor. They are not documentation actions and are not evidence gaps.

## P1: matching ledger domain is not sufficient to call the cited URL verified

The implementation checks whether `ac.domain` appears in `domain_counts`. That can mark `https://rust-lang.org/learn` as verified because some different Rust URL exists in the ledger.

Verification must compare a canonical URL (or an explicit verified evidence record connected to the cited URL after redirects), not merely a hostname.

## Required Sprint 7.4

1. Replace the collection action with an immutable **ObservedCitationCollectionCandidate** record. It must state `requires_human_manifest_approval=true` unless a persisted manifest candidate and source policy explicitly authorize the exact URL/domain.
2. Require an approved, versioned manifest/policy revision before any observed competitor URL reaches `SourceVerifier`.
3. Bind collection candidates to an explicit observed-citation finding—not a fabricated or missing `ClientEvidenceGap`.
4. Preserve exact canonical cited URL, competitor entity, profile hash, observation ID, raw-answer hash, and explicit answer-citation relationship in the candidate digest.
5. Treat an observed citation as verified only when a matching verified evidence record/canonical URL is present, not merely when its domain appears in the ledger.
6. Add tests for unapproved observed URLs, approved exact URLs, same-domain different-path URLs, redirects, and orphan action prevention.

## Pilot boundary

After Sprint 7.4, we can conduct an honest **collection-approval pilot**: an answer observes a competitor citation, a reviewer approves a specific manifest candidate, the existing secure verifier collects that URL, and the resulting evidence record is linked back to the observation. Comparative recommendations remain deferred until both competitor and client evidence are verified.
