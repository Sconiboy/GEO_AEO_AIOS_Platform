"""
Unit Tests for Runtime Report Export Evidence Ledger Validation
"""

import pytest
from src.domain.enums import SourceType, VerificationStatus
from src.domain.models import AuditRun, ClaimRecord, EvidenceRecord
from src.domain.validators import EvidenceLedgerValidationError
from src.exporter.report import ReportExporter


def test_valid_audit_run_exports_markdown_successfully():
    """Test that an audit run with valid verified evidence exports clean markdown."""
    ev1 = EvidenceRecord(
        evidence_id="ev-101",
        url="https://g2.com/products/brand-x/reviews",
        opened_excerpt="Brand X has the highest user satisfaction score in 2026.",
        source_type=SourceType.REVIEW_AGGREGATOR,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
    )

    claim = ClaimRecord(
        claim_id="claim-1",
        statement="Brand X leads user satisfaction in the category.",
        evidence_ids=["ev-101"],
    )

    audit_run = AuditRun(
        run_id="run-001",
        client_domain="brandx.com",
        category="SEO Software",
        evidence_ledger={"ev-101": ev1},
        claims=[claim],
    )

    markdown_report = ReportExporter.export_to_markdown(audit_run)
    assert "# 📊 GEO/AEO Evidence-Governed Audit Report" in markdown_report
    assert "Brand X leads user satisfaction" in markdown_report
    assert "https://g2.com/products/brand-x/reviews" in markdown_report


def test_export_fails_when_claim_has_no_evidence_ids():
    """Test that report export is blocked if a claim has empty evidence_ids."""
    claim_without_evidence = ClaimRecord(
        claim_id="claim-ungrounded",
        statement="Competitor Y is losing market share rapidly.",
        evidence_ids=[],  # Empty!
    )

    audit_run = AuditRun(
        run_id="run-002",
        client_domain="client.com",
        category="SEO Software",
        evidence_ledger={},
        claims=[claim_without_evidence],
    )

    with pytest.raises(EvidenceLedgerValidationError) as exc_info:
        ReportExporter.export_to_markdown(audit_run)

    err = exc_info.value
    assert "claim-ungrounded" in err.ungrounded_claims
    assert "has zero linked evidence IDs" in err.message


def test_export_fails_when_evidence_id_is_missing_from_ledger():
    """Test that report export is blocked if a claim references a missing evidence ID."""
    claim_with_ghost_evidence = ClaimRecord(
        claim_id="claim-ghost",
        statement="Client domain has 50% higher authority score.",
        evidence_ids=["ev-nonexistent"],
    )

    audit_run = AuditRun(
        run_id="run-003",
        client_domain="client.com",
        category="Analytics",
        evidence_ledger={},
        claims=[claim_with_ghost_evidence],
    )

    with pytest.raises(EvidenceLedgerValidationError) as exc_info:
        ReportExporter.export_to_markdown(audit_run)

    err = exc_info.value
    assert "claim-ghost" in err.ungrounded_claims
    assert "missing from the evidence_ledger" in err.message


def test_export_fails_when_evidence_status_is_inaccessible():
    """Test that report export is blocked if linked evidence is not OPENED_VERIFIED."""
    unverified_ev = EvidenceRecord(
        evidence_id="ev-broken",
        url="https://paywalled-news.com/article",
        opened_excerpt="Snippet retrieved from search cache only.",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
        verification_status=VerificationStatus.INACCESSIBLE,  # Inaccessible!
    )

    claim = ClaimRecord(
        claim_id="claim-paywall",
        statement="Industry analyst ranks client #1 in security.",
        evidence_ids=["ev-broken"],
    )

    audit_run = AuditRun(
        run_id="run-004",
        client_domain="client.com",
        category="Security",
        evidence_ledger={"ev-broken": unverified_ev},
        claims=[claim],
    )

    with pytest.raises(EvidenceLedgerValidationError) as exc_info:
        ReportExporter.export_to_markdown(audit_run)

    err = exc_info.value
    assert "claim-paywall" in err.ungrounded_claims
    assert "inaccessible" in err.message.lower()
