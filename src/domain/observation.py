"""
Domain Models for Manual Answer-Surface Observation Contracts
"""

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class CaptureMethod(str, Enum):
    """Method used to capture answer surface response."""

    MANUAL_PASTE = "manual_paste"
    HUMAN_OPERATOR_CONSOLE = "human_operator_console"
    SYNTHETIC_FIXTURE_IMPORT = "synthetic_fixture_import"


class ExtractionStatus(str, Enum):
    """Verification state of machine-extracted statements from raw answers."""

    PROPOSED_UNVERIFIED = "proposed_unverified"
    SOURCE_VERIFIED = "source_verified"
    HUMAN_APPROVED = "human_approved"
    REJECTED = "rejected"


class ExtractedStatement(BaseModel):
    """
    An individual statement extracted from a raw model response.
    Must remain PROPOSED_UNVERIFIED until verified against a source ledger.
    """

    statement_id: str = Field(..., description="Unique statement identifier")
    text: str = Field(..., min_length=5, description="Extracted statement text")
    extraction_status: ExtractionStatus = Field(
        default=ExtractionStatus.PROPOSED_UNVERIFIED,
        description="Verification state of this extracted proposal",
    )
    linked_evidence_id: Optional[str] = Field(
        default=None, description="Linked EvidenceRecord ID if verified"
    )
    human_notes: Optional[str] = Field(
        default=None, description="Human auditor review notes"
    )


class AnswerObservation(BaseModel):
    """
    Immutable observation record capturing a raw answer surface response from a named model.
    Binds directly to an approved TargetQuery and Source Ledger AuditRun.
    """

    observation_id: str = Field(..., description="Unique observation identifier")
    query_id: str = Field(..., description="Approved TargetQuery ID this observation answers")
    query_map_id: str = Field(..., description="QueryMap ID")
    source_ledger_run_id: str = Field(..., description="Linked Source Ledger AuditRun ID")
    provider_name: str = Field(..., description="Model provider (e.g. OpenAI, Anthropic, Ollama)")
    model_identifier: str = Field(..., description="Exact model label (e.g. gpt-4o, claude-3-5-sonnet, hermes-3)")
    capture_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of manual answer capture",
    )
    capture_method: CaptureMethod = Field(..., description="Capture method used")
    raw_answer_text: str = Field(..., min_length=10, description="Unmodified raw answer text")
    raw_answer_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 digest of raw_answer_text"
    )
    extracted_statements: List[ExtractedStatement] = Field(
        default_factory=list, description="List of proposed extracted statements"
    )
    operator_notes: Optional[str] = Field(default=None, description="Human operator notes")
    locale: Optional[str] = Field(default="en-US", description="Language locale")
    region: Optional[str] = Field(default="US", description="Geographic region")

    @field_validator("raw_answer_sha256")
    @classmethod
    def validate_hash_integrity(cls, v: str, info: object) -> str:
        """Validates that raw_answer_sha256 matches the SHA-256 digest of raw_answer_text."""
        raw_text = getattr(info, "data", {}).get("raw_answer_text")
        if raw_text is not None:
            expected_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            if v.lower() != expected_hash.lower():
                raise ValueError(
                    f"Integrity failure: raw_answer_sha256 ('{v}') does not match calculated digest of raw_answer_text ('{expected_hash}')"
                )
        return v.lower()
