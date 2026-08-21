# Manus Sprint 1 Remediation Review

**Reviewed commit:** `0253fe4`  
**Status:** **Approved for controlled live-collection development; not yet approved for a live client audit**  
**Date:** August 21, 2026

## Verdict

The remediation is real. The original provenance failure is no longer being hidden behind a polished fixture report. The repository now has reproducible dependency declarations, documented setup, CI, strict support and counter-evidence validation, verification-artifact requirements, an explicit synthetic-fixture banner, and an adversarial failure fixture.

Independent review reproduced the declared validation path:

| Check | Independent result |
|---|---|
| Dependency installation from `requirements.txt` | Passed |
| Unit suite | 13 passed |
| Coverage | 88% reported by `pytest-cov` |
| Static type check | `mypy src` passed with 0 issues |
| Valid synthetic fixture export | Passed and displayed a prominent synthetic-data warning |
| Adversarial mixed-evidence fixture | Rejected with exit code 1 because an `OPENED_VERIFIED` source lacked a `VerificationArtifact` |

The current report also exposes the provisional formula version and factor breakdown. That makes the 0.90 score inspectable rather than pretending it is an objective model truth.

## What is now safe to say

The project has a **working local evidence-led prototype**. It can load structured fixture data, reject important classes of unsupported claims, calculate a transparent provisional confidence score, and render an internally auditable Markdown report.

The project must still not say it has performed an LLM visibility audit, has source-verification automation, or can issue client-ready recommendations from live data. The synthetic fixture remains intentionally synthetic; its `.example.com` sources and declared test snapshots are correct for a contract test, not evidence of real market research.

## Remaining constraints

1. A `VerificationArtifact` schema is now required, but there is no actual source collector, snapshot store, or quote-matching verifier yet. The next implementation must create those artifacts from real source bytes—not merely accept them as input JSON.
2. The confidence formula is explicitly provisional. It does not yet score recency, root-domain concentration, source-quality calibration, or evidence dependence beyond a supplied duplicate flag. Keep it provisional until evaluation data exists.
3. The sample fixture still uses a real company name in synthetic copy. The report banner is clear, but future fixtures should prefer a fully fictional entity to avoid accidental reuse as marketing evidence.
4. The README setup is materially improved, although older local `file:///Users/...` links should be converted to repository-relative links in a cleanup pass.

## Approved next work: controlled live-collection spike

Do not add multi-model routing, paid APIs, broad scraping, subscriptions, or a client dashboard next. Build one bounded source-verification path:

1. Accept one manually selected public URL and a candidate excerpt.
2. Fetch or open the source under an approved method and source-policy rule.
3. Save an immutable source snapshot or content-addressed artifact.
4. Compute the SHA-256 from the stored bytes.
5. Verify exact excerpt alignment against those stored bytes.
6. Create the `VerificationArtifact` from the actual verification run.
7. Reject report export if the artifact cannot be reproduced from the stored snapshot.
8. Repeat with one source that should fail: inaccessible, changed, stale, quote-mismatched, or duplicate.

The first target should be a **non-client, public test entity** with permission-free public sources. This is an engineering and evidence-verification spike, not a commercial audit. After it passes, the team can define the first controlled live audit query map and answer-surface observation workflow.

## Approval outcome

**Approved:** begin the controlled live-collection spike above.

**Not approved:** live client audit, paid model API activation, broad source scraping, claims of LLM recommendation share, or client-facing billing/subscription work.

Once the spike is implemented, record its source-policy constraints, fixture or test results, and artifact-retention behavior in this repository for the next review.
