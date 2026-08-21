"""
Unit and Adversarial Tests for ComparativeEvidenceReconciler & Sprint 8.1 Workflow
"""

import hashlib
from pathlib import Path
import pytest
from src.collector.candidate_collector import CandidateCollector
from src.collector.comparative_reconciler import ComparativeEvidenceReconciler
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest
from src.domain.comparative import ComparativeEvidenceRecord
from src.domain.enums import ReconciliationStatus, SourceRelationship, VerificationStatus
from src.domain.models import AuditRun, EvidenceRecord, VerificationArtifact
from src.domain.observation import AnswerObservation
from src.domain.profile import SubjectProfile
from src.domain.query_map import QueryMap
from src.exporter.report import ReportExporter


def test_comparative_evidence_reconciler_execution() -> None:
    """Proves ComparativeEvidenceReconciler creates a valid comparative record and canonical digest."""
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

    initial_ledger = AuditRun(
        run_id="run-test-comp-001",
        client_domain=profile.client_profile.client_domain,
        category="python_programming",
        evidence_ledger={},
    )
    raw_ledger_bytes = initial_ledger.model_dump_json().encode("utf-8")

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=initial_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    client_evidence = EvidenceRecord(
        evidence_id="ev-client-pep20",
        url="https://peps.python.org/pep-0020/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=False,
        opened_excerpt="Beautiful is better than ugly. Explicit is better than implicit. Simple is better than complex.",
    )

    comp_evidence = EvidenceRecord(
        evidence_id="ev-comp-rustbook",
        url="https://doc.rust-lang.org/book/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        opened_excerpt="The Rust Programming Language",
    )

    reconciler = ComparativeEvidenceReconciler()
    record = reconciler.compare_evidence(
        observation=observation,
        query_map=query_map,
        gap_record=gap_record,
        profile=profile,
        client_evidence=client_evidence,
        competitor_evidence=comp_evidence,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    assert record.observation_id == observation.observation_id
    assert record.query_id == "q-001"
    assert record.evidence_gap_identified is True
    assert record.client_evidence.domain == "peps.python.org"
    assert record.competitor_evidence.domain == "doc.rust-lang.org"
    assert record.verify_integrity() is True
    assert record.human_review_required is True

    report_md = ReportExporter.export_comparative_analysis_record(record, query_map)
    assert "Bounded Comparative Evidence Analysis" in report_md
    assert "Content-Addressed 9-Hash Artifact Bindings" in report_md
    assert "https://peps.python.org/pep-0020/" in report_md
    assert "https://doc.rust-lang.org/book/" in report_md
    assert "ACTION HYPOTHESIS" in report_md


def test_unrelated_competitor_relationship_rejected() -> None:
    """Proves compare_evidence fails closed when non-competitor URL passed as competitor evidence."""
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

    initial_ledger = AuditRun(
        run_id="run-test-comp-002",
        client_domain=profile.client_profile.client_domain,
        category="python_programming",
        evidence_ledger={},
    )
    raw_ledger_bytes = initial_ledger.model_dump_json().encode("utf-8")

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=initial_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    client_evidence = EvidenceRecord(
        evidence_id="ev-client-pep20",
        url="https://peps.python.org/pep-0020/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=False,
        opened_excerpt="Beautiful is better than ugly.",
    )

    # Passing unrelated/third-party URL as competitor evidence
    unrelated_comp_evidence = EvidenceRecord(
        evidence_id="ev-unrelated-thirdparty",
        url="https://wikipedia.org/wiki/Python",
        source_type="independent_editorial",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        opened_excerpt="Python is a programming language.",
    )

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="classified as 'independent_editorial', expected 'competitor_owned'"):
        reconciler.compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record,
            profile=profile,
            client_evidence=client_evidence,
            competitor_evidence=unrelated_comp_evidence,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_unrelated_client_relationship_rejected() -> None:
    """Proves compare_evidence fails closed when non-client URL passed as client evidence."""
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

    initial_ledger = AuditRun(
        run_id="run-test-comp-003",
        client_domain=profile.client_profile.client_domain,
        category="python_programming",
        evidence_ledger={},
    )
    raw_ledger_bytes = initial_ledger.model_dump_json().encode("utf-8")

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=initial_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    # Passing competitor URL as client evidence
    invalid_client_evidence = EvidenceRecord(
        evidence_id="ev-invalid-client",
        url="https://doc.rust-lang.org/book/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        opened_excerpt="The Rust Programming Language",
    )

    comp_evidence = EvidenceRecord(
        evidence_id="ev-comp-rustbook",
        url="https://doc.rust-lang.org/book/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        opened_excerpt="The Rust Programming Language",
    )

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="classified as 'competitor_owned', expected 'client_owned'"):
        reconciler.compare_evidence(
            observation=observation,
            query_map=query_map,
            gap_record=gap_record,
            profile=profile,
            client_evidence=invalid_client_evidence,
            competitor_evidence=comp_evidence,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
        )


def test_tampered_comparative_digest_fails_verify_integrity() -> None:
    """Proves ComparativeEvidenceRecord.verify_integrity returns False if canonical_digest or fields are tampered with."""
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

    initial_ledger = AuditRun(
        run_id="run-test-comp-004",
        client_domain=profile.client_profile.client_domain,
        category="python_programming",
        evidence_ledger={},
    )
    raw_ledger_bytes = initial_ledger.model_dump_json().encode("utf-8")

    gap_analyzer = ForensicGapAnalyzer()
    gap_record = gap_analyzer.analyze_gaps(
        subject_profile=profile,
        observation=observation,
        source_ledger=initial_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    client_evidence = EvidenceRecord(
        evidence_id="ev-client-pep20",
        url="https://peps.python.org/pep-0020/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=False,
        opened_excerpt="Beautiful is better than ugly.",
    )

    comp_evidence = EvidenceRecord(
        evidence_id="ev-comp-rustbook",
        url="https://doc.rust-lang.org/book/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        opened_excerpt="The Rust Programming Language",
    )

    reconciler = ComparativeEvidenceReconciler()
    record = reconciler.compare_evidence(
        observation=observation,
        query_map=query_map,
        gap_record=gap_record,
        profile=profile,
        client_evidence=client_evidence,
        competitor_evidence=comp_evidence,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    assert record.verify_integrity() is True

    # Tamper with action_hypothesis
    tampered_record = record.model_copy(update={"action_hypothesis": "Forged instruction without updating digest"})
    assert tampered_record.verify_integrity() is False

    with pytest.raises(ValueError, match="Integrity failure"):
        ReportExporter.export_comparative_analysis_record(tampered_record, query_map)
