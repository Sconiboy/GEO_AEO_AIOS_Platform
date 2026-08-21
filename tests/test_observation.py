"""
Unit Tests for Manual Answer-Surface Observation Contracts and Pipeline Import (Sprint 4)
"""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.cli import run_cli_observation
from src.collector.observation_importer import ObservationImporter
from src.collector.query_map_runner import DatasetManifest, ManifestSourceCandidate, QueryMapRunner
from src.domain.enums import HumanApprovalState, QueryIntent
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


def test_observation_raw_text_hash_mismatch_raises_error():
    """STRICT RULE TEST: Test that modifying raw response text invalidates SHA-256 digest."""
    raw_text = "Python is a high-level, general-purpose programming language."
    correct_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    invalid_hash = "0" * 64

    with pytest.raises(ValueError, match="Integrity failure"):
        AnswerObservation(
            observation_id="obs-fail-01",
            query_id="q-approved",
            query_map_id="qm-obs-test-01",
            source_ledger_run_id="run-qm-qm-obs-test-01",
            provider_name="Ollama",
            model_identifier="hermes-3-llama-3.1-8b",
            capture_method=CaptureMethod.HUMAN_OPERATOR_CONSOLE,
            raw_answer_text=raw_text,
            raw_answer_sha256=invalid_hash,  # Invalid hash!
        )


def test_observation_unapproved_query_rejected():
    """P0 TEST: Test that an observation for an unapproved or proposed query is rejected."""
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

    runner = QueryMapRunner()
    source_ledger = runner.run_query_map_audit(qm, manifest)

    raw_text = "Python is a high-level programming language."
    correct_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    unapproved_obs = AnswerObservation(
        observation_id="obs-unapproved-01",
        query_id="q-unapproved",  # UNAPPROVED query!
        query_map_id="qm-obs-test-01",
        source_ledger_run_id=source_ledger.run_id,
        provider_name="Ollama",
        model_identifier="hermes-3-llama-3.1-8b",
        capture_method=CaptureMethod.HUMAN_OPERATOR_CONSOLE,
        raw_answer_text=raw_text,
        raw_answer_sha256=correct_hash,
    )

    with pytest.raises(ValueError, match="Query is unapproved or missing"):
        ObservationImporter.import_observation(
            observation=unapproved_obs, query_map=qm, source_ledger=source_ledger
        )


def test_observation_unlinked_statements_default_proposed_unverified():
    """P1 TEST: Test that unlinked extracted statements default to PROPOSED_UNVERIFIED."""
    raw_text = "Python is a high-level programming language."
    correct_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    obs = AnswerObservation(
        observation_id="obs-stmt-test",
        query_id="q-approved",
        query_map_id="qm-obs-test-01",
        source_ledger_run_id="run-qm-qm-obs-test-01",
        provider_name="Ollama",
        model_identifier="hermes-3-llama-3.1-8b",
        capture_method=CaptureMethod.HUMAN_OPERATOR_CONSOLE,
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
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.info.return_value = {"Content-Type": "text/html"}
    mock_response.read.return_value = b"<html><body><p>Herman Melville - Moby-Dick</p></body></html>"
    mock_response.__enter__.return_value = mock_response

    runner = QueryMapRunner()
    with patch("urllib.request.build_opener") as mock_build_opener:
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_build_opener.return_value = mock_opener
        source_ledger = runner.run_query_map_audit(qm, manifest)

    imported = ObservationImporter.import_observation(
        observation=obs, query_map=qm, source_ledger=source_ledger
    )

    # Must be reset to PROPOSED_UNVERIFIED because linked_evidence_id was None
    assert imported.extracted_statements[0].extraction_status == ExtractionStatus.PROPOSED_UNVERIFIED


def test_cli_observation_command(tmp_path: Path):
    """Test CLI observation subcommand execution."""
    qm_file = Path("data/fixtures/sample_query_map.json")
    man_file = Path("data/fixtures/controlled_dataset_manifest.json")
    obs_file = Path("data/fixtures/sample_observation.json")
    output_file = tmp_path / "observation_record.md"

    exit_code = run_cli_observation(
        query_map_path=qm_file,
        manifest_path=man_file,
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
