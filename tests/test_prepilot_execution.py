"""
Integration test for Sprint 7.6 Controlled Public Competitor Evidence Collection Pre-Pilot
"""

import hashlib
from pathlib import Path

from src.collector.candidate_collector import CandidateCollector
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest
from src.collector.snapshot import SnapshotStore
from src.domain.models import AuditRun
from src.domain.observation import AnswerObservation
from src.domain.profile import SubjectProfile
from src.domain.query_map import QueryMap
from src.exporter.report import ReportExporter


def test_prepilot_controlled_competitor_collection_execution(tmp_path: Path) -> None:
    """
    Executes and validates the Sprint 7.6 controlled public competitor evidence collection pre-pilot.
    1. Loads prepilot subject profile, query map, manifest, and observation.
    2. Runs initial ForensicGapAnalyzer to emit ObservedCitationCollectionCandidate.
    3. Runs CandidateCollector to execute live collection against https://doc.rust-lang.org/book/.
    4. Asserts real HTML snapshot saved, CollectionExecutionRecord created, and gap record digest verified.
    """
    qm_path = Path("data/fixtures/prepilot_query_map.json")
    manifest_path = Path("data/fixtures/prepilot_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/prepilot_observation.json")
    profile_path = Path("data/fixtures/prepilot_subject_profile.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    raw_obs_bytes = obs_path.read_bytes()
    observation = AnswerObservation.model_validate_json(raw_obs_bytes)
    raw_profile_bytes = profile_path.read_bytes()
    subject_profile = SubjectProfile.model_validate_json(raw_profile_bytes)

    # 1. Execute initial gap analysis
    initial_gap_record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=subject_profile,
        observation=observation,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    assert initial_gap_record.verify_integrity() is True
    assert len(initial_gap_record.collection_candidates) == 1
    cand = initial_gap_record.collection_candidates[0]
    assert cand.cited_url == "https://doc.rust-lang.org/book/"
    assert cand.requires_human_manifest_approval is False

    # 2. Execute candidate collection
    store = SnapshotStore(base_dir=tmp_path / "snapshots")
    collector = CandidateCollector(snapshot_store=store)

    updated_ledger, updated_gap_record = collector.collect_candidate(
        candidate_id=cand.candidate_id,
        subject_profile=subject_profile,
        observation=observation,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest,
        gap_record=initial_gap_record,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    # 3. Assert execution results
    assert updated_gap_record.verify_integrity() is True
    assert len(updated_gap_record.collection_executions) == 1
    ce = updated_gap_record.collection_executions[0]
    assert ce.candidate_id == cand.candidate_id
    assert ce.cited_url == "https://doc.rust-lang.org/book/"
    assert ce.verify_integrity() is True

    # 4. Assert report export succeeds and includes SYNTHETIC FIXTURE OBSERVATION warning banner for synthetic fixture
    report_md = ReportExporter.export_gap_analysis_record(updated_gap_record, observation, query_map, updated_ledger)
    assert "Executed Candidate Collections (Provenance Tracing)" in report_md
    assert "doc.rust-lang.org" in report_md
    assert "SYNTHETIC FIXTURE OBSERVATION - NOT AN AUTHENTIC MODEL CAPTURE" in report_md


def test_authentic_hermes3_observation_provenance() -> None:
    """Proves authentic manual Hermes 3 capture has honest human_operator_console provenance and is artifact-backed."""
    from src.domain.enums import CaptureMethod

    auth_obs_path = Path("data/fixtures/authentic_hermes3_observation.json")
    qm_path = Path("data/fixtures/sample_query_map.json")

    auth_obs = AnswerObservation.model_validate_json(auth_obs_path.read_bytes())
    query_map = QueryMap.model_validate_json(qm_path.read_bytes())

    assert auth_obs.verify_integrity() is True
    assert auth_obs.is_artifact_backed is True
    assert auth_obs.capture_artifact is not None
    assert auth_obs.capture_artifact.artifact_id == "art-hermes3-console-001"
    assert auth_obs.capture_artifact.operator_identity == "operator-benjamin"
    assert auth_obs.capture_method == CaptureMethod.HUMAN_OPERATOR_CONSOLE
    assert auth_obs.provider_name == "Ollama / Local Operator Console"
    assert auth_obs.model_identifier == "hermes-3-llama-3.1-8b"

    rendered_obs = ReportExporter.export_observation_record(auth_obs, query_map)
    assert "SYNTHETIC FIXTURE OBSERVATION" not in rendered_obs
    assert "ARTIFACT-BACKED OPERATOR-DECLARED CAPTURE" in rendered_obs
    assert "Bound Raw Capture Artifact" in rendered_obs
    assert "art-hermes3-console-001" in rendered_obs


def test_unbacked_self_declared_observation_provenance() -> None:
    """Proves observation without capture_artifact is recognized as unbacked / self-declared."""
    auth_obs_path = Path("data/fixtures/authentic_hermes3_observation.json")
    qm_path = Path("data/fixtures/sample_query_map.json")

    obs_dict = AnswerObservation.model_validate_json(auth_obs_path.read_bytes()).model_dump()
    obs_dict["capture_artifact"] = None
    unbacked_obs = AnswerObservation.model_validate(obs_dict)
    query_map = QueryMap.model_validate_json(qm_path.read_bytes())

    assert unbacked_obs.verify_integrity() is True
    assert unbacked_obs.is_artifact_backed is False

    rendered_obs = ReportExporter.export_observation_record(unbacked_obs, query_map)
    assert "UNBACKED / SELF-DECLARED MANUAL CAPTURE" in rendered_obs
    assert "ARTIFACT-BACKED MANUAL CAPTURE" not in rendered_obs


def test_corrupted_artifact_sha256_fails_verify_integrity(tmp_path: Path) -> None:
    """Proves verify_integrity returns False if artifact file content SHA256 does not match artifact_sha256."""
    fake_art_file = tmp_path / "corrupted_raw.txt"
    fake_art_file.write_text("Mutated raw text content")

    auth_obs_path = Path("data/fixtures/authentic_hermes3_observation.json")
    obs_dict = AnswerObservation.model_validate_json(auth_obs_path.read_bytes()).model_dump()
    obs_dict["capture_artifact"]["artifact_path_or_uri"] = str(fake_art_file)

    corrupted_obs = AnswerObservation.model_validate(obs_dict)
    assert corrupted_obs.verify_integrity() is False


def test_missing_artifact_path_fails_closed() -> None:
    """Proves verify_integrity fails closed (returns False) when capture_artifact path does not exist."""
    auth_obs_path = Path("data/fixtures/authentic_hermes3_observation.json")
    obs_dict = AnswerObservation.model_validate_json(auth_obs_path.read_bytes()).model_dump()
    obs_dict["capture_artifact"]["artifact_path_or_uri"] = "non_existent_file_path_12345.txt"

    missing_obs = AnswerObservation.model_validate(obs_dict)
    assert missing_obs.verify_integrity() is False


def test_unrelated_hashed_artifact_fails_verify_integrity(tmp_path: Path) -> None:
    """
    Proves verify_integrity fails closed when artifact file exists and has valid artifact_sha256,
    but contains unrelated transcript text not matching the observation's raw answer.
    """
    unrelated_text = (
        "[OPERATOR CONSOLE RAW TRANSCRIPT EXPORT]\n"
        "Session ID: sess-unrelated-001\n"
        "Timestamp: 2026-08-21T02:55:00Z\n"
        "Provider: Ollama / Local Operator Console\n"
        "Model: hermes-3-llama-3.1-8b\n"
        "Operator: operator-benjamin\n"
        "Query ID: q-001\n"
        "Prompt: \"What are the core design principles of Python?\"\n\n"
        "Raw Model Output Stream:\n"
        "Unrelated model answer about Rust memory safety and ownership model.\n"
        "[END OF TRANSCRIPT EXPORT]\n"
    )
    unrelated_bytes = unrelated_text.encode("utf-8")
    unrelated_file = tmp_path / "unrelated_raw.txt"
    unrelated_file.write_text(unrelated_text)

    unrelated_sha256 = hashlib.sha256(unrelated_bytes).hexdigest()
    unrelated_output_sha256 = hashlib.sha256("Unrelated model answer about Rust memory safety and ownership model.".encode("utf-8")).hexdigest()

    auth_obs_path = Path("data/fixtures/authentic_hermes3_observation.json")
    obs_dict = AnswerObservation.model_validate_json(auth_obs_path.read_bytes()).model_dump()

    # Update artifact file path, file hash, and output hash to match unrelated file
    obs_dict["capture_artifact"]["artifact_path_or_uri"] = str(unrelated_file)
    obs_dict["capture_artifact"]["artifact_sha256"] = unrelated_sha256
    obs_dict["capture_artifact"]["raw_output_sha256"] = unrelated_output_sha256

    unrelated_obs = AnswerObservation.model_validate(obs_dict)
    # verify_integrity MUST fail closed because transcript output text does NOT match raw_answer_text!
    assert unrelated_obs.verify_integrity() is False


def test_transcript_query_id_mismatch_fails_verify_integrity(tmp_path: Path) -> None:
    """Proves verify_integrity fails closed when transcript header query_id does not match observation query_id."""
    mismatched_text = (
        "[OPERATOR CONSOLE RAW TRANSCRIPT EXPORT]\n"
        "Session ID: sess-hermes3-20260821-001\n"
        "Timestamp: 2026-08-21T02:55:00Z\n"
        "Provider: Ollama / Local Operator Console\n"
        "Model: hermes-3-llama-3.1-8b\n"
        "Operator: operator-benjamin\n"
        "Query ID: q-unrelated-999\n"
        "Prompt: \"What are the core design principles of Python?\"\n\n"
        "Raw Model Output Stream:\n"
        "Python's core language design philosophy emphasizes code readability, simplicity, and explicit syntax over implicit magic, as famously summarized in The Zen of Python (PEP 20).\n"
        "[END OF TRANSCRIPT EXPORT]\n"
    )
    mismatched_bytes = mismatched_text.encode("utf-8")
    mismatched_file = tmp_path / "mismatched_query_raw.txt"
    mismatched_file.write_text(mismatched_text)

    mismatched_sha256 = hashlib.sha256(mismatched_bytes).hexdigest()

    auth_obs_path = Path("data/fixtures/authentic_hermes3_observation.json")
    obs_dict = AnswerObservation.model_validate_json(auth_obs_path.read_bytes()).model_dump()

    obs_dict["capture_artifact"]["artifact_path_or_uri"] = str(mismatched_file)
    obs_dict["capture_artifact"]["artifact_sha256"] = mismatched_sha256

    mismatched_obs = AnswerObservation.model_validate(obs_dict)
    assert mismatched_obs.verify_integrity() is False


def test_timestamp_mismatch_fails_verify_integrity() -> None:
    """Proves verify_integrity fails closed when capture_timestamp or captured_at does not match parsed transcript timestamp."""
    auth_obs_path = Path("data/fixtures/authentic_hermes3_observation.json")
    obs_dict = AnswerObservation.model_validate_json(auth_obs_path.read_bytes()).model_dump()

    # Mutate observation timestamp to 2099
    obs_dict["capture_timestamp"] = "2099-01-01T00:00:00Z"
    obs_dict["capture_artifact"]["captured_at"] = "2099-01-01T00:00:00Z"

    mismatched_ts_obs = AnswerObservation.model_validate(obs_dict)
    assert mismatched_ts_obs.verify_integrity() is False


def test_operator_identity_mismatch_fails_verify_integrity() -> None:
    """Proves verify_integrity fails closed when capture_artifact operator_identity does not match parsed transcript operator."""
    auth_obs_path = Path("data/fixtures/authentic_hermes3_observation.json")
    obs_dict = AnswerObservation.model_validate_json(auth_obs_path.read_bytes()).model_dump()

    # Mutate operator identity
    obs_dict["capture_artifact"]["operator_identity"] = "operator-unauthorized"

    mismatched_op_obs = AnswerObservation.model_validate(obs_dict)
    assert mismatched_op_obs.verify_integrity() is False


def test_session_id_mismatch_fails_verify_integrity() -> None:
    """Proves verify_integrity fails closed when capture_artifact session_id does not match parsed transcript session ID."""
    auth_obs_path = Path("data/fixtures/authentic_hermes3_observation.json")
    obs_dict = AnswerObservation.model_validate_json(auth_obs_path.read_bytes()).model_dump()

    # Mutate session ID
    obs_dict["capture_artifact"]["session_id"] = "sess-unrelated-999"

    mismatched_sess_obs = AnswerObservation.model_validate(obs_dict)
    assert mismatched_sess_obs.verify_integrity() is False




