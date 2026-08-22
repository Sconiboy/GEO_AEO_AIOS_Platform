"""Persist a citation-classification gap-analysis record from frozen artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest
from src.domain.models import AuditRun
from src.domain.observation import AnswerObservation
from src.domain.profile import SubjectProfile
from src.domain.query_map import QueryMap


def load_model(path: Path, model_class: object) -> object:
    return model_class.model_validate_json(path.read_bytes())  # type: ignore[attr-defined]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a frozen artifact-backed observation without semantic promotion."
    )
    parser.add_argument("--query-map", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--subject-profile", type=Path, required=True)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw_qm = args.query_map.read_bytes()
    raw_manifest = args.manifest.read_bytes()
    raw_ledger = args.source_ledger.read_bytes()
    raw_profile = args.subject_profile.read_bytes()

    query_map = QueryMap.model_validate_json(raw_qm)
    manifest = DatasetManifest.model_validate_json(raw_manifest)
    source_ledger = AuditRun.model_validate_json(raw_ledger)
    subject_profile = SubjectProfile.model_validate_json(raw_profile)
    observation = AnswerObservation.model_validate_json(args.observation.read_bytes())

    if not observation.verify_integrity():
        raise ValueError("Refusing to analyze an observation that fails capture-artifact verification.")

    analysis = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=subject_profile,
        observation=observation,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm,
        raw_manifest_bytes=raw_manifest,
        raw_ledger_bytes=raw_ledger,
        raw_profile_bytes=raw_profile,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(analysis.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Persisted citation-classification record: {args.output}")


if __name__ == "__main__":
    main()
