# Manus Sprint 7.6 Controlled Competitor Collection Pre-Pilot Review

**Reviewed commit:** `fd2d645`  
**Status:** **Live public source collection accepted; forensic pre-pilot attribution rejected.**  
**Date:** August 21, 2026

## What the commit genuinely proved

| Control | Independent result |
|---|---|
| Exact authorization | The committed manifest approves `https://doc.rust-lang.org/book/` for approved query `q-001`; the query-map policy explicitly permits `doc.rust-lang.org`. |
| Declared competitor relationship | The pre-pilot profile explicitly identifies Rust Foundation and `doc.rust-lang.org` as a competitor domain. |
| Public retrieval | The emitted ledger records `OPENED_VERIFIED`, HTTP 200, visible-text verification, and a verifier run for the Rust Book. |
| Retained snapshot | The committed snapshot SHA-256 matches the evidence record and the snapshot contains “The Rust Programming Language.” |
| Candidate-to-evidence link | The execution record binds the approved Rust candidate, pre-fetch context, evidence ID, verifier run ID, and snapshot hash. |
| Regression baseline | Independent run returned **71 tests passed** and **0 mypy issues**. |

The secure collection pipeline has therefore retrieved a real public competitor-owned source under the approved exact URL/query boundary.

## What the commit does **not** prove

The input that supposedly triggered collection is not an actual preserved Hermes response. `prepilot_observation.json` was constructed by a local script with hand-authored raw text, then labeled:

```json
"provider_name": "Ollama / Local Operator Console",
"model_identifier": "hermes-3-llama-3.1-8b",
"capture_method": "human_operator_console"
```

There is no recorded operator transcript, console export, model run artifact, or cryptographically bound capture proving Hermes actually produced the Rust URL. The source collection is live; the observed answer citation is **scripted fixture content**.

This must not be described as a live LLM-visibility finding, an observed competitor mention, or a forensic pre-pilot result. It is a controlled integration test with a real public retrieval leg.

## Required correction before the first genuine forensic pre-pilot

1. Create a real manual answer capture through the approved operator path. Preserve the exact raw transcript, capture time, provider/model label, locale/region, and capture-method provenance.
2. Label any fixture or hand-authored answer `synthetic_fixture_import`; never label it `human_operator_console` or attribute it to a model.
3. Bind the observation’s raw-answer hash to an immutable capture artifact/reference before analysis begins.
4. Use the actual cited competitor URL from that real captured answer as the collection candidate.
5. Preserve the same collection boundary: one approved public competitor URL, one query, no comparative conclusion yet.

## Product implication

The pipeline is ready for a true controlled observation-to-source-collection run. It is not ready to claim that a model cited Rust until we capture that answer honestly. Distinguishing a real collection event from a fabricated trigger is exactly the kind of discipline required for the forensic product.
