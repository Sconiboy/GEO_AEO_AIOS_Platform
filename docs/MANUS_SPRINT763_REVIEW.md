# Manus Sprint 7.6.3 Transcript-Bound Capture Review

**Reviewed commit:** `8fa10fc`  
**Status:** **Transcript content binding approved; capture-metadata binding incomplete.**  
**Date:** August 21, 2026

## What now works

| Control | Independent result |
|---|---|
| Transcript structure | Parser requires header, output-stream marker, and footer. |
| Output binding | Parsed transcript output hash must match the observation raw-answer hash. |
| File binding | Artifact bytes must match the declared artifact SHA-256. |
| Missing artifact | Fails closed. |
| Query/provider/model | Parsed transcript values must match the observation. |
| Unrelated artifact | The prior unrelated-but-correctly-hashed artifact attack is now rejected. |
| Baseline | Independent run returned **81 tests passed** and **0 mypy issues**. |

The raw answer is now genuinely bound to the preserved transcript output. That fixes the central Sprint 7.6.2 failure.

## P0: capture timestamp and declared operator identity are still mutable metadata

The parser reads transcript timestamp and operator identity, but `AnswerObservation.verify_integrity()` never compares them to:

- `capture_timestamp`;
- `capture_artifact.captured_at`; or
- `capture_artifact.operator_identity`.

Independent adversarial result:

```text
integrity_with_timestamp_and_operator_mismatch=true
```

I changed the observation capture time and capture-artifact time to `2099-01-01T00:00:00Z` and changed the declared operator identity, while leaving the preserved transcript unchanged. Integrity still passed.

That means the system can truthfully say that a transcript contains the answer text, but it cannot yet truthfully claim that the answer was captured at the stated time by the stated operator.

## Required Sprint 7.6.4

1. Require parsed transcript timestamp to equal both `capture_timestamp` and `capture_artifact.captured_at` after timezone normalization.
2. Require parsed transcript operator identity to equal `capture_artifact.operator_identity`.
3. Include parsed session ID in the capture artifact and bind it to the transcript.
4. Add timestamp/operator/session mismatch tests and ensure all fail closed.
5. Keep user-facing wording precise: this remains an **artifact-backed, operator-declared** capture unless the operator identity itself is authenticated/signed by an independent system.

## Boundary

Sprint 7.6.3 proves transcript-to-answer binding, not full capture-event provenance. Do not yet call this a complete authentic model observation or use it to launch the forensic comparison pilot.
