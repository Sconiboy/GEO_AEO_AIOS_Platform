"""
Domain Models for Manual Answer-Surface Observation Contracts (Sprint 4.1 Immutable Controls)
"""

import hashlib
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


from .enums import CaptureMethod


class ExtractionStatus(str, Enum):
    """Verification state of machine-extracted statements from raw answers."""

    PROPOSED_UNVERIFIED = "proposed_unverified"
    SOURCE_VERIFIED = "source_verified"
    HUMAN_APPROVED = "human_approved"
    REJECTED = "rejected"


class ExtractedStatement(BaseModel):
    """
    An individual statement extracted from a raw model response.
    Immutable model. Must remain PROPOSED_UNVERIFIED until verified against an OPENED_VERIFIED source record.
    """

    model_config = ConfigDict(frozen=True)

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
    Binds directly to an approved TargetQuery, QueryMap hash, Manifest hash, and frozen Source Ledger hash.
    """

    model_config = ConfigDict(frozen=True)

    observation_id: str = Field(..., description="Unique observation identifier")
    query_id: str = Field(..., description="Approved TargetQuery ID this observation answers")
    query_map_id: str = Field(..., description="QueryMap ID")
    source_ledger_run_id: str = Field(..., description="Linked Source Ledger AuditRun ID")

    # Content-Addressed Frozen Artifact Hash Bindings
    query_map_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 hash of bound QueryMap JSON artifact"
    )
    manifest_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 hash of bound DatasetManifest JSON artifact"
    )
    source_ledger_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 hash of bound frozen Source Ledger JSON artifact"
    )

    provider_name: str = Field(..., description="Model provider (e.g. OpenAI, Anthropic, Ollama)")
    model_identifier: str = Field(..., description="Exact model label (e.g. gpt-4o, claude-3-5-sonnet, hermes-3)")

    # Required capture timestamp (no silent default context)
    capture_timestamp: datetime = Field(..., description="Operator-provided capture timestamp")
    capture_method: CaptureMethod = Field(..., description="Capture method used")

    raw_answer_text: str = Field(..., min_length=10, description="Unmodified raw answer text")
    raw_answer_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 digest of raw_answer_text"
    )
    extracted_statements: List[ExtractedStatement] = Field(
        default_factory=list, description="List of proposed extracted statements"
    )
    operator_notes: Optional[str] = Field(default=None, description="Human operator notes")

    # Nullable locale/region (rendered explicitly as Unknown if None, no silent default context)
    locale: Optional[str] = Field(default=None, description="Language locale (e.g. en-US or None)")
    region: Optional[str] = Field(default=None, description="Geographic region (e.g. US or None)")

    @field_validator("raw_answer_sha256", "query_map_sha256", "manifest_sha256", "source_ledger_sha256")
    @classmethod
    def clean_hash_lowercase(cls, v: str) -> str:
        return v.strip().lower()

    def verify_integrity(self) -> bool:
        """
        Re-verifies that raw_answer_sha256 exactly matches the SHA-256 digest of raw_answer_text.
        Returns True if intact, False if mutated or corrupted.
        """
        calculated_hash = hashlib.sha256(self.raw_answer_text.encode("utf-8")).hexdigest()
        return self.raw_answer_sha256.lower() == calculated_hash.lower()
