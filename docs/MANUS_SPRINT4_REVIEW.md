# Manus Sprint 4 Manual Observation Review

**Reviewed commit:** `142f5834839cf9b3f46f4eb27a2027202ac43f8e`  
**Status:** **Not approved for a controlled manual observation. Implement Sprint 4.1 evidence-integrity remediation first.**  
**Date:** August 21, 2026

## What independently passed

Sprint 4 moves the platform in the correct direction. It adds a distinct observation record, raw-answer SHA-256 calculation, approved-query lookup, source-ledger ID matching, a non-commercial renderer, and no provider API client. The record renderer clearly labels the output as a manual answer-surface observation and does not present a recommendation, rank, share, or commercial audit conclusion.

| Check | Independent result |
|---|---|
| Test suite | 37 passed |
| Static type check | `mypy src` passed with 0 issues |
| Hash-at-construction check | A mismatched answer/hash fixture is rejected |
| Query approval | Proposed query imports are rejected |
| Renderer | Outputs raw answer, model label, capture metadata, digest, and explicitly proposed statements without commercial score language |
| Paid/API scope | No model API client, unattended model call, scheduler, or client-data path was introduced |

## Why this remains blocked

The current contract is not yet an immutable observation record. Its hash protects the constructor input, but not the record after construction; provenance is silently invented when unknown; and the ledger “link” is a deterministic ID regenerated from a new live collection rather than a reference to a frozen ledger artifact.

| Priority | Finding | Evidence | Required remediation |
|---|---|---|
| P0 | Raw evidence is mutable after hash validation. | Independent check changed `raw_answer_text` without error while the stored digest retained the old value. | Make the record immutable (`frozen`) and verify integrity again at every import/render boundary. Do not permit any output from a hash-mismatched instance. |
| P0 | Unknown provenance is replaced with defaults. | Omitted locale/region become `en-US` / `US`; capture time defaults to import-time `now`. | Require a supplied capture timestamp. Make locale and region nullable with explicit `unknown`/`None` rendering. Never infer capture context. |
| P0 | “Proposed-only” extraction can be bypassed. | Importer permits `SOURCE_VERIFIED` or `HUMAN_APPROVED` whenever a linked evidence ID exists; it does not require that evidence to be `OPENED_VERIFIED`. | At import, require every extracted statement to be `PROPOSED_UNVERIFIED`; optionally permit a link only to an opened-and-verified ledger record. Create a later, separately reviewed verification transition if needed. |
| P0 | Source-ledger linkage is not immutable. | CLI re-runs source collection from the manifest and checks only a predictable `run-qm-{query_map_id}` ID. The observation is therefore not anchored to the ledger state available at capture time. | Persist/load a frozen ledger artifact and bind the observation to its canonical SHA-256 digest, query-map digest, and manifest digest. Observation import must consume that artifact, not recollect sources. |
| P1 | Sprint 4 CLI smoke test is network-dependent. | `test_cli_observation_command` invokes the real controlled manifest rather than a mocked or frozen ledger input. | Make tests hermetic; mock collection or load a deterministic serialized source-ledger fixture. |
| P1 | The sample fixture misrepresents its capture method. | It is a repository-created fixture but declares `human_operator_console`. | Use `synthetic_fixture_import` and state that it is not a captured model response. A real manual observation must be created only after Sprint 4.1 approval. |

## Sprint 4.1 acceptance criteria

1. Direct assignment and model-copy mutation of raw answer or digest must fail, or must be detected and rejected before import or render.
2. Missing locale, region, or capture timestamp must remain visibly unknown or fail validation—never silently become current/default context.
3. Imported statement statuses must all be `PROPOSED_UNVERIFIED`; a linked evidence ID, if supported, must reference an `OPENED_VERIFIED` record.
4. A source-ledger artifact must be immutable and content-addressed. The observation must bind to the artifact hash plus immutable query-map and manifest hashes.
5. The observation CLI must load the frozen ledger artifact and make no collection/network request.
6. Every test must be hermetic, including CLI observation tests; run `pytest` and `mypy` from a clean checkout.
7. The synthetic fixture must accurately declare synthetic capture provenance.

## Approval boundary

No live manual observation is approved yet. Once Sprint 4.1 passes, the first permitted observation remains exactly one response for the existing public Python test entity and one approved query. It must be stored as an internal evidence artifact only—without a recommendation, visibility measurement, comparative claim, client conclusion, paid model API, or customer data.
