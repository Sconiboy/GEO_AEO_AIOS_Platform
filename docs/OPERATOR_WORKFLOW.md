# Evidence-Governed GEO/AEO Operator Workflow

This workflow turns the platform into a repeatable service operation. Every stage has a defined input, output, accountable human decision, and stop condition. It is intentionally slower than generic mention tracking because a commercial recommendation must remain traceable to the evidence that supports it.

## Operating Rule

> **No artifact, no claim. No approved query, no capture. No exact source authorization, no collection. No human decision, no semantic promotion.**

| Stage | Operator action | Required artifact | Human gate | Stop condition |
| --- | --- | --- | --- | --- |
| 0. Scope | Define category, geography, client domains, declared competitors, and commercial question. | SubjectProfile | Approve scope. | Client asks for an unsupported ranking or causal promise. |
| 1. Query design | Create the buyer-intent QueryMap and cap sources per query. | Frozen QueryMap | Approve each target query. | Queries are vague, unbounded, or prohibited. |
| 2. Capture policy | Declare model surface, operator, expected citation format, and capture metadata. | Capture protocol | Approve capture conditions. | Login, region, or provider blocks reproducible capture. |
| 3. Natural answer capture | Preserve the exact answer to the approved buyer question in a context-neutral session. | AnswerObservation + CaptureArtifact | Validate transcript integrity and session conditions. | Transcript is reconstructed, account-specific context appears, metadata is missing, or hashes differ. |
| 4. Source candidate review | Turn each visible answer URL into a candidate with publisher context, source type, and entity relationship. | CitationCandidateSet | Approve exact URLs for collection. | Citation is inferred, URL is ambiguous, or publisher context cannot be identified. |
| 5. Collection | Fetch only approved post-capture candidate URLs under source policy and retain snapshots. | AuditRun / source ledger | Review failures and redirects. | Source fails SSRF, content, quote, or snapshot verification. |
| 6. Classification | Compare exact observed citations to collected evidence and declared entity relationships. | ForensicGapAnalysisRecord | Review candidates and classification. | Subject or competitor ownership is undeclared. |
| 7. Semantic review | Compare exact passages and issue a human decision where warranted. | HumanDecisionRecord | Approve, reject, or mark not assessable. | The claim relies on keywords, generic similarity, or no evidence. |
| 8. Executive report | Convert approved observations and hypotheses into a decision brief and 90-day plan. | Report + artifact appendix | Approve delivery scope. | Report implies causal ranking, universal visibility, or guaranteed outcomes. |

## Practical Operating Cadence

The first engagement should use a deliberately small panel: three to five approved buyer queries and two accessible model surfaces. Each captured answer creates its own reviewed source-candidate set. The operator should then decide whether results justify expanding the query panel or whether access quality, evidence quality, or commercial relevance is too weak.

| Cadence | Activity | Output |
| --- | --- | --- |
| Intake week | Scope, entity profiles, query workshop, and authorization. | Approved scope packet. |
| Week 1–2 | Captures and approved evidence collection. | Frozen observation and source-ledger bundle. |
| Week 2 | Human reconciliation and hypothesis review. | Approved / rejected / not-assessable hypothesis register. |
| Week 3 | Executive report and 90-day evidence plan. | Client-ready report only if human-approved. |
| Monthly | Repeat a defined subset with the same controls. | Comparable trend record, not a universal rank. |

## Escalation and Stop Conditions

The operator stops and records the limitation when model access is blocked, sources cannot be retained, answer citations are absent, only first-party marketing evidence is available, or the sample is too small to support a client-facing statement. The correct output in these cases is an **evidence limitation**, not an invented insight.

The operator also stops when a requested action would require fake testimonials, undisclosed paid community seeding, spam, scraped personal data, or any other manipulative evidence creation. The platform is designed to improve legitimate proof, documentation, and earned references.
