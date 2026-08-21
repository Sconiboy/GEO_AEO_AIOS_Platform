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
