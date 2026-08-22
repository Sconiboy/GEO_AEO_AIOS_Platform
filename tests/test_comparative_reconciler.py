"""
Unit and Adversarial Tests for ComparativeEvidenceReconciler & Sprint 8.5.1 Workflow
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
import pytest

from src.collector.candidate_collector import CandidateCollector
from src.collector.comparative_reconciler import ComparativeEvidenceReconciler
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest
from src.domain.candidate_collection import CollectionExecutionRecord
from src.domain.comparative import ComparativeEvidenceRecord
from src.domain.enums import ReconciliationMethod, ReconciliationStatus, SourceRelationship, VerificationStatus
from src.domain.human_decision import HumanDecisionRecord, HumanStatementDecision, QuotedEvidencePassage
from src.domain.models import AuditRun, EvidenceRecord, VerificationArtifact
from src.domain.observation import AnswerObservation
from src.domain.profile import SubjectProfile
from src.domain.query_map import QueryMap
from src.exporter.report import ReportExporter


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
        snapshot_sha256="1e2b8d7404d38ac6999999999999999999999999999999999999999999999999",
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
        snapshot_sha256="2f3c9e8505e49bd7000000000000000000000000000000000000000000000000",
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


def test_forged_execution_digest_rejected() -> None:
    """P0 ADVERSARIAL TEST: Proves CollectionExecutionRecord with forged canonical_digest is rejected."""
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
        snapshot_sha256="1e2b8d7404d38ac6999999999999999999999999999999999999999999999999",
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
        snapshot_sha256="2f3c9e8505e49bd7000000000000000000000000000000000000000000000000",
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
        run_id="run-test-forged-exec-001",
        client_domain=profile.client_profile.client_domain,
        category="python_programming",
        evidence_ledger={
            client_evidence.evidence_id: client_evidence,
            comp_evidence.evidence_id: comp_evidence,
        },
    )
    raw_ledger_bytes = ledger.model_dump_json().encode("utf-8")

    now = datetime.now(timezone.utc)
    forged_exec = CollectionExecutionRecord(
        execution_id="exec-client-forged",
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
        canonical_digest="0" * 64,  # Forged canonical digest!
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
        collection_executions=[forged_exec],
    )

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


def test_mismatched_quote_execution_id_prevents_promotion() -> None:
    """P0 ADVERSARIAL TEST: Proves HumanStatementDecision with mismatched collection_execution_id prevents claim promotion."""
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

    snap_sha256 = "1e2b8d7404d38ac6999999999999999999999999999999999999999999999999"
    client_art = VerificationArtifact(
        verifier_run_id="vrun-client-003",
        verification_timestamp=datetime.now(timezone.utc),
        verifier_method="PARSED_VISIBLE_TEXT_BS4",
        snapshot_sha256=snap_sha256,
        quote_exact_match=True,
        final_url="https://peps.python.org/pep-0020/",
        http_status=200,
        content_type="text/html",
        content_length_bytes=1200,
        retrieval_duration_ms=45.0,
    )
    comp_art = VerificationArtifact(
        verifier_run_id="vrun-comp-003",
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

    client_evidence = EvidenceRecord(
        evidence_id="ev-client-pep20",
        url="https://peps.python.org/pep-0020/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=False,
        opened_excerpt="Beautiful is better than ugly.",
        verification_artifact=client_art,
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
        run_id="run-test-comp-mismatched-exec-quote-001",
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
        execution_id="exec-client-real",
        candidate_id="cand-client-003",
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
        execution_id="exec-comp-real",
        candidate_id="cand-comp-003",
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
            execution_id="exec-client-real",
            candidate_id="cand-client-003",
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
            execution_id="exec-comp-real",
            candidate_id="cand-comp-003",
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
                evidence_id="ev-client-pep20",
                evidence_url=client_evidence.url,
                snapshot_sha256=snap_sha256,
                verifier_run_id=client_art.verifier_run_id,
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

    # Mismatched execution ID in quote prevents status promotion -> remains CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert record.client_claim_assessments[0].assessment_status == ReconciliationStatus.CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert record.client_claim_assessments[0].assessment_status != ReconciliationStatus.SUPPORTED


def test_authentic_sprint851_comparative_promotion_succeeds() -> None:
    """P0 TEST: Proves authentic HumanStatementDecision matching all 6 quote fields promotes claim assessment to SUPPORTED."""
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

    snap_sha256 = "1e2b8d7404d38ac6999999999999999999999999999999999999999999999999"
    client_art = VerificationArtifact(
        verifier_run_id="vrun-client-004",
        verification_timestamp=datetime.now(timezone.utc),
        verifier_method="PARSED_VISIBLE_TEXT_BS4",
        snapshot_sha256=snap_sha256,
        quote_exact_match=True,
        final_url="https://peps.python.org/pep-0020/",
        http_status=200,
        content_type="text/html",
        content_length_bytes=1200,
        retrieval_duration_ms=45.0,
    )
    comp_art = VerificationArtifact(
        verifier_run_id="vrun-comp-004",
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

    client_evidence = EvidenceRecord(
        evidence_id="ev-client-pep20",
        url="https://peps.python.org/pep-0020/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=False,
        opened_excerpt="Beautiful is better than ugly.",
        verification_artifact=client_art,
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
        run_id="run-test-comp-authentic-001",
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
        execution_id="exec-client-004",
        candidate_id="cand-client-004",
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
        execution_id="exec-comp-004",
        candidate_id="cand-comp-004",
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
            execution_id="exec-client-004",
            candidate_id="cand-client-004",
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
            execution_id="exec-comp-004",
            candidate_id="cand-comp-004",
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
                snapshot_sha256=snap_sha256,
                verifier_run_id=client_art.verifier_run_id,
                collection_execution_id="exec-client-004",
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
    )

    # Authentic decision matching all 6 quote fields -> successfully promoted to SUPPORTED
    assert record.client_claim_assessments[0].assessment_status == ReconciliationStatus.SUPPORTED
