# 7-oh.org Initial Evidence and Discoverability Audit

Captured: 2026-08-22 UTC

## What the Public Site Represents

The homepage identifies 7-oh.org as a “Legal Resource Center” and a “harm reduction initiative.” It combines legal-lead pages, education and recovery content, an attorney directory, and a “research-grade” SR-17018 shop. The same public site therefore carries legal-information, health-information, commercial, and advocacy signals.

## Immediate Credibility Findings

| Observed public element | Why it matters | Required disposition before visibility work |
| --- | --- | --- |
| The homepage calls itself “the largest 7-OH Legal Resource” and says it covers legal precedents nationwide. | This is a comparative and scope claim. | Retain only with documented measurement method, date, and support; otherwise remove or replace with a precise non-comparative description. |
| Medical and safety assertions appear on the homepage and “What is 7-OH” page without visible primary citations adjacent to the claims. | These are high-consequence claims that must be traceable to reliable sources. | Cite current agency, academic, or public-health sources next to each material assertion; have appropriate subject-matter review. |
| “See if you qualify,” “Join the Lawsuit,” and related lead-generation calls to action appear alongside site educational material. | The site needs an explicit distinction between information, referral, and legal representation. | Add persistent disclosure of who operates the site, attorney/referral relationships, payment arrangements, and that no attorney-client relationship exists. |
| The homepage presents three named harm stories linked to generic `gofundme.com` URLs. | Unverified or placeholder personal stories and fundraising links create material consumer-protection and reputational risk. | Remove immediately unless each story, image, fundraiser, permission, and destination is documented and kept current. Do not replace with invented examples. |
| A public Base44 builder badge is visible. | It weakens ownership and operational trust signals. | Remove from production if the hosting plan supports it, after confirming that doing so does not impair site functionality. |
| The About page says 7-oh.org brings justice through lawsuits and class actions to “hundreds of thousands” of Americans. | This asserts both scale and an advocacy/legal-results role without visible method, operator identity, or source support. | Replace with an accurate operator disclosure, a dated methodology where any scale claim is retained, and a clear description of whether the site is a directory, referral service, publisher, advocacy organization, retailer, or some combination. |
| “Threat Tracker” cards make specific claims about MDX-01, MGM-15, MGM-16, adulterated Cat’s Claw, testing evasion, and active warnings. | These are specific high-stakes safety assertions but no evidence source, author, date, review process, or primary citation is visibly attached. | Remove, pause, or label as unverified pending documented primary evidence and qualified editorial review. Do not present a live warning system until a reliable data and review process exists. |

## Crawlability Findings

| Check | Observed result | Implication |
| --- | --- | --- |
| HTTPS homepage | `200 OK` and HTTPS are present. | Basic crawl access is available. |
| `robots.txt` | Allows all crawlers, but declares `https://7-oh-authority.vercel.app/sitemap.xml` rather than the canonical 7-oh.org sitemap. | The cross-domain sitemap declaration is confusing. Publish one canonical sitemap on 7-oh.org and point `robots.txt` to that exact URL. |
| `https://7-oh.org/sitemap.xml` | Public extraction returned an unstructured URL list rather than a validated XML sitemap response; header inspection returned `text/html`. | Validate and replace with standards-compliant XML (`application/xml` or `application/xml; charset=utf-8`) containing only indexable canonical public URLs. |
| Sitemap URL inventory | Public sitemap includes administrative and transactional routes such as `AdminAttorneys`, `AdminLeads`, `ManageContent`, `ReviewModeration`, `Cart`, and `OrderStatus`. | Remove non-public/admin/thin transactional routes from the sitemap and use authentication plus `noindex` where appropriate. |

## Boundary

This is an observed public-site audit. It does not establish ownership, legal status, medical facts, or any causal relationship with an AI answer. Subsequent recommendations must use verified primary sources and a clean buyer-question panel.
