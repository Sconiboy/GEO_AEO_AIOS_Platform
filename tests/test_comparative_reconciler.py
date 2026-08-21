"""
Unit and Adversarial Tests for ComparativeEvidenceReconciler & Sprint 8.3 Workflow
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
import pytest
from src.collector.candidate_collector import CandidateCollector
from src.collector.comparative_reconciler import ComparativeEvidenceReconciler
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest
from src.domain.comparative import ComparativeEvidenceRecord
from src.domain.enums import ReconciliationMethod, ReconciliationStatus, SourceRelationship, VerificationStatus
from src.domain.human_decision import HumanDecisionRecord, HumanStatementDecision, QuotedEvidencePassage
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


def test_false_positive_keyword_claim_returns_candidate_for_human_review() -> None:
    """Proves adversarial claim 'Rust guarantees every application is secure...' returns CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW, never auto-SUPPORTED."""
    false_statement_id = "stmt-false-001"
    false_statement_text = "Rust guarantees every application is secure and easy to maintain."
    comp_excerpt = "The Rust Programming Language."

    comp_evidence = EvidenceRecord(
        evidence_id="ev-rust-excerpt",
        url="https://doc.rust-lang.org/book/",
        source_type="official_documentation",
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
        opened_excerpt=comp_excerpt,
    )

    assessment = ComparativeEvidenceReconciler.evaluate_claim_support(
        statement_id=false_statement_id,
        statement_text=false_statement_text,
        evidence=comp_evidence,
        expected_role=SourceRelationship.COMPETITOR_OWNED,
    )

    assert assessment.assessment_status == ReconciliationStatus.CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert assessment.assessment_status != ReconciliationStatus.SUPPORTED


def test_cross_evidence_human_decision_replay_rejected() -> None:
    """
    Adversarial Test (P0): Proves a human decision approving PEP 20 evidence ('ev-client-pep20')
    is NOT replayed onto Rust Book evidence ('ev-comp-rustbook'). Rust evidence remains CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW.
    """
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
        run_id="run-test-comp-replay-001",
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

    # Human decision approving ONLY client PEP 20 evidence ('ev-client-pep20')
    stmt_id = observation.extracted_statements[0].statement_id
    hd_dec = HumanStatementDecision(
        decision_id="hsd-pep20-only",
        statement_id=stmt_id,
        decision_status=ReconciliationStatus.SUPPORTED,
        declared_reviewer_identity="auditor-benjamin",
        decision_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
        auditor_rationale="Verified PEP 20 document substantiates readability principles.",
        quoted_evidence=[
            QuotedEvidencePassage(
                evidence_id="ev-client-pep20",
                quoted_passage="Beautiful is better than ugly.",
            )
        ],
    )

    dig = HumanDecisionRecord.compute_canonical_digest(
        decision_record_id="hdr-pep20-only",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=initial_ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
    )

    hd_record = HumanDecisionRecord(
        decision_record_id="hdr-pep20-only",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=initial_ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
        created_at=datetime.now(timezone.utc),
        canonical_digest=dig,
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
        human_decision_record=hd_record,
    )

    # Client evidence is promoted to SUPPORTED because decision matches ev-client-pep20
    assert record.client_claim_assessments[0].assessment_status == ReconciliationStatus.SUPPORTED

    # Competitor evidence ('ev-comp-rustbook') MUST NOT BE PROMOTED! (evidence_id mismatch)
    assert record.competitor_claim_assessments[0].assessment_status == ReconciliationStatus.CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert record.competitor_claim_assessments[0].assessment_status != ReconciliationStatus.SUPPORTED


def test_mismatched_observation_id_human_decision_raises_error() -> None:
    """Proves passing a HumanDecisionRecord with mismatched observation_id raises ValueError."""
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
        run_id="run-test-comp-mismatch-001",
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

    stmt_id = observation.extracted_statements[0].statement_id
    hd_dec = HumanStatementDecision(
        decision_id="hsd-mismatch",
        statement_id=stmt_id,
        decision_status=ReconciliationStatus.SUPPORTED,
        declared_reviewer_identity="auditor-benjamin",
        decision_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
        auditor_rationale="Verified PEP 20 document.",
        quoted_evidence=[
            QuotedEvidencePassage(
                evidence_id="ev-client-pep20",
                quoted_passage="Beautiful is better than ugly.",
            )
        ],
    )

    # Mismatched observation_id
    wrong_obs_id = "obs-unrelated-999"
    dig = HumanDecisionRecord.compute_canonical_digest(
        decision_record_id="hdr-mismatch",
        observation_id=wrong_obs_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=initial_ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
    )

    hd_record = HumanDecisionRecord(
        decision_record_id="hdr-mismatch",
        observation_id=wrong_obs_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=initial_ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
        created_at=datetime.now(timezone.utc),
        canonical_digest=dig,
    )

    reconciler = ComparativeEvidenceReconciler()
    with pytest.raises(ValueError, match="HumanDecisionRecord Context Mismatch: observation_id"):
        reconciler.compare_evidence(
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
            human_decision_record=hd_record,
        )


def test_altered_quoted_passage_prevents_promotion() -> None:
    """Proves quoted passage not present in opened_excerpt prevents claim status promotion."""
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
        run_id="run-test-comp-quote-001",
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

    # Quoted passage is NOT present in client_evidence.opened_excerpt
    stmt_id = observation.extracted_statements[0].statement_id
    hd_dec = HumanStatementDecision(
        decision_id="hsd-bad-passage",
        statement_id=stmt_id,
        decision_status=ReconciliationStatus.SUPPORTED,
        declared_reviewer_identity="auditor-benjamin",
        decision_timestamp=datetime.now(timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
        auditor_rationale="Fabricated quoted passage not in excerpt.",
        quoted_evidence=[
            QuotedEvidencePassage(
                evidence_id="ev-client-pep20",
                quoted_passage="Fabricated passage never written in PEP 20.",
            )
        ],
    )

    dig = HumanDecisionRecord.compute_canonical_digest(
        decision_record_id="hdr-bad-passage",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=initial_ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
    )

    hd_record = HumanDecisionRecord(
        decision_record_id="hdr-bad-passage",
        observation_id=observation.observation_id,
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=initial_ledger.run_id,
        source_ledger_sha256=hashlib.sha256(raw_ledger_bytes).hexdigest(),
        query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
        manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
        decisions=[hd_dec],
        created_at=datetime.now(timezone.utc),
        canonical_digest=dig,
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
        human_decision_record=hd_record,
    )

    # Passage mismatch prevents promotion -> remains CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert record.client_claim_assessments[0].assessment_status == ReconciliationStatus.CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW
    assert record.client_claim_assessments[0].assessment_status != ReconciliationStatus.SUPPORTED
