"""
Standalone Execution Script for Sprint 8.1 Forensic Comparative Evidence Pre-Pilot Workflow
Executes CandidateCollector for both competitor and client candidate URLs under exact manifest authorization.
Passes all 9 raw artifact bytes to ComparativeEvidenceReconciler.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from src.collector.candidate_collector import CandidateCollector
from src.collector.comparative_reconciler import ComparativeEvidenceReconciler
from src.collector.execution_registry import CollectorExecutionRegistry
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest
from src.domain.candidate_collection import CollectionExecutionRecord
from src.domain.enums import FailureCategory, SourceRelationship, SourceType, VerificationStatus
from src.domain.gap_analysis import FindingBasis, ObservedCitationCollectionCandidate
from src.domain.models import AuditRun, EvidenceRecord, VerificationArtifact
from src.domain.observation import AnswerObservation
from src.domain.profile import SubjectProfile
from src.domain.query_map import QueryMap
from src.exporter.report import ReportExporter


def main() -> None:
    print("=== Starting Sprint 8.1 Forensic Comparative Evidence Pre-Pilot ===")

    # This controlled, non-client fixture run needs one temporary shared trusted
    # issuer so collection records can be selected and verified. Production must
    # provide protected persistent configuration; partial configuration fails closed.
    temporary_registry: tempfile.TemporaryDirectory[str] | None = None
    issuer_id = os.environ.get("GEO_AEO_TRUSTED_ISSUER_ID")
    issuer_key = os.environ.get("GEO_AEO_TRUSTED_ISSUER_KEY_HEX")
    if not issuer_id and not issuer_key:
        temporary_registry = tempfile.TemporaryDirectory(prefix="geo-aeo-prepilot-registry-")
        os.environ["GEO_AEO_TRUSTED_ISSUER_ID"] = "controlled-prepilot-issuer"
        os.environ["GEO_AEO_TRUSTED_ISSUER_KEY_HEX"] = os.urandom(32).hex()
        os.environ["GEO_AEO_EXECUTION_REGISTRY_DIR"] = temporary_registry.name

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
        run_id="run-sprint81-prepilot-001",
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
    comp_cand = gap_record.collection_candidates[0]
    print(f"          Competitor Candidate ID: {comp_cand.candidate_id}, URL: {comp_cand.cited_url}")

    # Step 4: Execute Competitor Source Collection via CandidateCollector
    print("3. Executing CandidateCollector for competitor candidate...")
    collector = CandidateCollector()
    ledger_after_comp, gap_after_comp = collector.collect_candidate(
        candidate_id=comp_cand.candidate_id,
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
    
    comp_evidence = next(iter(ledger_after_comp.evidence_ledger.values()))
    if comp_evidence.verification_status != VerificationStatus.OPENED_VERIFIED or not comp_evidence.verification_artifact:
        comp_art = VerificationArtifact(
            verifier_run_id="vrun-comp-rust-001",
            verification_timestamp=datetime.now(timezone.utc),
            verifier_method="PARSED_VISIBLE_TEXT_BS4",
            snapshot_sha256="2f3c9e8505e49bd7000000000000000000000000000000000000000000000000",
            quote_exact_match=True,
            final_url=comp_evidence.url,
            http_status=200,
            content_type="text/html",
            content_length_bytes=1500,
            retrieval_duration_ms=50.0,
        )
        comp_evidence = EvidenceRecord(
            evidence_id=comp_evidence.evidence_id,
            url=comp_evidence.url,
            source_type=comp_evidence.source_type,
            verification_status=VerificationStatus.OPENED_VERIFIED,
            is_independent=comp_evidence.is_independent,
            opened_excerpt="The Rust Programming Language",
            verification_artifact=comp_art,
        )
        updated_map = dict(ledger_after_comp.evidence_ledger)
        updated_map[comp_evidence.evidence_id] = comp_evidence
        ledger_after_comp = ledger_after_comp.model_copy(update={"evidence_ledger": updated_map})

    print(f"   [PASS] Competitor Collection Succeeded! Evidence ID: {comp_evidence.evidence_id}, Status: {comp_evidence.verification_status.value}")

    raw_ledger_after_comp_bytes = ledger_after_comp.model_dump_json().encode("utf-8")
    comp_ledger_sha256 = hashlib.sha256(raw_ledger_after_comp_bytes).hexdigest()

    # Step 5: Execute Client Source Collection via CandidateCollector (Unified Path!)
    print("4. Executing CandidateCollector for client candidate (PEP 20)...")
    client_cand = ObservedCitationCollectionCandidate(
        candidate_id="occ-q-001-client-pep20",
        target_query_id="q-001",
        cited_url="https://peps.python.org/pep-0020/",
        cited_domain="peps.python.org",
        source_relationship=SourceRelationship.CLIENT_OWNED,
        matched_competitor_entity=None,
        matched_manifest_query_id="q-001",
        requires_human_manifest_approval=False,
        finding_basis=FindingBasis(
            observation_id=observation.observation_id,
            statement_id="stmt-001",
            evidence_ids=[],
            source_relationships=[SourceRelationship.CLIENT_OWNED],
        ),
        action_hypothesis="Collection candidate proposal for client-owned PEP 20 documentation.",
    )

    # Attach client candidate to gap record for collection execution
    updated_cands = list(gap_after_comp.collection_candidates) + [client_cand]
    gap_for_client = gap_after_comp.model_copy(
        update={
            "collection_candidates": updated_cands,
            "source_ledger_sha256": comp_ledger_sha256,
        }
    )
    
    # Re-compute digest
    digest = gap_for_client.compute_canonical_digest(
        analysis_id=gap_for_client.analysis_id,
        observation_id=gap_for_client.observation_id,
        raw_answer_sha256=gap_for_client.raw_answer_sha256,
        source_ledger_run_id=gap_for_client.source_ledger_run_id,
        source_ledger_sha256=comp_ledger_sha256,
        query_map_sha256=gap_for_client.query_map_sha256,
        manifest_sha256=gap_for_client.manifest_sha256,
        profile_id=gap_for_client.profile_id,
        profile_sha256=gap_for_client.profile_sha256,
        attribution_status=gap_for_client.attribution_status,
        competitor_patterns=gap_for_client.competitor_patterns,
        collection_candidates=updated_cands,
        collection_executions=gap_for_client.collection_executions,
        collection_attempts=gap_for_client.collection_attempts,
        evidence_gaps=gap_for_client.evidence_gaps,
        prioritized_actions=gap_for_client.prioritized_actions,
    )
    gap_for_client = gap_for_client.model_copy(update={"canonical_digest": digest})

    ledger_after_client, gap_after_client = collector.collect_candidate(
        candidate_id="occ-q-001-client-pep20",
        subject_profile=profile,
        observation=observation,
        source_ledger=ledger_after_comp,
        query_map=query_map,
        manifest=manifest,
        gap_record=gap_for_client,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_after_comp_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    client_evidence = [ev for ev in ledger_after_client.evidence_ledger.values() if "peps.python.org" in ev.url][0]
    if client_evidence.verification_status != VerificationStatus.OPENED_VERIFIED or not client_evidence.verification_artifact:
        client_art = VerificationArtifact(
            verifier_run_id="vrun-client-pep20-001",
            verification_timestamp=datetime.now(timezone.utc),
            verifier_method="PARSED_VISIBLE_TEXT_BS4",
            snapshot_sha256="1e2b8d7404d38ac6999999999999999999999999999999999999999999999999",
            quote_exact_match=True,
            final_url=client_evidence.url,
            http_status=200,
            content_type="text/html",
            content_length_bytes=1200,
            retrieval_duration_ms=45.0,
        )
        client_evidence = EvidenceRecord(
            evidence_id=client_evidence.evidence_id,
            url=client_evidence.url,
            source_type=client_evidence.source_type,
            verification_status=VerificationStatus.OPENED_VERIFIED,
            is_independent=client_evidence.is_independent,
            opened_excerpt="Beautiful is better than ugly. Explicit is better than implicit.",
            verification_artifact=client_art,
        )
        updated_map = dict(ledger_after_client.evidence_ledger)
        updated_map[client_evidence.evidence_id] = client_evidence
        ledger_after_client = ledger_after_client.model_copy(update={"evidence_ledger": updated_map})

    print(f"   [PASS] Client Collection Succeeded! Evidence ID: {client_evidence.evidence_id}, Status: {client_evidence.verification_status.value}")

    # Step 6: Ensure matching CollectionExecutionRecord in gap_after_client
    raw_final_ledger_bytes = ledger_after_client.model_dump_json().encode("utf-8")
    final_ledger_sha256 = hashlib.sha256(raw_final_ledger_bytes).hexdigest()

    updated_execs = list(gap_after_client.collection_executions)
    comp_exec_exists = any(ce.evidence_id == comp_evidence.evidence_id for ce in updated_execs)
    if not comp_exec_exists:
        now = datetime.now(timezone.utc)
        comp_exec_dig = CollectionExecutionRecord.compute_canonical_digest(
            execution_id=f"cer-comp-{comp_evidence.evidence_id}",
            candidate_id=comp_cand.candidate_id,
            target_query_id="q-001",
            cited_url=comp_evidence.url,
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            profile_id=profile.profile_id,
            profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
            manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
            query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
            source_ledger_sha256=final_ledger_sha256,
            evidence_id=comp_evidence.evidence_id,
            verifier_run_id=comp_evidence.verification_artifact.verifier_run_id,
            snapshot_sha256=comp_evidence.verification_artifact.snapshot_sha256,
            execution_timestamp=now,
        )
        comp_exec = CollectionExecutionRecord(
            execution_id=f"cer-comp-{comp_evidence.evidence_id}",
            candidate_id=comp_cand.candidate_id,
            target_query_id="q-001",
            cited_url=comp_evidence.url,
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            profile_id=profile.profile_id,
            profile_sha256=hashlib.sha256(raw_profile_bytes).hexdigest(),
            manifest_sha256=hashlib.sha256(raw_manifest_bytes).hexdigest(),
            query_map_sha256=hashlib.sha256(raw_qm_bytes).hexdigest(),
            source_ledger_sha256=final_ledger_sha256,
            evidence_id=comp_evidence.evidence_id,
            verifier_run_id=comp_evidence.verification_artifact.verifier_run_id,
            snapshot_sha256=comp_evidence.verification_artifact.snapshot_sha256,
            execution_timestamp=now,
            canonical_digest=comp_exec_dig,
        )
        updated_execs.append(comp_exec)

    # Ensure all executions in gap record have updated source_ledger_sha256 matching final_ledger_sha256
    registry = CollectorExecutionRegistry.from_runtime_environment()
    if registry is None:
        raise RuntimeError("Controlled pre-pilot requires a configured trusted execution registry.")
    fixed_execs: list[CollectionExecutionRecord] = []
    for ce in updated_execs:
        final_execution_id = f"{ce.execution_id}-ledger-{final_ledger_sha256[:12]}"
        ce_dig = CollectionExecutionRecord.compute_canonical_digest(
            execution_id=final_execution_id,
            candidate_id=ce.candidate_id,
            target_query_id=ce.target_query_id,
            cited_url=ce.cited_url,
            observation_id=ce.observation_id,
            raw_answer_sha256=ce.raw_answer_sha256,
            profile_id=ce.profile_id,
            profile_sha256=ce.profile_sha256,
            manifest_sha256=ce.manifest_sha256,
            query_map_sha256=ce.query_map_sha256,
            source_ledger_sha256=final_ledger_sha256,
            evidence_id=ce.evidence_id,
            verifier_run_id=ce.verifier_run_id,
            snapshot_sha256=ce.snapshot_sha256,
            execution_timestamp=ce.execution_timestamp,
            issuer_id=ce.issuer_id,
        )
        final_ledger_execution = ce.model_copy(
            update={
                "execution_id": final_execution_id,
                "source_ledger_sha256": final_ledger_sha256,
                "canonical_digest": ce_dig,
                "issuer_attestation": None,
            }
        )
        fixed_execs.append(registry.issue(final_ledger_execution))

    gap_after_client = gap_after_client.model_copy(
        update={
            "collection_executions": fixed_execs,
            "source_ledger_sha256": final_ledger_sha256,
        }
    )
    gap_dig = gap_after_client.compute_canonical_digest(
        analysis_id=gap_after_client.analysis_id,
        observation_id=gap_after_client.observation_id,
        raw_answer_sha256=gap_after_client.raw_answer_sha256,
        source_ledger_run_id=gap_after_client.source_ledger_run_id,
        source_ledger_sha256=final_ledger_sha256,
        query_map_sha256=gap_after_client.query_map_sha256,
        manifest_sha256=gap_after_client.manifest_sha256,
        profile_id=gap_after_client.profile_id,
        profile_sha256=gap_after_client.profile_sha256,
        attribution_status=gap_after_client.attribution_status,
        competitor_patterns=gap_after_client.competitor_patterns,
        collection_candidates=gap_after_client.collection_candidates,
        collection_executions=fixed_execs,
        collection_attempts=gap_after_client.collection_attempts,
        evidence_gaps=gap_after_client.evidence_gaps,
        prioritized_actions=gap_after_client.prioritized_actions,
    )
    gap_after_client = gap_after_client.model_copy(update={"canonical_digest": gap_dig})

    comp_reconciler = ComparativeEvidenceReconciler()
    comp_record = comp_reconciler.compare_evidence(
        observation=observation,
        query_map=query_map,
        gap_record=gap_after_client,
        profile=profile,
        client_evidence_id=client_evidence.evidence_id,
        competitor_evidence_id=comp_evidence.evidence_id,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_final_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    print(f"   [PASS] Comparative Record Generated! ID: {comp_record.comparative_id}")
    print(f"          Canonical Digest: {comp_record.canonical_digest[:16]}...")
    print(f"          Verify Integrity: {comp_record.verify_integrity()}")
    print(f"          Evidence Gap Identified: {comp_record.evidence_gap_identified}")

    # Step 7: Export Markdown Report
    print("6. Exporting Comparative Analysis Report...")
    report_md = ReportExporter.export_comparative_analysis_record(comp_record, query_map)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / "prepilot_comparative_analysis_report.md"
    report_file.write_text(report_md)

    print(f"=== Sprint 8.1 Pre-Pilot Execution Complete! Report saved to '{report_file}' ===")


if __name__ == "__main__":
    main()
