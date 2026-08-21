"""
Unit Tests for Human Semantic Decision Artifact and CLI Workflow (Sprint 6.4.1 Remediation)
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from src.cli import run_cli_human_decision
from src.domain.enums import ReconciliationMethod, ReconciliationStatus
from src.domain.human_decision import HumanDecisionRecord, HumanStatementDecision, QuotedEvidencePassage


def test_human_decision_model_integrity_and_timestamp_tampering():
    """P0 TEST: Verify timestamp and reconciliation_method tampering invalidates canonical_digest."""
    qe = QuotedEvidencePassage(
        evidence_id="ev-2968acf27391",
        quoted_passage="Explicit is better than implicit.",
        snapshot_sha256="1e2b8d7404d38ac66e3f685c06490787fdd60391b79c338f20b390901aab899d",
    )
    stmt_dec = HumanStatementDecision(
        decision_id="hdec-stmt-001",
        statement_id="stmt-001",
        decision_status=ReconciliationStatus.SUPPORTED,
        quoted_evidence=[qe],
        auditor_rationale="Explicit human auditor verification rationale.",
        declared_reviewer_identity="Lead Systems Architect",
        decision_timestamp=datetime(2026, 8, 21, 4, 15, 0, tzinfo=timezone.utc),
    )

    digest = HumanDecisionRecord.compute_canonical_digest(
        decision_record_id="hdec-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        decisions=[stmt_dec],
    )

    rec = HumanDecisionRecord(
        decision_record_id="hdec-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        decisions=[stmt_dec],
        canonical_digest=digest,
    )

    assert rec.verify_integrity() is True

    # P0 Tamper check 1: Modifying decision_timestamp MUST fail verify_integrity()
    tampered_time_dec = HumanStatementDecision(
        decision_id="hdec-stmt-001",
        statement_id="stmt-001",
        decision_status=ReconciliationStatus.SUPPORTED,
        quoted_evidence=[qe],
        auditor_rationale="Explicit human auditor verification rationale.",
        declared_reviewer_identity="Lead Systems Architect",
        decision_timestamp=datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc),  # Tampered timestamp
    )
    tampered_time_rec = HumanDecisionRecord(
        decision_record_id="hdec-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        decisions=[tampered_time_dec],
        canonical_digest=digest,  # Original digest
    )
    assert tampered_time_rec.verify_integrity() is False

    # P0 Tamper check 2: Modifying reconciliation_method MUST fail verify_integrity()
    tampered_method_dec = HumanStatementDecision(
        decision_id="hdec-stmt-001",
        statement_id="stmt-001",
        decision_status=ReconciliationStatus.SUPPORTED,
        quoted_evidence=[qe],
        auditor_rationale="Explicit human auditor verification rationale.",
        declared_reviewer_identity="Lead Systems Architect",
        decision_timestamp=datetime(2026, 8, 21, 4, 15, 0, tzinfo=timezone.utc),
        reconciliation_method=ReconciliationMethod.STRUCTURED_LLM_ASSISTED_REVIEW,  # Tampered method
    )
    tampered_method_rec = HumanDecisionRecord(
        decision_record_id="hdec-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        decisions=[tampered_method_dec],
        canonical_digest=digest,  # Original digest
    )
    assert tampered_method_rec.verify_integrity() is False


def test_cli_human_decision_execution(tmp_path: Path):
    """Test successful CLI human-decision execution with valid verbatim quote."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/live_pep20_manifest.json")
    ledger_file = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_file = Path("data/fixtures/emitted_pep20_observation.json")

    output_json = tmp_path / "test_human_decision.json"
    output_md = tmp_path / "test_human_decision_record.md"

    ledger_data = json.loads(ledger_file.read_text(encoding="utf-8"))
    ev_id = list(ledger_data["evidence_ledger"].keys())[0]
    valid_quote = ledger_data["evidence_ledger"][ev_id]["opened_excerpt"]

    exit_code = run_cli_human_decision(
        query_map_path=qm_file,
        manifest_path=man_file,
        source_ledger_path=ledger_file,
        observation_path=obs_file,
        statement_id="stmt-001",
        status_str="supported",
        evidence_ids=[ev_id],
        quotes=[valid_quote],
        rationale="Detailed human auditor verification rationale for statement stmt-001.",
        auditor_identity="Lead Systems Architect & Auditor",
        output_json_path=output_json,
        output_path=output_md,
    )

    assert exit_code == 0
    assert output_json.exists()
    assert output_md.exists()

    rec_obj = HumanDecisionRecord.model_validate_json(output_json.read_bytes())
    assert rec_obj.verify_integrity() is True
    assert rec_obj.decisions[0].decision_status == ReconciliationStatus.SUPPORTED

    md_content = output_md.read_text(encoding="utf-8")
    assert "Human Semantic Decision Record" in md_content
    assert "Declared Reviewer Identity" in md_content
    assert "SUPPORTED" in md_content


def test_cli_human_decision_refuses_fabricated_quote(tmp_path: Path):
    """P0 ADVERSARIAL TEST: Verify CLI rejects fabricated quote string provided in Manus review."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/live_pep20_manifest.json")
    ledger_file = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_file = Path("data/fixtures/emitted_pep20_observation.json")

    ledger_data = json.loads(ledger_file.read_text(encoding="utf-8"))
    ev_id = list(ledger_data["evidence_ledger"].keys())[0]

    # Exact adversarial quote from Manus Sprint 6.4 review
    fabricated_quote = "This fabricated quotation does not occur in the source."

    exit_code = run_cli_human_decision(
        query_map_path=qm_file,
        manifest_path=man_file,
        source_ledger_path=ledger_file,
        observation_path=obs_file,
        statement_id="stmt-001",
        status_str="supported",
        evidence_ids=[ev_id],
        quotes=[fabricated_quote],
        rationale="Attempting to pass fabricated quotation.",
    )

    assert exit_code == 1
