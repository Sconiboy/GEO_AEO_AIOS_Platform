# GA4 and Search Console Integration Boundary

## Measurement Position

The Evidence Pattern Map should display three distinct, non-interchangeable signals:

| Signal | Source | User-visible label | What it establishes | What it does not establish |
| --- | --- | --- | --- | --- |
| Observed AI referral | GA4 session source/medium or referrer, restricted to known answer-engine referrer domains | **Observed AI referral traffic** | A tracked visit arrived with an identifiable referring source. | Total LLM-influenced traffic or why the engine recommended the page. |
| Unattributed movement | GA4 direct/(none) by affected landing page, annotated with a documented site release | **Unattributed traffic movement after release** | A direct/unknown traffic metric changed after a release. | That an LLM, the release, or any single channel caused the change. |
| Google demand and discoverability | Search Console query/page performance and indexability observations | **Google search demand and page visibility** | Google Search clicks, impressions, CTR, position, and query/page associations. | LLM traffic or answer-engine citation share. |

GA4 documents `(direct) / (none)` as traffic without a clear referral source. Missing tags, redirects, copied/shortened links, offline documents, and ad blockers can contribute to this category.[1] The interface must not call it “LLM traffic.”

## Read-Only Data Contract

### GA4

Use the Google Analytics Data API with read-only access to a selected GA4 property. The Data API supports custom reports and programmatic dashboards, including standard reporting and realtime data.[2]

Required reporting fields for the first release:

- date;
- session source / medium;
- landing page (or page path plus query string);
- sessions, engaged sessions, users, event counts, conversions/key events, and engagement rate where available;
- optional page referrer for diagnostic exploration where consent and retention settings permit.

Known-answer-engine referrer lists must be versioned and editable by a workspace administrator. The system should retain the raw source value alongside the normalized category so future classification does not rewrite history.

### Search Console

Use the Search Console Search Analytics API with the read-only OAuth scope `https://www.googleapis.com/auth/webmasters.readonly`. The query endpoint returns grouped rows for dimensions including date, page, query, country, and device, with clicks, impressions, CTR, and average position.[3] Search Console documents that API result sets are subject to internal limits and do not guarantee every data row, so the interface must label results as returned Search Console data rather than a complete keyword universe.[3]

## Release Annotation Object

Every approved site change needs a release annotation so live data can be interpreted against a documented intervention rather than an anonymous date range.

```yaml
release_id: REL-2026-001
workspace_id: <workspace>
published_at_utc: <timestamp>
change_type: content | technical | structured_data | disclosure | removal
affected_urls:
  - https://example.com/path
work_order_id: <approved work-order>
evidence_ids:
  - <source evidence ID>
expected_signal: "Improved crawl clarity" | "Answer an unsatisfied buyer question" | "Correct unsupported claim"
comparison_window_days: 28
approval_record: <review decision ID>
rollback_reference: <CMS revision or deployment version>
```

The interface should compare pre/post windows for the affected URL set, annotate overlapping releases, show observed AI referrals separately, and display uncertainty when the window contains too little data or multiple confounding changes.

## Permission and Safety Boundary

1. Connect with user-consented OAuth, read-only scopes wherever possible.
2. Let the client choose a GA4 property and Search Console property after authorization; do not infer ownership from a domain alone.
3. Never expose raw access tokens in the client or a report.
4. Do not grant site-editing permissions through this integration. Publishing remains governed by the separate work-order approval workflow.
5. Do not show personally identifiable user-level analytics in the customer-facing application.

## Customer-Facing Insight Pattern

The live screen should state the evidence first:

> **Observed:** 18 identifiable answer-engine referral sessions reached `/regulatory-status` in the selected period. Direct/unknown sessions rose 21% after Release REL-2026-001, while Google Search impressions for the same page rose 14%.
>
> **Interpretation:** The page has a multi-signal traffic change after the documented release. The data does not establish that any one answer engine or release caused the movement.

No example values should appear as live data until a connected account returns them.

## References

[1]: https://support.google.com/analytics/answer/15258820?hl=en "Google Analytics Help: Understand (direct) / (none) traffic"
[2]: https://developers.google.com/analytics/devguides/reporting/data/v1 "Google Analytics Data API overview"
[3]: https://developers.google.com/webmaster-tools/v1/searchanalytics/query "Search Console API: Search Analytics query"
[4]: https://developers.google.com/webmaster-tools/v1/how-tos/authorizing "Search Console API: Authorize Requests"
