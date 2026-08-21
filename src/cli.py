"""
Internal Audit Console & CLI Runner for Evidence-Governed Audits
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import List, Optional

from .collector.observation_importer import ObservationImporter
from .collector.query_map_runner import DatasetManifest, QueryMapRunner
from .collector.reconciler import ClaimReconciler
from .collector.verifier import SourceVerifier
from .domain.enums import SourceType
from .domain.models import AuditRun
from .domain.observation import AnswerObservation
from .domain.query_map import QueryMap
from .domain.validators import EvidenceLedgerValidationError, validate_audit_run_ledger
from .exporter.report import ReportExporter


def load_audit_run_from_json(file_path: Path) -> AuditRun:
    """Loads and parses an AuditRun from a JSON fixture file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return AuditRun.model_validate(data)


def run_cli_audit(fixture_path: Path, output_path: Optional[Path] = None) -> int:
    """
    Executes an offline audit run:
    1. Loads fixture JSON data.
    2. Validates evidence ledger contracts.
    3. Renders and saves/prints auditable Markdown report.
    """
    print(f"🔍 Loading audit fixture from: {fixture_path}")

    try:
        audit_run = load_audit_run_from_json(fixture_path)
        print(
            f"✅ Fixture loaded successfully. Run ID: {audit_run.run_id} | Client: {audit_run.client_domain}"
        )

        print("⚡ Running evidence ledger validation...")
        validated_run = validate_audit_run_ledger(audit_run)
        print(
            f"✅ Evidence validation PASSED for {len(validated_run.claims)} claim(s)."
        )

        markdown_content = ReportExporter.export_to_markdown(validated_run)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"📄 Audit report exported to: {output_path}")
        else:
            print("\n" + "=" * 50)
            print(markdown_content)
            print("=" * 50)

        return 0

    except EvidenceLedgerValidationError as e:
        print(f"\n❌ AUDIT VALIDATION FAILED: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        return 1


def run_cli_verify_source(
    url: str, excerpt: str, source_type_str: str = "independent_editorial"
) -> int:
    """
    Executes live source verification CLI command:
    Fetches public URL, stores immutable snapshot, verifies quote alignment, and prints result.
    """
    print(f"🌐 Verifying live source URL: {url}")
    print(f"📝 Candidate Excerpt: \"{excerpt}\"")

    try:
        source_type = SourceType(source_type_str.lower())
    except ValueError:
        print(f"❌ Invalid source type '{source_type_str}'. Allowed: {[st.value for st in SourceType]}", file=sys.stderr)
        return 1

    verifier = SourceVerifier()
    evidence_record = verifier.verify_url(
        url=url, candidate_excerpt=excerpt, source_type=source_type
    )

    print(f"\n📊 VERIFICATION RESULT:")
    print(f"- Status: {evidence_record.verification_status.value}")
    print(f"- Evidence ID: {evidence_record.evidence_id}")

    if evidence_record.failure_category:
        print(f"- Failure Category: {evidence_record.failure_category.value}")
    if evidence_record.failure_reason:
        print(f"- Failure Reason: {evidence_record.failure_reason}")

    if evidence_record.verification_artifact:
        art = evidence_record.verification_artifact
        print(f"- Snapshot Hash: {art.snapshot_sha256}")
        print(f"- Quote Exact Match: {art.quote_exact_match}")
        print(f"- Verifier Method: {art.verifier_method}")
        print(f"- Verifier Run ID: {art.verifier_run_id}")
    else:
        print(f"- Verification Artifact: NONE (Verification failed)")

    return 0 if evidence_record.verification_status.value == "opened_verified" else 1


def run_cli_query_map(
    query_map_path: Path, manifest_path: Path, output_path: Optional[Path] = None
) -> int:
    """
    Executes controlled QueryMap source verification against dataset manifest under domain allowlists.
    """
    print(f"🎯 Loading QueryMap: {query_map_path}")
    print(f"📜 Loading Dataset Manifest: {manifest_path}")

    try:
        with open(query_map_path, "r", encoding="utf-8") as f:
            qm_data = json.load(f)
        query_map = QueryMap.model_validate(qm_data)

        with open(manifest_path, "r", encoding="utf-8") as f:
            man_data = json.load(f)
        manifest = DatasetManifest.model_validate(man_data)

        print(f"✅ Loaded Entity: '{query_map.entity_name}' | Allowed Domains: {query_map.policy_profile.source_scope.allowed_domains}")

        runner = QueryMapRunner()
        audit_run = runner.run_query_map_audit(query_map, manifest)

        markdown_content = ReportExporter.export_source_ledger(audit_run)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"📄 Source Ledger exported to: {output_path}")
        else:
            print("\n" + "=" * 50)
            print(markdown_content)
            print("=" * 50)

        return 0

    except Exception as e:
        print(f"\n❌ QUERY-MAP RUN FAILED: {e}", file=sys.stderr)
        return 1


def run_cli_observation(
    query_map_path: Path,
    manifest_path: Path,
    source_ledger_path: Path,
    observation_path: Path,
    output_path: Optional[Path] = None,
) -> int:
    """
    Executes manual Answer-Surface Observation import against frozen JSON artifacts and renders an Observation Record.
    Hermetic and offline: makes ZERO network calls.
    """
    print(f"🎯 Loading QueryMap artifact: {query_map_path}")
    print(f"📜 Loading Dataset Manifest artifact: {manifest_path}")
    print(f"🏛️ Loading Frozen Source Ledger artifact: {source_ledger_path}")
    print(f"🔬 Loading Observation artifact: {observation_path}")

    try:
        raw_qm_bytes = query_map_path.read_bytes()
        query_map = QueryMap.model_validate(json.loads(raw_qm_bytes.decode("utf-8")))

        raw_manifest_bytes = manifest_path.read_bytes()
        manifest = DatasetManifest.model_validate(json.loads(raw_manifest_bytes.decode("utf-8")))

        raw_ledger_bytes = source_ledger_path.read_bytes()
        source_ledger = AuditRun.model_validate(json.loads(raw_ledger_bytes.decode("utf-8")))

        raw_obs_bytes = observation_path.read_bytes()
        observation = AnswerObservation.model_validate(json.loads(raw_obs_bytes.decode("utf-8")))

        # Validate observation against frozen JSON artifacts
        validated_obs = ObservationImporter.import_observation(
            observation=observation,
            query_map=query_map,
            manifest=manifest,
            source_ledger=source_ledger,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
        )

        markdown_content = ReportExporter.export_observation_record(
            observation=validated_obs, query_map=query_map
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"📄 Observation Record exported to: {output_path}")
        else:
            print("\n" + "=" * 50)
            print(markdown_content)
            print("=" * 50)

        return 0

    except Exception as e:
        print(f"\n❌ OBSERVATION IMPORT FAILED: {e}", file=sys.stderr)
        return 1


def run_cli_reconcile(
    query_map_path: Path,
    manifest_path: Path,
    source_ledger_path: Path,
    observation_path: Path,
    output_path: Optional[Path] = None,
    reconciliation_json_path: Optional[Path] = None,
) -> int:
    """
    Executes Claim Reconciliation against a frozen AnswerObservation and Source Ledger.
    Evaluates raw statement proposals semantically against source evidence.
    Persists versioned ObservationReconciliation JSON artifact and renders report.
    """
    print(f"🎯 Loading QueryMap artifact: {query_map_path}")
    print(f"📜 Loading Dataset Manifest artifact: {manifest_path}")
    print(f"🏛️ Loading Frozen Source Ledger artifact: {source_ledger_path}")
    print(f"🔬 Loading Observation artifact: {observation_path}")

    try:
        raw_qm_bytes = query_map_path.read_bytes()
        query_map = QueryMap.model_validate(json.loads(raw_qm_bytes.decode("utf-8")))

        raw_manifest_bytes = manifest_path.read_bytes()
        manifest = DatasetManifest.model_validate(json.loads(raw_manifest_bytes.decode("utf-8")))

        raw_ledger_bytes = source_ledger_path.read_bytes()
        source_ledger = AuditRun.model_validate(json.loads(raw_ledger_bytes.decode("utf-8")))

        raw_obs_bytes = observation_path.read_bytes()
        observation = AnswerObservation.model_validate(json.loads(raw_obs_bytes.decode("utf-8")))

        # Step 1: Validate observation import pipeline
        validated_obs = ObservationImporter.import_observation(
            observation=observation,
            query_map=query_map,
            manifest=manifest,
            source_ledger=source_ledger,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
        )

        # Step 2: Load existing stored JSON reconciliation or generate fresh reconciliation
        from .domain.reconciliation import ObservationReconciliation

        if reconciliation_json_path and reconciliation_json_path.exists():
            print(f"📦 Loading pre-existing Reconciliation JSON artifact: {reconciliation_json_path}")
            rec_bytes = reconciliation_json_path.read_bytes()
            reconciliation = ObservationReconciliation.model_validate(
                json.loads(rec_bytes.decode("utf-8"))
            )
            # Gate 1: Check self-integrity digest
            if not reconciliation.verify_integrity():
                raise ValueError(
                    f"Integrity failure: Stored Reconciliation JSON artifact '{reconciliation_json_path}' failed digest verification."
                )

            # Gate 2: Check observation context bindings
            if reconciliation.observation_id != validated_obs.observation_id:
                raise ValueError(
                    f"Context mismatch: Stored reconciliation observation_id ('{reconciliation.observation_id}') "
                    f"does not match current observation ID ('{validated_obs.observation_id}')."
                )

            if reconciliation.raw_answer_sha256.lower() != validated_obs.raw_answer_sha256.lower():
                raise ValueError(
                    f"Context mismatch: Stored reconciliation raw_answer_sha256 ('{reconciliation.raw_answer_sha256}') "
                    f"does not match current observation digest ('{validated_obs.raw_answer_sha256}')."
                )

            # Gate 3: Check source ledger context bindings
            actual_ledger_sha256 = hashlib.sha256(raw_ledger_bytes).hexdigest()
            if reconciliation.source_ledger_run_id != source_ledger.run_id:
                raise ValueError(
                    f"Context mismatch: Stored reconciliation source_ledger_run_id ('{reconciliation.source_ledger_run_id}') "
                    f"does not match current source ledger run ID ('{source_ledger.run_id}')."
                )

            if reconciliation.source_ledger_sha256.lower() != actual_ledger_sha256.lower():
                raise ValueError(
                    f"Context mismatch: Stored reconciliation source_ledger_sha256 ('{reconciliation.source_ledger_sha256}') "
                    f"does not match current raw source ledger digest ('{actual_ledger_sha256}')."
                )

            # Gate 4: Check statement ID presence
            obs_stmt_ids = {s.statement_id for s in validated_obs.extracted_statements}
            for rec_stmt in reconciliation.reconciliations:
                if rec_stmt.statement_id not in obs_stmt_ids:
                    raise ValueError(
                        f"Context mismatch: Stored reconciliation contains statement_id ('{rec_stmt.statement_id}') "
                        f"which does not exist in current observation."
                    )
        else:
            print("⚡ Reconciling statement proposals against source ledger...")
            reconciliation = ClaimReconciler.reconcile_observation(
                observation=validated_obs,
                source_ledger=source_ledger,
                raw_ledger_bytes=raw_ledger_bytes,
            )

        # Step 3: Persist canonical versioned JSON artifact if path specified
        if reconciliation_json_path:
            reconciliation_json_path.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(reconciliation.model_dump(mode="json"), indent=2)
            reconciliation_json_path.write_text(serialized, encoding="utf-8")
            print(f"💾 Saved versioned Reconciliation JSON artifact to: {reconciliation_json_path}")

        # Step 4: Render Markdown report
        markdown_content = ReportExporter.export_reconciliation_record(
            reconciliation=reconciliation,
            observation=validated_obs,
            query_map=query_map,
            source_ledger=source_ledger,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"📄 Claim Reconciliation Record exported to: {output_path}")
        else:
            print("\n" + "=" * 50)
            print(markdown_content)
            print("=" * 50)

        return 0

    except Exception as e:
        print(f"\n❌ CLAIM RECONCILIATION FAILED: {e}", file=sys.stderr)
        return 1


def run_cli_human_decision(
    query_map_path: Path,
    manifest_path: Path,
    source_ledger_path: Path,
    observation_path: Path,
    statement_id: str,
    status_str: str,
    evidence_ids: List[str],
    quotes: List[str],
    rationale: str,
    auditor_identity: str = "Lead Systems Architect & Auditor",
    output_json_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> int:
    """
    Executes a formal Human Auditor Adjudication operation.
    Transitions a statement proposal from NOT_ASSESSABLE to SUPPORTED/CONTRADICTED backed by explicit human decision.
    Validates all 6 context bindings, verifies verbatim quoted passages against opened evidence excerpts,
    computes canonical digest, persists HumanDecisionRecord JSON, and exports Markdown.
    """
    from .domain.enums import ReconciliationStatus
    from .domain.human_decision import HumanDecisionRecord, HumanStatementDecision, QuotedEvidencePassage

    print(f"🏛️ Executing Human Auditor Semantic Adjudication for statement: {statement_id}")
    print(f"🎯 QueryMap: {query_map_path}")
    print(f"📜 Manifest: {manifest_path}")
    print(f"🏛️ Source Ledger: {source_ledger_path}")
    print(f"🔬 Observation: {observation_path}")

    try:
        raw_qm_bytes = query_map_path.read_bytes()
        qm_sha256 = hashlib.sha256(raw_qm_bytes).hexdigest()
        query_map = QueryMap.model_validate(json.loads(raw_qm_bytes.decode("utf-8")))

        raw_manifest_bytes = manifest_path.read_bytes()
        manifest_sha256 = hashlib.sha256(raw_manifest_bytes).hexdigest()
        manifest = DatasetManifest.model_validate(json.loads(raw_manifest_bytes.decode("utf-8")))

        raw_ledger_bytes = source_ledger_path.read_bytes()
        ledger_sha256 = hashlib.sha256(raw_ledger_bytes).hexdigest()
        source_ledger = AuditRun.model_validate(json.loads(raw_ledger_bytes.decode("utf-8")))

        raw_obs_bytes = observation_path.read_bytes()
        observation = AnswerObservation.model_validate(json.loads(raw_obs_bytes.decode("utf-8")))

        # Validate observation import & context bindings
        validated_obs = ObservationImporter.import_observation(
            observation=observation,
            query_map=query_map,
            manifest=manifest,
            source_ledger=source_ledger,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
        )

        # Validate statement_id existence in observation
        stmt_obj = next((s for s in validated_obs.extracted_statements if s.statement_id == statement_id), None)
        if not stmt_obj:
            raise ValueError(f"Statement ID '{statement_id}' does not exist in observation '{validated_obs.observation_id}'.")

        if len(evidence_ids) != len(quotes):
            raise ValueError(f"Length mismatch: {len(evidence_ids)} evidence IDs provided for {len(quotes)} quotes.")

        quoted_evidence_list: List[QuotedEvidencePassage] = []

        # Validate each quote against opened_excerpt
        for eid, quote in zip(evidence_ids, quotes):
            if eid not in source_ledger.evidence_ledger:
                raise ValueError(f"Evidence ID '{eid}' does not exist in Source Ledger.")
            ev = source_ledger.evidence_ledger[eid]
            if ev.verification_status.value != "opened_verified":
                raise ValueError(f"Evidence ID '{eid}' has status '{ev.verification_status.value}', not 'opened_verified'.")

            # Verbatim normalized substring check against opened_excerpt
            norm_quote = " ".join(quote.strip().split())
            norm_excerpt = " ".join(ev.opened_excerpt.strip().split())
            if norm_quote not in norm_excerpt:
                raise ValueError(
                    f"Fabricated quote rejected: Passage '{quote}' is not a verbatim substring of opened_excerpt for evidence record '{eid}'."
                )

            snap_hash = ev.verification_artifact.snapshot_sha256 if ev.verification_artifact else None
            quoted_evidence_list.append(
                QuotedEvidencePassage(
                    evidence_id=eid,
                    quoted_passage=quote,
                    snapshot_sha256=snap_hash,
                )
            )

        status_enum = ReconciliationStatus(status_str.lower())

        stmt_decision = HumanStatementDecision(
            decision_id=f"hdec-{statement_id}",
            statement_id=statement_id,
            decision_status=status_enum,
            quoted_evidence=quoted_evidence_list,
            auditor_rationale=rationale,
            declared_reviewer_identity=auditor_identity,
        )

        rec_id = f"hdec-rec-{validated_obs.observation_id}"

        canonical_digest = HumanDecisionRecord.compute_canonical_digest(
            decision_record_id=rec_id,
            observation_id=validated_obs.observation_id,
            raw_answer_sha256=validated_obs.raw_answer_sha256,
            source_ledger_run_id=source_ledger.run_id,
            source_ledger_sha256=ledger_sha256,
            query_map_sha256=qm_sha256,
            manifest_sha256=manifest_sha256,
            decisions=[stmt_decision],
        )

        decision_record = HumanDecisionRecord(
            decision_record_id=rec_id,
            observation_id=validated_obs.observation_id,
            raw_answer_sha256=validated_obs.raw_answer_sha256,
            source_ledger_run_id=source_ledger.run_id,
            source_ledger_sha256=ledger_sha256,
            query_map_sha256=qm_sha256,
            manifest_sha256=manifest_sha256,
            decisions=[stmt_decision],
            canonical_digest=canonical_digest,
        )

        if output_json_path:
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(decision_record.model_dump(mode="json"), indent=2)
            output_json_path.write_text(serialized, encoding="utf-8")
            print(f"💾 Saved versioned HumanDecisionRecord JSON artifact to: {output_json_path}")

        markdown_content = ReportExporter.export_human_decision_record(
            decision_record=decision_record,
            observation=validated_obs,
            query_map=query_map,
            source_ledger=source_ledger,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown_content, encoding="utf-8")
            print(f"📄 Human Semantic Decision Record exported to: {output_path}")
        else:
            print("\n" + "=" * 50)
            print(markdown_content)
            print("=" * 50)

        return 0

    except Exception as e:
        print(f"\n❌ HUMAN DECISION ADJUDICATION FAILED: {e}", file=sys.stderr)
        return 1


def run_cli_analyze_gaps(
    query_map_path: Path,
    manifest_path: Path,
    source_ledger_path: Path,
    observation_path: Path,
    human_decision_path: Optional[Path] = None,
    output_json_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> int:
    """
    Executes Forensic Competitor Evidence-Gap Analysis.
    Detects competitor citation patterns, client evidence gaps, and confidence-bounded ethical action plans.
    Persists versioned ForensicGapAnalysisRecord JSON and exports Markdown report.
    """
    from .collector.gap_analyzer import ForensicGapAnalyzer
    from .domain.human_decision import HumanDecisionRecord

    print(f"🎯 Executing Forensic Evidence-Gap Analysis for observation: {observation_path}")
    print(f"🎯 QueryMap: {query_map_path}")
    print(f"📜 Manifest: {manifest_path}")
    print(f"🏛️ Source Ledger: {source_ledger_path}")

    try:
        raw_qm_bytes = query_map_path.read_bytes()
        query_map = QueryMap.model_validate(json.loads(raw_qm_bytes.decode("utf-8")))

        raw_manifest_bytes = manifest_path.read_bytes()
        manifest = DatasetManifest.model_validate(json.loads(raw_manifest_bytes.decode("utf-8")))

        raw_ledger_bytes = source_ledger_path.read_bytes()
        source_ledger = AuditRun.model_validate(json.loads(raw_ledger_bytes.decode("utf-8")))

        raw_obs_bytes = observation_path.read_bytes()
        observation = AnswerObservation.model_validate(json.loads(raw_obs_bytes.decode("utf-8")))

        # Validate observation import pipeline
        validated_obs = ObservationImporter.import_observation(
            observation=observation,
            query_map=query_map,
            manifest=manifest,
            source_ledger=source_ledger,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
        )

        human_decision: Optional[HumanDecisionRecord] = None
        if human_decision_path and human_decision_path.exists():
            hdec_bytes = human_decision_path.read_bytes()
            human_decision = HumanDecisionRecord.model_validate(json.loads(hdec_bytes.decode("utf-8")))
            if not human_decision.verify_integrity():
                raise ValueError(f"HumanDecisionRecord '{human_decision_path}' failed integrity verification.")

        gap_record = ForensicGapAnalyzer.analyze_gaps(
            observation=validated_obs,
            source_ledger=source_ledger,
            query_map=query_map,
            manifest=manifest,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            human_decision=human_decision,
        )

        if output_json_path:
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(gap_record.model_dump(mode="json"), indent=2)
            output_json_path.write_text(serialized, encoding="utf-8")
            print(f"💾 Saved versioned ForensicGapAnalysisRecord JSON artifact to: {output_json_path}")

        markdown_content = ReportExporter.export_gap_analysis_record(
            gap_record=gap_record,
            observation=validated_obs,
            query_map=query_map,
            source_ledger=source_ledger,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown_content, encoding="utf-8")
            print(f"📄 Forensic Gap Analysis Record exported to: {output_path}")
        else:
            print("\n" + "=" * 50)
            print(markdown_content)
            print("=" * 50)

        return 0

    except Exception as e:
        print(f"\n❌ FORENSIC GAP ANALYSIS FAILED: {e}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GEO/AEO Platform - Evidence-Governed Audit Console CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'audit' subcommand
    audit_parser = subparsers.add_parser(
        "audit", help="Run an evidence-governed audit on a fixture file"
    )
    audit_parser.add_argument(
        "--fixture",
        type=Path,
        required=True,
        help="Path to fixture JSON file containing AuditRun data",
    )
    audit_parser.add_argument(
        "--output",
        type=Path,
        required=False,
        help="Optional path to write generated Markdown report",
    )

    # 'verify-source' subcommand
    verify_parser = subparsers.add_parser(
        "verify-source", help="Execute live source verification on a public URL"
    )
    verify_parser.add_argument(
        "--url", type=str, required=True, help="Public URL to fetch and verify"
    )
    verify_parser.add_argument(
        "--excerpt", type=str, required=True, help="Candidate excerpt to match against raw bytes"
    )
    verify_parser.add_argument(
        "--source-type",
        type=str,
        default="independent_editorial",
        help="Source type classification (default: independent_editorial)",
    )

    # 'query-map' subcommand
    qm_parser = subparsers.add_parser(
        "query-map", help="Execute controlled QueryMap audit on a manifest dataset"
    )
    qm_parser.add_argument(
        "--query-map",
        type=Path,
        required=True,
        help="Path to QueryMap JSON definition",
    )
    qm_parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to pre-approved DatasetManifest JSON",
    )
    qm_parser.add_argument(
        "--output",
        type=Path,
        required=False,
        help="Optional path to write generated Source Ledger report",
    )

    # 'observation' subcommand
    obs_parser = subparsers.add_parser(
        "observation", help="Import manual Answer-Surface Observation and export Observation Record"
    )
    obs_parser.add_argument(
        "--query-map",
        type=Path,
        required=True,
        help="Path to QueryMap JSON definition",
    )
    obs_parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to pre-approved DatasetManifest JSON",
    )
    obs_parser.add_argument(
        "--source-ledger",
        type=Path,
        required=True,
        help="Path to frozen Source Ledger AuditRun JSON artifact",
    )
    obs_parser.add_argument(
        "--observation",
        type=Path,
        required=True,
        help="Path to AnswerObservation JSON definition",
    )
    obs_parser.add_argument(
        "--output",
        type=Path,
        required=False,
        help="Optional path to write generated Observation Record",
    )

    # 'reconcile' subcommand
    rec_parser = subparsers.add_parser(
        "reconcile", help="Reconcile Answer-Surface Observation statements against Source Ledger"
    )
    rec_parser.add_argument(
        "--query-map",
        type=Path,
        required=True,
        help="Path to QueryMap JSON definition",
    )
    rec_parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to pre-approved DatasetManifest JSON",
    )
    rec_parser.add_argument(
        "--source-ledger",
        type=Path,
        required=True,
        help="Path to frozen Source Ledger AuditRun JSON artifact",
    )
    rec_parser.add_argument(
        "--observation",
        type=Path,
        required=True,
        help="Path to AnswerObservation JSON definition",
    )
    rec_parser.add_argument(
        "--output",
        type=Path,
        required=False,
        help="Optional path to write generated Claim Reconciliation Record Markdown",
    )

    # 'human-decision' subcommand
    hdec_parser = subparsers.add_parser(
        "human-decision", help="Execute formal Human Auditor Semantic Adjudication operation"
    )
    hdec_parser.add_argument("--query-map", type=Path, required=True, help="Path to QueryMap JSON definition")
    hdec_parser.add_argument("--manifest", type=Path, required=True, help="Path to pre-approved DatasetManifest JSON")
    hdec_parser.add_argument("--source-ledger", type=Path, required=True, help="Path to frozen Source Ledger JSON artifact")
    hdec_parser.add_argument("--observation", type=Path, required=True, help="Path to AnswerObservation JSON definition")
    hdec_parser.add_argument("--statement-id", type=str, required=True, help="Target statement ID to adjudicate")
    hdec_parser.add_argument("--status", type=str, required=True, help="Adjudicated status (supported, unsupported, contradicted, not_assessable)")
    hdec_parser.add_argument("--evidence-id", type=str, action="append", required=True, help="Evaluated evidence ID(s)")
    hdec_parser.add_argument("--quote", type=str, action="append", required=True, help="Quoted supporting/refuting passage(s)")
    hdec_parser.add_argument("--rationale", type=str, required=True, help="Detailed auditor technical rationale")
    hdec_parser.add_argument("--auditor-identity", type=str, default="Lead Systems Architect & Auditor", help="Auditor identity or role")
    hdec_parser.add_argument("--output-json", type=Path, required=False, help="Optional path to write HumanDecisionRecord JSON")
    hdec_parser.add_argument("--output", type=Path, required=False, help="Optional path to write Markdown report")

    # 'analyze-gaps' subcommand
    gap_parser = subparsers.add_parser(
        "analyze-gaps", help="Execute Forensic Competitor Evidence-Gap Analysis"
    )
    gap_parser.add_argument("--query-map", type=Path, required=True, help="Path to QueryMap JSON definition")
    gap_parser.add_argument("--manifest", type=Path, required=True, help="Path to pre-approved DatasetManifest JSON")
    gap_parser.add_argument("--source-ledger", type=Path, required=True, help="Path to frozen Source Ledger JSON artifact")
    gap_parser.add_argument("--observation", type=Path, required=True, help="Path to AnswerObservation JSON definition")
    gap_parser.add_argument("--human-decision", type=Path, required=False, help="Optional path to HumanDecisionRecord JSON artifact")
    gap_parser.add_argument("--output-json", type=Path, required=False, help="Optional path to write ForensicGapAnalysisRecord JSON")
    gap_parser.add_argument("--output", type=Path, required=False, help="Optional path to write Markdown report")

    args = parser.parse_args()

    if args.command == "audit":
        sys.exit(run_cli_audit(args.fixture, args.output))
    elif args.command == "verify-source":
        sys.exit(run_cli_verify_source(args.url, args.excerpt, args.source_type))
    elif args.command == "query-map":
        sys.exit(run_cli_query_map(args.query_map, args.manifest, args.output))
    elif args.command == "observation":
        sys.exit(
            run_cli_observation(
                args.query_map,
                args.manifest,
                args.source_ledger,
                args.observation,
                args.output,
            )
        )
    elif args.command == "reconcile":
        sys.exit(
            run_cli_reconcile(
                args.query_map,
                args.manifest,
                args.source_ledger,
                args.observation,
                args.output,
                args.reconciliation_json,
            )
        )
    elif args.command == "human-decision":
        sys.exit(
            run_cli_human_decision(
                query_map_path=args.query_map,
                manifest_path=args.manifest,
                source_ledger_path=args.source_ledger,
                observation_path=args.observation,
                statement_id=args.statement_id,
                status_str=args.status,
                evidence_ids=args.evidence_id,
                quotes=args.quote,
                rationale=args.rationale,
                auditor_identity=args.auditor_identity,
                output_json_path=args.output_json,
                output_path=args.output,
            )
        )
    elif args.command == "analyze-gaps":
        sys.exit(
            run_cli_analyze_gaps(
                query_map_path=args.query_map,
                manifest_path=args.manifest,
                source_ledger_path=args.source_ledger,
                observation_path=args.observation,
                human_decision_path=args.human_decision,
                output_json_path=args.output_json,
                output_path=args.output,
            )
        )


if __name__ == "__main__":
    main()

