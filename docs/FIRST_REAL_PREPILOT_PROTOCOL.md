# First Real Comparative Pre-Pilot Protocol

## Purpose and Scope

This protocol produces **one public, non-client comparative evidence package**. Its purpose is to demonstrate the platform's evidentiary workflow, not to rank agencies, diagnose why an AI model behaved as it did, or sell a conclusion disguised as measurement.

The proposed portfolio subject is **Searchbloom**, a public search-marketing agency. The subject is not a client and no non-public material, account data, customer data, or paid-model API is required. The initial buyer question is deliberately bounded:

> “Which SEO agencies specialize in B2B SaaS organic growth, and what public sources support the options?”

The exact wording, selected model surface, capture time, operator, session context, and raw answer transcript must be frozen before collection. The model is not asked to disclose hidden reasoning. Only its visible answer and explicit citations are in scope.

## Evidence Gates

| Stage | Required input | Fail-closed condition |
| --- | --- | --- |
| Query approval | One typed `TargetQuery` explicitly approved for this public portfolio run | No answer capture or source collection on an unapproved query. |
| Answer capture | Artifact-backed raw transcript with timestamp, operator, session binding, and transcript digest | No analysis if the capture is altered, incomplete, or lacks a declared citation. |
| Competitor selection | One competitor URL explicitly cited in that exact captured answer | Never infer a competitor from a search result, memory, or a general industry list. |
| Competitor collection | Exact cited URL approved in the manifest for the captured query, then verified with snapshot and verifier provenance | No collection against a URL merely because it is a plausible competitor page. |
| Subject collection | One relevant, public Searchbloom-owned source approved in the same run | Treat it as first-party evidence, never as independent validation. |
| Optional independent evidence | One exact review-platform or editorial URL separately approved and collected | Do not manufacture, paraphrase, or extrapolate reviews. |
| Comparative promotion | Protected trusted issuer, durable execution registry, retained snapshots, and human quote decision where semantic support is asserted | Leave status as `NOT_ASSESSABLE` if any condition is absent. |

## Minimal Evidence Package

The target output contains exactly the following records:

1. An approved query map and exact manifest.
2. One immutable answer-surface observation whose visible answer explicitly cites a competitor source.
3. One successful competitor collection execution for that cited URL.
4. One successful Searchbloom collection execution for a relevant public owned URL.
5. Optionally, one independently verified public source, clearly labeled as independent.
6. One human-reviewed **evidence-gap hypothesis**, not a causal conclusion.

The hypothesis must use this form:

> “In the captured answer for the approved query, the model cited **[competitor URL]**. In the limited verified evidence set, that source contained **[exact verified passage]**. The selected Searchbloom source contained / did not contain **[exact verified comparable passage]**. This supports a hypothesis for further testing; it does not establish why the model selected the competitor.”

## Explicit Non-Claims

The report must not state that Searchbloom or any competitor is objectively the best agency, that a review count caused inclusion, that a page caused an AI answer, or that a single model answer represents user demand. It may only state what was captured, verified, compared, and reviewed inside the declared scope.

## Operational Readiness Before Capture

Before executing this protocol, configure the protected issuer environment documented in [`EXECUTION_ATTESTATION.md`](EXECUTION_ATTESTATION.md). The key and registry directory must be durable and protected. The controlled fixture's temporary issuer is not a production configuration and cannot be reused for a real portfolio artifact.

## Acceptance Criteria

The pre-pilot is successful if it produces a complete artifact whose every evidence and promotion assertion can be replayed from its query map, raw capture, raw ledger, retained snapshots, execution registry, and human decision record. It is also a successful result if the platform fails closed and reports `NOT_ASSESSABLE`; that outcome is more credible than forcing a weak recommendation.

## Source-Planning References

The public source-planning notes are maintained separately in [`searchbloom_prepilot_source_notes.md`](../../research/searchbloom_prepilot_source_notes.md). They are discovery references only and do not authorize collection or prove any comparative claim.
