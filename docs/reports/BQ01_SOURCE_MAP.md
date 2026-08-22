# Buyer Question 01: Source Map

**Buyer question:** Who are the best B2B SaaS SEO agencies?  
**Answer surface:** Claude, Haiku 4.5 Extended, web search enabled  
**Capture:** `obs-panel-bq01-claude-v1`  
**Panel:** Public non-client validation; captured 2026-08-22

## What appeared

Claude named MADX Digital, First Page Sage, Stratabeat, Grow and Convert, SimpleTiger, Directive, Powered by Search, and Genevate. The answer used five visible source URLs. It gave no URL for Powered by Search.

The answer reads like a list assembled from agency-ranking pages. That matters because the source type shapes the strength of each claim.

| Agency named by Claude | Visible source | Collector result | What the page context tells us |
| --- | --- | --- | --- |
| MADX Digital | Cutting Edge PR’s B2B SaaS agency overview | URL visible in Claude; quote did not verify because the collector received a small `202` response rather than the cited page text. | Treat the citation as an observed model source. The page claim remains unverified. |
| First Page Sage; Genevate | First Page Sage’s B2B SaaS agency list | URL visible in Claude; collection received `403 Forbidden`. | Treat the citation as observed. The source page could not be verified by this run. |
| Stratabeat | Optimist’s B2B SEO agency list | URL visible in Claude; TLS handshake timed out during collection. | Treat the citation as observed. The source page could not be verified by this run. |
| Grow and Convert | Grow and Convert’s B2B SaaS agency list | URL visible in Claude; the page was discovered after the manifest had already been frozen. | Candidate for a later approved collection. It has no verified evidence record in this run. |
| SimpleTiger; Directive | SaaS Hackers’ B2B SaaS agency directory | **Opened and quote-verified.** | A directory/ranking page whose stated method should be treated as the publisher’s view. It supports that Claude surfaced this page for these agencies. |
| Powered by Search | None shown | No visible citation. | Claude named the agency without a displayed source URL in this answer. |

## What the source trail means

The buyer asked a short, ordinary question. Claude searched the web and responded with agency names plus ranking-page citations. The visible trail points to a mix of directory content and agency-published listicles, including pages where the publisher promotes itself in the same category.

That is useful client intelligence. The answer did not arrive from a blank black box; it drew on public pages that can be examined, categorized, and compared with a client’s own proof.

## First evidence opportunity

For this question, the strongest immediate lesson is **source quality and source context**. A company that wants to compete for this type of answer needs more than a generic agency page. It needs public proof that fits the buyer’s decision:

1. A clear category page that explains the B2B SaaS offer, scope, and buyer fit.
2. Specific proof: relevant work, measurable outcomes, named methods, and current examples.
3. Legitimate independent evidence, such as credible editorial coverage, directory inclusion, earned reviews, and useful community participation.
4. Ongoing measurement of which sources appear when buyers ask the actual question.

The next panel questions should test different buyer priorities—technical SEO, pipeline growth, and AI-search visibility—before any agency-level recommendation is made.

## Evidence record

| Source state | Count | URLs |
| --- | ---: | --- |
| Visible in the captured answer | 5 | Cutting Edge PR, First Page Sage, Optimist, Grow and Convert, SaaS Hackers |
| Opened and quote-verified | 1 | SaaS Hackers |
| Collector could not verify | 3 | Cutting Edge PR, First Page Sage, Optimist |
| Newly discovered after manifest freeze | 1 | Grow and Convert |

### References

[1]: https://cuttingedgepr.com/articles/6-best-b2b-saas-seo-agencies-in-2026-a-brief-overview/ "Cutting Edge PR: 6 Best B2B SaaS SEO Agencies"
[2]: https://firstpagesage.com/seo-blog/top-b2b-saas-seo-agencies/ "First Page Sage: Top B2B SaaS SEO Agencies"
[3]: https://www.yesoptimist.com/best-b2b-seo-agencies/ "Optimist: Best B2B SEO Agencies"
[4]: https://www.growandconvert.com/seo/best-b2b-saas-seo-agencies/ "Grow and Convert: Best B2B SaaS SEO Agencies"
[5]: https://www.saas-hackers.com/top/b2b-saas-seo-agencies "SaaS Hackers: B2B SaaS SEO Agencies"
