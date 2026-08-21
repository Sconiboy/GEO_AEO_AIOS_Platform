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
    observation_path: Path,
    output_path: Optional[Path] = None,
) -> int:
    """
    Executes manual Answer-Surface Observation import and renders an Observation Record.
    """
    print(f"🎯 Loading QueryMap: {query_map_path}")
    print(f"📜 Loading Dataset Manifest: {manifest_path}")
    print(f"🔬 Loading Observation: {observation_path}")

    try:
        with open(query_map_path, "r", encoding="utf-8") as f:
            qm_data = json.load(f)
        query_map = QueryMap.model_validate(qm_data)

        with open(manifest_path, "r", encoding="utf-8") as f:
            man_data = json.load(f)
        manifest = DatasetManifest.model_validate(man_data)

        with open(observation_path, "r", encoding="utf-8") as f:
            obs_data = json.load(f)
        observation = AnswerObservation.model_validate(obs_data)

        # Step 1: Run query map to build source ledger
        runner = QueryMapRunner()
        source_ledger = runner.run_query_map_audit(query_map, manifest)

        # Step 2: Validate observation against query map and source ledger
        validated_obs = ObservationImporter.import_observation(
            observation=observation, query_map=query_map, source_ledger=source_ledger
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
                args.query_map, args.manifest, args.observation, args.output
            )
        )


if __name__ == "__main__":
    main()
