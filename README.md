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
- [`src/domain/models.py`](src/domain/models.py) - Typed Pydantic domain contracts (`EvidenceRecord`, `VerificationArtifact`, `ConfidenceScore`, `ClaimRecord`, `AuditRun`).
- [`src/domain/validators.py`](src/domain/validators.py) - Strict evidence ledger validator enforcing zero ungrounded claims.
- [`src/exporter/report.py`](src/exporter/report.py) - Auditable Markdown report generator.
- [`src/cli.py`](src/cli.py) - Internal CLI audit console runner.
