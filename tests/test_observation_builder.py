"""Regression tests for artifact-backed observation construction."""

from pathlib import Path

from scripts.create_artifact_backed_observation import read_raw_output


def test_read_raw_output_matches_transcript_parser_boundary(tmp_path: Path) -> None:
    """A valid raw-output file may have a terminal newline from file serialization."""
    raw_output = tmp_path / "raw_output.txt"
    raw_output.write_text("Visible answer text\n", encoding="utf-8")

    assert read_raw_output(raw_output) == "Visible answer text"
