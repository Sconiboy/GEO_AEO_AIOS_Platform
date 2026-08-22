# First Real Comparative Pre-Pilot Review Packet

**Status:** Evidence-gated review packet; **not** a commercial client audit and **not** an approved causal finding.  
**Prepared by:** Manus AI  
**Capture surface:** Claude, model label `Haiku 4.5 Extended`  
**Capture timestamp:** 2026-08-22T14:43:58Z  
**Scope:** One public, non-client answer; one pre-approved competitor-owned source; one pre-approved subject-owned source.

## Decision Context

This packet tests whether the platform can preserve and compare a real visible model answer without silently converting a single answer into a ranking, a causal explanation, or a demand estimate. It does **not** answer which agency is “best,” why a model selected an agency, or what all users ask.

| Artifact | Frozen identifier | Integrity binding |
| --- | --- | --- |
| Approved query map | `qm-claude-b2b-saas-seo-20260822` | `8edf25f55496bac90e999c0f7f35126af37620889560c79fe663c56487524542` |
| Dataset manifest | `manifest_claude_b2b_saas_seo.json` | `e900331706c2025ffe2178a58a10933097845a8be82fb70b3065312a1145d74b` |
| Initial source ledger | `run-qm-qm-claude-b2b-saas-seo-20260822` | `4a73dc46591b44fa013f537e9d814adef5d0091a8e88bb564a6a6736e3aea1d3` |
| Artifact-backed answer observation | `obs-claude-b2b-saas-seo-20260822-001` | Raw answer SHA-256: `aa32c964f39fbfa8ccce05e291d3608e6fb9cf58b7e04598fea2f445babba49a` |
| Citation-classification record | `fga-rec-obs-claude-b2b-saas-seo-20260822-001` | Canonical SHA-256: `2b0ae0feed2556fdbcc1330071ee2b86b04971527cce4f3edcabf32018c9185c` |

The initial Claude response that preceded artifact approval remains intentionally classified as **discovery-only**. It is not used in this packet.

## What Was Actually Observed

The fresh Claude response named five agencies and displayed their URLs. It explicitly cited Virayo’s page, while Searchbloom was **not** cited in this one answer. Only Virayo was pre-approved as a competitor candidate and verified against the frozen ledger. The other cited URLs were correctly retained as **unapproved collection candidates**, not fetched or treated as evidence.

| Answer-surface result | Classification | Evidence status |
| --- | --- | --- |
| `https://virayo.com/saas-seo` | Explicit answer citation; declared competitor-owned (Virayo) | Exact URL is `opened_verified` in the frozen ledger. |
| `https://www.searchbloom.com/ai-information/` | Declared subject-owned source | `opened_verified` in the frozen ledger; **not cited in the model answer**. |
| Kalungi, Productive Shop, Growtika, and Cutting Edge PR URLs | Explicit answer citations | Unapproved candidates only; no collection or evidentiary use in this packet. |

> **Verified competitor passage:** “Virayo is a B2B SaaS SEO agency that builds organic pipeline across traditional search and AI discovery.” [1]

> **Verified subject passage:** “Searchbloom is an award-winning, full-service search marketing agency.” [2]

## Limited Evidence-Gap Hypothesis — Pending Human Approval

The only defensible hypothesis from this narrow snapshot is that **the captured answer contains a competitor-owned, category-specific B2B SaaS/AI-discovery statement with an explicit URL, while the single subject-owned source collected for Searchbloom expresses a broader search-marketing position and is absent from that answer.** This may justify collecting a broader, approved set of category-specific subject evidence before attempting any content or reference plan.

This is **not** evidence that Virayo is better, that Claude systematically prefers Virayo, that Searchbloom lacks relevant public material, or that either source caused the answer. Both verified sources are first-party marketing pages, so neither establishes independent third-party corroboration.

| Allowed next action | Why it is allowed | Prohibited conclusion |
| --- | --- | --- |
| Expand the approved manifest to collect several category-specific pages from each declared entity and a small number of independent sources. | It enlarges the evidence base before making a comparative recommendation. | “Publish more pages and Claude will cite Searchbloom.” |
| Repeat the approved neutral query across a declared, bounded panel of answer surfaces and timestamps. | It measures a defined sample rather than assuming one answer represents all usage. | “Searchbloom does not rank in AI.” |
| Human-review exact excerpts for topic, proof type, and source relationship. | Semantic assessment remains governed and traceable. | “Virayo’s page explains why it appeared.” |

## Required Human Decision

The platform needs a human reviewer to approve or reject the hypothesis above before it becomes a report finding. The recommended decision is:

> **Approve only as a preliminary evidence-collection hypothesis.** Do not authorize client-facing ranking, causal, or 90-day optimization recommendations from this one-answer sample.

## References

[1]: https://virayo.com/saas-seo "Virayo — SaaS SEO"
[2]: https://www.searchbloom.com/ai-information/ "Searchbloom — AI Information"
