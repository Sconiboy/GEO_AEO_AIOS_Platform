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
    tampered_gap_record = cand_basis.model_copy(update={"collection_candidates": [tampered_cand]})

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
