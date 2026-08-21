"""
Unit Tests for Human Semantic Decision Artifact and CLI Workflow (Sprint 6.4)
"""

import hashlib
import json
from pathlib import Path

import pytest
from src.cli import run_cli_human_decision
from src.domain.enums import ReconciliationStatus
from src.domain.human_decision import HumanDecisionRecord, HumanStatementDecision


def test_human_decision_model_integrity_and_immutability():
    """Test HumanStatementDecision and HumanDecisionRecord model immutability and verify_integrity."""
    stmt_dec = HumanStatementDecision(
        decision_id="hdec-stmt-001",
        statement_id="stmt-001",
        decision_status=ReconciliationStatus.SUPPORTED,
        evaluated_evidence_ids=["ev-2968acf27391"],
        quoted_passages=["Explicit is better than implicit."],
        auditor_rationale="Explicit human auditor verification rationale.",
        auditor_identity="Lead Systems Architect",
    )

    with pytest.raises(Exception):
        stmt_dec.auditor_rationale = "Mutated rationale"  # type: ignore

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

    # Tampering digest fails verify_integrity()
    tampered = HumanDecisionRecord(
        decision_record_id="hdec-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        decisions=[stmt_dec],
        canonical_digest="0" * 64,
    )
    assert tampered.verify_integrity() is False


def test_cli_human_decision_execution(tmp_path: Path):
    """Test CLI human-decision subcommand execution end-to-end."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/live_pep20_manifest.json")
    ledger_file = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_file = Path("data/fixtures/emitted_pep20_observation.json")

    output_json = tmp_path / "test_human_decision.json"
    output_md = tmp_path / "test_human_decision_record.md"

    ledger_data = json.loads(ledger_file.read_text(encoding="utf-8"))
    ev_id = list(ledger_data["evidence_ledger"].keys())[0]

    exit_code = run_cli_human_decision(
        query_map_path=qm_file,
        manifest_path=man_file,
        source_ledger_path=ledger_file,
        observation_path=obs_file,
        statement_id="stmt-001",
        status_str="supported",
        evidence_ids=[ev_id],
        quotes=["Explicit is better than implicit. Simple is better than complex."],
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
    assert "SUPPORTED" in md_content
    assert "Explicit is better than implicit" in md_content


def test_cli_human_decision_refuses_non_existent_statement(tmp_path: Path):
    """P0 ADVERSARIAL TEST: Verify human-decision command rejects non-existent statement_id."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/live_pep20_manifest.json")
    ledger_file = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_file = Path("data/fixtures/emitted_pep20_observation.json")

    ledger_data = json.loads(ledger_file.read_text(encoding="utf-8"))
    ev_id = list(ledger_data["evidence_ledger"].keys())[0]

    exit_code = run_cli_human_decision(
        query_map_path=qm_file,
        manifest_path=man_file,
        source_ledger_path=ledger_file,
        observation_path=obs_file,
        statement_id="stmt-non-existent-999",
        status_str="supported",
        evidence_ids=[ev_id],
        quotes=["Some quote"],
        rationale="Some rationale for non-existent statement.",
    )

    assert exit_code == 1
