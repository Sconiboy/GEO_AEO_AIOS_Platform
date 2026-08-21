# Manus Architecture Review and Pilot Decision

**Status:** Proposed for Antigravity/Gemini acknowledgement before core implementation  
**Date:** August 21, 2026  
**Applies to:** `GEO_AEO_AIOS_Platform`

## Decision

The project should proceed as an **evidence-governed LLM visibility audit**, not as a general-purpose multi-agent operating system. Antigravity/Gemini leads local architecture, coding, tests, repository management, and controlled execution. Manus leads the evidence methodology, source-quality standards, adversarial review, and web-intelligence design.

The first client outcome is specific:

> A client asks, “When buyers ask AI systems who to choose in our category, do we surface, why do competitors surface, what evidence appears to drive that, and what should we legitimately improve?”

The pilot must return an auditable answer to that question. It does not promise an LLM rank.

## Approved minimal operating stack

| Component | Role in the pilot | Rule |
|---|---|---|
| Antigravity / Gemini | Local architecture, code execution, tests, Git, internal operator console | **Lead implementation environment** |
| Manus | Evidence policy, source hierarchy, web-intelligence method, adversarial review | Research and quality-governance partner; not a production runtime dependency |
| Hermes via Ollama | Bounded local extraction, classification, schema assistance, and fixture parsing | Must return structured artifacts; cannot be final source or recommendation authority |
| External paid model APIs | Adapter targets only | **Disabled for the pilot** until an evaluated client need proves a specific provider adds value |

Hermes does not become reliable simply because it “learns.” Reliable system learning comes from versioned prompts, preserved evidence, evaluation cases, source snapshots, human approvals, and measured feedback. Hermes can be valuable as a cheap local worker inside those controls.

## What to adopt from the original pitch

The original proposal is right about local-first development, persistent project context, role specialization, GitHub-mediated collaboration, and using a low-cost local model for narrow processing tasks. Those are useful Apex-inspired operating patterns.

## What to change before coding

The original implementation sequence begins with multi-LLM query connectors and then local parsing. That is backwards for a client intelligence product. It produces model prose first and tries to reconstruct evidence afterward.

The required sequence is:

1. Create a reproducible repository foundation with tests, CI, configuration rules, and an internal console shell.
2. Define a client workspace, intake, buyer-query map, audit run state, and local persistence.
3. Build the evidence ledger before model routing. Every material claim needs a URL, opened-source excerpt, source type, independence label, retrieval date, source snapshot, and counter-evidence where applicable.
4. Build deterministic evidence verification: inaccessible source, quote mismatch, duplicate/circular source, stale evidence, and missing availability status must be visible failures.
5. Add manual or fixture answer-surface observations. Preserve exact prompt, provider, raw answer, citations/links where available, and observation time.
6. Build the competitor evidence map and client report. The report must link every material conclusion to evidence records and expose uncertainty.
7. Only then add one model adapter. Add additional providers only after evaluations demonstrate that they improve a defined job.

## Non-negotiable evidence controls

1. **No source, no claim.** Model memory can generate leads, but cannot support a client conclusion.
2. **No snippet-only evidence.** A source must be opened before it is used in the ledger.
3. **No source-type collapse.** Vendor pages, affiliate content, independent editorial, communities, reviews, and official records remain visibly distinct.
4. **No repetition fallacy.** Copied, syndicated, or circular material counts as one underlying signal.
5. **No silent disagreement.** Source or model conflict is retained as uncertainty.
6. **No autonomous external action.** Research and drafting are allowed within a run budget; publishing, messaging, purchasing, or client-system changes require human approval.
7. **No fabricated proof.** The project must never create fake reviews, citations, source excerpts, authority, availability, or competitive claims.

## Immediate change to the active backlog

Do not begin `Task A-1: Multi-LLM Query Connector` yet. Replace it with a foundation work package that creates the repository skeleton, test tooling, CI, internal audit-console shell, typed domain contracts, and one test proving that a report claim cannot exist without linked evidence IDs.

The query connector becomes a later, controlled adapter after the evidence ledger and report contract work end-to-end on fixtures.

## Acceptance gate for the first implementation phase

Antigravity/Gemini should not start external-model calls, broad scraping, dashboards that claim visibility scores, billing, subscriptions, or a general AIOS. The first phase is complete when a fresh clone installs, linting/type checks/tests pass, a minimal internal console starts, and a fixture report visibly fails when a material claim lacks verified evidence.

## Collaboration protocol

This repository is the canonical implementation repository. Commit decisions, contracts, tests, and progress here. Keep Markdown task files concise, but treat typed schemas, migrations, tests, issue records, and Git history as the authoritative operational memory.

Before moving past the foundation, Antigravity/Gemini should record its acknowledgement, any technical disagreement, and the revised first work package in `docs/ANTIGRAVITY_TASKS.md` or an issue/PR.
