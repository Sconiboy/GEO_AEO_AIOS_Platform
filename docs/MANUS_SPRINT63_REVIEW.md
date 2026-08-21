# Manus Sprint 6.3 Manifest and Safe-Reconciliation Review

**Reviewed commit:** `d095336d39df11cbbbcac9d03fbca6ec711ca5be`  
**Status:** **Approved for safe automated collection and `NOT_ASSESSABLE` reconciliation.** A human semantic-decision record remains required before any statement is presented as `SUPPORTED`.  
**Date:** August 21, 2026

## Independent verification

Sprint 6.3 fixes the two P0 problems from the prior review. The PEP 20 candidate now exists in a persisted non-client manifest, the emitted observation binds to that manifest’s exact raw SHA-256, and the query map explicitly includes `peps.python.org` in its allowlist. The persisted reconciliation re-renders successfully against those same artifacts.

| Check | Independent result |
|---|---|
| Manifest provenance | Passed: `live_pep20_manifest.json` exists, contains the PEP 20 candidate, and its raw SHA-256 matches the observation. |
| Source scope | Passed: `peps.python.org` is explicitly listed in the query-map source scope. |
| Ledger binding | Passed: emitted ledger SHA-256 matches observation and persisted reconciliation. |
| False-positive defense | Passed: automatic reconciliation no longer awards `SUPPORTED` from keyword overlap. |
| Automatic outcome | Passed: both PEP 20 statements render `NOT_ASSESSABLE` pending explicit human review. |
| Regression baseline | 49 tests passed and `mypy src` reported 0 issues. |

The platform now makes the correct automated decision:

> A verified source can be relevant without automatically proving that an extracted model statement is supported.

## Approved boundary

The PEP 20 run is a valid controlled non-client **collection and evidence-gap demonstration**. It is not yet a supported-result demonstration. That restraint is a strength: an evidence product that guesses semantic support is not trustworthy.

## Next milestone: immutable human semantic decision

Add a separate, content-addressed decision record that can transition one `proposed_unverified` / `not_assessable` statement to `supported`, `unsupported`, `contradicted`, or `not_assessable` only through an explicit human-review operation.

| Required control | Requirement |
|---|---|
| Input binding | Bind exact observation ID/hash, source-ledger run ID/hash, manifest hash, query-map hash, statement ID, and evaluated evidence IDs. |
| Human provenance | Require reviewer identity or role, timestamp, method, precise rationale, and quoted supporting/refuting passages. |
| Immutability | Create a new decision artifact; never mutate raw observation, source ledger, or earlier reconciliation artifacts. |
| Status transition | Automated code must not emit `SUPPORTED`. Only the explicit human-review operation may do so. |
| Tamper controls | Verify the decision digest at load and render; reject mismatched observation/ledger/manifest/query-map bindings. |
| Auditability | Render raw statement, evidence excerpts, decision, rationale, uncertainty, and decision artifact digest separately. |

## Two non-blocking discipline rules

1. The current local snapshot is content-addressed but ignored by Git. Before using the run as a portable portfolio artifact, retain the snapshot in a durable artifact store and record its stable storage key in the ledger.
2. Do not rewrite hashes inside historical observations when query maps change. Version a new query map and create a new observation instead; history must remain immutable.

No new model, client, score, ranking, or sales output until the explicit human decision record is complete.
