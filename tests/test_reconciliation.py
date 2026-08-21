"""
Unit Tests for Claim Reconciliation Engine and CLI Subcommand (Sprint 5)
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError
from src.cli import run_cli_reconcile
from src.collector.reconciler import ClaimReconciler
from src.domain.enums import ReconciliationMethod, ReconciliationStatus, SourceType, VerificationStatus
from src.domain.models import AuditRun, EvidenceRecord, VerificationArtifact
from src.domain.observation import AnswerObservation, CaptureMethod, ExtractedStatement
from src.domain.reconciliation import ObservationReconciliation, StatementReconciliation


def make_sample_ledger_with_python_evidence() -> AuditRun:
    art = VerificationArtifact(
        verifier_run_id="verifier-run-py-01",
        verifier_method="PARSED_VISIBLE_TEXT_BS4",
        snapshot_sha256="4f" * 32,
        quote_exact_match=True,
        final_url="https://python.org/philosophy",
        http_status=200,
        content_type="text/html",
    )
    ev = EvidenceRecord(
        evidence_id="ev-py-design-01",
        url="https://python.org/philosophy",
        opened_excerpt="Python's design philosophy emphasizes code readability and simplicity.",
        source_type=SourceType.OFFICIAL_DOCUMENTATION,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=False,
        verification_artifact=art,
    )
    return AuditRun(
        run_id="run-qm-qm-python-pub-001",
        client_domain="Python Software Foundation",
        category="Programming Languages",
        is_synthetic_fixture=True,
        evidence_ledger={"ev-py-design-01": ev},
    )


def test_reconciliation_model_is_frozen_and_immutable():
    """Test that StatementReconciliation and ObservationReconciliation are frozen Pydantic models."""
    rec = StatementReconciliation(
        reconciliation_id="rec-001",
        statement_id="stmt-001",
        status=ReconciliationStatus.NOT_ASSESSABLE,
        evaluated_evidence_ids=[],
        semantic_rationale="No relevant opened evidence records exist.",
        reviewer_role="Lead Auditor",
        reconciliation_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
    )

    with pytest.raises(ValidationError):
        rec.semantic_rationale = "Mutated rationale"  # type: ignore


def test_reconciliation_default_not_assessable_for_irrelevant_evidence():
    """Test that irrelevant evidence (e.g. httpbin Moby Dick excerpt) results in NOT_ASSESSABLE."""
    raw_text = "Python is a high-level, general-purpose programming language."
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    art = VerificationArtifact(
        verifier_run_id="v1",
        verifier_method="PARSED_VISIBLE_TEXT_BS4",
        snapshot_sha256="1" * 64,
        quote_exact_match=True,
    )
    ev = EvidenceRecord(
        evidence_id="ev-httpbin-001",
        url="https://httpbin.org/html",
        opened_excerpt="Herman Melville - Moby-Dick",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        verification_artifact=art,
    )
    ledger = AuditRun(
        run_id="run-qm-qm-python-pub-001",
        client_domain="Python",
        category="PL",
        evidence_ledger={"ev-httpbin-001": ev},
    )

    obs = AnswerObservation(
        observation_id="obs-test-01",
        query_id="q-001",
        query_map_id="qm-python-pub-001",
        source_ledger_run_id="run-qm-qm-python-pub-001",
        query_map_sha256="a" * 64,
        manifest_sha256="b" * 64,
        source_ledger_sha256="c" * 64,
        provider_name="Ollama",
        model_identifier="hermes-3",
        capture_timestamp=datetime.now(timezone.utc),
        capture_method=CaptureMethod.SYNTHETIC_FIXTURE_IMPORT,
        raw_answer_text=raw_text,
        raw_answer_sha256=digest,
        extracted_statements=[
            ExtractedStatement(
                statement_id="stmt-pep20",
                text="The Zen of Python (PEP 20) summarizes Python design.",
                linked_evidence_id="ev-httpbin-001",
            )
        ],
    )

    result = ClaimReconciler.reconcile_observation(observation=obs, source_ledger=ledger)

    assert len(result.reconciliations) == 1
    rec = result.reconciliations[0]
    assert rec.status == ReconciliationStatus.NOT_ASSESSABLE
    assert "semantically irrelevant" in rec.semantic_rationale


def test_reconciliation_manual_override_supported_decision():
    """Test manual decision override for SUPPORTED statement with valid OPENED_VERIFIED evidence."""
    raw_text = "Python is a high-level programming language emphasizing readability."
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    ledger = make_sample_ledger_with_python_evidence()

    obs = AnswerObservation(
        observation_id="obs-test-02",
        query_id="q-001",
        query_map_id="qm-python-pub-001",
        source_ledger_run_id=ledger.run_id,
        query_map_sha256="a" * 64,
        manifest_sha256="b" * 64,
        source_ledger_sha256="c" * 64,
        provider_name="Ollama",
        model_identifier="hermes-3",
        capture_timestamp=datetime.now(timezone.utc),
        capture_method=CaptureMethod.SYNTHETIC_FIXTURE_IMPORT,
        raw_answer_text=raw_text,
        raw_answer_sha256=digest,
        extracted_statements=[
            ExtractedStatement(
                statement_id="stmt-py-01",
                text="Python emphasizes readability.",
                linked_evidence_id="ev-py-design-01",
            )
        ],
    )

    manual_rec = StatementReconciliation(
        reconciliation_id="rec-py-01",
        statement_id="stmt-py-01",
        status=ReconciliationStatus.SUPPORTED,
        evaluated_evidence_ids=["ev-py-design-01"],
        semantic_rationale="Official Python documentation explicitly supports that design philosophy emphasizes code readability.",
        reviewer_role="Lead Auditor",
        reconciliation_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
    )

    result = ClaimReconciler.reconcile_observation(
        observation=obs, source_ledger=ledger, manual_reconciliations=[manual_rec]
    )

    assert len(result.reconciliations) == 1
    assert result.reconciliations[0].status == ReconciliationStatus.SUPPORTED
    assert result.reconciliations[0].evaluated_evidence_ids == ["ev-py-design-01"]


def test_cli_reconcile_command_execution(tmp_path: Path):
    """Test CLI reconcile subcommand against authorized first observation and frozen ledger."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/controlled_dataset_manifest.json")
    ledger_file = Path("data/fixtures/frozen_source_ledger.json")
    obs_file = Path("data/fixtures/authorized_first_observation.json")
    output_file = tmp_path / "authorized_first_reconciliation_record.md"

    exit_code = run_cli_reconcile(
        query_map_path=qm_file,
        manifest_path=man_file,
        source_ledger_path=ledger_file,
        observation_path=obs_file,
        output_path=output_file,
    )

    assert exit_code == 0
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")
    assert "Claim Reconciliation Record" in content
    assert "NOT_ASSESSABLE" in content
    assert "Python Software Foundation" in content
