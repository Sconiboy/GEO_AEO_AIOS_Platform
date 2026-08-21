# GEO / AEO Multi-LLM Optimization Platform (AIOS)

Commercial Generative Engine Optimization (GEO) & Answer Engine Optimization (AEO) evidence-governed audit engine built for enterprise SEO agencies (Searchbloom, PartnerCentric) and brand clients.

> **NOTICE**: The fixture files in `data/fixtures/` are **SYNTHETIC FIXTURE DATA FOR UNIT TESTING ONLY**. They are not real client audit evidence.

---

## 🛠️ Reproducible Environment Setup

### 1. Requirements
- Python 3.10+ (Tested on Python 3.12)
- Virtual Environment (`venv`)

### 2. Quickstart Installation
```bash
# Clone repository
git clone https://github.com/Sconiboy/GEO_AEO_AIOS_Platform.git
cd GEO_AEO_AIOS_Platform

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🧪 Running Verification Suite & Tests

```bash
# Run Mypy Type Checker (Strict Mode)
mypy src

# Run Pytest Suite with Coverage
pytest --cov=src tests/

# Execute CLI Fixture Auditor Output
python -m src.cli audit --fixture data/fixtures/sample_audit.json --output reports/sample_report.md
```

---

## 📂 Repository Contents
- [`AGENT_CONTEXT.md`](AGENT_CONTEXT.md) - Active sprint status and system architecture anchor.
- [`PROPOSAL_TO_MANUS.md`](PROPOSAL_TO_MANUS.md) - Proposal to Manus AI detailing architectural leadership and division of labor.
- [`docs/MANUS_SPRINT1_REVIEW.md`](docs/MANUS_SPRINT1_REVIEW.md) - Manus Sprint 1 implementation review and quality gate.
- [`docs/MANUS_SPRINT1_REMEDIATION_REVIEW.md`](docs/MANUS_SPRINT1_REMEDIATION_REVIEW.md) - Current approval state and the controlled live-collection gate.
- [`docs/MANUS_SPRINT2_REVIEW.md`](docs/MANUS_SPRINT2_REVIEW.md) - Controlled live-collection review and required source-policy hardening before client query-map work.
- [`docs/MANUS_SPRINT21_REVIEW.md`](docs/MANUS_SPRINT21_REVIEW.md) - Sprint 2.1 source-policy review and required secure-fetch gate before any real collection.
- [`docs/MANUS_SPRINT22_REVIEW.md`](docs/MANUS_SPRINT22_REVIEW.md) - Sprint 2.2 secure-fetch review and controlled non-client query-map approval boundary.
- [`docs/MANUS_SPRINT3_REVIEW.md`](docs/MANUS_SPRINT3_REVIEW.md) - Sprint 3 query-map review and required policy-enforcement remediation before answer-surface observation.
- [`docs/MANUS_SPRINT31_REVIEW.md`](docs/MANUS_SPRINT31_REVIEW.md) - Sprint 3.1 policy-enforcement approval and the manual-capture answer-observation contract.
- [`docs/MANUS_SPRINT4_REVIEW.md`](docs/MANUS_SPRINT4_REVIEW.md) - Sprint 4 manual-observation review and required evidence-integrity remediation before any live capture.
- [`docs/MANUS_SPRINT41_REVIEW.md`](docs/MANUS_SPRINT41_REVIEW.md) - Sprint 4.1 evidence-integrity review and the final proposal-only import correction before live capture.
- [`docs/MANUS_SPRINT42_REVIEW.md`](docs/MANUS_SPRINT42_REVIEW.md) - Sprint 4.2 approval for one controlled manual observation and its execution boundary.
- [`docs/MANUS_FIRST_OBSERVATION_ASSESSMENT.md`](docs/MANUS_FIRST_OBSERVATION_ASSESSMENT.md) - Assessment of the first authorized observation and the claim-reconciliation requirement it exposed.
- [`docs/MANUS_SPRINT5_REVIEW.md`](docs/MANUS_SPRINT5_REVIEW.md) - Sprint 5 reconciliation review and the required frozen-artifact integrity correction.
- [`docs/MANUS_SPRINT51_REVIEW.md`](docs/MANUS_SPRINT51_REVIEW.md) - Sprint 5.1 integrity approval and the persistence requirement for durable reconciliation records.
- [`docs/MANUS_SPRINT52_6_REVIEW.md`](docs/MANUS_SPRINT52_6_REVIEW.md) - Sprint 5.2/6 review requiring persisted-artifact context binding and authentic PEP 20 source verification.
- [`docs/MANUS_SPRINT521_61_REVIEW.md`](docs/MANUS_SPRINT521_61_REVIEW.md) - Sprint 5.2.1 replay-defense approval and Sprint 6.1 synthetic-fixture qualification.
- [`docs/MANUS_SPRINT62_REVIEW.md`](docs/MANUS_SPRINT62_REVIEW.md) - Sprint 6.2 review requiring persisted manifest provenance and human-governed semantic support.
- [`docs/MANUS_SPRINT63_REVIEW.md`](docs/MANUS_SPRINT63_REVIEW.md) - Sprint 6.3 approval for safe automation and the required human semantic-decision record.
- [`docs/MANUS_SPRINT64_REVIEW.md`](docs/MANUS_SPRINT64_REVIEW.md) - Sprint 6.4 review requiring quote provenance and complete decision-integrity protection.
- [`docs/MANUS_SPRINT641_REVIEW.md`](docs/MANUS_SPRINT641_REVIEW.md) - Sprint 6.4.1 approval for controlled human decisions and the remaining snapshot-portability boundary.
- [`docs/MANUS_SPRINT7_REVIEW.md`](docs/MANUS_SPRINT7_REVIEW.md) - Sprint 7 review requiring explicit client/competitor ownership and evidence-basis provenance before forensic action plans are accepted.
- [`docs/MANUS_SPRINT71_REVIEW.md`](docs/MANUS_SPRINT71_REVIEW.md) - Sprint 7.1 review requiring profile-hash binding, decision-context checks, attribution states, and false-gap prevention.
- [`docs/MANUS_SPRINT72_REVIEW.md`](docs/MANUS_SPRINT72_REVIEW.md) - Sprint 7.2 review approving provenance safeguards while requiring direct answer-citation competitor classification.
- [`docs/MANUS_SPRINT73_REVIEW.md`](docs/MANUS_SPRINT73_REVIEW.md) - Sprint 7.3 review approving direct competitor recognition while requiring manifest-approved collection candidates and exact URL evidence linkage.
- [`docs/MANUS_SPRINT74_REVIEW.md`](docs/MANUS_SPRINT74_REVIEW.md) - Sprint 7.4 review requiring exact URL-and-query manifest authorization before any observed competitor citation can be collected.
- [`docs/MANUS_SPRINT741_REVIEW.md`](docs/MANUS_SPRINT741_REVIEW.md) - Sprint 7.4.1 approval for exact candidate authorization, with execution-time revalidation required before collection.
- [`docs/MANUS_SPRINT75_REVIEW.md`](docs/MANUS_SPRINT75_REVIEW.md) - Sprint 7.5 review requiring collection-context validation and immutable candidate-to-evidence provenance before execution.
- [`docs/MANUS_SPRINT751_REVIEW.md`](docs/MANUS_SPRINT751_REVIEW.md) - Sprint 7.5.1 review requiring failed verifier results to remain attempts rather than completed collection executions.
- [`docs/MANUS_SPRINT752_REVIEW.md`](docs/MANUS_SPRINT752_REVIEW.md) - Sprint 7.5.2 approval for one tightly controlled public competitor-source collection pre-pilot.
- [`docs/MANUS_SPRINT76_REVIEW.md`](docs/MANUS_SPRINT76_REVIEW.md) - Sprint 7.6 review accepting the live Rust retrieval but rejecting the scripted observation as evidence of an actual model citation.
- [`docs/MANUS_SPRINT761_REVIEW.md`](docs/MANUS_SPRINT761_REVIEW.md) - Sprint 7.6.1 review approving synthetic-fixture labeling while requiring an artifact-backed capture before accepting a model observation as genuine.
- [`docs/MANUS_SPRINT762_REVIEW.md`](docs/MANUS_SPRINT762_REVIEW.md) - Sprint 7.6.2 review requiring the preserved transcript itself to prove the observation’s raw answer and capture metadata.
- [`docs/MANUS_SPRINT763_REVIEW.md`](docs/MANUS_SPRINT763_REVIEW.md) - Sprint 7.6.3 review accepting transcript-to-answer binding while requiring capture timestamp and declared operator bindings.
- [`docs/MANUS_SPRINT764_REVIEW.md`](docs/MANUS_SPRINT764_REVIEW.md) - Sprint 7.6.4 approval for an artifact-backed, operator-declared controlled observation.
- [`docs/MANUS_SPRINT8_REVIEW.md`](docs/MANUS_SPRINT8_REVIEW.md) - Sprint 8 review accepting the citation-bearing capture and source retrieval while rejecting the hard-coded comparative artifact.
- [`docs/MANUS_SPRINT81_REVIEW.md`](docs/MANUS_SPRINT81_REVIEW.md) - Sprint 8.1 review accepting ownership/context improvements while rejecting keyword-based semantic support and an incomplete comparative decision digest.
- [`docs/MANUS_SPRINT82_REVIEW.md`](docs/MANUS_SPRINT82_REVIEW.md) - Sprint 8.2 review accepting zero automatic promotion while requiring human-decision evidence/context binding.
- [`docs/MANUS_SPRINT83_REVIEW.md`](docs/MANUS_SPRINT83_REVIEW.md) - Sprint 8.3 review accepting context and quote checks while requiring immutable ledger/snapshot evidence resolution.
- [`src/domain/models.py`](src/domain/models.py) - Typed Pydantic domain contracts (`EvidenceRecord`, `VerificationArtifact`, `ConfidenceScore`, `ClaimRecord`, `AuditRun`).
- [`src/domain/validators.py`](src/domain/validators.py) - Strict evidence ledger validator enforcing zero ungrounded claims.
- [`src/exporter/report.py`](src/exporter/report.py) - Auditable Markdown report generator.
- [`src/cli.py`](src/cli.py) - Internal CLI audit console runner.
