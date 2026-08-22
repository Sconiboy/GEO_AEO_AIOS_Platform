# Site-Evidence Operations Work Order

## Operating Model

The Evidence Pattern Map acts as a **supervised site-evidence operations specialist**. It observes buyer questions and source ecosystems, turns reviewed evidence gaps into a structured work order, and hands that work order to the LLM or developer that manages the client site.

It does not directly publish high-consequence claims. It prepares a precise, reviewable change request that another system can implement and validate.

> **Observed question and source evidence → human-reviewed finding → implementation work order → site-manager execution → validation → publication approval → follow-up observation**

## Work-Order Contract

| Field | Required content | Why it exists |
| --- | --- | --- |
| `work_order_id` | Immutable unique ID and creation time. | Allows audit and rollback. |
| `workspace_id` | Client/workspace boundary. | Prevents cross-client data leakage. |
| `change_type` | `content`, `technical_seo`, `structured_data`, `disclosure`, `directory_data`, `correction`, or `removal`. | Routes work to the right implementation path. |
| `target` | Exact URL, route, component, CMS record, template, or infrastructure asset. | Prevents a vague “improve the site” instruction. |
| `business_goal` | Buyer question and the user need being served. | Keeps work people-first. |
| `observed_evidence` | Answer-capture IDs, exact visible source URLs, verified passages, current site observations, and evidence limits. | Gives the site-management LLM the factual basis. |
| `finding` | A human-reviewed, bounded statement about the gap. | Separates evidence from recommendation. |
| `approved_claim_boundary` | Exact facts permitted in the change, prohibited claims, and mandatory uncertainty language. | Prevents hallucinated or inflated claims. |
| `source_pack` | Primary-source URLs, quotes, dates, publisher relationship, and citation format. | Enables traceable implementation. |
| `implementation_task` | Specific instructions to draft, edit, remove, or configure a change. | Makes the work executable. |
| `acceptance_tests` | Content, URL, accessibility, structured-data, link, disclosure, and technical checks. | Defines “done” before publication. |
| `risk_class` | `standard`, `sensitive`, or `high_consequence`. | Determines approval requirements. |
| `review_requirements` | Required roles: operator, client owner, legal, medical/scientific, privacy, or technical reviewer. | Ensures accountability. |
| `publish_state` | `draft`, `implementation_ready`, `implemented_pending_validation`, `approved_to_publish`, `published`, `rejected`, or `rolled_back`. | Prevents unreviewed publication. |
| `rollback_reference` | Prior content/version and reversal action. | Makes every publication reversible. |

## Example: 7-oh.org Sitemap Repair

```yaml
work_order_id: WO-7OH-TECH-001
change_type: technical_seo
target: https://7-oh.org/robots.txt and https://7-oh.org/sitemap.xml
business_goal: Make legitimate public resource pages discoverable while excluding internal routes.
observed_evidence:
  - robots.txt referenced a sitemap on a different domain.
  - the public sitemap response was HTML and listed administrative and transactional routes.
finding: The public sitemap does not cleanly declare canonical editorial URLs and exposes non-editorial routes.
approved_claim_boundary:
  permitted: ["This change improves crawler clarity and indexability hygiene."]
  prohibited: ["This guarantees Google or an AI answer engine will cite 7-oh.org."]
implementation_task:
  - Serve a standards-compliant XML sitemap from https://7-oh.org/sitemap.xml.
  - List only indexable canonical public URLs.
  - Update robots.txt to point to the same canonical sitemap URL.
  - Require authentication and/or noindex for internal, transactional, duplicate, and user-submitted routes.
acceptance_tests:
  - sitemap returns XML with valid absolute 7-oh.org URLs.
  - robots.txt references the canonical sitemap.
  - no admin/order/cart/moderation routes appear in the sitemap.
  - each sitemap URL has a self-referential canonical and a 200 response.
risk_class: standard
review_requirements: [technical_reviewer, client_owner]
publish_state: implementation_ready
rollback_reference: repository release tag or CMS revision ID
```

## Example: 7-oh.org Regulatory Resource Page

```yaml
work_order_id: WO-7OH-CONTENT-002
change_type: content
target: /regulatory-status
business_goal: Answer “What is the current federal status of concentrated 7-OH products?” with dated primary sources.
observed_evidence:
  - FDA pages are official public sources but did not appear in the observed Claude capture.
  - the current site makes regulatory assertions without adjacent primary citations.
finding: A dated source-cited regulatory resource would close a first-party evidence gap; it does not establish future model citation.
approved_claim_boundary:
  permitted:
    - Describe the FDA’s published statements with source and date.
    - Distinguish FDA recommendation, DEA process, and final scheduling action.
    - State when the page was last reviewed.
  prohibited:
    - State that federal scheduling is final unless an authoritative source confirms it.
    - Give legal advice or describe a reader’s personal legal exposure.
    - Describe non-primary claims as confirmed facts.
source_pack:
  - https://www.fda.gov/news-events/public-health-focus/hiding-plain-sight-7-oh-products
  - https://www.fda.gov/news-events/press-announcements/fda-takes-steps-restrict-7-oh-opioid-products-threatening-american-consumers
implementation_task:
  - Draft a scoped factual resource with a visible byline, reviewed date, source links beside material claims, methodology link, and correction link.
  - Add Article JSON-LD only if all markup fields are visible and truthful.
acceptance_tests:
  - every material claim has an adjacent primary source.
  - page distinguishes concentrated 7-OH from natural leaf as the cited source does.
  - a qualified legal/regulatory reviewer signs off before publication.
  - structured data validates and matches visible page content.
risk_class: high_consequence
review_requirements: [client_owner, legal_or_regulatory_reviewer, technical_reviewer]
publish_state: draft
rollback_reference: CMS revision ID
```

## Automation Boundaries

| Change class | Site-management LLM may do automatically | Must wait for human approval |
| --- | --- | --- |
| Mechanical technical changes | Draft a patch, run non-destructive tests, and produce validation evidence. | DNS, auth, redirect, robots/noindex, sitemap, canonical, or production changes must be approved before release. |
| Source-backed standard content | Draft a page from an approved source pack and run citation/link checks. | Publish only after client-owner review. |
| Legal, medical, regulatory, safety, referral, testimonial, donation, or user-story content | Prepare a draft and enumerate source gaps. | Any substantive publication, claim change, testimonial, attorney/referral statement, or emergency guidance requires the relevant human reviewer. |
| Third-party outreach | Draft a disclosed pitch or correction request. | Send, post, solicit, pay, or contact third parties only with explicit approval. |

## Execution Loop

1. The conversational workspace creates a work order only from an approved finding.
2. The site-management LLM receives the work order and may produce a draft or code patch.
3. It runs acceptance tests and returns an implementation record with changed files/URLs and test evidence.
4. The workspace checks that the implementation stayed inside the approved claim boundary.
5. Required human reviewers approve publication or reject/return the work.
6. The release record retains the published version, source pack, approvers, validation results, and rollback reference.
7. A follow-up question capture measures what publicly surfaced next, without claiming that the change caused an answer.

## First Build Decision

Build a **Work Orders** capability immediately after the thin Capture Desk and Source Map. It is the bridge between evidence intelligence and actual site operations. Without it, the product remains a reporting tool; with it, the product becomes an accountable operating system for credible visibility work.
