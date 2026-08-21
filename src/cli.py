"""
Internal Audit Console & CLI Runner for Evidence-Governed Audits
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

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
            if not reconciliation.verify_integrity():
                raise ValueError(
                    f"Integrity failure: Stored Reconciliation JSON artifact '{reconciliation_json_path}' failed digest verification."
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
    rec_parser.add_argument(
        "--reconciliation-json",
        type=Path,
        required=False,
        help="Optional path to write or read versioned ObservationReconciliation JSON artifact",
    )

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


if __name__ == "__main__":
    main()

