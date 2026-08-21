"""
Unit and Integration Tests for CandidateCollector Engine (Sprint 7.5)
Verifies execution-time authorization gate, fail-closed policy enforcement,
and candidate evidence collection pipeline.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
import pytest

from src.collector.candidate_collector import CandidateCollector
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest, ManifestSourceCandidate
from src.collector.snapshot import SnapshotStore
from src.domain.enums import (
    AttributionStatus,
    HumanApprovalState,
    SourceRelationship,
    SourceType,
    VerificationStatus,
)
from src.domain.gap_analysis import ForensicGapAnalysisRecord, ObservedCitationCollectionCandidate
from src.domain.models import AuditRun
from src.domain.observation import AnswerObservation
from src.domain.profile import SubjectProfile
from src.domain.query_map import QueryMap


@pytest.fixture
def sample_subject_profile() -> SubjectProfile:
    path = Path("data/fixtures/pep20_subject_profile.json")
    return SubjectProfile.model_validate_json(path.read_bytes())


def test_unauthorized_candidate_collection_fails_closed(
    sample_subject_profile: SubjectProfile,
) -> None:
    """Proves that candidate collection fails closed if candidate.requires_human_manifest_approval is True."""
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
    orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

    # Observation cites https://rust-lang.org (unauthorized candidate!)
    competitor_answer_text = (
        orig_obs.raw_answer_text + "\n\nFor speed comparison, see https://rust-lang.org official documentation."
    )
    competitor_obs = orig_obs.model_copy(
        update={
            "raw_answer_text": competitor_answer_text,
            "raw_answer_sha256": hashlib.sha256(competitor_answer_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    gap_record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    assert len(gap_record.collection_candidates) == 1
    unauthorized_cand = gap_record.collection_candidates[0]
    assert unauthorized_cand.requires_human_manifest_approval is True

    collector = CandidateCollector()

    # Attempt to collect unauthorized candidate MUST raise ValueError!
    with pytest.raises(
        ValueError,
        match="Execution Gate Blocked: Candidate '.*' for URL 'https://rust-lang.org' requires explicit human approval",
    ):
        collector.collect_candidate(
            candidate_id=unauthorized_cand.candidate_id,
            subject_profile=sample_subject_profile,
            observation=competitor_obs,
            source_ledger=source_ledger,
            query_map=query_map,
            manifest=manifest,
            gap_record=gap_record,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_mismatched_query_id_candidate_fails_closed(
    sample_subject_profile: SubjectProfile,
) -> None:
    """Proves candidate collection fails closed if exact candidate URL exists in manifest for a different query_id."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    orig_manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)

    # Add candidate for query q-unrelated
    manifest_other_q = orig_manifest.model_copy(
        update={
            "candidates": orig_manifest.candidates + [
                ManifestSourceCandidate(
                    url="https://rust-lang.org",
                    candidate_excerpt="Rust official site",
                    source_type=SourceType.OFFICIAL_DOCUMENTATION,
                    query_id="q-unrelated-999",
                )
            ]
        }
    )
    auth_manifest_bytes = manifest_other_q.model_dump_json().encode("utf-8")

    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    raw_obs_bytes = obs_path.read_bytes()
    orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

    competitor_answer_text = (
        orig_obs.raw_answer_text + "\n\nFor speed comparison, see https://rust-lang.org official documentation."
    )
    competitor_obs = orig_obs.model_copy(
        update={
            "raw_answer_text": competitor_answer_text,
            "raw_answer_sha256": hashlib.sha256(competitor_answer_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    # Force candidate to have requires_human_manifest_approval=False to test execution-time manifest re-verification
    cand_basis = gap_record_basis = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest_other_q,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=auth_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )
    mismatched_cand = cand_basis.collection_candidates[0]

    # Tamper candidate to set requires_human_manifest_approval=False to test execution gate re-check
    tampered_cand = mismatched_cand.model_copy(update={"requires_human_manifest_approval": False})
    valid_digest = ForensicGapAnalysisRecord.compute_canonical_digest(
        analysis_id=cand_basis.analysis_id,
        observation_id=cand_basis.observation_id,
        raw_answer_sha256=cand_basis.raw_answer_sha256,
        source_ledger_run_id=cand_basis.source_ledger_run_id,
        source_ledger_sha256=cand_basis.source_ledger_sha256,
        query_map_sha256=cand_basis.query_map_sha256,
        manifest_sha256=cand_basis.manifest_sha256,
        profile_id=cand_basis.profile_id,
        profile_sha256=cand_basis.profile_sha256,
        attribution_status=cand_basis.attribution_status,
        competitor_patterns=cand_basis.competitor_patterns,
        collection_candidates=[tampered_cand],
        collection_executions=cand_basis.collection_executions,
        collection_attempts=cand_basis.collection_attempts,
        evidence_gaps=cand_basis.evidence_gaps,
        prioritized_actions=cand_basis.prioritized_actions,
    )
    tampered_gap_record = cand_basis.model_copy(
        update={"collection_candidates": [tampered_cand], "canonical_digest": valid_digest}
    )

    collector = CandidateCollector()

    with pytest.raises(
        ValueError,
        match="Execution Gate Blocked: Exact URL 'https://rust-lang.org' for query 'q-001' is not found in current DatasetManifest",
    ):
        collector.collect_candidate(
            candidate_id=tampered_cand.candidate_id,
            subject_profile=sample_subject_profile,
            observation=competitor_obs,
            source_ledger=source_ledger,
            query_map=query_map,
            manifest=manifest_other_q,
            gap_record=tampered_gap_record,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=auth_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_authorized_candidate_collection_success(
    sample_subject_profile: SubjectProfile,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proves that an execution-time authorized competitor candidate is fetched by verifier and added to source ledger."""
    from src.collector.verifier import SourceVerifier
    from src.domain.models import EvidenceRecord, VerificationArtifact

    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    orig_manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)

    # Authorize https://rust-lang.org/learn for query q-001 in manifest
    authorized_manifest = orig_manifest.model_copy(
        update={
            "candidates": orig_manifest.candidates + [
                ManifestSourceCandidate(
                    url="https://rust-lang.org/learn",
                    candidate_excerpt="Rust is a language empowering everyone to build reliable software.",
                    source_type=SourceType.OFFICIAL_DOCUMENTATION,
                    query_id="q-001",
                )
            ]
        }
    )
    auth_manifest_bytes = authorized_manifest.model_dump_json().encode("utf-8")

    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    raw_obs_bytes = obs_path.read_bytes()
    orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

    # Answer cites unverified competitor URL https://rust-lang.org/learn
    competitor_answer_text = (
        orig_obs.raw_answer_text + "\n\nLearn Rust at https://rust-lang.org/learn."
    )
    competitor_obs = orig_obs.model_copy(
        update={
            "raw_answer_text": competitor_answer_text,
            "raw_answer_sha256": hashlib.sha256(competitor_answer_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    # Generate initial gap record
    initial_gap_record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=authorized_manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=auth_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    # Initial gap record should have candidate with requires_human_manifest_approval=False
    assert len(initial_gap_record.collection_candidates) == 1
    cand = initial_gap_record.collection_candidates[0]
    assert cand.requires_human_manifest_approval is False
    assert cand.cited_url == "https://rust-lang.org/learn"

    # Monkeypatch SourceVerifier.verify_url to mock successful verifier snapshot
    def mock_verify_url(self: SourceVerifier, url: str, candidate_excerpt: str, source_type: SourceType, is_independent: bool = False) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id="ev-rust-learn-collected",
            url=url,
            opened_excerpt=candidate_excerpt,
            verification_status=VerificationStatus.OPENED_VERIFIED,
            source_type=source_type,
            is_independent=is_independent,
            retrieval_timestamp=datetime(2026, 8, 21, 0, 0, 0, tzinfo=timezone.utc),
            verification_artifact=VerificationArtifact(
                verifier_run_id="run-test-collect",
                verifier_method="DIRECT_HTTP_SNAPSHOT",
                snapshot_sha256="c" * 64,
                quote_exact_match=True,
            ),
        )

    monkeypatch.setattr(SourceVerifier, "verify_url", mock_verify_url)

    # Execute CandidateCollector
    store = SnapshotStore(base_dir=tmp_path / "snapshots")
    collector = CandidateCollector(snapshot_store=store)

    updated_ledger, updated_gap_record = collector.collect_candidate(
        candidate_id=cand.candidate_id,
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=authorized_manifest,
        gap_record=initial_gap_record,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=auth_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    # Verify updated ledger contains newly collected EvidenceRecord!
    new_ev_records = [
        ev for ev in updated_ledger.evidence_ledger.values()
        if ev.url == "https://rust-lang.org/learn" and ev.verification_status == VerificationStatus.OPENED_VERIFIED
    ]
    assert len(new_ev_records) == 1
    new_ev = new_ev_records[0]
    assert new_ev.verification_artifact is not None
    assert new_ev.verification_artifact.snapshot_sha256 == "c" * 64

    # Verify updated gap record digest passes verification
    assert updated_gap_record.verify_integrity() is True


def test_tampered_or_mismatched_gap_record_fails_closed(
    sample_subject_profile: SubjectProfile,
) -> None:
    """Proves candidate collection fails closed if gap_record fails verify_integrity() or has context binding mismatches."""
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

    gap_record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=observation,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    collector = CandidateCollector()

    # 1. Tamper gap_record digest -> fails integrity verification
    tampered_gap_record = gap_record.model_copy(update={"canonical_digest": "0" * 64})
    with pytest.raises(ValueError, match="failed canonical digest integrity verification"):
        collector.collect_candidate(
            candidate_id="occ-q-001-fake",
            subject_profile=sample_subject_profile,
            observation=observation,
            source_ledger=source_ledger,
            query_map=query_map,
            manifest=manifest,
            gap_record=tampered_gap_record,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )

    # 2. Context binding mismatch (mismatched profile_id)
    mismatched_gap_record = gap_record.model_copy(update={"profile_id": "prof-OTHER"})
    # Fix digest to bypass gate 0a so gate 0b catches context mismatch
    valid_digest_for_mismatch = ForensicGapAnalysisRecord.compute_canonical_digest(
        analysis_id=gap_record.analysis_id,
        observation_id=gap_record.observation_id,
        raw_answer_sha256=gap_record.raw_answer_sha256,
        source_ledger_run_id=gap_record.source_ledger_run_id,
        source_ledger_sha256=gap_record.source_ledger_sha256,
        query_map_sha256=gap_record.query_map_sha256,
        manifest_sha256=gap_record.manifest_sha256,
        profile_id="prof-OTHER",
        profile_sha256=gap_record.profile_sha256,
        attribution_status=gap_record.attribution_status,
        competitor_patterns=gap_record.competitor_patterns,
        collection_candidates=gap_record.collection_candidates,
        collection_executions=gap_record.collection_executions,
        collection_attempts=gap_record.collection_attempts,
        evidence_gaps=gap_record.evidence_gaps,
        prioritized_actions=gap_record.prioritized_actions,
    )
    mismatched_gap_record = mismatched_gap_record.model_copy(update={"canonical_digest": valid_digest_for_mismatch})

    with pytest.raises(ValueError, match="Context mismatch: gap_record.profile_id"):
        collector.collect_candidate(
            candidate_id="occ-q-001-fake",
            subject_profile=sample_subject_profile,
            observation=observation,
            source_ledger=source_ledger,
            query_map=query_map,
            manifest=manifest,
            gap_record=mismatched_gap_record,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_failed_candidate_collection_creates_attempt_record_not_execution(
    sample_subject_profile: SubjectProfile,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Proves that when SourceVerifier returns a non-success status (e.g. INACCESSIBLE):
    1. A CollectionAttemptRecord is created capturing verification_status, failure_category, and failure_reason.
    2. NO CollectionExecutionRecord is created.
    3. No dummy snapshot_sha256="unknown" is stored in execution provenance.
    4. ForensicGapAnalysisRecord digest passes verification.
    """
    from src.collector.verifier import SourceVerifier
    from src.domain.enums import FailureCategory
    from src.domain.models import EvidenceRecord

    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    orig_manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)

    # Authorize https://rust-lang.org/learn for query q-001 in manifest
    authorized_manifest = orig_manifest.model_copy(
        update={
            "candidates": orig_manifest.candidates + [
                ManifestSourceCandidate(
                    url="https://rust-lang.org/learn",
                    candidate_excerpt="Rust is a language empowering everyone to build reliable software.",
                    source_type=SourceType.OFFICIAL_DOCUMENTATION,
                    query_id="q-001",
                )
            ]
        }
    )
    auth_manifest_bytes = authorized_manifest.model_dump_json().encode("utf-8")

    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    raw_obs_bytes = obs_path.read_bytes()
    orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

    # Answer cites unverified competitor URL https://rust-lang.org/learn
    competitor_answer_text = (
        orig_obs.raw_answer_text + "\n\nLearn Rust at https://rust-lang.org/learn."
    )
    competitor_obs = orig_obs.model_copy(
        update={
            "raw_answer_text": competitor_answer_text,
            "raw_answer_sha256": hashlib.sha256(competitor_answer_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    initial_gap_record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=authorized_manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=auth_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    cand = initial_gap_record.collection_candidates[0]

    # Monkeypatch SourceVerifier.verify_url to simulate HTTP 404 INACCESSIBLE failure
    def mock_verify_url_failed(self: SourceVerifier, url: str, candidate_excerpt: str, source_type: SourceType, is_independent: bool = False) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id="ev-rust-learn-failed",
            url=url,
            opened_excerpt=candidate_excerpt,
            verification_status=VerificationStatus.INACCESSIBLE,
            failure_category=FailureCategory.HTTP_STATUS_ERROR,
            failure_reason="HTTP 404 Not Found",
            source_type=source_type,
            is_independent=is_independent,
            retrieval_timestamp=datetime(2026, 8, 21, 0, 0, 0, tzinfo=timezone.utc),
            verification_artifact=None,
        )

    monkeypatch.setattr(SourceVerifier, "verify_url", mock_verify_url_failed)

    store = SnapshotStore(base_dir=tmp_path / "snapshots")
    collector = CandidateCollector(snapshot_store=store)

    updated_ledger, updated_gap_record = collector.collect_candidate(
        candidate_id=cand.candidate_id,
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=authorized_manifest,
        gap_record=initial_gap_record,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=auth_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    # 1. Assert NO CollectionExecutionRecord was created
    assert len(updated_gap_record.collection_executions) == 0

    # 2. Assert CollectionAttemptRecord WAS created
    assert len(updated_gap_record.collection_attempts) == 1
    attempt = updated_gap_record.collection_attempts[0]
    assert attempt.candidate_id == cand.candidate_id
    assert attempt.cited_url == "https://rust-lang.org/learn"
    assert attempt.verification_status == VerificationStatus.INACCESSIBLE
    assert attempt.failure_category == FailureCategory.HTTP_STATUS_ERROR
    assert attempt.failure_reason == "HTTP 404 Not Found"
    assert attempt.verify_integrity() is True

    # 3. Assert updated gap record canonical digest passes verification
    assert updated_gap_record.verify_integrity() is True


def test_non_mocked_real_http_candidate_collection(
    sample_subject_profile: SubjectProfile,
    tmp_path: Path,
) -> None:
    """
    Non-mocked integration test: Spins up local HTTP server thread, executes CandidateCollector
    with REAL SourceVerifier and SnapshotStore (NO MONKEYPATCHING!), verifies HTML snapshot saved on disk,
    proves EvidenceRecord + CollectionExecutionRecord generated and 7 upstream context bindings verified.
    """
    import threading
    import typing
    from http.server import BaseHTTPRequestHandler, HTTPServer

    # 1. Local HTTP server handler
    class TestHTTPHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (
                "<!DOCTYPE html><html><body>"
                "<h1>Rust Official Documentation</h1>"
                "<p>Rust is a language empowering everyone to build reliable and efficient software.</p>"
                "</body></html>"
            )
            self.wfile.write(html.encode("utf-8"))

        def log_message(self, format: str, *args: typing.Any) -> None:
            pass  # Suppress HTTP server output in test runner

    server = HTTPServer(("127.0.0.1", 0), TestHTTPHandler)
    port = server.server_address[1]
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    try:
        url = f"http://127.0.0.1:{port}/learn"

        qm_path = Path("data/fixtures/sample_query_map.json")
        manifest_path = Path("data/fixtures/live_pep20_manifest.json")
        ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
        obs_path = Path("data/fixtures/emitted_pep20_observation.json")

        raw_qm_bytes = qm_path.read_bytes()
        orig_qm = QueryMap.model_validate_json(raw_qm_bytes)
        # Update QueryMap policy to allow HTTP scheme and 127.0.0.1 domain for local test
        updated_qm = orig_qm.model_copy(
            update={
                "policy_profile": orig_qm.policy_profile.model_copy(
                    update={
                        "allowed_schemes": {"http", "https"},
                        "source_scope": orig_qm.policy_profile.source_scope.model_copy(
                            update={"allowed_domains": orig_qm.policy_profile.source_scope.allowed_domains + ["127.0.0.1"]}
                        ),
                    }
                )
            }
        )
        raw_qm_bytes = updated_qm.model_dump_json().encode("utf-8")

        raw_manifest_bytes = manifest_path.read_bytes()
        orig_manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)

        # Authorize local HTTP candidate URL for query q-001
        authorized_manifest = orig_manifest.model_copy(
            update={
                "candidates": orig_manifest.candidates + [
                    ManifestSourceCandidate(
                        url=url,
                        candidate_excerpt="Rust is a language empowering everyone to build reliable and efficient software.",
                        source_type=SourceType.OFFICIAL_DOCUMENTATION,
                        query_id="q-001",
                    )
                ]
            }
        )
        raw_manifest_bytes = authorized_manifest.model_dump_json().encode("utf-8")

        # Update subject profile to include 127.0.0.1 as a competitor domain
        from src.domain.profile import CompetitorProfile
        competitor_profile = CompetitorProfile(
            competitor_entity_name="Rust Foundation",
            competitor_domains=["rust-lang.org", "127.0.0.1"],
        )
        updated_profile = sample_subject_profile.model_copy(
            update={"competitor_profiles": [competitor_profile]}
        )
        raw_profile_bytes = updated_profile.model_dump_json().encode("utf-8")

        raw_ledger_bytes = ledger_path.read_bytes()
        source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
        raw_obs_bytes = obs_path.read_bytes()
        orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

        # Answer cites local test URL
        competitor_answer_text = orig_obs.raw_answer_text + f"\n\nLearn Rust at {url}."
        competitor_obs = orig_obs.model_copy(
            update={
                "raw_answer_text": competitor_answer_text,
                "raw_answer_sha256": hashlib.sha256(competitor_answer_text.encode("utf-8")).hexdigest(),
            }
        )

        initial_gap_record = ForensicGapAnalyzer.analyze_gaps(
            subject_profile=updated_profile,
            observation=competitor_obs,
            source_ledger=source_ledger,
            query_map=updated_qm,
            manifest=authorized_manifest,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )

        assert len(initial_gap_record.collection_candidates) == 1
        cand = initial_gap_record.collection_candidates[0]
        assert cand.requires_human_manifest_approval is False

        # Execute candidate collector through REAL verifier and REAL snapshot store (NO MOCKS!)
        store = SnapshotStore(base_dir=tmp_path / "snapshots")
        collector = CandidateCollector(snapshot_store=store, block_private_ips=False)

        updated_ledger, updated_gap_record = collector.collect_candidate(
            candidate_id=cand.candidate_id,
            subject_profile=updated_profile,
            observation=competitor_obs,
            source_ledger=source_ledger,
            query_map=updated_qm,
            manifest=authorized_manifest,
            gap_record=initial_gap_record,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )

        # 1. Assert real evidence record created in updated ledger
        new_ev_records = [
            ev for ev in updated_ledger.evidence_ledger.values()
            if ev.url.lower().rstrip("/") == url.lower().rstrip("/") and ev.verification_status == VerificationStatus.OPENED_VERIFIED
        ]
        assert len(new_ev_records) == 1
        new_ev = new_ev_records[0]
        assert new_ev.verification_artifact is not None
        snap_hash = new_ev.verification_artifact.snapshot_sha256

        # 2. Assert snapshot file was ACTUALLY written to disk in SnapshotStore
        saved_snapshot_bytes = store.load_snapshot(snap_hash)
        assert saved_snapshot_bytes is not None
        assert b"Rust is a language empowering everyone to build reliable and efficient software." in saved_snapshot_bytes

        # 3. Assert CollectionExecutionRecord was generated and binds all 7 context SHA-256 digests
        assert len(updated_gap_record.collection_executions) == 1
        ce = updated_gap_record.collection_executions[0]
        assert ce.candidate_id == cand.candidate_id
        assert ce.observation_id == competitor_obs.observation_id
        assert ce.raw_answer_sha256 == competitor_obs.raw_answer_sha256
        assert ce.evidence_id == new_ev.evidence_id
        assert ce.snapshot_sha256 == snap_hash
        assert ce.verify_integrity() is True

        # 4. Assert updated gap record digest passes verification
        assert updated_gap_record.verify_integrity() is True

    finally:
        server.shutdown()
        server.server_close()
