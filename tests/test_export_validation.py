"""
Unit Tests for Runtime Report Export Evidence Ledger Validation (Strict Rules)
"""

import pytest
from src.domain.enums import SourceType, VerificationStatus
from src.domain.models import AuditRun, ClaimRecord, EvidenceRecord, VerificationArtifact
from src.domain.validators import EvidenceLedgerValidationError
from src.exporter.report import ReportExporter


def make_artifact(quote_match: bool = True) -> VerificationArtifact:
    return VerificationArtifact(
        verifier_run_id="run-test-1",
        verifier_method="DIRECT_HTTP_SNAPSHOT",
        snapshot_sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        quote_exact_match=quote_match,
    )


def test_valid_audit_run_exports_markdown_successfully():
    """Test that an audit run with valid verified evidence exports clean markdown with synthetic banner."""
    ev1 = EvidenceRecord(
        evidence_id="ev-101",
        url="https://g2.com/products/brand-x/reviews",
        opened_excerpt="Brand X has the highest user satisfaction score in 2026.",
        source_type=SourceType.REVIEW_AGGREGATOR,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        verification_artifact=make_artifact(),
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
        is_synthetic_fixture=True,
        evidence_ledger={"ev-101": ev1},
        claims=[claim],
    )

    markdown_report = ReportExporter.export_to_markdown(audit_run)
    assert "SYNTHETIC FIXTURE DATA" in markdown_report
    assert "# 📊 GEO/AEO Evidence-Governed Audit Report" in markdown_report
    assert "Brand X leads user satisfaction" in markdown_report
    assert "https://g2.com/products/brand-x/reviews" in markdown_report
    assert "Snapshot Hash:" in markdown_report


def test_export_fails_when_claim_has_no_evidence_ids():
    """Test that report export is blocked if a claim has empty evidence_ids."""
    with pytest.raises(ValueError):
        ClaimRecord(
            claim_id="claim-ungrounded",
            statement="Competitor Y is losing market share rapidly.",
            evidence_ids=[],  # Min length 1 validation error!
        )


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
    assert "missing from evidence_ledger" in err.message


def test_export_fails_when_evidence_status_is_inaccessible():
    """Test that report export is blocked if linked evidence is not OPENED_VERIFIED."""
    unverified_ev = EvidenceRecord(
        evidence_id="ev-broken",
        url="https://paywalled-news.com/article",
        opened_excerpt="Snippet retrieved from search cache only.",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
        verification_status=VerificationStatus.INACCESSIBLE,
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


def test_export_fails_on_mixed_valid_and_invalid_evidence():
    """STRICT RULE: Test that export FAILS if ANY supporting evidence ID is invalid/missing."""
    valid_ev = EvidenceRecord(
        evidence_id="ev-good",
        url="https://valid-domain.com/article",
        opened_excerpt="Valid opened excerpt from verifiable source.",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        verification_artifact=make_artifact(),
    )

    invalid_ev = EvidenceRecord(
        evidence_id="ev-bad",
        url="https://broken-domain.com/article",
        opened_excerpt="Invalid excerpt with inaccessible status.",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
        verification_status=VerificationStatus.INACCESSIBLE,
    )

    claim = ClaimRecord(
        claim_id="claim-mixed",
        statement="Client leads in market penetration.",
        evidence_ids=["ev-good", "ev-bad"],  # One valid, one invalid!
    )

    audit_run = AuditRun(
        run_id="run-mixed",
        client_domain="client.com",
        category="Enterprise",
        evidence_ledger={"ev-good": valid_ev, "ev-bad": invalid_ev},
        claims=[claim],
    )

    with pytest.raises(EvidenceLedgerValidationError) as exc_info:
        ReportExporter.export_to_markdown(audit_run)

    err = exc_info.value
    assert "claim-mixed" in err.ungrounded_claims
    assert "inaccessible" in err.message.lower()


def test_export_fails_when_opened_verified_lacks_verification_artifact():
    """STRICT RULE: Test that export FAILS if OPENED_VERIFIED evidence lacks a VerificationArtifact."""
    ev_no_artifact = EvidenceRecord(
        evidence_id="ev-no-art",
        url="https://valid-domain.com/article",
        opened_excerpt="Opened excerpt text without verification artifact.",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        verification_artifact=None,  # Missing artifact!
    )

    claim = ClaimRecord(
        claim_id="claim-no-art",
        statement="Client has industry certification.",
        evidence_ids=["ev-no-art"],
    )

    audit_run = AuditRun(
        run_id="run-no-art",
        client_domain="client.com",
        category="Testing",
        evidence_ledger={"ev-no-art": ev_no_artifact},
        claims=[claim],
    )

    with pytest.raises(EvidenceLedgerValidationError) as exc_info:
        ReportExporter.export_to_markdown(audit_run)

    err = exc_info.value
    assert "lacks a VerificationArtifact" in err.message


def test_export_fails_when_counter_evidence_id_is_missing():
    """STRICT RULE: Test that export FAILS if counter-evidence ID is missing or invalid."""
    valid_ev = EvidenceRecord(
        evidence_id="ev-good",
        url="https://valid-domain.com/article",
        opened_excerpt="Valid opened excerpt from verifiable source.",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        verification_artifact=make_artifact(),
    )

    claim = ClaimRecord(
        claim_id="claim-counter-missing",
        statement="Client maintains high retention.",
        evidence_ids=["ev-good"],
        counter_evidence_ids=["ev-missing-counter"],  # Missing!
    )

    audit_run = AuditRun(
        run_id="run-counter",
        client_domain="client.com",
        category="Testing",
        evidence_ledger={"ev-good": valid_ev},
        claims=[claim],
    )

    with pytest.raises(EvidenceLedgerValidationError) as exc_info:
        ReportExporter.export_to_markdown(audit_run)

    err = exc_info.value
    assert "Counter-evidence error" in err.message
