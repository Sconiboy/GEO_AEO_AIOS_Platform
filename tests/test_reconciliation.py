"""
Unit Tests for Claim Reconciliation Engine and CLI Subcommand (Sprint 5.1 Remediation)
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError
from src.cli import load_audit_run_from_json, run_cli_reconcile
from src.collector.observation_importer import ObservationImporter
from src.collector.query_map_runner import DatasetManifest
from src.collector.reconciler import ClaimReconciler
from src.domain.enums import (
    QueryIntent,
    ReconciliationMethod,
    ReconciliationStatus,
    SourceType,
    VerificationStatus,
)
from src.domain.models import AuditRun, EvidenceRecord, VerificationArtifact
from src.domain.observation import (
    AnswerObservation,
    CaptureMethod,
    ExtractedStatement,
    ExtractionStatus,
)
from src.domain.query_map import CollectionPolicyProfile, QueryMap, SourceScope, TargetQuery
from src.domain.reconciliation import ObservationReconciliation, StatementReconciliation
from src.exporter.report import ReportExporter


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


def test_reconciliation_raw_ledger_hash_mismatch_raises_error():
    """P0 INTEGRITY TEST: Test that a raw ledger hash mismatch raises ValueError during reconciliation."""
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

    wrong_ledger_bytes = b"wrong ledger content payload"

    obs = AnswerObservation(
        observation_id="obs-test-01",
        query_id="q-001",
        query_map_id="qm-python-pub-001",
        source_ledger_run_id="run-qm-qm-python-pub-001",
        query_map_sha256="a" * 64,
        manifest_sha256="b" * 64,
        source_ledger_sha256="c" * 64,  # Does not match wrong_ledger_bytes!
        provider_name="Ollama",
        model_identifier="hermes-3",
        capture_timestamp=datetime.now(timezone.utc),
        capture_method=CaptureMethod.SYNTHETIC_FIXTURE_IMPORT,
        raw_answer_text=raw_text,
        raw_answer_sha256=digest,
    )

    with pytest.raises(ValueError, match="Artifact mismatch"):
        ClaimReconciler.reconcile_observation(
            observation=obs, source_ledger=ledger, raw_ledger_bytes=wrong_ledger_bytes
        )


def test_reconciliation_canonical_digest_tampering_detected():
    """P0 INTEGRITY TEST: Test that tampering with reconciliation metadata or decisions invalidates verify_integrity()."""
    statement_rec = StatementReconciliation(
        reconciliation_id="rec-001",
        statement_id="stmt-001",
        status=ReconciliationStatus.NOT_ASSESSABLE,
        evaluated_evidence_ids=[],
        semantic_rationale="No relevant opened evidence records exist.",
        reviewer_role="Lead Auditor",
        reconciliation_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
    )

    canonical_digest = ObservationReconciliation.compute_canonical_digest(
        reconciliation_run_id="rec-run-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        reconciliations=[statement_rec],
    )

    rec_run = ObservationReconciliation(
        reconciliation_run_id="rec-run-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        reconciliations=[statement_rec],
        reconciliation_sha256=canonical_digest,
    )

    assert rec_run.verify_integrity() is True

    # Tampered reconciliation digest MUST fail verify_integrity()
    tampered_rec_run = ObservationReconciliation(
        reconciliation_run_id="rec-run-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        reconciliations=[statement_rec],
        reconciliation_sha256="0" * 64,  # Tampered digest!
    )
    assert tampered_rec_run.verify_integrity() is False


def test_exporter_refuses_tampered_reconciliation_record():
    """P0 INTEGRITY TEST: Test that ReportExporter.export_reconciliation_record fails closed on tampered reconciliation."""
    raw_text = "Python is a high-level programming language."
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    qm = QueryMap(
        query_map_id="qm-python-pub-001",
        entity_name="Python Software Foundation",
        category="Programming Languages",
        target_buyer_persona="Systems Architect",
        policy_profile=CollectionPolicyProfile(
            profile_id="p1",
            source_scope=SourceScope(scope_id="s1", allowed_domains=["python.org"]),
        ),
        queries=[
            TargetQuery(
                query_id="q-001",
                text="What is Python core language design philosophy?",
                intent=QueryIntent.INFORMATIONAL_EVALUATION,
                rationale="Test query rationale.",
            )
        ],
    )
    ledger = AuditRun(
        run_id="run-001",
        client_domain="Python",
        category="PL",
    )
    obs = AnswerObservation(
        observation_id="obs-001",
        query_id="q-001",
        query_map_id="qm-python-pub-001",
        source_ledger_run_id="run-001",
        query_map_sha256="a" * 64,
        manifest_sha256="b" * 64,
        source_ledger_sha256="c" * 64,
        provider_name="Ollama",
        model_identifier="hermes-3",
        capture_timestamp=datetime.now(timezone.utc),
        capture_method=CaptureMethod.SYNTHETIC_FIXTURE_IMPORT,
        raw_answer_text=raw_text,
        raw_answer_sha256=digest,
    )

    tampered_rec = ObservationReconciliation(
        reconciliation_run_id="rec-run-001",
        observation_id="obs-001",
        raw_answer_sha256=digest,
        source_ledger_run_id="run-001",
        source_ledger_sha256="c" * 64,
        reconciliations=[],
        reconciliation_sha256="0" * 64,  # Invalid hash!
    )

    with pytest.raises(ValueError, match="Integrity failure"):
        ReportExporter.export_reconciliation_record(
            reconciliation=tampered_rec,
            observation=obs,
            query_map=qm,
            source_ledger=ledger,
        )


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
    ledger_hash = ClaimReconciler.compute_model_hash(ledger.model_dump(mode="json"))

    obs = AnswerObservation(
        observation_id="obs-test-01",
        query_id="q-001",
        query_map_id="qm-python-pub-001",
        source_ledger_run_id="run-qm-qm-python-pub-001",
        query_map_sha256="a" * 64,
        manifest_sha256="b" * 64,
        source_ledger_sha256=ledger_hash,
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
    assert "requires explicit human auditor review" in rec.semantic_rationale
    assert result.verify_integrity() is True


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


def test_cli_reconcile_with_json_persistence_and_loading(tmp_path: Path):
    """P0 TEST: Test that CLI reconcile writes versioned JSON artifact and re-loads it preserving decision state."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/controlled_dataset_manifest.json")
    ledger_file = Path("data/fixtures/frozen_source_ledger.json")
    obs_file = Path("data/fixtures/authorized_first_observation.json")
    output_file = tmp_path / "test_reconciliation_record.md"
    json_file = tmp_path / "test_reconciliation.json"

    # Step 1: Run CLI to persist JSON artifact
    exit_code_1 = run_cli_reconcile(
        query_map_path=qm_file,
        manifest_path=man_file,
        source_ledger_path=ledger_file,
        observation_path=obs_file,
        output_path=output_file,
        reconciliation_json_path=json_file,
    )
    assert exit_code_1 == 0
    assert json_file.exists()

    json_bytes = json_file.read_bytes()
    rec_obj = ObservationReconciliation.model_validate_json(json_bytes)
    assert rec_obj.verify_integrity() is True
    first_timestamp = rec_obj.reconciliations[0].reconciliation_timestamp

    # Step 2: Re-run CLI loading pre-existing JSON artifact
    exit_code_2 = run_cli_reconcile(
        query_map_path=qm_file,
        manifest_path=man_file,
        source_ledger_path=ledger_file,
        observation_path=obs_file,
        output_path=output_file,
        reconciliation_json_path=json_file,
    )
    assert exit_code_2 == 0

    reloaded_obj = ObservationReconciliation.model_validate_json(json_file.read_bytes())
    assert reloaded_obj.verify_integrity() is True
    # Verify original decision timestamp was preserved!
    assert reloaded_obj.reconciliations[0].reconciliation_timestamp == first_timestamp


def test_cli_reconcile_refuses_replayed_mismatched_reconciliation_json(tmp_path: Path):
    """P0 ADVERSARIAL TEST: Test that CLI reconcile rejects loading stored JSON artifact when replayed against unrelated observation or source ledger."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/controlled_dataset_manifest.json")
    original_ledger = Path("data/fixtures/frozen_source_ledger.json")
    original_obs = Path("data/fixtures/authorized_first_observation.json")

    unrelated_ledger = Path("data/fixtures/pep20_source_ledger.json")
    unrelated_obs = Path("data/fixtures/pep20_observation.json")

    # Step 1: Create a valid reconciliation JSON for original_obs & original_ledger
    reconciliation_json = tmp_path / "original_reconciliation.json"
    output_file = tmp_path / "output.md"

    exit_code_1 = run_cli_reconcile(
        query_map_path=qm_file,
        manifest_path=man_file,
        source_ledger_path=original_ledger,
        observation_path=original_obs,
        output_path=output_file,
        reconciliation_json_path=reconciliation_json,
    )
    assert exit_code_1 == 0
    assert reconciliation_json.exists()

    # Step 2: Attempt REPLAY ATTACK by supplying original_reconciliation.json with unrelated_obs & unrelated_ledger
    # Must fail closed with exit code 1!
    exit_code_replay = run_cli_reconcile(
        query_map_path=qm_file,
        manifest_path=man_file,
        source_ledger_path=unrelated_ledger,
        observation_path=unrelated_obs,
        output_path=output_file,
        reconciliation_json_path=reconciliation_json,
    )
    assert exit_code_replay == 1


def test_reconciler_refuses_unsafe_keyword_auto_supported():
    """P0 ADVERSARIAL TEST: Verify that keyword overlaps (e.g. 'Python design' vs 'Beautiful is better than ugly') NEVER auto-evaluates as SUPPORTED."""
    import json
    raw_text = "Python design guarantees that every program is easy to learn."
    raw_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    ledger = load_audit_run_from_json(Path("data/fixtures/emitted_pep20_source_ledger.json"))
    raw_ledger_bytes = Path("data/fixtures/emitted_pep20_source_ledger.json").read_bytes()
    ledger_sha256 = hashlib.sha256(raw_ledger_bytes).hexdigest()
    ev_id = list(ledger.evidence_ledger.keys())[0]

    obs = AnswerObservation(
        observation_id="obs-adv-001",
        query_id="q-001",
        query_map_id="qm-python-pub-001",
        source_ledger_run_id=ledger.run_id,
        query_map_sha256="ce5d03d441eefcca8eef361dc21ad9bff1a0245fea53293bba60022cf6eb4ce6",
        manifest_sha256="71333fd91a308167fac7a2b457f62f07314687d2cf01b8cfedf92d49cc569d0c",
        source_ledger_sha256=ledger_sha256,
        provider_name="Ollama / Local Operator Console",
        model_identifier="hermes-3-llama-3.1-8b",
        capture_timestamp="2026-08-21T04:00:00Z",
        capture_method=CaptureMethod.HUMAN_OPERATOR_CONSOLE,
        raw_answer_text=raw_text,
        raw_answer_sha256=raw_sha256,
        extracted_statements=[
            ExtractedStatement(
                statement_id="stmt-adv-001",
                text="Python design guarantees that every program is easy to learn.",
                extraction_status=ExtractionStatus.PROPOSED_UNVERIFIED,
                linked_evidence_id=ev_id,
            )
        ],
    )

    reconciliation = ClaimReconciler.reconcile_observation(
        observation=obs, source_ledger=ledger, raw_ledger_bytes=raw_ledger_bytes
    )

    # Must default to NOT_ASSESSABLE, NEVER SUPPORTED!
    assert reconciliation.reconciliations[0].status == ReconciliationStatus.NOT_ASSESSABLE
    assert "requires explicit human auditor review" in reconciliation.reconciliations[0].semantic_rationale


def test_observation_importer_validates_exact_manifest_sha256():
    """P0 TEST: Verify ObservationImporter rejects observation with mismatched manifest_sha256 digest."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/controlled_dataset_manifest.json")
    ledger_file = Path("data/fixtures/emitted_pep20_source_ledger.json")

    qm_bytes = qm_file.read_bytes()
    man_bytes = man_file.read_bytes()
    ledger_bytes = ledger_file.read_bytes()

    qm = QueryMap.model_validate_json(qm_bytes)
    man = DatasetManifest.model_validate_json(man_bytes)
    ledger = AuditRun.model_validate_json(ledger_bytes)

    # Supply invalid manifest_sha256 in observation
    obs_file = Path("data/fixtures/emitted_pep20_observation.json")
    obs_dict = json.loads(obs_file.read_text(encoding="utf-8"))
    obs_dict["manifest_sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
    invalid_obs = AnswerObservation.model_validate(obs_dict)

    with pytest.raises(ValueError, match="manifest_sha256"):
        ObservationImporter.import_observation(
            observation=invalid_obs,
            query_map=qm,
            manifest=man,
            source_ledger=ledger,
            raw_qm_bytes=qm_bytes,
            raw_manifest_bytes=man_bytes,
            raw_ledger_bytes=ledger_bytes,
        )



