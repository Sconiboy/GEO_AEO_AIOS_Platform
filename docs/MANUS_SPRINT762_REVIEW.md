# Manus Sprint 7.6.2 Artifact-Backed Capture Review

**Reviewed commit:** `26404b6`  
**Status:** **Artifact preservation approved; observation-to-artifact evidence binding rejected.**  
**Date:** August 21, 2026

## What is now useful

| Control | Result |
|---|---|
| Preserved transcript file | The committed Hermes transcript file exists and its SHA-256 matches the observation’s declared artifact hash. |
| Artifact metadata | Artifact ID, type, path, declared operator identity, and timestamp are stored with the observation. |
| Artifact tampering | Changing the captured file without updating its declared hash makes `verify_integrity()` fail. |
| Renderer disclosure | Artifact-backed, self-declared, and synthetic records have distinct presentation labels. |

This is a meaningful improvement over a standalone JSON claim. It preserves a static transcript and detects later file mutation.

## P0: the artifact is not bound to the observation’s raw answer

`verify_integrity()` separately checks:

1. `raw_answer_sha256` matches `raw_answer_text`; and
2. the artifact file matches `artifact_sha256`.

It never establishes that the artifact contains the raw answer or that the transcript’s query, provider, model, timestamp, and output agree with the observation fields.

Independent adversarial result:

| Input | Result |
|---|---|
| Observation raw answer | The claimed Hermes answer |
| Artifact file | A different unrelated response |
| Artifact hash | Correctly updated for the unrelated file |
| `is_artifact_backed` | `true` |
| `verify_integrity()` | `true` |
| Raw answer present in artifact | `false` |

Thus, a truthful-looking artifact-backed label can still attach an unrelated transcript to any observation. It proves file preservation, not observation provenance.

## P1: missing artifact paths fail open

When `artifact_path_or_uri` does not exist locally, `verify_integrity()` returns true after checking only the raw answer. A local artifact reference must either resolve and validate or be explicitly rendered as unavailable/unverified. It cannot continue to claim artifact-backed provenance.

## Required Sprint 7.6.3

1. Add a deterministic `raw_output_sha256` field to `CaptureArtifact`; it must equal `AnswerObservation.raw_answer_sha256`.
2. Define a parseable raw-transcript schema (or equivalent immutable transcript payload) with output boundary markers, query ID, provider/model, and capture timestamp.
3. During integrity verification, require the artifact path to resolve, verify the full artifact hash, extract the transcript output, and compare its raw-output digest to the observation’s raw-answer digest.
4. Require transcript query/provider/model/timestamp metadata to match the observation, or explicitly flag a mismatch.
5. Fail closed when an artifact-backed path is missing or unreadable.
6. Add adversarial tests for unrelated-but-hashed files, missing artifact paths, altered transcript metadata, and output-only mismatch.

## Boundary

The current Hermes JSON/transcript pair is a **preserved self-declared capture artifact**, not proof that Hermes produced the bound answer. Do not use it for forensic attribution, competitive collection, or portfolio claims until the transcript-to-answer binding passes.
