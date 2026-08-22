# 7-oh.org: 30/60/90-Day Discoverability Plan

**Prepared:** 2026-08-22  
**Goal:** Make 7-oh.org easier for search systems and answer engines to discover, understand, and cite *when the site has genuinely useful, accurate, and attributable public information*.  
**Success boundary:** The work can improve availability, clarity, and public evidence. It cannot guarantee model citations, rankings, referral traffic, or legal outcomes.

## The Decision

**Do not start by adding more 7-OH pages or trying to manufacture mentions.** The first work is credibility and technical cleanup. The public site currently mixes harm-reduction education, attorney referrals, lawsuit calls to action, a research-materials shop, unsourced threat alerts, and personal fundraising stories. That makes its purpose and editorial standard unclear. For high-consequence health and legal topics, clear sourcing, identifiable authorship, expert review, and a focused purpose matter more than content volume.[1]

The site should adopt one defensible public position:

> **7-oh.org is a transparently operated, source-cited public-information resource about concentrated 7-OH products, regulatory developments, and how to locate official records and qualified help.**

If the legal-directory and shop businesses remain, they need explicit and persistent separation from editorial content. The site must disclose operator identity, referral/advertising relationships, data handling, and commercial relationships. A visitor should never have to guess whether a page is neutral education, paid legal lead generation, product marketing, or a referral directory.

## What Must Be Fixed First

| Priority | Observed problem | Required action | Completion artifact |
| --- | --- | --- | --- |
| **P0 — remove/verify** | Named injury stories link to generic GoFundMe URLs; they appear to be illustrative or placeholder stories. | Remove them immediately unless each person, photograph, fundraiser, consent, and live destination can be documented. Do not substitute invented stories, reviews, testimonials, or fundraisers. | Public-page diff and an internal evidence file for every retained story. |
| **P0 — remove/verify** | “Threat Tracker” and Cat’s Claw alerts make specific claims without visible dated primary sources, author, or review method. | Pause or remove every alert until it has a dated primary-source record, an accountable reviewer, a source link beside the claim, and a correction process. | Source ledger; reviewed alert template; public update date and source link. |
| **P0 — correct** | “Largest” legal-resource and “hundreds of thousands” affected claims are unsupported on the public page. | Remove them unless the site can publish a current, verifiable methodology and evidence. | Revised copy or dated methodology page. |
| **P0 — disclose** | Legal education, attorney directory, case intake, and commercial functions are visually intertwined. | Publish a sitewide operator, editorial, legal-referral, advertising, privacy, and conflict-of-interest disclosure. Place a short version near every intake, directory, and attorney CTA. | Linked policies, per-page disclosure blocks, and an approved disclosure inventory. |
| **P0 — clarify** | The legal-help page says an AI-assisted tool helps identify “strongest claims” and determine whether a visitor “qualifies.” | Reframe it as an administrative intake or informational questionnaire. It must not diagnose eligibility, make legal conclusions, or imply lawyer review unless that is actually happening. | Revised user flow, reviewed copy, and test captures. |

## Days 0–30: Build a Trustworthy, Crawlable Base

### Days 0–14: Verify Every Public Claim and Establish Editorial Ownership

Create a source inventory for every medical, safety, regulatory, and legal statement. For each claim, record its page URL, exact text, source URL, source type, publication date, reviewer, last-reviewed date, and disposition: retain, revise, or remove. Only primary government, court, or peer-reviewed sources should support material factual claims. Secondary reporting can provide context but cannot substitute for a primary source where one exists.

Start with a small set of stable, attributable facts. The FDA states that it is focused on concentrated 7-OH products rather than natural kratom leaf, and that the DEA has final authority over federal scheduling after a rulemaking process.[2] The FDA’s July 2026 public update describes a temporary-scheduling process and distinguishes concentrated/synthetic products from natural leaf containing trace 7-OH.[3] 7-oh.org should quote and link to those sources accurately rather than paraphrasing broad conclusions or presenting regulatory status as settled when it is not.

Build four public trust pages before publishing new topical content:

| Page | What it must state | What it must not claim |
| --- | --- | --- |
| **About and operator disclosure** | Legal entity or responsible operator, mission, contact channel, geographic scope, and the site’s exact role. | “Independent” or “largest” without proof. |
| **Editorial and source policy** | Source hierarchy, author/reviewer qualifications, dates, corrections process, use of automation, and how content is updated. | That the site “verifies” medical or legal facts without a documented method. |
| **Attorney/referral and advertising disclosure** | Whether attorneys pay for listings, whether referrals generate compensation, how attorney credentials are checked, and whether users’ data is sold/shared. | That the platform itself provides legal representation. |
| **Methodology and limitations** | How the site distinguishes legal information, official docket data, agency notices, research, editorial analysis, and paid/sponsored content. | That a lawyer-intake page is an official case record. |

### Days 15–30: Repair Indexing and Machine Readability

The public crawl audit found `robots.txt` allows access but points to a Vercel-hosted sitemap, while `https://7-oh.org/sitemap.xml` returns an HTML response and exposes administrative and transactional URLs. Replace this with one standards-compliant XML sitemap on `7-oh.org` that lists only canonical, public, indexable editorial and directory pages. Google advises using fully qualified canonical URLs in the sitemap and limiting it to URLs intended for search results.[4]

Implement the following technical baseline:

| Work | Required implementation | Verification |
| --- | --- | --- |
| Canonical URLs | Choose one public URL per page; redirect `/Home` to `/`; emit a self-referential canonical on every indexable page. | Browser source check and URL Inspection. |
| Sitemap | Serve valid XML from `https://7-oh.org/sitemap.xml`; point `robots.txt` to this same URL; remove admin, order, cart, moderation, and duplicate routes. | XML validation, Search Console sitemap report, and crawler recheck. |
| Private/non-editorial routes | Require authentication for admin routes. Add `noindex` to transactional, user-submitted, thin, duplicate, and internal-tool routes that remain publicly accessible. | Auth test, meta/header audit, and indexed-URL review. Google notes that `robots.txt` alone is not a reliable way to keep web pages out of results.[5] |
| Search Console | Verify the 7-oh.org domain property, submit the fixed sitemap, inspect the home page and each high-priority resource page, and record baseline impressions, indexed pages, and crawl errors. | Baseline dashboard export. |
| Answer-engine crawl access | Maintain explicit access for `OAI-SearchBot`; do not confuse it with `GPTBot`. OpenAI documents that `OAI-SearchBot` is used for ChatGPT search results and can be allowed independently of training crawlers.[6] | Versioned `robots.txt` and server-log check. |
| Structured data | Use JSON-LD only for information that is visible and true: `Organization`, `WebSite`, `BreadcrumbList`, and `Article`/`NewsArticle` when pages have real authors, dates, and an editorial process. | Rich Results Test and Schema Validator. Google requires markup to describe the page where it appears and emphasizes complete, accurate properties over volume.[7] |

## Days 31–60: Publish Pages Answer Engines Can Reliably Understand

The publishing goal is **not** keyword expansion. It is a small evidence library that answers a real user question with a direct explanation, dated primary sources, clear authorship, and a transparent limit.

### The First Five Public Resources

| Resource | Buyer question it serves | Required evidence and structure | Commercial boundary |
| --- | --- | --- | --- |
| **What 7-OH refers to** | “What is 7-OH?” | Plain-language definition, distinction between concentrated 7-OH products and natural kratom leaf, FDA source links, last reviewed date, named author and reviewer. | No product promotion or attorney CTA inside the factual answer. |
| **Regulatory status tracker** | “What is the current federal status of concentrated 7-OH?” | Dated timeline using FDA, DEA, HHS, and state primary sources; show “last checked” and distinguish proposal, notice, rule, action, and enforcement. | No “live alert” status without a documented update cadence and source record. |
| **How to verify a lawsuit or settlement** | “Is there an active 7-OH case, and where do I verify it?” | Explain the difference among a complaint, docket, order, settlement notice, attorney investigation, and lead page; link official court or government records where public. | Do not funnel the reader to intake before explaining official-record verification. |
| **Help and reporting resources** | “Where can I get help or report a suspected adverse event?” | Direct links to official and credible services, including FDA reporting and Poison Help where appropriate, with a plain emergency disclaimer. | No data capture before access to urgent help. |
| **Methods, sources, and corrections** | “Why should I trust this page?” | Source hierarchy, author/reviewer bios, correction log, disclose funding/referral/advertising, page change history. | Must be accessible from every editorial page. |

Each page must use the same evidence block:

> **Reviewed:** date • **Author:** named individual or accountable team • **Medical/legal review:** name and scope, if applicable • **Primary sources:** linked beside each material claim • **Last substantive change:** date • **Corrections:** linked policy

That is aligned with Google’s published guidance for high-consequence topics: clear sourcing, author/site background, accurate authorship, and a clear purpose are central to trust assessment.[1]

## Days 61–90: Earn Legitimate Public Evidence

After the primary resource pages are live and reviewed, build third-party discoverability through work that a publisher, nonprofit, researcher, journalist, or attorney can independently evaluate.

| Channel | Legitimate action | Evidence of completion | Prohibited shortcut |
| --- | --- | --- | --- |
| Public-interest sources | Offer a concise, sourced briefing with direct links to official agency materials, a methodology page, and an identified spokesperson. | A disclosed earned mention, quotation, or resource link. | Paid “news,” undisclosed placements, or fake editorial roundups. |
| Professional experts | Invite qualified health, toxicology, legal-ethics, and recovery experts to correct or review narrowly scoped pages; disclose their role and any compensation. | Named reviewed page and scope-of-review statement. | Invented expert endorsements or broad approval claims. |
| Legal directory | If attorney listings are a real business, establish public vetting criteria, pricing/disclosure, location/licensure fields, and an independent way to report a problem. | Public directory policy and per-listing data fields. | “Verified” labels without a documented verification process. |
| Community participation | Answer requests for official sources and corrections where disclosure is appropriate. | Archived, attributable participation that adds real value. | Reddit seeding, fake accounts, astroturfing, or undisclosed affiliate/referral links. |
| Research updates | Publish only material updates with a primary citation and a documented change log. | Dated update page and source record. | High-volume AI rewrites, invented alerts, or backdating pages. |

## The Buyer-Question Panel

Once the initial resources are live, run a clean-session natural-question panel. Each capture must preserve the exact question, model, UTC time, raw answer, and visible URLs. The goal is to observe public discovery, not to force an answer engine to cite the client.

| Question | Intended evidence use |
| --- | --- |
| “What is 7-OH, and how is it distinct from traditional kratom leaf?” | Tests whether factual resource pages are understandable and whether primary sources dominate. |
| “What is the current federal status of concentrated 7-OH products?” | Tests the dated regulatory tracker against official agency sources. |
| “How can I tell the difference between an official 7-OH lawsuit record and a law-firm intake page?” | Tests the public legal-literacy resource without soliciting legal advice. |
| “Where can someone find official health and safety information about concentrated 7-OH products?” | Tests whether the site is discoverable as a transparent directory to primary sources. |

For every answer, classify visible URLs as official agency/court, independent editorial, client-owned, law-firm intake, affiliate, community, or unknown. The result is an evidence map, not a claim about hidden model reasoning or a promise of future visibility.

## Measurement: What Counts as Progress

| Measure | Baseline | 30 days | 60 days | 90 days |
| --- | --- | --- | --- | --- |
| Sitemap health | Current sitemap response, submitted URL count, indexable URL list | Valid XML sitemap and no administrative URLs | Stable validation in Search Console | Monthly automated check and change log |
| Crawl/index quality | Crawl errors, canonical conflicts, excluded URLs | Priority pages inspect cleanly | Index coverage matches intended public library | Quarterly review |
| Evidence completeness | % of material claims with adjacent primary citation, author, date, and review status | 100% on first five resources | 100% on all published high-consequence pages | Quarterly source-refresh log |
| Trust disclosures | Current policy/link locations | Operator/editorial/referral disclosures live | Per-page disclosures live | Annual legal/privacy review |
| Public discovery | Search Console impressions/clicks for evidence pages; clean answer-panel observations | Baseline recorded | First capture panel | Repeat panel; compare visible source mix | 

Use the answer panel and referrer logs as directional evidence only. A change in a model answer does not prove that a page caused the change.

## Owner Decisions Needed Before Publishing

1. **What is 7-oh.org’s actual primary role?** Choose one public core: information publisher, attorney-referral directory, advocacy organization, or commerce platform. Secondary functions can exist, but they cannot be disguised.
2. **Who is the accountable operator?** The site needs a real legal entity or responsible publisher identity, contact, and scope of operation—not only “industry insiders.”
3. **What commercial relationships exist?** Attorney listing fees, referral fees, research-material sales, sponsored content, and data-sharing must be disclosed accurately.
4. **Who can review high-consequence content?** Assign a named legal-review process for legal pages and a qualified medical/scientific-review process for health pages. If no reviewer exists, narrow the content to sourced summaries and link out.
5. **Which claims can be documented today?** Any claim without a source record and approval owner should be removed before the technical/indexing push.

## References

[1]: https://developers.google.com/search/docs/fundamentals/creating-helpful-content "Google Search Central: Creating helpful, reliable, people-first content"
[2]: https://www.fda.gov/news-events/press-announcements/fda-takes-steps-restrict-7-oh-opioid-products-threatening-american-consumers "FDA: Takes Steps to Restrict 7-OH Opioid Products Threatening American Consumers"
[3]: https://www.fda.gov/news-events/public-health-focus/hiding-plain-sight-7-oh-products "FDA: Hiding in Plain Sight: 7-OH Products"
[4]: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap "Google Search Central: Build and submit a sitemap"
[5]: https://developers.google.com/search/docs/crawling-indexing/robots/intro "Google Search Central: Introduction to robots.txt"
[6]: https://openai.com/gptbot/ "OpenAI: Overview of OpenAI Crawlers"
[7]: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data "Google Search Central: Introduction to structured data markup"
