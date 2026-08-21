# GEO / AEO Multi-LLM Optimization Platform (AIOS)

Commercial Generative Engine Optimization (GEO) & Answer Engine Optimization (AEO) platform built for enterprise SEO agencies (Searchbloom, PartnerCentric) and brand clients.

## Repository Contents
- [`AGENT_CONTEXT.md`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/AGENT_CONTEXT.md) - Active sprint status and system architecture anchor.
- [`PROPOSAL_TO_MANUS.md`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/PROPOSAL_TO_MANUS.md) - Proposal to Manus AI detailing architectural leadership, division of labor, and inter-agent communication protocols.
- [`docs/MANUS_TASKS.md`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/docs/MANUS_TASKS.md) - Backlog of autonomous web scraping & intelligence tasks for Manus AI.
- [`docs/ANTIGRAVITY_TASKS.md`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/docs/ANTIGRAVITY_TASKS.md) - Core codebase development backlog for Antigravity.

---

## Inter-Agent Communication Protocol
This repository serves as the shared communication hub between **Antigravity** (Local Systems Architect) and **Manus AI** (Web Intelligence Specialist). All task handoffs and research outputs are committed directly to markdown logs in `docs/` and `data/`.

## Current Architecture Decision

Read [`docs/MANUS_REVIEW.md`](docs/MANUS_REVIEW.md) before beginning core development. It records the proposed pilot decision: Antigravity/Gemini leads local execution; Manus governs evidence methodology and review; Hermes performs bounded local parsing; external paid model APIs remain disabled until the evidence-led audit workflow passes its first evaluation gate.

Read [`docs/MANUS_SPRINT1_REVIEW.md`](docs/MANUS_SPRINT1_REVIEW.md) before using the sample report or beginning any live audit. It records the Sprint 1 remediation gate and distinguishes the local prototype from client-ready evidence collection.
