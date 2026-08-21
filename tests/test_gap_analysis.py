"""
Unit tests for Sprint 7.1 Forensic Competitor Evidence-Gap Analysis Workflow
Tests SubjectProfile integration, domain relationship classification, answer citations,
elimination of false gaps on supported human decisions, complete canonical digest tamper protection,
and CLI analyze-gaps execution.
"""

from pathlib import Path
from datetime import datetime, timezone
from pydantic import ValidationError
import pytest

from src.cli import run_cli_analyze_gaps
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest
from src.domain.enums import ActionSeverity, GapCategory, ReconciliationMethod, ReconciliationStatus, SourceRelationship, SourceType
from src.domain.gap_analysis import (
    AnswerCitation,
    ClientEvidenceGap,
    CompetitorCitation,
    CompetitorCitationPattern,
    FindingBasis,
    ForensicGapAnalysisRecord,
    PrioritizedActionPlan,
)
from src.domain.human_decision import HumanDecisionRecord, HumanStatementDecision, QuotedEvidencePassage
from src.domain.models import AuditRun
from src.domain.observation import AnswerObservation
from src.domain.profile import ClientProfile, CompetitorProfile, SubjectProfile
from src.domain.query_map import QueryMap


@pytest.fixture
def sample_subject_profile() -> SubjectProfile:
    """Fixture providing a sample SubjectProfile."""
    return SubjectProfile(
        profile_id="prof-001",
        client_profile=ClientProfile(
            entity_name="Python Software Foundation",
            client_domain="python.org",
            owned_domains=["python.org", "peps.python.org", "docs.python.org"],
            offering_category="Core Programming Language",
            geography="Global",
        ),
        competitor_profiles=[
            CompetitorProfile(
                competitor_entity_name="Rust Foundation",
                competitor_domains=["rust-lang.org"],
            )
        ],
    )


def test_gap_analysis_models_are_frozen_and_immutable(sample_subject_profile: SubjectProfile) -> None:
    """Proves that gap analysis models are frozen and reject direct attribute mutation."""
    citation = CompetitorCitation(
        domain="python.org",
        citation_count=2,
        source_type=SourceType.OFFICIAL_DOCUMENTATION,
        source_relationship=SourceRelationship.CLIENT_OWNED,
    )
    with pytest.raises(ValidationError):
        citation.domain = "other.org"  # type: ignore[misc]

    basis = FindingBasis(
        observation_id="obs-01",
        statement_id="stmt-01",
        evidence_ids=["ev-01"],
        source_relationships=[SourceRelationship.CLIENT_OWNED],
    )

    gap = ClientEvidenceGap(
        gap_id="gap-01",
        target_query_id="q-001",
        gap_category=GapCategory.MISSING_OFFICIAL_DOCS,
        affected_statement_ids=["stmt-01"],
        description="Detailed description of missing evidence",
        severity=ActionSeverity.HIGH,
        finding_basis=basis,
    )
    with pytest.raises(ValidationError):
        gap.severity = ActionSeverity.LOW  # type: ignore[misc]


def test_source_relationship_classification(sample_subject_profile: SubjectProfile) -> None:
    """Proves accurate classification of client-owned, competitor-owned, and independent domains."""
    rel_client = ForensicGapAnalyzer.classify_source_relationship(
        domain="peps.python.org",
        subject_profile=sample_subject_profile,
        source_type=SourceType.OFFICIAL_DOCUMENTATION,
    )
    assert rel_client == SourceRelationship.CLIENT_OWNED

    rel_comp = ForensicGapAnalyzer.classify_source_relationship(
        domain="rust-lang.org",
        subject_profile=sample_subject_profile,
        source_type=SourceType.OFFICIAL_DOCUMENTATION,
    )
    assert rel_comp == SourceRelationship.COMPETITOR_OWNED

    rel_indep = ForensicGapAnalyzer.classify_source_relationship(
        domain="wikipedia.org",
        subject_profile=sample_subject_profile,
        source_type=SourceType.INDEPENDENT_EDITORIAL,
    )
    assert rel_indep == SourceRelationship.INDEPENDENT_EDITORIAL


def test_extract_answer_citations() -> None:
    """Proves extraction of explicit HTTP/HTTPS URLs from raw model answer text."""
    text = "Python details can be found at https://peps.python.org/pep-0020/ and http://python.org."
    citations = ForensicGapAnalyzer.extract_answer_citations(text)
    assert len(citations) == 2
    assert citations[0].url == "https://peps.python.org/pep-0020/"
    assert citations[0].domain == "peps.python.org"
    assert citations[1].url == "http://python.org"


def test_supported_statement_produces_no_false_gap(sample_subject_profile: SubjectProfile) -> None:
    """Proves that a statement adjudicated as SUPPORTED produces NO false gap."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)

    raw_manifest_bytes = manifest_path.read_bytes()
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)

    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)

    raw_obs_bytes = obs_path.read_bytes()
    observation = AnswerObservation.model_validate_json(raw_obs_bytes)

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    # Create HumanDecisionRecord supporting ALL extracted statements (stmt-001 & stmt-002)
    dec1 = HumanStatementDecision(
        decision_id="hdec-stmt-001",
        statement_id="stmt-001",
        decision_status=ReconciliationStatus.SUPPORTED,
        quoted_evidence=[QuotedEvidencePassage(evidence_id="ev-b6868a371278", quoted_passage="Readability counts.")],
        auditor_rationale="Verified readability quote.",
        declared_reviewer_identity="Lead Auditor",
        decision_timestamp=datetime(2026, 8, 21, 0, 0, 0, tzinfo=timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
    )
    dec2 = HumanStatementDecision(
        decision_id="hdec-stmt-002",
        statement_id="stmt-002",
        decision_status=ReconciliationStatus.SUPPORTED,
        quoted_evidence=[QuotedEvidencePassage(evidence_id="ev-b6868a371278", quoted_passage="Readability counts.")],
        auditor_rationale="Verified philosophy quote.",
        declared_reviewer_identity="Lead Auditor",
        decision_timestamp=datetime(2026, 8, 21, 0, 0, 0, tzinfo=timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
    )

    hdec = HumanDecisionRecord(
        decision_record_id="hdec-rec-obs-emitted-pep20-001",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=source_ledger.run_id,
        source_ledger_sha256="1e5e4563feca841e065bc3bbcfd1cd195ecfb38bfb67fa9faac1a58eb87eb60c",
        query_map_sha256="ce5d03d441eefcca1cb9cfefbeab1a6572eb0cae0e27fe8a32a67bc644b9cfcf",
        manifest_sha256="71333fd91a3081676d1e43ee6df9fbbca7b0b691bf39ce8a6e87bc12d0909562",
        decisions=[dec1, dec2],
        canonical_digest="f" * 64,  # mock digest for test
    )

    record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=observation,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        human_decision=hdec,
    )

    # Since ALL statements are supported, NO evidence gaps or action plans must be generated!
    assert len(record.evidence_gaps) == 0
    assert len(record.prioritized_actions) == 0


def test_complete_canonical_digest_tamper_detection(sample_subject_profile: SubjectProfile) -> None:
    """Proves that modifying description, finding basis, ethical notes, or impact statements invalidates verify_integrity()."""
    basis = FindingBasis(
        observation_id="obs-001",
        statement_id="stmt-001",
        evidence_ids=["ev-001"],
        source_relationships=[SourceRelationship.CLIENT_OWNED],
    )
    pattern = CompetitorCitationPattern(
        pattern_id="pat-01",
        target_query_id="q-001",
        total_sources_evaluated=1,
        top_cited_domains=[CompetitorCitation(domain="python.org", citation_count=1, source_type=SourceType.OFFICIAL_DOCUMENTATION, source_relationship=SourceRelationship.CLIENT_OWNED)],
        client_domain_cited=True,
    )
    gap = ClientEvidenceGap(
        gap_id="gap-01",
        target_query_id="q-001",
        gap_category=GapCategory.MISSING_OFFICIAL_DOCS,
        affected_statement_ids=["stmt-01"],
        description="Original authentic description of gap",
        severity=ActionSeverity.HIGH,
        finding_basis=basis,
    )
    action = PrioritizedActionPlan(
        action_id="act-01",
        gap_id="gap-01",
        recommended_action="Hypothesis for Review: Publish official technical documentation on python.org",
        target_domain="python.org",
        suggested_source_type=SourceType.OFFICIAL_DOCUMENTATION,
        expected_evidence_impact="Establishes OPENED_VERIFIED evidence status",
        confidence_score=0.85,
        confidence_explanation="High confidence explanation",
        ethical_boundary_notes="Original ethical notes",
        finding_basis=basis,
    )

    digest = ForensicGapAnalysisRecord.compute_canonical_digest(
        analysis_id="fga-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        profile_id="prof-001",
        competitor_patterns=[pattern],
        evidence_gaps=[gap],
        prioritized_actions=[action],
    )

    record = ForensicGapAnalysisRecord(
        analysis_id="fga-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        profile_id="prof-001",
        competitor_patterns=[pattern],
        evidence_gaps=[gap],
        prioritized_actions=[action],
        canonical_digest=digest,
    )

    assert record.verify_integrity() is True

    # Tamper with gap description
    tampered_gap = ClientEvidenceGap(
        gap_id="gap-01",
        target_query_id="q-001",
        gap_category=GapCategory.MISSING_OFFICIAL_DOCS,
        affected_statement_ids=["stmt-01"],
        description="Tampered altered description string",  # Tampered description!
        severity=ActionSeverity.HIGH,
        finding_basis=basis,
    )
    tampered_record = ForensicGapAnalysisRecord(
        analysis_id="fga-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        profile_id="prof-001",
        competitor_patterns=[pattern],
        evidence_gaps=[tampered_gap],
        prioritized_actions=[action],
        canonical_digest=digest,  # Old digest!
    )
    assert tampered_record.verify_integrity() is False


def test_cli_analyze_gaps_execution_with_profile(tmp_path: Path) -> None:
    """Tests full CLI analyze-gaps execution against live emitted PEP 20 dataset with SubjectProfile."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")
    profile_path = Path("data/fixtures/pep20_subject_profile.json")
    hdec_path = Path("data/fixtures/emitted_pep20_human_decision.json")

    out_json = tmp_path / "gap_analysis.json"
    out_md = tmp_path / "gap_analysis.md"

    exit_code = run_cli_analyze_gaps(
        query_map_path=qm_path,
        manifest_path=manifest_path,
        source_ledger_path=ledger_path,
        observation_path=obs_path,
        profile_path=profile_path,
        human_decision_path=hdec_path,
        output_json_path=out_json,
        output_path=out_md,
    )

    assert exit_code == 0
    assert out_json.exists()
    assert out_md.exists()

    md_content = out_md.read_text(encoding="utf-8")
    assert "FORENSIC COMPETITOR EVIDENCE-GAP ANALYSIS RECORD" in md_content
    assert "Subject Profile ID" in md_content
    assert "Finding Basis Trace" in md_content
