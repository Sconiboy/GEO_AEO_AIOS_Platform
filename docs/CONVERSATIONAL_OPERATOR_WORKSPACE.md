# Evidence Pattern Map: Conversational Operator Workspace

## Product Definition

The Evidence Pattern Map is a **guided conversational workspace for evidence-governed AI visibility work**. It does not ask a client to enter a domain and return an opaque score. It helps an operator work through a real buyer question, preserve what an answer engine visibly returned, inspect the sources surrounding that answer, identify a credible gap, and turn that gap into human-approved work.

> **Buyer question → natural answer capture → visible sources → verified source context → evidence gap → reviewed action plan → follow-up capture**

The conversation is the operating surface. The durable evidence objects, review decisions, and client report are produced underneath it.

## The Core Interaction

| Step | What the operator says or provides | What the workspace does | Required human decision |
| --- | --- | --- | --- |
| 1. Frame the work | “A client wants to appear when buyers ask this question.” | Captures client, objective, target audience, geography, exact natural question, and known constraints. | Approve the buyer question and scope. |
| 2. Preserve what appeared | Pastes or imports a clean-session answer capture. | Stores the raw answer, model surface, date/time, session condition, visible URLs, and capture artifact. | Confirm that the capture is clean and usable. |
| 3. Explain the source set | “Who is showing up, and what are these sources?” | Classifies each visible URL by entity, publisher role, commercial interest, source type, and evidence limit. | Approve or reject sources for further collection. |
| 4. Test the site honestly | “What does the client site have—or lack—relative to this source set?” | Separates public-site facts, technical discoverability, cited proof, independently earned evidence, and unresolved claims. | Promote only source-backed findings. |
| 5. Decide what to do | “What work would legitimately close the gap?” | Generates specific content, proof, technical, disclosure, review-process, or earned-reference actions with completion artifacts. | Approve an owner, due date, and compliance review. |
| 6. Measure again | “What changed?” | Runs the same approved question panel, shows what surfaced, and preserves any source changes. | Interpret results as observations, not proof of causality. |

## Minimal Durable Objects

| Object | Purpose | Non-negotiable fields |
| --- | --- | --- |
| **Workspace** | Isolates one client or internal project. | Client identity, domain(s), access roles, data-retention policy. |
| **BuyerQuestion** | Preserves natural buyer language. | Exact text, origin, approval status, target intent, scope notes. |
| **AnswerCapture** | Records the answer as observed. | Raw answer, visible URL list, model/surface, UTC time, session condition, artifact reference/digest. |
| **SourceCandidate** | Represents a URL surfaced in one exact capture. | Normalized URL, capture ID, publisher/entity, source-role proposal, collection decision. |
| **SourceEvidence** | Holds reviewed, collected source context. | Retained snapshot/reference, quote, source type, publisher relationship, collection time, evidence limit. |
| **Finding** | States a bounded observed pattern or gap. | Linked captures and evidence IDs, claim text, uncertainty, reviewer decision. |
| **ActionPlanItem** | Converts a reviewed gap into owned work. | Action, owner, rationale/evidence links, completion artifact, status, due date. |
| **ReviewDecision** | Creates an accountable human gate. | Reviewer role, method, date/time, rationale, promoted/rejected status. |

## Conversation Rules

The workspace should ask the next useful question instead of pretending it has enough information. Examples include:

| If the user says… | The workspace should ask… |
| --- | --- |
| “Why is that company appearing?” | “I can show the pages visibly cited in this capture and the evidence they contain. Would you like to classify the sources first, or compare them with your public proof?” |
| “Make us show up there.” | “Which buyer question matters first? I’ll preserve the current answer and sources, then identify credible proof and discoverability work. I cannot promise a citation.” |
| “That claim is wrong.” | “Do you have a primary source, correction record, or approved statement? I’ll mark the claim unresolved until it is reviewed.” |
| “We need content.” | “What fact can you support with a primary source, accountable author, and update date? We should publish the proof page before expanding topical content.” |
| “They show more reviews than we do.” | “Are those reviews public and authentic? We can improve review collection and permissions, but we will not create or seed reviews.” |

## Guardrails

The workspace must enforce the following boundaries in conversation and in reports:

1. It cannot claim access to a model’s hidden reasoning, training data, retrieval logs, or ranking formula.
2. A visible source is an observed co-occurrence in one capture, not proof that the source caused the answer.
3. It must preserve the buyer’s natural question before any internal analysis prompt is applied.
4. It must label client-owned, law-firm, affiliate, advertiser, editorial, official, community, and unknown publisher relationships.
5. It must never invent reviews, testimonials, case studies, statistics, endorsements, sources, or personal harm stories.
6. High-consequence legal, health, financial, and regulatory claims require primary sources, current dates, and an accountable reviewer before promotion.
7. It must separate official court/agency information from lawyer intake, referral, lead-generation, and sponsored content.
8. It must prohibit spam, astroturfing, deceptive listicles, undisclosed placements, and promises of model placement.

## First Thin Operator Shell

The first usable application should implement only the workflow needed to do the work shown in the 7-OH example:

| Screen | User task | Required capability |
| --- | --- | --- |
| **Conversation / Intake** | State client, goal, buyer question, and constraints in plain language. | Structured extraction into a draft workspace; operator can correct before approval. |
| **Capture Desk** | Paste a clean answer or upload a transcript/screenshot. | Store raw content, timestamp, model/surface, visible URLs, and declared session condition. |
| **Source Map** | Review who appears and why the page matters. | URL cards with source role, publisher relationship, commercial disclosure, quote, and evidence limit. |
| **Evidence Gap** | Compare client proof with the observed source set. | Evidence-backed gap records; no automated causal score. |
| **Action Board** | Turn findings into accountable work. | Owner, completion artifact, review flag, status, and supporting evidence. |
| **Report View** | Explain the decision to a client. | Buyer question, answer sources, source map, gap, actions, limits, and review history. |

## Product Decision

Build this **thin operator shell next**, not another abstract provenance layer and not a generic domain-monitoring dashboard. The platform already has the policy and provenance contracts needed to make the shell trustworthy. The shell makes them usable by an operator and legible to a client.
