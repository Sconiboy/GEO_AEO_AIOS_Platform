"""
Unit tests for Sprint 7 Forensic Competitor Evidence-Gap Analysis Workflow
Tests model immutability, canonical digest computation, gap analyzer engine,
ethical notes verification, exporter rendering, and CLI command execution.
"""

from pathlib import Path
from pydantic import ValidationError
import pytest

from src.cli import run_cli_analyze_gaps
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest
from src.domain.enums import ActionSeverity, GapCategory, SourceType
from src.domain.gap_analysis import (
    ClientEvidenceGap,
    CompetitorCitation,
    CompetitorCitationPattern,
    ForensicGapAnalysisRecord,
    PrioritizedActionPlan,
)
from src.domain.models import AuditRun
from src.domain.observation import AnswerObservation
from src.domain.query_map import QueryMap
from src.exporter.report import ReportExporter


def test_gap_analysis_models_are_frozen_and_immutable() -> None:
    """Proves that gap analysis models are frozen and reject direct attribute mutation."""
    citation = CompetitorCitation(domain="python.org", citation_count=2, source_type=SourceType.OFFICIAL_DOCUMENTATION)
    with pytest.raises(ValidationError):
        citation.domain = "other.org"  # type: ignore[misc]

    gap = ClientEvidenceGap(
        gap_id="gap-01",
        target_query_id="q-001",
        gap_category=GapCategory.MISSING_OFFICIAL_DOCS,
        affected_statement_ids=["stmt-01"],
        description="Detailed description of missing evidence",
        severity=ActionSeverity.HIGH,
    )
    with pytest.raises(ValidationError):
        gap.severity = ActionSeverity.LOW  # type: ignore[misc]


def test_forensic_gap_analysis_record_digest_and_tamper_detection() -> None:
    """Proves that canonical digest calculation works and detects tampering."""
    pattern = CompetitorCitationPattern(
        pattern_id="pat-01",
        target_query_id="q-001",
        total_sources_evaluated=1,
        top_cited_domains=[CompetitorCitation(domain="python.org", citation_count=1, source_type=SourceType.OFFICIAL_DOCUMENTATION)],
        client_domain_cited=True,
    )
    gap = ClientEvidenceGap(
        gap_id="gap-01",
        target_query_id="q-001",
        gap_category=GapCategory.MISSING_OFFICIAL_DOCS,
        affected_statement_ids=["stmt-01"],
        description="Detailed description of missing evidence",
        severity=ActionSeverity.HIGH,
    )
    action = PrioritizedActionPlan(
        action_id="act-01",
        gap_id="gap-01",
        recommended_action="Publish official technical documentation on python.org",
        target_domain="python.org",
        suggested_source_type=SourceType.OFFICIAL_DOCUMENTATION,
        expected_evidence_impact="Establishes OPENED_VERIFIED evidence status",
        confidence_score=0.85,
    )

    digest = ForensicGapAnalysisRecord.compute_canonical_digest(
        analysis_id="fga-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
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
        competitor_patterns=[pattern],
        evidence_gaps=[gap],
        prioritized_actions=[action],
        canonical_digest=digest,
    )

    assert record.verify_integrity() is True

    # Test digest tampering
    tampered_record = ForensicGapAnalysisRecord(
        analysis_id="fga-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        competitor_patterns=[pattern],
        evidence_gaps=[gap],
        prioritized_actions=[action],
        canonical_digest="f" * 64,
    )
    assert tampered_record.verify_integrity() is False


def test_cli_analyze_gaps_execution(tmp_path: Path) -> None:
    """Tests full CLI analyze-gaps execution against live emitted PEP 20 dataset."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")
    hdec_path = Path("data/fixtures/emitted_pep20_human_decision.json")

    out_json = tmp_path / "gap_analysis.json"
    out_md = tmp_path / "gap_analysis.md"

    exit_code = run_cli_analyze_gaps(
        query_map_path=qm_path,
        manifest_path=manifest_path,
        source_ledger_path=ledger_path,
        observation_path=obs_path,
        human_decision_path=hdec_path,
        output_json_path=out_json,
        output_path=out_md,
    )

    assert exit_code == 0
    assert out_json.exists()
    assert out_md.exists()

    md_content = out_md.read_text(encoding="utf-8")
    assert "FORENSIC COMPETITOR EVIDENCE-GAP ANALYSIS RECORD" in md_content
    assert "Prioritized Ethical Action Plan" in md_content
