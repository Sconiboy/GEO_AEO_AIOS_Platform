"""
Unit Tests for Manual Answer-Surface Observation Contracts and Pipeline Import (Sprint 4.1 Remediation)
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from src.cli import run_cli_observation
from src.collector.observation_importer import ObservationImporter
from src.collector.query_map_runner import DatasetManifest, ManifestSourceCandidate
from src.domain.enums import HumanApprovalState, QueryIntent, SourceType, VerificationStatus
from src.domain.models import AuditRun, EvidenceRecord, VerificationArtifact
from src.domain.observation import AnswerObservation, CaptureMethod, ExtractedStatement, ExtractionStatus
from src.domain.query_map import CollectionPolicyProfile, QueryMap, SourceScope, TargetQuery


def make_sample_query_map() -> QueryMap:
    return QueryMap(
        query_map_id="qm-obs-test-01",
        entity_name="Python Software Foundation",
        category="Programming Languages",
        target_buyer_persona="Systems Architect",
        policy_profile=CollectionPolicyProfile(
            profile_id="pol-01",
            source_scope=SourceScope(
                scope_id="scope-01",
                allowed_domains=["python.org", "httpbin.org"],
            ),
        ),
        queries=[
            TargetQuery(
                query_id="q-approved",
                text="What is Python core language design philosophy?",
                intent=QueryIntent.INFORMATIONAL_EVALUATION,
                rationale="Evaluates core language principles.",
                approval_state=HumanApprovalState.APPROVED,
            ),
            TargetQuery(
                query_id="q-unapproved",
                text="Unapproved query example",
                intent=QueryIntent.COMMERCIAL_BUYER_INTENT,
                rationale="Unapproved query text.",
                approval_state=HumanApprovalState.PROPOSED,
            ),
        ],
    )


def make_sample_ledger() -> AuditRun:
    art = VerificationArtifact(
        verifier_run_id="verifier-run-001",
        verifier_method="PARSED_VISIBLE_TEXT_BS4",
        snapshot_sha256="3f324f9914742e62cf082861ba03b207282dba781c3349bee9d7c1b5ef8e0bfe",
        quote_exact_match=True,
        final_url="https://httpbin.org/html",
        http_status=200,
        content_type="text/html",
    )
    ev = EvidenceRecord(
        evidence_id="ev-verified-001",
        url="https://httpbin.org/html",
        opened_excerpt="Herman Melville - Moby-Dick",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        verification_artifact=art,
    )
    return AuditRun(
        run_id="run-qm-qm-obs-test-01",
        client_domain="Python Software Foundation",
        category="Programming Languages",
        is_synthetic_fixture=True,
        evidence_ledger={"ev-verified-001": ev},
    )


def test_observation_model_is_frozen_and_immutable():
    """P0 IMMUTABILITY TEST: Test that AnswerObservation and ExtractedStatement are frozen Pydantic models."""
    raw_text = "Python is a high-level, general-purpose programming language."
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    obs = AnswerObservation(
        observation_id="obs-freeze-01",
        query_id="q-approved",
        query_map_id="qm-obs-test-01",
        source_ledger_run_id="run-qm-qm-obs-test-01",
        query_map_sha256="a" * 64,
        manifest_sha256="b" * 64,
        source_ledger_sha256="c" * 64,
        provider_name="Ollama",
        model_identifier="hermes-3-llama-3.1-8b",
        capture_timestamp=datetime.now(timezone.utc),
        capture_method=CaptureMethod.SYNTHETIC_FIXTURE_IMPORT,
        raw_answer_text=raw_text,
        raw_answer_sha256=digest,
    )

    # Attempting to mutate raw_answer_text on a frozen model MUST raise ValidationError
    with pytest.raises(ValidationError):
        obs.raw_answer_text = "Mutated answer text"  # type: ignore


def test_observation_raw_text_hash_mismatch_raises_error():
    """P0 INTEGRITY TEST: Test that raw_answer_sha256 mismatch is rejected by verify_integrity()."""
    raw_text = "Python is a high-level, general-purpose programming language."
    invalid_hash = "0" * 64

    obs = AnswerObservation(
        observation_id="obs-fail-01",
        query_id="q-approved",
        query_map_id="qm-obs-test-01",
        source_ledger_run_id="run-qm-qm-obs-test-01",
        query_map_sha256="a" * 64,
        manifest_sha256="b" * 64,
        source_ledger_sha256="c" * 64,
        provider_name="Ollama",
        model_identifier="hermes-3-llama-3.1-8b",
        capture_timestamp=datetime.now(timezone.utc),
        capture_method=CaptureMethod.SYNTHETIC_FIXTURE_IMPORT,
        raw_answer_text=raw_text,
        raw_answer_sha256=invalid_hash,  # Invalid hash!
    )

    assert obs.verify_integrity() is False

    qm = make_sample_query_map()
    manifest = DatasetManifest(
        manifest_id="m1",
        description="d",
        candidates=[
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://httpbin.org/html",
                candidate_excerpt="Herman Melville - Moby-Dick",
            )
        ],
    )
    ledger = make_sample_ledger()

    with pytest.raises(ValueError, match="Integrity failure"):
        ObservationImporter.import_observation(
            observation=obs, query_map=qm, manifest=manifest, source_ledger=ledger
        )


def test_observation_linked_evidence_must_be_opened_verified():
    """P0 EVIDENCE RULE TEST: Test that linked_evidence_id must reference an OPENED_VERIFIED evidence record."""
    raw_text = "Python is a high-level programming language."
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    qm = make_sample_query_map()
    manifest = DatasetManifest(
        manifest_id="m1",
        description="d",
        candidates=[
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://httpbin.org/html",
                candidate_excerpt="Herman Melville - Moby-Dick",
            )
        ],
    )

    # Ledger has evidence with status INACCESSIBLE
    inaccessible_ev = EvidenceRecord(
        evidence_id="ev-inaccessible-001",
        url="https://example.com",
        opened_excerpt="Some excerpt",
        verification_status=VerificationStatus.INACCESSIBLE,
    )
    ledger = AuditRun(
        run_id="run-qm-qm-obs-test-01",
        client_domain="Python Software Foundation",
        category="Programming Languages",
        evidence_ledger={"ev-inaccessible-001": inaccessible_ev},
    )

    qm_hash = ObservationImporter.compute_artifact_hash(qm.model_dump(mode="json"))
    manifest_hash = ObservationImporter.compute_artifact_hash(manifest.model_dump(mode="json"))
    ledger_hash = ObservationImporter.compute_artifact_hash(ledger.model_dump(mode="json"))

    obs = AnswerObservation(
        observation_id="obs-link-test",
        query_id="q-approved",
        query_map_id=qm.query_map_id,
        source_ledger_run_id=ledger.run_id,
        query_map_sha256=qm_hash,
        manifest_sha256=manifest_hash,
        source_ledger_sha256=ledger_hash,
        provider_name="Ollama",
        model_identifier="hermes-3",
        capture_timestamp=datetime.now(timezone.utc),
        capture_method=CaptureMethod.SYNTHETIC_FIXTURE_IMPORT,
        raw_answer_text=raw_text,
        raw_answer_sha256=digest,
        extracted_statements=[
            ExtractedStatement(
                statement_id="stmt-1",
                text="Extracted text",
                extraction_status=ExtractionStatus.SOURCE_VERIFIED,
                linked_evidence_id="ev-inaccessible-001",  # Linked to INACCESSIBLE evidence!
            )
        ],
    )

    with pytest.raises(ValueError, match="not OPENED_VERIFIED"):
        ObservationImporter.import_observation(
            observation=obs, query_map=qm, manifest=manifest, source_ledger=ledger
        )


def test_observation_unlinked_statements_default_proposed_unverified():
    """P1 TEST: Test that unlinked extracted statements default to PROPOSED_UNVERIFIED."""
    raw_text = "Python is a high-level programming language."
    correct_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    qm = make_sample_query_map()
    manifest = DatasetManifest(
        manifest_id="m1",
        description="d",
        candidates=[
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://httpbin.org/html",
                candidate_excerpt="Herman Melville - Moby-Dick",
            )
        ],
    )
    ledger = make_sample_ledger()

    qm_hash = ObservationImporter.compute_artifact_hash(qm.model_dump(mode="json"))
    manifest_hash = ObservationImporter.compute_artifact_hash(manifest.model_dump(mode="json"))
    ledger_hash = ObservationImporter.compute_artifact_hash(ledger.model_dump(mode="json"))

    obs = AnswerObservation(
        observation_id="obs-stmt-test",
        query_id="q-approved",
        query_map_id=qm.query_map_id,
        source_ledger_run_id=ledger.run_id,
        query_map_sha256=qm_hash,
        manifest_sha256=manifest_hash,
        source_ledger_sha256=ledger_hash,
        provider_name="Ollama",
        model_identifier="hermes-3-llama-3.1-8b",
        capture_timestamp=datetime.now(timezone.utc),
        capture_method=CaptureMethod.SYNTHETIC_FIXTURE_IMPORT,
        raw_answer_text=raw_text,
        raw_answer_sha256=correct_hash,
        extracted_statements=[
            ExtractedStatement(
                statement_id="stmt-1",
                text="Python is high level.",
                extraction_status=ExtractionStatus.SOURCE_VERIFIED,  # Attempting to set SOURCE_VERIFIED without link!
            )
        ],
    )

    imported = ObservationImporter.import_observation(
        observation=obs, query_map=qm, manifest=manifest, source_ledger=ledger
    )

    # Must be reset to PROPOSED_UNVERIFIED because linked_evidence_id was None
    assert imported.extracted_statements[0].extraction_status == ExtractionStatus.PROPOSED_UNVERIFIED


def test_observation_status_escalation_forged_payload_downgraded_to_proposed_unverified():
    """ADVERSARIAL P0 TEST (Sprint 4.2): Test that an input payload containing HUMAN_APPROVED or SOURCE_VERIFIED with valid OPENED_VERIFIED evidence is FORCED to PROPOSED_UNVERIFIED upon import."""
    raw_text = "Python is a high-level, general-purpose programming language."
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    qm = make_sample_query_map()
    manifest = DatasetManifest(
        manifest_id="man-obs-test",
        description="Test manifest",
        candidates=[
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://httpbin.org/html",
                candidate_excerpt="Herman Melville - Moby-Dick",
            )
        ],
    )
    ledger = make_sample_ledger()

    qm_hash = ObservationImporter.compute_artifact_hash(qm.model_dump(mode="json"))
    manifest_hash = ObservationImporter.compute_artifact_hash(manifest.model_dump(mode="json"))
    ledger_hash = ObservationImporter.compute_artifact_hash(ledger.model_dump(mode="json"))

    # Forged input payload attempting to claim HUMAN_APPROVED on statement
    forged_obs = AnswerObservation(
        observation_id="obs-forged-01",
        query_id="q-approved",
        query_map_id=qm.query_map_id,
        source_ledger_run_id=ledger.run_id,
        query_map_sha256=qm_hash,
        manifest_sha256=manifest_hash,
        source_ledger_sha256=ledger_hash,
        provider_name="Ollama",
        model_identifier="hermes-3-llama-3.1-8b",
        capture_timestamp=datetime.now(timezone.utc),
        capture_method=CaptureMethod.SYNTHETIC_FIXTURE_IMPORT,
        raw_answer_text=raw_text,
        raw_answer_sha256=digest,
        extracted_statements=[
            ExtractedStatement(
                statement_id="stmt-forged-1",
                text="Python is high-level.",
                extraction_status=ExtractionStatus.HUMAN_APPROVED,  # FORGED STATUS!
                linked_evidence_id="ev-verified-001",  # Valid OPENED_VERIFIED evidence!
            )
        ],
    )

    imported = ObservationImporter.import_observation(
        observation=forged_obs, query_map=qm, manifest=manifest, source_ledger=ledger
    )

    # STRICT RULE: Must be forcibly downgraded to PROPOSED_UNVERIFIED upon import!
    imported_stmt = imported.extracted_statements[0]
    assert imported_stmt.extraction_status == ExtractionStatus.PROPOSED_UNVERIFIED
    assert imported_stmt.linked_evidence_id == "ev-verified-001"


def test_hermetic_cli_observation_command(tmp_path: Path):
    """P1 HERMETIC CLI TEST: Test CLI observation subcommand with frozen ledger artifact (making ZERO network calls)."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/controlled_dataset_manifest.json")
    ledger_file = Path("data/fixtures/frozen_source_ledger.json")
    obs_file = Path("data/fixtures/sample_observation.json")
    output_file = tmp_path / "observation_record.md"

    exit_code = run_cli_observation(
        query_map_path=qm_file,
        manifest_path=man_file,
        source_ledger_path=ledger_file,
        observation_path=obs_file,
        output_path=output_file,
    )

    assert exit_code == 0
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")
    assert "Answer-Surface Observation Record" in content
    assert "Ollama / Local" in content
    assert "hermes-3-llama-3.1-8b" in content
    assert "Python is a high-level" in content
