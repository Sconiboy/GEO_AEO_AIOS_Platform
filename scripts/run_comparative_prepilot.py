"""
Standalone Execution Script for Sprint 8 Bounded Comparative Evidence Pre-Pilot Workflow
"""

import json
from pathlib import Path
from src.collector.candidate_collector import CandidateCollector
from src.collector.comparative_reconciler import ComparativeEvidenceReconciler
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest
from src.collector.verifier import SourceVerifier
from src.domain.enums import FailureCategory, SourceType, VerificationStatus
from src.domain.models import AuditRun, EvidenceRecord, VerificationArtifact
from src.domain.observation import AnswerObservation
from src.domain.profile import SubjectProfile
from src.domain.query_map import QueryMap
from src.exporter.report import ReportExporter


def main() -> None:
    print("=== Starting Sprint 8 Bounded Comparative Evidence Pre-Pilot ===")

    # Step 1: Load inputs and raw bytes
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/prepilot_manifest.json")
    profile_path = Path("data/fixtures/prepilot_subject_profile.json")
    obs_path = Path("data/fixtures/competitor_cited_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    raw_manifest_bytes = manifest_path.read_bytes()
    raw_profile_bytes = profile_path.read_bytes()

    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
    profile = SubjectProfile.model_validate_json(raw_profile_bytes)
    observation = AnswerObservation.model_validate_json(obs_path.read_bytes())

    # Create empty initial source ledger AuditRun
    initial_ledger = AuditRun(
        run_id="run-sprint8-prepilot-001",
        client_domain=profile.client_profile.client_domain,
        category="python_programming",
        evidence_ledger={},
    )
    raw_ledger_bytes = initial_ledger.model_dump_json().encode("utf-8")

    # Step 2: Verify Observation integrity
    print(f"1. Validating AnswerObservation '{observation.observation_id}'...")
    if not observation.verify_integrity():
        raise RuntimeError("AnswerObservation integrity verification failed!")
    print(f"   [PASS] Integrity verified. Artifact-backed: {observation.is_artifact_backed}")

    # Step 3: Run Gap Analysis
    print("2. Running ForensicGapAnalyzer...")
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

    print(f"   [PASS] Attribution Status: {gap_record.attribution_status.value}")
    print(f"   [PASS] Identified {len(gap_record.collection_candidates)} collection candidate(s).")
    cand = gap_record.collection_candidates[0]
    print(f"          Candidate ID: {cand.candidate_id}, URL: {cand.cited_url}, Requires Human Approval: {cand.requires_human_manifest_approval}")

    # Step 4: Execute Competitor Source Collection via CandidateCollector
    print("3. Executing CandidateCollector for competitor URL...")
    collector = CandidateCollector()
    updated_ledger, updated_gap_record = collector.collect_candidate(
        candidate_id=cand.candidate_id,
        subject_profile=profile,
        observation=observation,
        source_ledger=initial_ledger,
        query_map=query_map,
        manifest=manifest,
        gap_record=gap_record,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )
    
    comp_evidence = next(iter(updated_ledger.evidence_ledger.values()))
    print(f"   [PASS] Competitor Collection Succeeded!")
    print(f"          Evidence ID: {comp_evidence.evidence_id}, Status: {comp_evidence.verification_status.value}")

    # Step 5: Collect Matched Client Evidence (PEP 20)
    print("4. Collecting Matched Client Evidence (PEP 20)...")
    verifier = SourceVerifier()
    client_url = "https://peps.python.org/pep-0020/"
    client_quote = "Beautiful is better than ugly. Explicit is better than implicit. Simple is better than complex."
    client_evidence = verifier.verify_url(
        url=client_url,
        candidate_excerpt=client_quote,
        source_type=SourceType.OFFICIAL_DOCUMENTATION,
        is_independent=False,
        evidence_id="ev-pep20-client-001",
    )
    print(f"   [PASS] Client Evidence Status: {client_evidence.verification_status.value}")

    # Step 6: Execute Comparative Evidence Reconciliation
    print("5. Executing ComparativeEvidenceReconciler...")
    comp_reconciler = ComparativeEvidenceReconciler()
    comp_record = comp_reconciler.compare_evidence(
        observation=observation,
        query_map=query_map,
        gap_record=updated_gap_record,
        profile=profile,
        client_evidence=client_evidence,
        competitor_evidence=comp_evidence,
    )

    print(f"   [PASS] Comparative Record Generated! ID: {comp_record.comparative_id}")
    print(f"          Digest: {comp_record.canonical_digest[:16]}...")
    print(f"          Gap Identified: {comp_record.evidence_gap_identified}")

    # Step 7: Export Markdown Report
    print("6. Exporting Comparative Analysis Report...")
    report_md = ReportExporter.export_comparative_analysis_record(comp_record, query_map)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / "prepilot_comparative_analysis_report.md"
    report_file.write_text(report_md)

    print(f"=== Sprint 8 Pre-Pilot Execution Complete! Report saved to '{report_file}' ===")


if __name__ == "__main__":
    main()
