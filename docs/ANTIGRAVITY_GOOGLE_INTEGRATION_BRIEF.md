# Antigravity Engineering Brief: Commercial Google Data Connection

## Mission

Implement the secure, server-side **Google Analytics 4 and Google Search Console data connection** for the Evidence Pattern Map. The application is a source-first evidence-operations workspace, not a generic analytics dashboard. The integration must provide live, read-only data that can be tied to a workspace, a buyer-question evidence map, an approved work order, and a documented site release.

No CSV or manual-upload workflow belongs in the commercial customer experience.

## Product Contract

| Requirement | Required behavior |
| --- | --- |
| Client consent | The client connects Google through OAuth and explicitly selects a GA4 property and Search Console property. |
| Minimum permission | Request only `https://www.googleapis.com/auth/analytics.readonly` and `https://www.googleapis.com/auth/webmasters.readonly`. |
| Data access | All tokens and API calls remain server-side. The browser receives connection state, permitted property metadata, and aggregated report results only. |
| Workspace isolation | A workspace may query only its selected GA4 and Search Console properties. Every record carries `workspace_id`. |
| Evidence boundary | Observed AI referral, direct/(none) movement, and Search Console performance are separate measurements. No component may label direct/(none) traffic as “LLM traffic.” |
| Publication boundary | Google data may prioritize a work order; it cannot automatically publish content or change a connected website. |

## Required Product Flow

1. A workspace administrator selects **Connect GA4 + Search Console**.
2. The server creates an OAuth authorization request with state, PKCE, and the two read-only scopes.
3. After callback validation, the server securely stores the token material and fetches only the property metadata needed for selection.
4. The administrator selects one GA4 property and one Search Console property and confirms the binding.
5. The server validates both selections with a minimal report/query, storing status, timezone, property identifiers, and a timestamp.
6. The system refreshes bounded aggregated reports on the defined schedule and after approved release annotations.
7. The UI shows only returned data, its date range, property timezone, report freshness, and clear uncertainty labels.
8. The administrator can disconnect, which revokes/invalidates the integration credentials and records an audit event.

## Suggested Data Model

```text
google_connections
  id, workspace_id, connected_by_user_id, status,
  encrypted_refresh_token, granted_scopes, connected_at, disconnected_at,
  token_expires_at, last_error_code, last_error_at

google_property_bindings
  id, workspace_id, connection_id,
  provider (ga4 | search_console), external_property_id, display_name,
  site_url, timezone, selected_at, validated_at, validation_status

analytics_snapshots
  id, workspace_id, binding_id, report_kind, period_start, period_end,
  fetched_at, source_timezone, query_definition_json, result_digest,
  aggregate_payload_json, freshness_state

site_releases
  id, workspace_id, work_order_id, published_at_utc, change_type,
  affected_urls_json, evidence_ids_json, approval_record_id,
  rollback_reference, comparison_window_days

integration_audit_events
  id, workspace_id, actor_user_id, action, connection_id,
  metadata_json, created_at
```

Encrypted token material must never enter `analytics_snapshots`, logs, client responses, source control, or error reporting.

## GA4 Adapter

Use the Google Analytics Data API server-side. The initial adapter must support bounded reports grouped by date, session source/medium, and landing page. Return only aggregated metrics needed for the workspace: sessions, users, engaged sessions, engagement rate, and configured conversion/key-event counts where available.

The system must:

- retain the raw source/medium values before normalizing a known answer-engine referrer category;
- version the answer-engine referrer mapping so historical records remain reproducible;
- render **Observed AI referral traffic** only when a source is identifiable;
- render direct/(none) as **Unattributed traffic movement after release** only when compared against a documented `site_releases` record;
- preserve the GA4 property reporting identity/timezone context in each snapshot.

## Search Console Adapter

Use the Search Console Search Analytics API server-side. The initial adapter must support date, query, page, country, and device dimensions as needed for a bounded report. Preserve clicks, impressions, CTR, position, selected property URL, date range, and whether returned data is finalized or includes fresh/incomplete data.

The UI and report generator must state that Search Console API results are returned rows subject to Search Console limits—not a complete keyword universe.

## Security and Review Requirements

| Area | Acceptance condition |
| --- | --- |
| OAuth callback | Validates state and PKCE; rejects replay, missing state, and user/workspace mismatch. |
| Token storage | Encrypts refresh tokens at rest; never returns token values through tRPC/API/UI. |
| Authorization | Enforces workspace membership and administrator role before connection, selection, refresh, disconnect, or report access. |
| Scope enforcement | Rejects a connection if the returned scopes do not include the two required read-only scopes. |
| API failures | Records safe error codes and retry state without leaking Google payloads or credentials. |
| Data minimization | Stores aggregated reporting results; does not ingest user-level paths, user IDs, or PII. |
| Refresh | Idempotent per workspace/report-kind/date window; rate-limited; observable through audit events. |
| Disconnect | Makes future refresh impossible, removes token material, records a disconnect audit event, and keeps only retention-permitted aggregate artifacts. |
| Tests | Covers OAuth state failure, workspace isolation, encrypted-token nonexposure, property mismatch, refresh idempotency, direct/(none) label, and disconnect behavior. |

## Deliverables

1. Schema migration and typed server models.
2. OAuth initiation and callback endpoints plus secure credential storage.
3. GA4 and Search Console adapter modules with narrow typed interfaces.
4. Property-listing, binding, validation, refresh, and disconnect procedures.
5. Scheduled refresh implementation using the application’s durable background mechanism—not a browser session.
6. Test suite covering every acceptance condition above.
7. A short implementation note that identifies the Google Cloud OAuth-client configuration and required redirect URI(s), without committing client secrets.

## Explicit Non-Goals

The first integration does not collect ad-platform data, scrape answer engines, store raw personal analytics events, claim causal LLM attribution, or make changes to the customer’s site. It provides read-only measurement input to the evidence-governed recommendation workflow.

## Primary References

[1]: https://developers.google.com/analytics/devguides/reporting/data/v1 "Google Analytics Data API overview"
[2]: https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart "Google Analytics API quickstart"
[3]: https://developers.google.com/webmaster-tools/v1/searchanalytics/query "Search Console API: Search Analytics query"
[4]: https://developers.google.com/webmaster-tools/v1/how-tos/authorizing "Search Console API: Authorize Requests"
[5]: https://support.google.com/analytics/answer/15258820?hl=en "Google Analytics Help: Understand (direct) / (none) traffic"
