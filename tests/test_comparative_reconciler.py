"""
Unit and Adversarial Tests for ComparativeEvidenceReconciler & Sprint 8.5.2 Workflow
Includes full 13-point adversarial test matrix defending every quote and collection execution binding.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import pytest
from pydantic import ValidationError

from src.collector.candidate_collector import CandidateCollector
from src.collector.comparative_reconciler import ComparativeEvidenceReconciler
from src.collector.execution_registry import CollectorExecutionRegistry
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest
from src.collector.snapshot import SnapshotStore
from src.domain.candidate_collection import CollectionExecutionRecord
from src.domain.comparative import ComparativeEvidenceRecord
from src.domain.enums import ReconciliationMethod, ReconciliationStatus, SourceRelationship, VerificationStatus
from src.domain.gap_analysis import FindingBasis, ForensicGapAnalysisRecord, ObservedCitationCollectionCandidate
from src.domain.human_decision import HumanDecisionRecord, HumanStatementDecision, QuotedEvidencePassage
from src.domain.models import AuditRun, EvidenceRecord, VerificationArtifact
from src.domain.observation import AnswerObservation
from src.domain.profile import SubjectProfile
from src.domain.query_map import QueryMap
from src.exporter.report import ReportExporter


def _with_authorized_execution_candidates(
    gap_record: ForensicGapAnalysisRecord,
) -> ForensicGapAnalysisRecord:
    """Adds test-only authorized candidates and recomputes the immutable gap record."""
    candidates = list(gap_record.collection_candidates)
    known_ids = {candidate.candidate_id for candidate in candidates}
    for execution in gap_record.collection_executions:
        if execution.candidate_id in known_ids:
            continue
        parsed_url = urlparse(execution.cited_url)
        candidates.append(
            ObservedCitationCollectionCandidate(
                candidate_id=execution.candidate_id,
                target_query_id=execution.target_query_id,
                cited_url=execution.cited_url,
                cited_domain=parsed_url.hostname or execution.cited_url,
                source_relationship=SourceRelationship.UNKNOWN,
                matched_manifest_query_id=execution.target_query_id,
                requires_human_manifest_approval=False,
                finding_basis=FindingBasis(
                    observation_id=gap_record.observation_id,
                    statement_id="stmt-001",
                    evidence_ids=[execution.evidence_id],
                    source_relationships=[SourceRelationship.UNKNOWN],
                ),
                action_hypothesis="Test-only authorized candidate retained for execution provenance validation.",
            )
        )
        known_ids.add(execution.candidate_id)
    digest = gap_record.compute_canonical_digest(
        analysis_id=gap_record.analysis_id,
        observation_id=gap_record.observation_id,
        raw_answer_sha256=gap_record.raw_answer_sha256,
        source_ledger_run_id=gap_record.source_ledger_run_id,
        source_ledger_sha256=gap_record.source_ledger_sha256,
        query_map_sha256=gap_record.query_map_sha256,
        manifest_sha256=gap_record.manifest_sha256,
        profile_id=gap_record.profile_id,
        profile_sha256=gap_record.profile_sha256,
        attribution_status=gap_record.attribution_status,
        competitor_patterns=gap_record.competitor_patterns,
        collection_candidates=candidates,
        collection_executions=gap_record.collection_executions,
        collection_attempts=gap_record.collection_attempts,
        evidence_gaps=gap_record.evidence_gaps,
        prioritized_actions=gap_record.prioritized_actions,
    )
    return gap_record.model_copy(
        update={"collection_candidates": candidates, "canonical_digest": digest}
    )


def test_comparative_evidence_reconciler_execution() -> None:
    """Proves ComparativeEvidenceReconciler parses raw_ledger_bytes and creates a valid comparative record."""
    obs_path = Path("data/fixtures/competitor_cited_observation.json")
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/prepilot_manifest.json")
    profile_path = Path("data/fixtures/prepilot_subject_profile.json")

    raw_qm_bytes = qm_path.read_bytes()
    raw_manifest_bytes = manifest_path.read_bytes()
    raw_profile_bytes = profile_path.read_bytes()

    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
    profile = SubjectProfile.model_validate_json(raw_profile_bytes)
    observation = AnswerObservation.model_validate_json(obs_path.read_bytes())

    assert observation.verify_integrity() is True

    client_art = VerificationArtifact(
        verifier_run_id="vrun-client-001",
        verification_timestamp=datetime.now(timezone.utc),
        verifier_method="PARSED_VISIBLE_TEXT_BS4",
        snapshot_sha256=hashlib.sha256(b"client snapshot bytes").hexdigest(),
        quote_exact_match=True,
        final_url="https://peps.python.org/pep-0020/",
        http_status=200,
        content_type="text/html",
        content_length_bytes=1200,
        retrieval_duration_ms=45.0,
    )

    comp_art = VerificationArtifact(
        verifier_run_id="vrun-comp-001",
        verification_timestamp=datetime.now(timezone.utc),
        verifier_method="PARSED_VISIBLE_TEXT_BS4",
        snapshot_sha256=hashlib.sha256(b"competitor snapshot bytes").hexdigest(),
        quote_exact_match=True,
        final_url="https://doc.rust-lang.org/book/",
        http_status=200,
        content_type="text/html",
        content_length_bytes=1500,
        retrieval_duration_ms=50.0,
    )

    client_evidence = EvidenceRecord(
        evidence_id="ev-client-pep20",
        url="https://peps.python.org/pep-0020/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=False,
        opened_excerpt="Beautiful is better than ugly. Explicit is better than implicit. Simple is better than complex.",
        verification_artifact=client_art,
        snapshot_id=f"snap-{client_art.snapshot_sha256[:16]}",
    )

    comp_evidence = EvidenceRecord(
        evidence_id="ev-comp-rustbook",
        url="https://doc.rust-lang.org/book/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        opened_excerpt="The Rust Programming Language",
        verification_artifact=comp_art,
        snapshot_id=f"snap-{comp_art.snapshot_sha256[:16]}",
    )

    ledger = AuditRun(
        run_id="run-test-comp-001",
        client_domain=profile.client_profile.client_domain,
        category="python_programming",
        evidence_ledger={
            client_evidence.evidence_id: client_evidence,
            comp_evidence.evidence_id: comp_evidence,
        },
    )
    raw_ledger_bytes = ledger.model_dump_json().encode("utf-8")

    now = datetime.now(timezone.utc)
    c_exec_dig = CollectionExecutionRecord.compute_canonical_digest(
        execution_id="exec-client-001",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_art.verifier_run_id,
        snapshot_sha256=client_art.snapshot_sha256,
        execution_timestamp=now,
    )
    comp_exec_dig = CollectionExecutionRecord.compute_canonical_digest(
        execution_id="exec-comp-001",
        candidate_id="cand-comp-001",
        target_query_id="q-001",
        cited_url=comp_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=comp_evidence.evidence_id,
        verifier_run_id=comp_art.verifier_run_id,
        snapshot_sha256=comp_art.snapshot_sha256,
        execution_timestamp=now,
    )
    exec_records = [
        CollectionExecutionRecord(
            execution_id="exec-client-001",
            candidate_id="cand-client-001",
            target_query_id="q-001",
            cited_url=client_evidence.url,
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            profile_id=profile.profile_id,
            profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
            manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
            query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
            source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
            evidence_id=client_evidence.evidence_id,
            verifier_run_id=client_art.verifier_run_id,
            snapshot_sha256=client_art.snapshot_sha256,
            execution_timestamp=now,
            canonical_digest=c_exec_dig,
        ),
        CollectionExecutionRecord(
            execution_id="exec-comp-001",
            candidate_id="cand-comp-001",
            target_query_id="q-001",
            cited_url=comp_evidence.url,
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            profile_id=profile.profile_id,
            profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
            manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
            query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
            source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
            evidence_id=comp_evidence.evidence_id,
            verifier_run_id=comp_art.verifier_run_id,
            snapshot_sha256=comp_art.snapshot_sha256,
            execution_timestamp=now,
            canonical_digest=comp_exec_dig,
        ),
    ]

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=exec_records,
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    reconciler = ComparativeEvidenceReconciler()
    record = reconciler.compare_evidence(
        observation=observation,
        query_map=query_map,
        gap_record=gap_record,
        profile=profile,
        client_evidence_id=client_evidence.evidence_id,
        competitor_evidence_id=comp_evidence.evidence_id,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    assert record.observation_id == observation.observation_id
    assert record.query_id == "q-001"
    assert record.client_evidence.domain == "peps.python.org"
    assert record.competitor_evidence.domain == "doc.rust-lang.org"
    assert record.verify_integrity() is True
    assert record.human_review_required is True

    # Zero keyword auto-support: status defaults to CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert record.client_claim_assessments[0].assessment_status == ReconciliationStatus.CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW

    report_md = ReportExporter.export_comparative_analysis_record(record, query_map)
    assert "Bounded Comparative Evidence Analysis" in report_md
    assert "Content-Addressed 9-Hash Artifact Bindings" in report_md
    assert "https://peps.python.org/pep-0020/" in report_md
    assert "https://doc.rust-lang.org/book/" in report_md
    assert "ACTION HYPOTHESIS" in report_md


def test_missing_verification_artifact_raises_error() -> None:
    """Proves evidence lacking verification_artifact fails closed with ValueError."""
    obs_path = Path("data/fixtures/competitor_cited_observation.json")
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/prepilot_manifest.json")
    profile_path = Path("data/fixtures/prepilot_subject_profile.json")

    raw_qm_bytes = qm_path.read_bytes()
    raw_manifest_bytes = manifest_path.read_bytes()
    raw_profile_bytes = profile_path.read_bytes()

    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
    profile = SubjectProfile.model_validate_json(raw_profile_bytes)
    observation = AnswerObservation.model_validate_json(obs_path.read_bytes())

    client_evidence = EvidenceRecord(
        evidence_id="ev-client-no-art",
        url="https://peps.python.org/pep-0020/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=False,
        opened_excerpt="Beautiful is better than ugly.",
        verification_artifact=None,
    )

    comp_art = VerificationArtifact(
        verifier_run_id="vrun-comp-001",
        verification_timestamp=datetime.now(timezone.utc),
        verifier_method="PARSED_VISIBLE_TEXT_BS4",
        snapshot_sha256="2f3c9e8505e49bd7000000000000000000000000000000000000000000000000",
        quote_exact_match=True,
        final_url="https://doc.rust-lang.org/book/",
        http_status=200,
        content_type="text/html",
        content_length_bytes=1500,
        retrieval_duration_ms=50.0,
    )

    comp_evidence = EvidenceRecord(
        evidence_id="ev-comp-rustbook",
        url="https://doc.rust-lang.org/book/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        opened_excerpt="The Rust Programming Language",
        verification_artifact=comp_art,
    )

    ledger = AuditRun(
        run_id="run-test-no-art-001",
        client_domain=profile.client_profile.client_domain,
        category="python_programming",
        evidence_ledger={
            client_evidence.evidence_id: client_evidence,
            comp_evidence.evidence_id: comp_evidence,
        },
    )
    raw_ledger_bytes = ledger.model_dump_json().encode("utf-8")

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="lacks verification artifact"):
        reconciler.compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record,
            profile=profile,
            client_evidence_id=client_evidence.evidence_id,
            competitor_evidence_id=comp_evidence.evidence_id,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def _setup_base_fixtures():
    """Helper to construct baseline clean test fixtures."""
    obs_path = Path("data/fixtures/competitor_cited_observation.json")
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/prepilot_manifest.json")
    profile_path = Path("data/fixtures/prepilot_subject_profile.json")

    raw_qm_bytes = qm_path.read_bytes()
    raw_manifest_bytes = manifest_path.read_bytes()
    raw_profile_bytes = profile_path.read_bytes()

    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
    profile = SubjectProfile.model_validate_json(raw_profile_bytes)
    observation = AnswerObservation.model_validate_json(obs_path.read_bytes())

    client_art = VerificationArtifact(
        verifier_run_id="vrun-client-001",
        verification_timestamp=datetime.now(timezone.utc),
        verifier_method="PARSED_VISIBLE_TEXT_BS4",
        snapshot_sha256=hashlib.sha256(b"client snapshot bytes").hexdigest(),
        quote_exact_match=True,
        final_url="https://peps.python.org/pep-0020/",
        http_status=200,
        content_type="text/html",
        content_length_bytes=1200,
        retrieval_duration_ms=45.0,
    )
    comp_art = VerificationArtifact(
        verifier_run_id="vrun-comp-001",
        verification_timestamp=datetime.now(timezone.utc),
        verifier_method="PARSED_VISIBLE_TEXT_BS4",
        snapshot_sha256=hashlib.sha256(b"competitor snapshot bytes").hexdigest(),
        quote_exact_match=True,
        final_url="https://doc.rust-lang.org/book/",
        http_status=200,
        content_type="text/html",
        content_length_bytes=1500,
        retrieval_duration_ms=50.0,
    )

    client_evidence = EvidenceRecord(
        evidence_id="ev-client-pep20",
        url="https://peps.python.org/pep-0020/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=False,
        opened_excerpt="Beautiful is better than ugly.",
        verification_artifact=client_art,
        snapshot_id=f"snap-{client_art.snapshot_sha256[:16]}",
    )
    comp_evidence = EvidenceRecord(
        evidence_id="ev-comp-rustbook",
        url="https://doc.rust-lang.org/book/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        opened_excerpt="The Rust Programming Language",
        verification_artifact=comp_art,
        snapshot_id=f"snap-{comp_art.snapshot_sha256[:16]}",
    )

    ledger = AuditRun(
        run_id="run-test-base-001",
        client_domain=profile.client_profile.client_domain,
        category="python_programming",
        evidence_ledger={
            client_evidence.evidence_id: client_evidence,
            comp_evidence.evidence_id: comp_evidence,
        },
    )
    raw_ledger_bytes = ledger.model_dump_json().encode("utf-8")

    now = datetime.now(timezone.utc)
    c_exec_dig = CollectionExecutionRecord.compute_canonical_digest(
        execution_id="exec-client-001",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_art.verifier_run_id,
        snapshot_sha256=client_art.snapshot_sha256,
        execution_timestamp=now,
    )
    comp_exec_dig = CollectionExecutionRecord.compute_canonical_digest(
        execution_id="exec-comp-001",
        candidate_id="cand-comp-001",
        target_query_id="q-001",
        cited_url=comp_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=comp_evidence.evidence_id,
        verifier_run_id=comp_art.verifier_run_id,
        snapshot_sha256=comp_art.snapshot_sha256,
        execution_timestamp=now,
    )
    c_exec = CollectionExecutionRecord(
        execution_id="exec-client-001",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_art.verifier_run_id,
        snapshot_sha256=client_art.snapshot_sha256,
        execution_timestamp=now,
        canonical_digest=c_exec_dig,
    )
    comp_exec = CollectionExecutionRecord(
        execution_id="exec-comp-001",
        candidate_id="cand-comp-001",
        target_query_id="q-001",
        cited_url=comp_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=comp_evidence.evidence_id,
        verifier_run_id=comp_art.verifier_run_id,
        snapshot_sha256=comp_art.snapshot_sha256,
        execution_timestamp=now,
        canonical_digest=comp_exec_dig,
    )

    return (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    )


def test_forged_execution_digest_rejected() -> None:
    """P0 ADVERSARIAL TEST 1: CollectionExecutionRecord with forged canonical_digest is rejected."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    forged_exec = c_exec.model_copy(update={"canonical_digest": "0" * 64})

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[forged_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="failed integrity verification"):
        reconciler.compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record,
            profile=profile,
            client_evidence_id=client_evidence.evidence_id,
            competitor_evidence_id=comp_evidence.evidence_id,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_same_evidence_id_foreign_execution_rejected() -> None:
    """P0 ADVERSARIAL TEST 2: Foreign execution with valid own digest but different observation context is rejected."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    # Foreign execution with valid own digest but wrong observation_id
    foreign_obs_id = "obs-FOREIGN-DIFFERENT"
    now = datetime.now(timezone.utc)
    foreign_dig = CollectionExecutionRecord.compute_canonical_digest(
        execution_id="exec-client-foreign",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=foreign_obs_id,  # Foreign!
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
        snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
        execution_timestamp=now,
    )
    foreign_exec = CollectionExecutionRecord(
        execution_id="exec-client-foreign",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=foreign_obs_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
        snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
        execution_timestamp=now,
        canonical_digest=foreign_dig,
    )
    assert foreign_exec.verify_integrity() is True

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[foreign_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="observation_id .* != observation ID"):
        reconciler.compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record,
            profile=profile,
            client_evidence_id=client_evidence.evidence_id,
            competitor_evidence_id=comp_evidence.evidence_id,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_execution_url_mismatch_rejected() -> None:
    """P0 ADVERSARIAL TEST 3: Execution with wrong cited_url raises ValueError."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    wrong_url = "https://peps.python.org/pep-0021/"
    now = datetime.now(timezone.utc)
    dig = CollectionExecutionRecord.compute_canonical_digest(
        execution_id="exec-client-wrong-url",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=wrong_url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
        snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
        execution_timestamp=now,
    )
    wrong_exec = CollectionExecutionRecord(
        execution_id="exec-client-wrong-url",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=wrong_url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
        snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
        execution_timestamp=now,
        canonical_digest=dig,
    )

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[wrong_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="cited_url .* != evidence URL"):
        reconciler.compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record,
            profile=profile,
            client_evidence_id=client_evidence.evidence_id,
            competitor_evidence_id=comp_evidence.evidence_id,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_execution_verifier_run_mismatch_rejected() -> None:
    """P0 ADVERSARIAL TEST 4: Execution with wrong verifier_run_id raises ValueError."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    wrong_vrun = "vrun-client-FOREIGN-999"
    now = datetime.now(timezone.utc)
    dig = CollectionExecutionRecord.compute_canonical_digest(
        execution_id="exec-client-wrong-vrun",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=wrong_vrun,
        snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
        execution_timestamp=now,
    )
    wrong_exec = CollectionExecutionRecord(
        execution_id="exec-client-wrong-vrun",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=wrong_vrun,
        snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
        execution_timestamp=now,
        canonical_digest=dig,
    )

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[wrong_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="verifier_run_id .* != artifact verifier_run_id"):
        reconciler.compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record,
            profile=profile,
            client_evidence_id=client_evidence.evidence_id,
            competitor_evidence_id=comp_evidence.evidence_id,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_execution_snapshot_mismatch_rejected() -> None:
    """P0 ADVERSARIAL TEST 5: Execution with wrong snapshot_sha256 raises ValueError."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    wrong_snap = "9" * 64
    now = datetime.now(timezone.utc)
    dig = CollectionExecutionRecord.compute_canonical_digest(
        execution_id="exec-client-wrong-snap",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
        snapshot_sha256=wrong_snap,
        execution_timestamp=now,
    )
    wrong_exec = CollectionExecutionRecord(
        execution_id="exec-client-wrong-snap",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
        snapshot_sha256=wrong_snap,
        execution_timestamp=now,
        canonical_digest=dig,
    )

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[wrong_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="snapshot_sha256 .* != artifact snapshot_sha256"):
        reconciler.compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record,
            profile=profile,
            client_evidence_id=client_evidence.evidence_id,
            competitor_evidence_id=comp_evidence.evidence_id,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_execution_ledger_hash_mismatch_rejected() -> None:
    """P0 ADVERSARIAL TEST 6: Execution with wrong source_ledger_sha256 raises ValueError."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    wrong_ledger_hash = "8" * 64
    now = datetime.now(timezone.utc)
    dig = CollectionExecutionRecord.compute_canonical_digest(
        execution_id="exec-client-wrong-ledger-hash",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=wrong_ledger_hash,
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
        snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
        execution_timestamp=now,
    )
    wrong_exec = CollectionExecutionRecord(
        execution_id="exec-client-wrong-ledger-hash",
        candidate_id="cand-client-001",
        target_query_id="q-001",
        cited_url=client_evidence.url,
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        profile_id=profile.profile_id,
        profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        source_ledger_sha256=wrong_ledger_hash,
        evidence_id=client_evidence.evidence_id,
        verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
        snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
        execution_timestamp=now,
        canonical_digest=dig,
    )

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[wrong_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="source_ledger_sha256 .* != raw ledger SHA-256"):
        reconciler.compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record,
            profile=profile,
            client_evidence_id=client_evidence.evidence_id,
            competitor_evidence_id=comp_evidence.evidence_id,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_gap_record_ledger_hash_mismatch_rejected() -> None:
    """P0 ADVERSARIAL TEST 7: Gap record with source_ledger_sha256 != raw ledger bytes raises ValueError."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[c_exec, comp_exec],
    )

    # Tamper gap record source_ledger_sha256 and re-compute digest
    tampered_hash = "7" * 64
    gap_record_tampered = gap_record.model_copy(update={"source_ledger_sha256": tampered_hash})
    tampered_dig = gap_record_tampered.compute_canonical_digest(
        analysis_id=gap_record_tampered.analysis_id,
        observation_id=gap_record_tampered.observation_id,
        raw_answer_sha256=gap_record_tampered.raw_answer_sha256,
        source_ledger_run_id=gap_record_tampered.source_ledger_run_id,
        source_ledger_sha256=tampered_hash,
        query_map_sha256=gap_record_tampered.query_map_sha256,
        manifest_sha256=gap_record_tampered.manifest_sha256,
        profile_id=gap_record_tampered.profile_id,
        profile_sha256=gap_record_tampered.profile_sha256,
        attribution_status=gap_record_tampered.attribution_status,
        competitor_patterns=gap_record_tampered.competitor_patterns,
        collection_candidates=gap_record_tampered.collection_candidates,
        collection_executions=gap_record_tampered.collection_executions,
        collection_attempts=gap_record_tampered.collection_attempts,
        evidence_gaps=gap_record_tampered.evidence_gaps,
        prioritized_actions=gap_record_tampered.prioritized_actions,
    )
    gap_record_tampered = gap_record_tampered.model_copy(update={"canonical_digest": tampered_dig})

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="Gap record source_ledger_sha256 .* does not match calculated raw ledger SHA-256"):
        reconciler.compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record_tampered,
            profile=profile,
            client_evidence_id=client_evidence.evidence_id,
            competitor_evidence_id=comp_evidence.evidence_id,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_missing_mandatory_quote_fields_fail_validation() -> None:
    """P0 ADVERSARIAL TEST 8: Prove Pydantic ValidationError when constructing QuotedEvidencePassage missing required fields."""
    with pytest.raises(ValidationError):
        # Missing evidence_url, snapshot_sha256, verifier_run_id, collection_execution_id
        QuotedEvidencePassage(
            evidence_id="ev-001",
            quoted_passage="Some text.",
        )

    with pytest.raises(ValidationError):
        # Missing collection_execution_id
        QuotedEvidencePassage(
            evidence_id="ev-001",
            evidence_url="https://peps.python.org/pep-0020/",
            snapshot_sha256="a" * 64,
            verifier_run_id="vrun-001",
            quoted_passage="Some text.",
        )


def test_mismatched_quote_evidence_url_prevents_promotion() -> None:
    """P0 ADVERSARIAL TEST 9: Quote evidence_url mismatch prevents claim status promotion."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[c_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    stmt_id = observation.extracted_statements[0].statement_id
    hd_dec = HumanStatementDecision(
    decision_id="hsd-wrong-url",
        statement_id=stmt_id,
        decision_status=ReconciliationStatus.SUPPORTED,
        declared_reviewer_identity="auditor-benjamin",
        decision_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
        auditor_rationale="Review with wrong quote evidence_url.",
        quoted_evidence=[
            QuotedEvidencePassage(
                evidence_id=client_evidence.evidence_id,
                evidence_url="https://peps.python.org/pep-9999/",  # Mismatched URL!
                snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
                verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
                collection_execution_id=c_exec.execution_id,
                quoted_passage="Beautiful is better than ugly.",
            )
        ],
    )

    dig = HumanDecisionRecord.compute_canonical_digest(
        decision_record_id="hdr-wrong-url",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
    )

    hd_record = HumanDecisionRecord(
        decision_record_id="hdr-wrong-url",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
        canonical_digest=dig,
    )

    reconciler = ComparativeEvidenceReconciler()
    record = reconciler.compare_evidence(
        observation=observation,
        query_map=query_map,
        gap_record=gap_record,
        profile=profile,
        client_evidence_id=client_evidence.evidence_id,
        competitor_evidence_id=comp_evidence.evidence_id,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        human_decision_record=hd_record,
    )

    assert record.client_claim_assessments[0].assessment_status == ReconciliationStatus.CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert record.client_claim_assessments[0].assessment_status != ReconciliationStatus.SUPPORTED


def test_mismatched_quote_snapshot_prevents_promotion() -> None:
    """P0 ADVERSARIAL TEST 10: Quote snapshot_sha256 mismatch prevents claim status promotion."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[c_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    stmt_id = observation.extracted_statements[0].statement_id
    hd_dec = HumanStatementDecision(
    decision_id="hsd-wrong-snap",
        statement_id=stmt_id,
        decision_status=ReconciliationStatus.SUPPORTED,
        declared_reviewer_identity="auditor-benjamin",
        decision_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
        auditor_rationale="Review with wrong quote snapshot_sha256.",
        quoted_evidence=[
            QuotedEvidencePassage(
                evidence_id=client_evidence.evidence_id,
                evidence_url=client_evidence.url,
                snapshot_sha256="5" * 64,  # Mismatched snapshot!
                verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
                collection_execution_id=c_exec.execution_id,
                quoted_passage="Beautiful is better than ugly.",
            )
        ],
    )

    dig = HumanDecisionRecord.compute_canonical_digest(
        decision_record_id="hdr-wrong-snap",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
    )

    hd_record = HumanDecisionRecord(
        decision_record_id="hdr-wrong-snap",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
        canonical_digest=dig,
    )

    reconciler = ComparativeEvidenceReconciler()
    record = reconciler.compare_evidence(
        observation=observation,
        query_map=query_map,
        gap_record=gap_record,
        profile=profile,
        client_evidence_id=client_evidence.evidence_id,
        competitor_evidence_id=comp_evidence.evidence_id,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        human_decision_record=hd_record,
    )

    assert record.client_claim_assessments[0].assessment_status == ReconciliationStatus.CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert record.client_claim_assessments[0].assessment_status != ReconciliationStatus.SUPPORTED


def test_mismatched_quote_verifier_run_prevents_promotion() -> None:
    """P0 ADVERSARIAL TEST 11: Quote verifier_run_id mismatch prevents claim status promotion."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[c_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    stmt_id = observation.extracted_statements[0].statement_id
    hd_dec = HumanStatementDecision(
    decision_id="hsd-wrong-vrun",
        statement_id=stmt_id,
        decision_status=ReconciliationStatus.SUPPORTED,
        declared_reviewer_identity="auditor-benjamin",
        decision_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
        auditor_rationale="Review with wrong quote verifier_run_id.",
        quoted_evidence=[
            QuotedEvidencePassage(
                evidence_id=client_evidence.evidence_id,
                evidence_url=client_evidence.url,
                snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
                verifier_run_id="vrun-client-WRONG-999",  # Mismatched verifier run ID!
                collection_execution_id=c_exec.execution_id,
                quoted_passage="Beautiful is better than ugly.",
            )
        ],
    )

    dig = HumanDecisionRecord.compute_canonical_digest(
        decision_record_id="hdr-wrong-vrun",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
    )

    hd_record = HumanDecisionRecord(
        decision_record_id="hdr-wrong-vrun",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
        canonical_digest=dig,
    )

    reconciler = ComparativeEvidenceReconciler()
    record = reconciler.compare_evidence(
        observation=observation,
        query_map=query_map,
        gap_record=gap_record,
        profile=profile,
        client_evidence_id=client_evidence.evidence_id,
        competitor_evidence_id=comp_evidence.evidence_id,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        human_decision_record=hd_record,
    )

    assert record.client_claim_assessments[0].assessment_status == ReconciliationStatus.CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert record.client_claim_assessments[0].assessment_status != ReconciliationStatus.SUPPORTED


def test_mismatched_quote_execution_id_prevents_promotion() -> None:
    """P0 ADVERSARIAL TEST 12: HumanStatementDecision with mismatched collection_execution_id prevents claim promotion."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[c_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    stmt_id = observation.extracted_statements[0].statement_id
    hd_dec = HumanStatementDecision(
    decision_id="hsd-mismatched-exec-quote",
        statement_id=stmt_id,
        decision_status=ReconciliationStatus.SUPPORTED,
        declared_reviewer_identity="auditor-benjamin",
        decision_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
        auditor_rationale="Review with wrong collection execution ID.",
        quoted_evidence=[
            QuotedEvidencePassage(
                evidence_id=client_evidence.evidence_id,
                evidence_url=client_evidence.url,
                snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
                verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
                collection_execution_id="exec-client-FOREIGN-WRONG",  # Mismatched execution ID!
                quoted_passage="Beautiful is better than ugly.",
            )
        ],
    )

    dig = HumanDecisionRecord.compute_canonical_digest(
        decision_record_id="hdr-mismatched-exec-quote",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
    )

    hd_record = HumanDecisionRecord(
        decision_record_id="hdr-mismatched-exec-quote",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
        canonical_digest=dig,
    )

    reconciler = ComparativeEvidenceReconciler()
    record = reconciler.compare_evidence(
        observation=observation,
        query_map=query_map,
        gap_record=gap_record,
        profile=profile,
        client_evidence_id=client_evidence.evidence_id,
        competitor_evidence_id=comp_evidence.evidence_id,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        human_decision_record=hd_record,
    )

    assert record.client_claim_assessments[0].assessment_status == ReconciliationStatus.CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert record.client_claim_assessments[0].assessment_status != ReconciliationStatus.SUPPORTED


def test_authentic_sprint851_comparative_promotion_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P0 TEST 13: Authentic HumanStatementDecision matching all 6 quote fields promotes claim assessment to SUPPORTED."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec
    ) = _setup_base_fixtures()

    snapshot_store = SnapshotStore(tmp_path)
    snapshot_store.save_snapshot(b"client snapshot bytes")
    snapshot_store.save_snapshot(b"competitor snapshot bytes")
    signing_key = b"test-execution-registry-signing-key"
    registry_dir = tmp_path / "execution-registry"
    monkeypatch.setenv("GEO_AEO_TRUSTED_ISSUER_ID", "trusted-test-issuer")
    monkeypatch.setenv("GEO_AEO_TRUSTED_ISSUER_KEY_HEX", signing_key.hex())
    monkeypatch.setenv("GEO_AEO_EXECUTION_REGISTRY_DIR", str(registry_dir))
    execution_registry = CollectorExecutionRegistry(
        signing_key, issuer_id="trusted-test-issuer", base_dir=registry_dir
    )
    c_exec = execution_registry.issue(c_exec)
    comp_exec = execution_registry.issue(comp_exec)

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[c_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)

    stmt_id = observation.extracted_statements[0].statement_id
    hd_dec = HumanStatementDecision(
    decision_id="hsd-authentic-sprint851",
        statement_id=stmt_id,
        decision_status=ReconciliationStatus.SUPPORTED,
        declared_reviewer_identity="auditor-benjamin",
        decision_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
        auditor_rationale="Authentic human decision matching all 6 quote fields.",
        quoted_evidence=[
            QuotedEvidencePassage(
                evidence_id=client_evidence.evidence_id,
                evidence_url=client_evidence.url,
                snapshot_sha256=client_evidence.verification_artifact.snapshot_sha256,
                verifier_run_id=client_evidence.verification_artifact.verifier_run_id,
                collection_execution_id=c_exec.execution_id,
                quoted_passage="Beautiful is better than ugly.",
            )
        ],
    )

    dig = HumanDecisionRecord.compute_canonical_digest(
        decision_record_id="hdr-authentic-sprint851",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
    )

    hd_record = HumanDecisionRecord(
        decision_record_id="hdr-authentic-sprint851",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
        canonical_digest=dig,
    )

    reconciler = ComparativeEvidenceReconciler()
    record = reconciler.compare_evidence(
        observation=observation,
        query_map=query_map,
        gap_record=gap_record,
        profile=profile,
        client_evidence_id=client_evidence.evidence_id,
        competitor_evidence_id=comp_evidence.evidence_id,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        human_decision_record=hd_record,
        snapshot_store=snapshot_store,
    )

    # Authentic decision matching all 6 quote fields -> successfully promoted to SUPPORTED
    assert record.client_claim_assessments[0].assessment_status == ReconciliationStatus.SUPPORTED


def test_gap_analyzer_rejects_same_run_id_substituted_ledger_model() -> None:
    """P0: Raw ledger bytes, not a same-run-ID model, govern gap analysis."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, _client_evidence,
        _comp_evidence, _c_exec, _comp_exec,
    ) = _setup_base_fixtures()
    substituted_ledger = ledger.model_copy(update={"evidence_ledger": {}})

    with pytest.raises(ValueError, match="Canonical artifact mismatch: supplied AuditRun"):
        ForensicGapAnalyzer.analyze_gaps(
            subject_profile=profile,
            observation=observation,
            source_ledger=substituted_ledger,
            query_map=query_map,
            manifest=manifest,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_comparator_rejects_substituted_profile_model() -> None:
    """P0: Relationship classification cannot use a profile different from raw bytes."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, client_evidence,
        comp_evidence, c_exec, comp_exec,
    ) = _setup_base_fixtures()
    gap_record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[c_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)
    substituted_profile = profile.model_copy(update={"profile_id": "profile-substituted"})

    with pytest.raises(ValueError, match="supplied SubjectProfile does not match its raw bytes"):
        ComparativeEvidenceReconciler().compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record,
            profile=substituted_profile,
            client_evidence_id=client_evidence.evidence_id,
            competitor_evidence_id=comp_evidence.evidence_id,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_retained_snapshot_reference_and_bytes_are_required(tmp_path: Path) -> None:
    """P0: Promotion cannot rely on a digest without reloadable retained bytes."""
    (
        _observation, _query_map, _manifest, _profile, _ledger, _raw_ledger_bytes,
        _raw_qm_bytes, _raw_manifest_bytes, _raw_profile_bytes, client_evidence,
        _comp_evidence, c_exec, _comp_exec,
    ) = _setup_base_fixtures()
    snapshot_store = SnapshotStore(tmp_path)
    without_reference = client_evidence.model_copy(update={"snapshot_id": None})

    with pytest.raises(ValueError, match="no retained snapshot reference"):
        ComparativeEvidenceReconciler._verify_retained_snapshot(without_reference, c_exec, snapshot_store)
    with pytest.raises(ValueError, match="retained snapshot is unavailable"):
        ComparativeEvidenceReconciler._verify_retained_snapshot(client_evidence, c_exec, snapshot_store)

    snapshot_path = snapshot_store.base_dir / f"{client_evidence.verification_artifact.snapshot_sha256}.txt"
    snapshot_path.write_bytes(b"substituted snapshot bytes")
    with pytest.raises(ValueError, match="retained snapshot bytes do not match"):
        ComparativeEvidenceReconciler._verify_retained_snapshot(client_evidence, c_exec, snapshot_store)


def test_execution_with_unauthorized_candidate_is_rejected() -> None:
    """P0: A self-consistent execution digest does not establish candidate authority."""
    (
        observation, query_map, manifest, profile, ledger, raw_ledger_bytes,
        raw_qm_bytes, raw_manifest_bytes, raw_profile_bytes, _client_evidence,
        _comp_evidence, c_exec, comp_exec,
    ) = _setup_base_fixtures()
    gap_record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
        collection_executions=[c_exec, comp_exec],
    )
    gap_record = _with_authorized_execution_candidates(gap_record)
    forged_digest = CollectionExecutionRecord.compute_canonical_digest(
        execution_id=c_exec.execution_id,
        candidate_id="candidate-never-authorized",
        target_query_id=c_exec.target_query_id,
        cited_url=c_exec.cited_url,
        observation_id=c_exec.observation_id,
        raw_answer_sha256=c_exec.raw_answer_sha256,
        profile_id=c_exec.profile_id,
        profile_sha256=c_exec.profile_sha256,
        manifest_sha256=c_exec.manifest_sha256,
        query_map_sha256=c_exec.query_map_sha256,
        source_ledger_sha256=c_exec.source_ledger_sha256,
        evidence_id=c_exec.evidence_id,
        verifier_run_id=c_exec.verifier_run_id,
        snapshot_sha256=c_exec.snapshot_sha256,
        execution_timestamp=c_exec.execution_timestamp,
    )
    forged_execution = c_exec.model_copy(
        update={"candidate_id": "candidate-never-authorized", "canonical_digest": forged_digest}
    )

    with pytest.raises(ValueError, match="unauthorized candidate"):
        ComparativeEvidenceReconciler._validate_execution_authority(
            forged_execution, gap_record, observation, query_map, manifest
        )


def test_collector_registry_rejects_new_id_fully_rehashed_execution() -> None:
    """P0: Public rehashing cannot turn a foreign execution into a collector-issued one."""
    (
        _observation, _query_map, _manifest, _profile, _ledger, _raw_ledger_bytes,
        _raw_qm_bytes, _raw_manifest_bytes, _raw_profile_bytes, _client_evidence,
        _comp_evidence, c_exec, _comp_exec,
    ) = _setup_base_fixtures()
    registry = CollectorExecutionRegistry(
        b"test-execution-registry-signing-key", issuer_id="trusted-test-issuer"
    )
    c_exec = registry.issue(c_exec)
    forged_id = "exec-client-self-consistent-forgery"
    forged_digest = CollectionExecutionRecord.compute_canonical_digest(
        execution_id=forged_id,
        candidate_id=c_exec.candidate_id,
        target_query_id=c_exec.target_query_id,
        cited_url=c_exec.cited_url,
        observation_id=c_exec.observation_id,
        raw_answer_sha256=c_exec.raw_answer_sha256,
        profile_id=c_exec.profile_id,
        profile_sha256=c_exec.profile_sha256,
        manifest_sha256=c_exec.manifest_sha256,
        query_map_sha256=c_exec.query_map_sha256,
        source_ledger_sha256=c_exec.source_ledger_sha256,
        evidence_id=c_exec.evidence_id,
        verifier_run_id=c_exec.verifier_run_id,
        snapshot_sha256=c_exec.snapshot_sha256,
        execution_timestamp=c_exec.execution_timestamp,
        issuer_id=c_exec.issuer_id,
    )
    forged_execution = c_exec.model_copy(
        update={"execution_id": forged_id, "canonical_digest": forged_digest}
    )
    assert forged_execution.verify_integrity() is True

    with pytest.raises(ValueError, match="is not registered"):
        registry.verify_issued(forged_execution)


def test_trusted_issuer_rejects_execution_attested_by_attacker_registry() -> None:
    """P0: A caller-supplied registry with another key cannot become the platform issuer."""
    (
        _observation, _query_map, _manifest, _profile, _ledger, _raw_ledger_bytes,
        _raw_qm_bytes, _raw_manifest_bytes, _raw_profile_bytes, _client_evidence,
        _comp_evidence, c_exec, _comp_exec,
    ) = _setup_base_fixtures()
    trusted_registry = CollectorExecutionRegistry(
        b"trusted-registry-signing-key-32-bytes", issuer_id="platform-trusted-issuer"
    )
    attacker_registry = CollectorExecutionRegistry(
        b"attacker-registry-signing-key-32-byt", issuer_id="attacker-controlled-issuer"
    )
    attacker_attested_execution = attacker_registry.issue(c_exec)

    assert attacker_attested_execution.verify_integrity() is True
    with pytest.raises(ValueError, match="is not trusted"):
        trusted_registry.verify_issued(attacker_attested_execution)
