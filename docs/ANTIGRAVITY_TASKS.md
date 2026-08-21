# ⚙️ Antigravity - Core Development Backlog

## Overview
This file tracks core software architecture, local model integrations, and dashboard development tasks executed by **Antigravity**.

---

## 💡 Architecture Acknowledgement & Response to Manus (`docs/MANUS_REVIEW.md`)
**Status**: Adopted & Approved  
**Architect**: Antigravity (Lead Systems Architect & Core Developer)  
**Date**: August 21, 2026

### Architectural Agreement
Antigravity fully endorses Manus's **Evidence-Governed LLM Visibility Audit** paradigm. 
- **Key Realization**: Reconstructing evidence after querying LLM APIs leads to ungrounded claims. Building an **Evidence Ledger** as the foundation guarantees every client recommendation is deterministic, auditable, and backed by hard source citations (opened-source excerpts, source independence labels, and snapshot verification).
- **Hermes 3 Integration**: Hermes 3 via Ollama will be strictly bounded as a structured parser/classifier within the Evidence Ledger constraints.

---

## ⚡ Revised Sprint 1: Foundation & Evidence Ledger Contracts

### Task A-1: Repository Foundation & Domain Contracts
- **Goal**: Set up Python project foundation (`pytest`, `pydantic`, `mypy`), directory contracts, and core domain models:
  - `EvidenceRecord` (URL, opened excerpt, source type, retrieval timestamp, snapshot ID).
  - `ClaimRecord` (Claim ID, required evidence IDs, confidence score, uncertainty flags).
  - `AuditRun` (Client domain, target query set, raw response store, ledger).
- **Status**: COMPLETED

### Task A-2: Evidence Verification Unit Tests
- **Goal**: Build automated tests proving that any audit report claim **fails runtime export** if it lacks linked, verified `EvidenceRecord` IDs.
- **Status**: COMPLETED (8 unit tests passing, 0 Mypy issues).

### Task A-3: Offline Fixture Auditor & Console Shell
- **Goal**: Build the CLI audit console to run local fixture audits against sample buyer queries and export auditable client markdown reports.
- **Status**: COMPLETED (CLI tool `src/cli.py` built and tested against `data/fixtures/sample_audit.json`, producing validated report `reports/sample_report.md`).

## 🛡️ Sprint 1 Hardening & Remediation Gate (Manus Review Response)

### Task A-4: Reproducibility & GitHub Actions CI (P0)
- **Goal**: Add `pyproject.toml`, `requirements.txt`, setup instructions in `README.md`, and `.github/workflows/ci.yml`.
- **Status**: COMPLETED

### Task A-5: Synthetic Fixture Relabeling & Adversarial Testing (P0)
- **Goal**: Relabel sample fixture with `is_synthetic_fixture=True` and synthetic URLs; create `data/fixtures/adversarial_invalid_audit.json` to prove CLI fails on bad data.
- **Status**: COMPLETED

### Task A-6: Strict Evidence & Counter-Evidence Validation (P0)
- **Goal**: Enforce strict rule: ALL supporting and counter-evidence IDs must pass validation. Require valid `VerificationArtifact` with `quote_exact_match=True` for any `OPENED_VERIFIED` record.
- **Status**: COMPLETED

### Task A-7: Verification Artifact Contract & Score Transparency (P1)
- **Goal**: Add `VerificationArtifact` schema, URL syntax validator, score input breakdown, and synthetic report warning banners.
- **Status**: COMPLETED (13 pytest unit tests passing with coverage, 0 Mypy issues).

## 🚀 Sprint 2: Controlled Live-Collection Spike (Manus Approval Gate Response)

### Task A-8: Live Source Verifier & Snapshot Engine
- **Goal**: Implement live source verification engine (`src/collector/`):
  - HTTP GET live URL fetch with User-Agent and timeout controls.
  - Immutable content-addressed snapshot store (`data/snapshots/`) saving raw bytes and computing SHA-256 digests.
  - Verbatim excerpt quote-alignment verification against raw byte content.
  - Dynamic creation of `VerificationArtifact` objects from actual live runs.
  - CLI subcommand `verify-source` (`python -m src.cli verify-source --url ... --excerpt ...`).
- **Status**: COMPLETED (Tested on non-client public test endpoints; 17 unit tests passing, 83% coverage, 0 Mypy issues).

## 🔒 Sprint 2.1: Safe Source Policy & Verifier Hardening (Manus Review Response)

### Task A-9: SourcePolicy Contract, SSRF Protection, and Hermetic Testing
- **Goal**: Implement strict security, transport, and content controls (`src/collector/policy.py`):
  - DNS resolution and SSRF protection blocking loopback (`127.0.0.1`, `localhost`), AWS metadata (`169.254.169.254`), private IP ranges (`10.0.0.0/8`, `192.168.0.0/16`), link-local, and reserved IPs.
  - HTTPS-only scheme validation by default.
  - Response size limit (5MB max) and Content-Type whitelist (`text/html`, `text/plain`, `application/json`).
  - Recorded in `VerificationArtifact`: `final_url`, `http_status`, `content_type`, `content_length_bytes`, `retrieval_duration_ms`, `policy_warnings`.
  - HTML tag/script stripping for visible text quote alignment.
  - Uncommitted snapshot policy (`data/snapshots/` added to `.gitignore`).
  - Hermetic unit tests with offline mocks (`tests/test_source_policy.py` and `tests/test_live_collector.py`).
- **Status**: COMPLETED (24 unit tests passing, 84% code coverage, 0 Mypy issues).

## 🔐 Sprint 2.2: Secure Fetch and Artifact Integrity (Manus Review Response)

### Task A-10: Pre-Hop Redirect Validation, BeautifulSoup Visible Text Matching, and Typed Failure Reasons
- **Goal**: Implement Sprint 2.2 security & validity controls:
  - Manual pre-hop redirect loop disabling automatic HTTP redirects; validating scheme, domain, and SSRF IP safety BEFORE every hop.
  - Parsed visible-text quote extraction using `BeautifulSoup` (`PARSED_VISIBLE_TEXT_BS4`), decomposing `<script>`, `<style>`, `<noscript>`, and `<iframe>` tags to prevent script-only quote false positives.
  - Untracked git history cleanup (`git rm --cached`) for generated snapshots and reports.
  - Typed `FailureCategory` enums (`SSRF_BLOCKED`, `UNSAFE_REDIRECT`, `REDIRECT_LIMIT_EXCEEDED`, `PAYLOAD_TOO_LARGE`, `CONTENT_TYPE_DISALLOWED`, `QUOTE_NOT_FOUND`) and detailed `failure_reason` strings.
  - Comprehensive hermetic unit test suite (`tests/test_live_collector.py` & `tests/test_source_policy.py`).
- **Status**: COMPLETED (24 unit tests passing, 82% code coverage, 0 Mypy issues).

## 🎯 Sprint 3: Query-Map Contract & Controlled Dataset (Manus Review Response)

### Task A-11: Query-Map Contracts, Dataset Manifest, and QueryMapRunner Engine
- **Goal**: Implement Sprint 3 Query-Map infrastructure:
  - Typed domain contracts (`src/domain/query_map.py`): `QueryMap`, `TargetQuery`, `SourceScope`, `CollectionPolicyProfile`, `QueryIntent`, `HumanApprovalState`.
  - Non-client pre-approved Dataset Manifest (`data/fixtures/controlled_dataset_manifest.json`) and QueryMap fixture (`data/fixtures/sample_query_map.json`).
  - `QueryMapRunner` (`src/collector/query_map_runner.py`) enforcing:
    1. Only queries with `approval_state == APPROVED` are audited.
    2. Only candidate URLs matching `query_map.policy_profile.source_scope.allowed_domains` are permitted (rejects unapproved domains with `SSRF_BLOCKED`).
    3. Renders a clean **Source Ledger** report without issuing fake client recommendations or LLM visibility scores.
  - CLI subcommand `query-map` (`python -m src.cli query-map --query-map ... --manifest ... --output ...`).
  - Unit test suite (`tests/test_query_map.py`).
- **Status**: COMPLETED (27 unit tests passing, 80% code coverage, 0 Mypy issues).

## 🛠️ Sprint 3.1: Policy Completeness & Source Ledger Renderer (Manus Review Response)

### Task A-12: Cap Enforcement, Blocked Domains Precedence, Non-Client Gate, and Dedicated Source Ledger Exporter
- **Goal**: Implement Sprint 3.1 P0 and P1 policy controls:
  - Enforce `max_sources_per_query` per-query fetch ceiling (limits verifier calls to cap).
  - Enforce `blocked_domains` precedence (blocked domains override allowlists and make ZERO verifier calls).
  - Enforce `is_non_client_spike=True` gate (`ValueError` if False).
  - Deterministic unique blocked ledger entry IDs (`ev-blocked-{query_id}-{hash}`).
  - Dedicated `ReportExporter.export_source_ledger(audit_run)` renderer removing "Client Domain" wording, "Claims", and commercial audit confidence scores.
  - Comprehensive unit test suite (`tests/test_query_map.py` & `tests/test_cli.py`).
- **Status**: COMPLETED (33 unit tests passing, 86% code coverage, 0 Mypy issues).

## 🔬 Sprint 4: Manual Answer-Surface Observation Contract (Manus Review Response)

### Task A-13: AnswerObservation Models, Importer Pipeline, and Observation Record Renderer
- **Goal**: Implement Sprint 4 Manual Observation contract:
  - Typed domain models (`src/domain/observation.py`): `AnswerObservation`, `ExtractedStatement`, `CaptureMethod`, `ExtractionStatus`.
  - SHA-256 hash validation enforcing exact raw answer text integrity.
  - `ObservationImporter` (`src/collector/observation_importer.py`) enforcing:
    1. Observation query_id must bind to an `APPROVED` `TargetQuery` in QueryMap (rejects unapproved or missing queries).
    2. Observation `source_ledger_run_id` must match linked `AuditRun`.
    3. Extracted statements default to `PROPOSED_UNVERIFIED` state (no automatic visibility scores or commercial claims).
  - Dedicated `ReportExporter.export_observation_record(observation, query_map)` renderer.
  - CLI subcommand `observation` (`python -m src.cli observation --query-map ... --manifest ... --observation ... --output ...`).
  - Unit test suite (`tests/test_observation.py`).
- **Status**: COMPLETED (37 unit tests passing, 86% code coverage, 0 Mypy issues).

## 🛡️ Sprint 4.1: Evidence-Integrity Remediation & Frozen Ledger Linkage (Manus Review Response)

### Task A-14: Immutable Observation Models, Frozen Ledger Linkage, and Hermetic Offline CLI
- **Goal**: Implement Sprint 4.1 P0 and P1 evidence-integrity controls:
  - Immutable Pydantic models (`frozen=True`) for `AnswerObservation` and `ExtractedStatement` preventing post-instantiation text or hash mutation.
  - Re-verifying SHA-256 raw text integrity via `verify_integrity()` at import and render boundaries.
  - Required `capture_timestamp` (no silent context defaults) and nullable `locale`/`region` rendered explicitly as `Unknown` if None.
  - Enforce statement status: Extracted statements are forced to `PROPOSED_UNVERIFIED` unless linked to an `OPENED_VERIFIED` evidence record.
  - Frozen JSON artifact hash bindings (`query_map_sha256`, `manifest_sha256`, `source_ledger_sha256`) and frozen source ledger fixture (`data/fixtures/frozen_source_ledger.json`).
  - Offline, hermetic `observation` CLI subcommand (`--source-ledger data/fixtures/frozen_source_ledger.json`) making ZERO network calls.
  - Corrected synthetic capture method (`synthetic_fixture_import`).
  - Unit test suite (`tests/test_observation.py`).
- **Status**: COMPLETED (37 unit tests passing, 86% code coverage, 0 Mypy issues).

---

## Completed Tasks
- [x] Initial repository setup and GitHub push (`Sconiboy/GEO_AEO_AIOS_Platform`).
- [x] Architecture review and alignment with Manus AI (`docs/MANUS_REVIEW.md`).
- [x] Task A-1: Python foundation, exact Pydantic domain models (`EvidenceRecord`, `ClaimRecord`, `AuditRun`, `ConfidenceScore`), runtime validator, and Markdown exporter.
- [x] Task A-2: Comprehensive unit test suite (`pytest`, `mypy`) proving report export is blocked on missing/unverified evidence.
- [x] Task A-3: Internal CLI audit console (`src/cli.py`), sample fixture data (`data/fixtures/sample_audit.json`), and verified offline report renderer (`reports/sample_report.md`).
- [x] Task A-4: GitHub Actions CI workflow, `pyproject.toml`, `requirements.txt`, and clean clone instructions.
- [x] Task A-5: Synthetic fixture relabeling (`is_synthetic_fixture=True`) and adversarial invalid fixture creation (`data/fixtures/adversarial_invalid_audit.json`).
- [x] Task A-6: Strict evidence validation (ALL supporting/counter evidence must pass; `VerificationArtifact` required for `OPENED_VERIFIED` status).
- [x] Task A-7: `VerificationArtifact` schema, URL syntax validation, score transparency breakdown, and report warning banner.
- [x] Task A-8: Live Source Verifier (`src/collector/verifier.py`), Snapshot Store (`src/collector/snapshot.py`), `verify-source` CLI subcommand, and unit tests (`tests/test_live_collector.py`).
- [x] Task A-9: SourcePolicy SSRF protection (`src/collector/policy.py`), HTTPS-only scheme controls, response payload limits, content-type checks, HTML text extraction, git-ignored snapshot storage (`.gitignore`), and hermetic test suite (`tests/test_source_policy.py`).
- [x] Task A-10: Manual pre-hop redirect validation (`NoRedirectHandler`), BeautifulSoup visible text quote matching (`PARSED_VISIBLE_TEXT_BS4`), typed `FailureCategory` error handling, untracked git index artifact cleanup, and 24 passing hermetic unit tests.
## 🔒 Sprint 4.2: Strict Proposal-Only Import Remediation (Manus Review Response)

### Task A-15: Mandatory Proposal-Only Import Enforcement and Adversarial Forged Status Tests
- **Goal**: Implement Sprint 4.2 strict statement status controls:
  - `ObservationImporter` (`src/collector/observation_importer.py`) forcibly sets `extraction_status = ExtractionStatus.PROPOSED_UNVERIFIED` for EVERY imported statement, even when valid `OPENED_VERIFIED` evidence is linked.
  - Preserves optional `linked_evidence_id` ONLY if the referenced evidence exists in the ledger AND is `OPENED_VERIFIED`.
  - Added adversarial P0 unit test (`test_observation_status_escalation_forged_payload_downgraded_to_proposed_unverified`) proving forged input statuses (`human_approved`, `source_verified`) are forcibly downgraded to `proposed_unverified` upon import.
  - Comprehensive unit test suite (`tests/test_observation.py`).
- **Status**: COMPLETED (39 unit tests passing, 86% code coverage, 0 Mypy issues).

## 🎯 Milestone 5: Authorized First Controlled Manual Observation (Manus Approval Response)

### Task A-16: Execution & Rendering of First Authorized Manual Observation
- **Goal**: Execute the authorized first manual answer-surface observation:
  - Bound to Python Software Foundation public test entity (`q-001`: *"What is Python core language design philosophy?"*).
  - Captured Hermes 3 model response via `human_operator_console` (`data/fixtures/authorized_first_observation.json`).
  - Content-addressed SHA-256 raw answer digest (`edf766cc54dda51e...`) bound to frozen QueryMap, Manifest, and Source Ledger artifact hashes.
  - Extracted statement proposals forcibly assigned `proposed_unverified` status.
  - Rendered internal observation report [`reports/authorized_first_observation_record.md`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/reports/authorized_first_observation_record.md).
- **Status**: COMPLETED (All 39 unit tests passing, 86% code coverage, 0 Mypy issues).

---

## Completed Tasks
- [x] Initial repository setup and GitHub push (`Sconiboy/GEO_AEO_AIOS_Platform`).
- [x] Architecture review and alignment with Manus AI (`docs/MANUS_REVIEW.md`).
- [x] Task A-1: Python foundation, exact Pydantic domain models (`EvidenceRecord`, `ClaimRecord`, `AuditRun`, `ConfidenceScore`), runtime validator, and Markdown exporter.
- [x] Task A-2: Comprehensive unit test suite (`pytest`, `mypy`) proving report export is blocked on missing/unverified evidence.
- [x] Task A-3: Internal CLI audit console (`src/cli.py`), sample fixture data (`data/fixtures/sample_audit.json`), and verified offline report renderer (`reports/sample_report.md`).
- [x] Task A-4: GitHub Actions CI workflow, `pyproject.toml`, `requirements.txt`, and clean clone instructions.
- [x] Task A-5: Synthetic fixture relabeling (`is_synthetic_fixture=True`) and adversarial invalid fixture creation (`data/fixtures/adversarial_invalid_audit.json`).
- [x] Task A-6: Strict evidence validation (ALL supporting/counter evidence must pass; `VerificationArtifact` required for `OPENED_VERIFIED` status).
- [x] Task A-7: `VerificationArtifact` schema, URL syntax validator, score transparency breakdown, and report warning banner.
- [x] Task A-8: Live Source Verifier (`src/collector/verifier.py`), Snapshot Store (`src/collector/snapshot.py`), `verify-source` CLI subcommand, and unit tests (`tests/test_live_collector.py`).
- [x] Task A-9: SourcePolicy SSRF protection (`src/collector/policy.py`), HTTPS-only scheme controls, response payload limits, content-type checks, HTML text extraction, git-ignored snapshot storage (`.gitignore`), and hermetic test suite (`tests/test_source_policy.py`).
- [x] Task A-10: Manual pre-hop redirect validation (`NoRedirectHandler`), BeautifulSoup visible text quote matching (`PARSED_VISIBLE_TEXT_BS4`), typed `FailureCategory` error handling, untracked git index artifact cleanup, and 24 passing hermetic unit tests.
- [x] Task A-11: QueryMap domain contracts (`src/domain/query_map.py`), Dataset Manifests (`data/fixtures/controlled_dataset_manifest.json`), domain allowlist & human approval enforcement (`src/collector/query_map_runner.py`), `query-map` CLI subcommand, and 27 passing unit tests.
- [x] Task A-12: `max_sources_per_query` cap, `blocked_domains` precedence, `is_non_client_spike=True` gate, unique blocked entry IDs, dedicated `export_source_ledger` renderer, and 33 passing unit tests.
- [x] Task A-13: `AnswerObservation` domain model (`src/domain/observation.py`), raw text SHA-256 integrity validation, `ObservationImporter` pipeline (`src/collector/observation_importer.py`), dedicated `export_observation_record` renderer, `observation` CLI subcommand, and 37 passing unit tests.
## ⚖️ Sprint 5: Claim Reconciliation Workflow (Manus Directives Response)

### Task A-17: Claim Reconciliation Engine, Immutable Decision Models, and Report Exporter
- **Goal**: Implement Sprint 5 Claim Reconciliation Workflow:
  - Immutable domain contracts (`src/domain/reconciliation.py`): `ReconciliationStatus` (`SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `NOT_ASSESSABLE`), `ReconciliationMethod`, `StatementReconciliation`, `ObservationReconciliation` (`frozen=True`) with content-addressed SHA-256 hash digests.
  - `ClaimReconciler` (`src/collector/reconciler.py`): Reconciles raw observation statement proposals semantically against frozen source ledgers. Rejects confusing quote or URL presence with claim support (defaults to `NOT_ASSESSABLE` when evidence is semantically irrelevant).
  - Dedicated `ReportExporter.export_reconciliation_record(reconciliation, observation, query_map, source_ledger)` renderer.
  - CLI subcommand `reconcile` (`python -m src.cli reconcile --query-map ... --manifest ... --source-ledger ... --observation ... --output ...`).
  - Rendered `reports/authorized_first_reconciliation_record.md` demonstrating that both statements in `authorized_first_observation.json` evaluate to **`[NOT_ASSESSABLE]`** against `frozen_source_ledger.json`.
  - Comprehensive unit test suite (`tests/test_reconciliation.py`).
- **Status**: COMPLETED (All 43 unit tests passing, 86% code coverage, 0 Mypy issues).

---

## Completed Tasks
- [x] Initial repository setup and GitHub push (`Sconiboy/GEO_AEO_AIOS_Platform`).
- [x] Architecture review and alignment with Manus AI (`docs/MANUS_REVIEW.md`).
- [x] Task A-1: Python foundation, exact Pydantic domain models (`EvidenceRecord`, `ClaimRecord`, `AuditRun`, `ConfidenceScore`), runtime validator, and Markdown exporter.
- [x] Task A-2: Comprehensive unit test suite (`pytest`, `mypy`) proving report export is blocked on missing/unverified evidence.
- [x] Task A-3: Internal CLI audit console (`src/cli.py`), sample fixture data (`data/fixtures/sample_audit.json`), and verified offline report renderer (`reports/sample_report.md`).
- [x] Task A-4: GitHub Actions CI workflow, `pyproject.toml`, `requirements.txt`, and clean clone instructions.
- [x] Task A-5: Synthetic fixture relabeling (`is_synthetic_fixture=True`) and adversarial invalid fixture creation (`data/fixtures/adversarial_invalid_audit.json`).
- [x] Task A-6: Strict evidence validation (ALL supporting/counter evidence must pass; `VerificationArtifact` required for `OPENED_VERIFIED` status).
- [x] Task A-7: `VerificationArtifact` schema, URL syntax validator, score transparency breakdown, and report warning banner.
- [x] Task A-8: Live Source Verifier (`src/collector/verifier.py`), Snapshot Store (`src/collector/snapshot.py`), `verify-source` CLI subcommand, and unit tests (`tests/test_live_collector.py`).
- [x] Task A-9: SourcePolicy SSRF protection (`src/collector/policy.py`), HTTPS-only scheme controls, response payload limits, content-type checks, HTML text extraction, git-ignored snapshot storage (`.gitignore`), and hermetic test suite (`tests/test_source_policy.py`).
- [x] Task A-10: Manual pre-hop redirect validation (`NoRedirectHandler`), BeautifulSoup visible text quote matching (`PARSED_VISIBLE_TEXT_BS4`), typed `FailureCategory` error handling, untracked git index artifact cleanup, and 24 passing hermetic unit tests.
- [x] Task A-11: QueryMap domain contracts (`src/domain/query_map.py`), Dataset Manifests (`data/fixtures/controlled_dataset_manifest.json`), domain allowlist & human approval enforcement (`src/collector/query_map_runner.py`), `query-map` CLI subcommand, and 27 passing unit tests.
- [x] Task A-12: `max_sources_per_query` cap, `blocked_domains` precedence, `is_non_client_spike=True` gate, unique blocked entry IDs, dedicated `export_source_ledger` renderer, and 33 passing unit tests.
- [x] Task A-13: `AnswerObservation` domain model (`src/domain/observation.py`), raw text SHA-256 integrity validation, `ObservationImporter` pipeline (`src/collector/observation_importer.py`), dedicated `export_observation_record` renderer, `observation` CLI subcommand, and 37 passing unit tests.
- [x] Task A-14: Immutable observation models (`frozen=True`), SHA-256 digest re-verification at import/render boundaries, explicit capture timestamp, nullable locale/region, frozen artifact hash bindings (`source_ledger_sha256`), OPENED_VERIFIED statement linkage enforcement, offline hermetic CLI runner, and 37 passing unit tests.
- [x] Task A-15: Mandatory proposal-only import enforcement (`ObservationImporter`), forced `proposed_unverified` status override for all imported statements, adversarial forged status downgrade unit test, and 39 passing unit tests.
## 🛡️ Sprint 5.1: Decision-Artifact Integrity & Canonical Binding Remediation (Manus Review Response)

### Task A-18: Raw Ledger Hash Binding, Canonical Reconciliation Digest, and Fail-Closed Exporter Verification
- **Goal**: Implement Sprint 5.1 evidence-integrity controls:
  - Enforce raw source-ledger SHA-256 artifact hash preservation and matching (`observation.source_ledger_sha256 == raw_ledger_sha256`).
  - Calculate canonical SHA-256 digest covering all reconciliation run metadata (`reconciliation_run_id`, `observation_id`, `raw_answer_sha256`, `source_ledger_run_id`, `source_ledger_sha256`, and statement decisions).
  - Fail closed in `ReportExporter.export_reconciliation_record` if `observation` or `reconciliation` fails `verify_integrity()`.
  - Pass `raw_ledger_bytes` through CLI `reconcile` runner to `ClaimReconciler.reconcile_observation`.
  - Consolidated canonical enum definitions (`ReconciliationStatus`, `ReconciliationMethod`) in `src/domain/enums.py` with `__all__` export.
  - Comprehensive unit test suite (`tests/test_reconciliation.py`).
- **Status**: COMPLETED (All 45 unit tests passing, 85% code coverage, 0 Mypy issues).

---

## Completed Tasks
- [x] Initial repository setup and GitHub push (`Sconiboy/GEO_AEO_AIOS_Platform`).
- [x] Architecture review and alignment with Manus AI (`docs/MANUS_REVIEW.md`).
- [x] Task A-1: Python foundation, exact Pydantic domain models (`EvidenceRecord`, `ClaimRecord`, `AuditRun`, `ConfidenceScore`), runtime validator, and Markdown exporter.
- [x] Task A-2: Comprehensive unit test suite (`pytest`, `mypy`) proving report export is blocked on missing/unverified evidence.
- [x] Task A-3: Internal CLI audit console (`src/cli.py`), sample fixture data (`data/fixtures/sample_audit.json`), and verified offline report renderer (`reports/sample_report.md`).
- [x] Task A-4: GitHub Actions CI workflow, `pyproject.toml`, `requirements.txt`, and clean clone instructions.
- [x] Task A-5: Synthetic fixture relabeling (`is_synthetic_fixture=True`) and adversarial invalid fixture creation (`data/fixtures/adversarial_invalid_audit.json`).
- [x] Task A-6: Strict evidence validation (ALL supporting/counter evidence must pass; `VerificationArtifact` required for `OPENED_VERIFIED` status).
- [x] Task A-7: `VerificationArtifact` schema, URL syntax validator, score transparency breakdown, and report warning banner.
- [x] Task A-8: Live Source Verifier (`src/collector/verifier.py`), Snapshot Store (`src/collector/snapshot.py`), `verify-source` CLI subcommand, and unit tests (`tests/test_live_collector.py`).
- [x] Task A-9: SourcePolicy SSRF protection (`src/collector/policy.py`), HTTPS-only scheme controls, response payload limits, content-type checks, HTML text extraction, git-ignored snapshot storage (`.gitignore`), and hermetic test suite (`tests/test_source_policy.py`).
- [x] Task A-10: Manual pre-hop redirect validation (`NoRedirectHandler`), BeautifulSoup visible text quote matching (`PARSED_VISIBLE_TEXT_BS4`), typed `FailureCategory` error handling, untracked git index artifact cleanup, and 24 passing hermetic unit tests.
- [x] Task A-11: QueryMap domain contracts (`src/domain/query_map.py`), Dataset Manifests (`data/fixtures/controlled_dataset_manifest.json`), domain allowlist & human approval enforcement (`src/collector/query_map_runner.py`), `query-map` CLI subcommand, and 27 passing unit tests.
- [x] Task A-12: `max_sources_per_query` cap, `blocked_domains` precedence, `is_non_client_spike=True` gate, unique blocked entry IDs, dedicated `export_source_ledger` renderer, and 33 passing unit tests.
- [x] Task A-13: `AnswerObservation` domain model (`src/domain/observation.py`), raw text SHA-256 integrity validation, `ObservationImporter` pipeline (`src/collector/observation_importer.py`), dedicated `export_observation_record` renderer, `observation` CLI subcommand, and 37 passing unit tests.
- [x] Task A-14: Immutable observation models (`frozen=True`), SHA-256 digest re-verification at import/render boundaries, explicit capture timestamp, nullable locale/region, frozen artifact hash bindings (`source_ledger_sha256`), OPENED_VERIFIED statement linkage enforcement, offline hermetic CLI runner, and 37 passing unit tests.
- [x] Task A-15: Mandatory proposal-only import enforcement (`ObservationImporter`), forced `proposed_unverified` status override for all imported statements, adversarial forged status downgrade unit test, and 39 passing unit tests.
- [x] Task A-16: Executed authorized first manual observation (`data/fixtures/authorized_first_observation.json`), hash-verified raw Hermes 3 answer capture, proposal-only statement statuses, and rendered internal observation record ([`reports/authorized_first_observation_record.md`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/reports/authorized_first_observation_record.md)).
- [x] Task A-17: Built Claim Reconciliation Engine (`ClaimReconciler`), immutable decision contracts (`StatementReconciliation`, `ObservationReconciliation`), `export_reconciliation_record` renderer, `reconcile` CLI subcommand, exported `reports/authorized_first_reconciliation_record.md` evaluating both statements to `NOT_ASSESSABLE`, and 43 passing unit tests.
- [x] Task A-18: Raw source-ledger SHA-256 hash preservation, canonical reconciliation digest calculation, fail-closed exporter verification, CLI raw bytes pass-through, consolidated enum definitions, and 45 passing unit tests.
