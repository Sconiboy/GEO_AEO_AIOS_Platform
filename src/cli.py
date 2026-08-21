"""
Internal Audit Console & CLI Runner for Evidence-Governed Audits
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .domain.models import AuditRun
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

    args = parser.parse_args()

    if args.command == "audit":
        sys.exit(run_cli_audit(args.fixture, args.output))


if __name__ == "__main__":
    main()
