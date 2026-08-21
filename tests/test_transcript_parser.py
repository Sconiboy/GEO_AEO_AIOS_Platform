"""
Unit tests for TranscriptParser and ParsedTranscriptRecord schema (Sprint 7.6.3)
"""

import hashlib
from pathlib import Path
import pytest
from src.collector.transcript_parser import TranscriptParser


def test_transcript_parser_valid_content() -> None:
    content = Path("data/captures/hermes3_q001_raw.txt").read_text()
    parsed = TranscriptParser.parse_transcript(content)

    assert parsed.query_id == "q-001"
    assert parsed.provider_name == "Ollama / Local Operator Console"
    assert parsed.model_identifier == "hermes-3-llama-3.1-8b"
    assert parsed.operator_identity == "operator-benjamin"
    assert "Python's core language design philosophy" in parsed.raw_output_text
    assert parsed.raw_output_sha256 == hashlib.sha256(parsed.raw_output_text.encode("utf-8")).hexdigest()


def test_transcript_parser_missing_header_raises_error() -> None:
    content = "Invalid header\nSession ID: 123\n"
    with pytest.raises(ValueError, match="missing header"):
        TranscriptParser.parse_transcript(content)


def test_transcript_parser_missing_footer_raises_error() -> None:
    content = "[OPERATOR CONSOLE RAW TRANSCRIPT EXPORT]\nSession ID: 123\n"
    with pytest.raises(ValueError, match="missing footer"):
        TranscriptParser.parse_transcript(content)


def test_transcript_parser_missing_output_stream_marker_raises_error() -> None:
    content = (
        "[OPERATOR CONSOLE RAW TRANSCRIPT EXPORT]\n"
        "Session ID: 123\n"
        "Timestamp: 2026-08-21T02:55:00Z\n"
        "Provider: Ollama\n"
        "Model: hermes-3\n"
        "Operator: benjamin\n"
        "Query ID: q-001\n"
        "[END OF TRANSCRIPT EXPORT]\n"
    )
    with pytest.raises(ValueError, match="missing 'Raw Model Output Stream:' marker"):
        TranscriptParser.parse_transcript(content)
