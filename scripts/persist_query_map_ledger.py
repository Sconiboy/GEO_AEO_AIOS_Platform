"""Persist an approved QueryMap run as canonical ledger JSON plus Markdown.

This operational runner uses the existing governed QueryMapRunner. It does not
create candidates, relax policy, or adjudicate semantic claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.collector.query_map_runner import DatasetManifest, QueryMapRunner
from src.domain.query_map import QueryMap
from src.exporter.report import ReportExporter


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an approved QueryMap and persist its canonical source ledger."
    )
    parser.add_argument("--query-map", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ledger-json", type=Path, required=True)
    parser.add_argument("--ledger-markdown", type=Path, required=True)
    args = parser.parse_args()

    raw_query_map = args.query_map.read_bytes()
    raw_manifest = args.manifest.read_bytes()
    query_map = QueryMap.model_validate_json(raw_query_map)
    manifest = DatasetManifest.model_validate_json(raw_manifest)

    ledger = QueryMapRunner().run_query_map_audit(query_map, manifest)

    args.ledger_json.parent.mkdir(parents=True, exist_ok=True)
    args.ledger_json.write_text(
        json.dumps(ledger.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    args.ledger_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.ledger_markdown.write_text(
        ReportExporter.export_source_ledger(ledger), encoding="utf-8"
    )

    print(f"Persisted canonical ledger JSON: {args.ledger_json}")
    print(f"Persisted ledger report: {args.ledger_markdown}")


if __name__ == "__main__":
    main()
