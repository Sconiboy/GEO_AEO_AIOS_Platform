# Evidence Pattern Map: Dashboard and Client Workflow

## The client journey

The client starts with buyer questions. The workspace shows the captured answers, the companies that appeared, the pages visibly linked in those answers, and the public evidence around those pages. The client ends with a short list of proof and exposure actions their team can own.

```
Buyer questions
      ↓
Captured answers
      ↓
Visible source map
      ↓
Verified evidence patterns
      ↓
Evidence gaps and action plan
```

## Home screen: evidence pattern map

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Client: Acme Widgets         Sample: 12 answers / 4 buyer questions          │
│ [Answers] [Source map] [Evidence patterns] [90-day plan] [Review queue]      │
├──────────────────────────────────────────────────────────────────────────────┤
│ “Who makes the best industrial widget for cold climates?”                     │
│                                                                              │
│  Answer coverage                                                         75% │
│  Clean captures                                                          12  │
│  Visible sources reviewed                                                28  │
│  Verified source pages                                                   19  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Entities that appeared          Repeated source patterns                     │
│                                                                              │
│  1. WidgetCo       8/12        • Category-specific proof pages        7     │
│  2. NorthWorks     6/12        • Independent editorial coverage       5     │
│  3. Acme Widgets   2/12        • Review-platform evidence             4     │
│                                                                              │
│  [Open source map]                                      [Open action plan]   │
└──────────────────────────────────────────────────────────────────────────────┘
```

The top numbers describe the reviewed sample. They are coverage indicators, not market rank scores.

## Answer view

The answer view keeps the buyer question and the captured output together. A client can open any answer and see the capture date, model surface, clean-session status, named entities, and visible URLs.

| Field | Client sees | Purpose |
| --- | --- | --- |
| Buyer question | Exact natural-language question | Connects the work to buyer intent. |
| Captured answer | Preserved answer excerpt | Shows which companies and pages appeared. |
| Source links | Exact URLs visible in the answer | Gives the client the starting evidence trail. |
| Capture details | Model surface, date, session condition | Makes the sample reviewable. |
| Review state | Ready, source review in progress, or evidence complete | Shows what remains to be checked. |

## Source map

The source map is the center of the client experience. Each source card answers: who published this page, why it appeared around the answer, what passage was verified, and what type of evidence it represents.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Source: example.com/best-industrial-widget-makers                            │
│ Appeared in 3 captured answers                                                │
│ Publisher: Competitor-owned agency list                                       │
│ Source type: Editorial-style roundup                                          │
│                                                                              │
│ Verified passage                                                             │
│ “WidgetCo provides ...”                                                      │
│                                                                              │
│ Evidence boundary                                                            │
│ The page establishes the publisher’s position. The publisher also promotes   │
│ its own service, so the card carries that relationship label.                │
└──────────────────────────────────────────────────────────────────────────────┘
```

The source map supports filters for entity, source type, publisher relationship, answer surface, buyer question, verification state, and date.

## Evidence pattern view

The pattern view groups evidence by what repeats across the reviewed answer set. It uses an **evidence pattern strength** score rather than a model-causality score.

| Component | Suggested starting weight | Meaning |
| --- | ---: | --- |
| Clean-capture recurrence | 30% | The entity or source appeared across independent captures. |
| Explicit visible citation | 25% | The model visibly linked the page in its answer. |
| Verified source content | 20% | The collector retained and verified a relevant passage. |
| Publisher independence | 15% | Independent editorial, review, and community sources receive a different relationship label from publisher-owned pages. |
| Buyer-question specificity and freshness | 10% | The evidence directly addresses the buyer question and remains current. |

The score helps order a review queue. It does not claim to reveal a model’s hidden ranking formula.

## Action plan view

The action plan translates source patterns into work the client team can complete. Every action has a linked evidence pattern, owner, completion artifact, and review date.

| Evidence pattern | Client action | Completion artifact |
| --- | --- | --- |
| Competitors repeatedly appear with category-specific proof pages. | Build one useful page that answers the buyer question with scope, method, examples, and factual proof. | Reviewed public page. |
| Independent roundups repeatedly name competitors. | Build a targeted earned-coverage and partner-reference plan. | Disclosed third-party reference or editorial coverage. |
| Review evidence repeatedly appears for competitors. | Improve the real customer-review process and publish attributable customer proof. | Public review profile and permissioned case study. |
| Source mix is mostly competitor-owned listicles. | Expand the panel and seek independent evidence before setting a major strategy. | Wider capture set and source review record. |

## Data-source stack

| Evidence type | Primary collection path | Required label | Client-facing use |
| --- | --- | --- |
| Model-visible page | Approved URL collector with retained snapshot | Publisher relationship and verification state | Exact source card and verified passage. |
| Community discussion | Reddit Data API through approved OAuth access | Community discussion | Public-market language and attributed discussion context. |
| G2 review evidence | G2 API with licensed access | Review platform | Product/category/review observation. |
| Trustpilot review evidence | Trustpilot API key for public business-unit review data | Review platform | Review text, date, rating, and verification fields where available. |
| Client-owned Google reviews | Client-authorized Google Business Profile API | Client-authorized review data | Client review audit and response opportunity. |
| Link profile | Ahrefs or Semrush licensed API | Link-index observation | Referring domain, anchor, first/last seen, and source-page context. |
| Editorial roundup | Approved URL collector plus publisher review | Editorial, partner, competitor-owned, or unknown | Publisher relationship and evidence passage. |

## Operator workflow

1. Approve the natural buyer-question panel and clean-capture policy.
2. Capture answers across the declared model surfaces.
3. Create capture-specific source candidate sets from visible URLs.
4. Review publisher relationships and approve exact collection URLs.
5. Collect source evidence and attach retained snapshots.
6. Group repeated entities and source patterns across clean captures.
7. Review the evidence pattern score with a human operator.
8. Issue action cards only where the evidence supports a practical next move.

## Build sequence

Start with the existing static client page as the visual reference. The first working application release needs four records: `BuyerQuestion`, `AnswerCapture`, `SourceCandidate`, and `EvidenceAction`. It then needs three working screens: answer capture, source review, and client evidence map. Add licensed external data connectors after the source-review workflow is stable.

## References

[1]: https://www.reddit.com/dev/api/oauth/ "Reddit API OAuth documentation"
[2]: https://documentation.g2.com/docs/g2-api "G2 API documentation"
[3]: https://developers.trustpilot.com/business-units-api "Trustpilot Business Units API"
[4]: https://developers.google.com/my-business/content/review-data "Google Business Profile review data"
[5]: https://docs.ahrefs.com/en/api/reference/site-explorer/get-all-backlinks "Ahrefs Site Explorer Backlinks API"
[6]: https://developer.semrush.com/api/v3/seo/backlinks/ "Semrush Backlinks API documentation"
