"""Build a verified AnswerObservation from frozen input artifacts and a raw transcript."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.domain.enums import CaptureMethod
from src.domain.observation import AnswerObservation, CaptureArtifact


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_raw_output(path: Path) -> str:
    """Read the same bounded text form that TranscriptParser verifies."""
    return path.read_text(encoding="utf-8").strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a self-verifying artifact-backed answer observation."
    )
    parser.add_argument("--observation-id", required=True)
    parser.add_argument("--query-id", required=True)
    parser.add_argument("--query-map-id", required=True)
    parser.add_argument("--source-ledger-run-id", required=True)
    parser.add_argument("--query-map", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--timestamp", required=True)
    parser.add_argument("--locale", default="en-US")
    parser.add_argument("--region", default="US")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    timestamp = datetime.fromisoformat(args.timestamp.replace("Z", "+00:00"))
    raw_answer_text = read_raw_output(args.raw_output)

    capture_artifact = CaptureArtifact(
        artifact_id=f"artifact-{args.observation_id}",
        session_id=args.session_id,
        artifact_type="operator_console_raw_transcript_export",
        artifact_path_or_uri=str(args.transcript.resolve()),
        artifact_sha256=sha256_file(args.transcript),
        raw_output_sha256=hashlib.sha256(raw_answer_text.encode("utf-8")).hexdigest(),
        operator_identity=args.operator,
        captured_at=timestamp,
    )

    observation = AnswerObservation(
        observation_id=args.observation_id,
        query_id=args.query_id,
        query_map_id=args.query_map_id,
        source_ledger_run_id=args.source_ledger_run_id,
        query_map_sha256=sha256_file(args.query_map),
        manifest_sha256=sha256_file(args.manifest),
        source_ledger_sha256=sha256_file(args.source_ledger),
        provider_name=args.provider,
        model_identifier=args.model,
        capture_timestamp=timestamp,
        capture_method=CaptureMethod.HUMAN_OPERATOR_CONSOLE,
        capture_artifact=capture_artifact,
        raw_answer_text=raw_answer_text,
        raw_answer_sha256=hashlib.sha256(raw_answer_text.encode("utf-8")).hexdigest(),
        extracted_statements=[],
        operator_notes=(
            "Bounded public non-client pre-pilot. Visible cited answer captured after "
            "the approved QueryMap, DatasetManifest, SubjectProfile, and initial "
            "source ledger were frozen."
        ),
        locale=args.locale,
        region=args.region,
    )

    if not observation.verify_integrity():
        raise ValueError("Refusing to persist an observation that fails artifact integrity verification.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(observation.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Persisted verified observation: {args.output}")


if __name__ == "__main__":
    main()
