# Manus Sprint 7 Forensic Evidence-Gap Workflow Review

**Reviewed commit:** `e571c738e4c70dbe7dceccfb9fecc8dfab24a42b`  
**Status:** **Rejected as a forensic competitor evidence-gap product.**  
**What is accepted:** the implementation is a useful structural scaffold for a future analysis record.  
**Date:** August 21, 2026

## Positive work

Sprint 7 adds immutable domain objects, a CLI, Markdown/JSON output, ethical boundary language, and a passing regression baseline of **55 tests** with clean `mypy`. The output is intentionally non-manipulative and does not recommend fake reviews, keyword stuffing, or automated spam.

That is useful groundwork. It is not yet the forensic product Benji described.

## P0: the analyzer creates a false gap even when the evidence and human decision support the statement

The PEP 20 fixture has an `OPENED_VERIFIED` official source, a real captured excerpt, and a human-supported decision for `stmt-001`. Yet the emitted gap report says both statements lack authoritative evidence and recommends publishing technical documentation on `python.org`.

The cause is direct in `gap_analyzer.py`: it ignores the supplied `human_decision`, treats **every** extracted statement as unsupported, and emits `MISSING_OFFICIAL_DOCS` whenever any extracted statement exists. This is a false conclusion, not an uncertainty-bound finding.

## P0: source-policy allowlist is incorrectly treated as the client’s identity

`client_domain_cited` is calculated by asking whether any cited domain is in `query_map.policy_profile.source_scope.allowed_domains`. An allowlist identifies **where collection may fetch**; it does not identify the client.

In the emitted PEP artifact, `peps.python.org` is an approved source domain, so the analysis declares the client cited even though no client profile or client-owned domain exists in the input. A real audit cannot infer ownership from collection policy.

## P0: no observed competitor evidence exists in the model answer

The engine counts domains in the source ledger, calls them “competitor citations,” and never distinguishes client-owned, competitor-owned, editorial, review, directory, forum, or other third-party evidence. It does not capture answer-level citations from the observed response, competitor entity IDs, or the relationship between a domain and a competitor.

Therefore it cannot honestly answer the central product question:

> Why did Competitor A appear, what evidence ecosystem may be associated with that appearance, and what client evidence gap is observed?

At present it can only count opened domains in a selected source ledger.

## P0: action confidence and severity are hard-coded, not evidence-derived

The analyzer assigns a generic `0.85` confidence score and emits a generic documentation action. It provides no findings basis, no evidence IDs supporting the action, no alternative explanations, no counterevidence, and no estimate of action effort or expected value.

This would create the exact kind of generic “write more content” output the product is meant to avoid.

## P1: the canonical digest does not protect the meaningful report content

Independent modification of the gap description, expected evidence impact, and ethical-boundary notes left `verify_integrity()` true. `total_sources_evaluated`, gap descriptions, action source type, expected impact, and ethical constraints are omitted from the canonical payload.

Those fields are the explanation and ethical limitation of the report. They must be protected before the report can be regarded as auditable.

## Required Sprint 7.1: re-scope rather than patch around the problem

1. Add an explicit immutable **subject profile**: client entity, owned domains, offering/category, geography, and declared competitor entities/domains. Never infer client ownership from a source collection allowlist.
2. Add explicit **source relationship** classification to each cited/observed domain: `client_owned`, `competitor_owned`, `independent_editorial`, `review_platform`, `directory`, `community`, `official_reference`, or `unknown`.
3. Capture and bind the observed answer’s actual cited/linked domains where an answer surface exposes them. If citations are unavailable, label competitor/source attribution **not assessable**.
4. Add an immutable finding-basis list. Every pattern, gap, and action must list its observation IDs, statement IDs, evidence IDs, and source relationships.
5. Respect human decisions. A `SUPPORTED` human decision cannot automatically be emitted as `MISSING_OFFICIAL_DOCS`.
6. Replace hard-coded severity/confidence with explicit confidence tiers and explanation. When evidence is insufficient, produce `NOT_ASSESSABLE`, not a gap or action.
7. Generate actions only from a documented pattern and label them as **hypotheses for review**, never proven causal mechanisms of LLM behavior.
8. Expand the canonical digest to every rendered finding and action field, including total counts, descriptions, source classifications, evidence basis, expected impact, confidence explanation, and ethical boundary.
9. Add adversarial tests for: a supported statement, an absent client domain, a competitor domain that is actually a neutral editorial source, no answer citations, contradictory sources, and explanatory-field tampering.

## Product boundary

Do not run another generic fixture expansion. Build the smallest honest forensic pilot with an explicit client/competitor data model and real observed answer citations. Only then can the system start producing the “why them, not us, and what should we do” plan Benji wants.
