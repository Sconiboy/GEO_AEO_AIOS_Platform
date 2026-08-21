# Manus Sprint 8 Bounded Comparative Evidence Pre-Pilot Review

**Reviewed commit:** `2760ab9`  
**Status:** **Citation-bearing capture accepted; comparative forensic artifact rejected.**  
**Date:** August 21, 2026

## What the commit genuinely proves

| Control | Independent result |
|---|---|
| Artifact-backed observation | The Rust citation appears in the preserved transcript output and the transcript bindings follow the approved operator-declared capture contract. |
| Observed citation | The model-answer artifact explicitly contains `https://doc.rust-lang.org/book/`. |
| Public competitor collection | Rust Book collection is within the approved competitor URL/query path. |
| Client source | PEP 20 is a valid client-owned public source. |
| Renderer wording | The report labels the output as an action hypothesis and does not itself introduce rank language. |
| Baseline | Submitted tests and type checks pass, but test scope is narrow. |

## Why the comparative artifact is not accepted

### 1. The comparator is hard-coded to Rust

`ComparativeEvidenceReconciler` classifies the competitor with a fixed `doc.rust-lang.org` domain rather than deriving it from `competitor_evidence.url` and the declared subject profile. It can misclassify arbitrary evidence as Rust competitor evidence.

### 2. The action hypothesis is fixed copy, not evidence analysis

The engine emits the same “Publish or update canonical documentation” instruction regardless of source excerpts, evidence types, ownership, whether client evidence is already complete, or whether the collected competitor source supports a comparable claim. This is a template, not a forensic hypothesis.

### 3. No source-to-claim comparison occurs

The record never maps the raw-answer Rust claim to a verified Rust excerpt, and never maps the Python claim to a verified PEP 20 excerpt. It only compares two source summaries. Evidence presence is not semantic evidence comparison.

### 4. Comparative integrity is thin

The canonical digest omits profile hash, observation raw-answer hash, source ledger hash, evidence IDs, verifier runs, snapshot hashes, source excerpts, comparison summary, and several other decision-driving fields. The record has no `verify_integrity()` method.

### 5. Execution scope bypasses the approved client collection route

The runner directly invokes `SourceVerifier` for the PEP 20 client page instead of using the same manifest/candidate authorization and immutable execution-provenance path. It also loads `sample_query_map.json` rather than the persisted pre-pilot query map. That breaks the claimed one controlled workflow.

## Required Sprint 8.1

1. Derive client and competitor relationship/entity from each actual evidence URL through `SubjectProfile`; reject unknown/mismatched evidence.
2. Bind every comparative record to observation raw-answer hash, profile/query-map/manifest/ledger hashes, exact evidence IDs, URLs, verifier runs, snapshot hashes, and collection execution IDs.
3. Require an explicit answer-claim → source-excerpt semantic assessment for both sides. If either relation is not assessable, say so; do not infer an evidence gap.
4. Generate action hypotheses from detected evidence differences only. Include a structured `finding_basis`, uncertainty, and `human_review_required=true`.
5. Use the same exact manifest/query candidate authorization and execution provenance path for client and competitor source retrieval.
6. Hash the complete canonical decision payload and implement `verify_integrity()` plus adversarial tampering, swapped-evidence, ownership-mismatch, and no-gap tests.

## Boundary

Sprint 8 is a successful **capture-plus-source-retrieval demonstration**, not the first forensic comparative report. Do not use its generic hypothesis for a client, portfolio claim, or product demo.
