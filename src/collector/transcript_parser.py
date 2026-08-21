"""
Parseable Raw Transcript Schema and Parser for Answer Observation Artifact Verification (Sprint 7.6.3)
"""

import hashlib
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ParsedTranscriptRecord(BaseModel):
    """
    Structured record extracted from a preserved raw transcript export file.
    """

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(..., description="Console or API session identifier")
    timestamp: datetime = Field(..., description="Capture timestamp extracted from header")
    provider_name: str = Field(..., description="Model provider name extracted from header")
    model_identifier: str = Field(..., description="Exact model label extracted from header")
    operator_identity: str = Field(..., description="Authenticated operator username or key label")
    query_id: str = Field(..., description="Approved TargetQuery ID extracted from header")
    prompt_text: str = Field(..., description="Raw prompt text submitted to model")
    raw_output_text: str = Field(..., min_length=1, description="Extracted raw model output text")
    raw_output_sha256: str = Field(..., min_length=64, max_length=64, description="SHA-256 digest of extracted raw_output_text")


class TranscriptParser:
    """
    Parser for structured raw console transcript exports.
    Extracts header metadata and bounded raw output stream text.
    """

    @classmethod
    def parse_transcript(cls, transcript_content: str) -> ParsedTranscriptRecord:
        """
        Parses structured raw transcript content.
        Raises ValueError if transcript header syntax or output boundary markers are invalid.
        """
        if "[OPERATOR CONSOLE RAW TRANSCRIPT EXPORT]" not in transcript_content:
            raise ValueError("Invalid transcript format: missing header '[OPERATOR CONSOLE RAW TRANSCRIPT EXPORT]'.")

        if "[END OF TRANSCRIPT EXPORT]" not in transcript_content:
            raise ValueError("Invalid transcript format: missing footer '[END OF TRANSCRIPT EXPORT]'.")

        if "Raw Model Output Stream:" not in transcript_content:
            raise ValueError("Invalid transcript format: missing 'Raw Model Output Stream:' marker.")

        # Extract header metadata
        session_match = re.search(r"Session ID:\s*(.+)", transcript_content)
        ts_match = re.search(r"Timestamp:\s*(.+)", transcript_content)
        provider_match = re.search(r"Provider:\s*(.+)", transcript_content)
        model_match = re.search(r"Model:\s*(.+)", transcript_content)
        operator_match = re.search(r"Operator:\s*(.+)", transcript_content)
        query_match = re.search(r"Query ID:\s*(.+)", transcript_content)
        prompt_match = re.search(r"Prompt:\s*\"([^\"]+)\"|Prompt:\s*(.+)", transcript_content)

        if not (session_match and ts_match and provider_match and model_match and operator_match and query_match):
            raise ValueError("Invalid transcript format: missing one or more required header fields.")

        session_id = session_match.group(1).strip()
        ts_str = ts_match.group(1).strip()
        provider_name = provider_match.group(1).strip()
        model_identifier = model_match.group(1).strip()
        operator_identity = operator_match.group(1).strip()
        query_id = query_match.group(1).strip()

        prompt_text = ""
        if prompt_match:
            prompt_text = (prompt_match.group(1) or prompt_match.group(2) or "").strip()

        try:
            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid transcript timestamp format '{ts_str}': {e}") from e

        # Extract bounded raw output stream
        output_start = transcript_content.find("Raw Model Output Stream:") + len("Raw Model Output Stream:")
        output_end = transcript_content.find("[END OF TRANSCRIPT EXPORT]")

        if output_start >= output_end:
            raise ValueError("Invalid transcript format: output stream section empty or misaligned.")

        raw_output_text = transcript_content[output_start:output_end].strip()
        raw_output_sha256 = hashlib.sha256(raw_output_text.encode("utf-8")).hexdigest().lower()

        return ParsedTranscriptRecord(
            session_id=session_id,
            timestamp=timestamp,
            provider_name=provider_name,
            model_identifier=model_identifier,
            operator_identity=operator_identity,
            query_id=query_id,
            prompt_text=prompt_text,
            raw_output_text=raw_output_text,
            raw_output_sha256=raw_output_sha256,
        )
