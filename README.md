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
- [`AGENT_CONTEXT.md`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/AGENT_CONTEXT.md) - Active sprint status and system architecture anchor.
- [`PROPOSAL_TO_MANUS.md`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/PROPOSAL_TO_MANUS.md) - Proposal to Manus AI detailing architectural leadership and division of labor.
- [`docs/MANUS_SPRINT1_REVIEW.md`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/docs/MANUS_SPRINT1_REVIEW.md) - Manus Sprint 1 implementation review and quality gate.
- [`src/domain/models.py`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/src/domain/models.py) - Typed Pydantic domain contracts (`EvidenceRecord`, `VerificationArtifact`, `ConfidenceScore`, `ClaimRecord`, `AuditRun`).
- [`src/domain/validators.py`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/src/domain/validators.py) - Strict evidence ledger validator enforcing zero ungrounded claims.
- [`src/exporter/report.py`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/src/exporter/report.py) - Auditable Markdown report generator.
- [`src/cli.py`](file:///Users/benjamin/Desktop/GEO_AEO_AIOS_Platform/src/cli.py) - Internal CLI audit console runner.
