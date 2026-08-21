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


class CaptureArtifact(BaseModel):
    """
    Immutable capture artifact contract binding a preserved raw transcript, console export, or screenshot.
    """

    model_config = ConfigDict(frozen=True)

    artifact_id: str = Field(..., description="Unique capture artifact identifier")
    session_id: str = Field(..., min_length=1, description="Console or API session identifier")
    artifact_type: str = Field(..., description="Artifact category (e.g. raw_transcript_export, console_log_export, session_screenshot)")
    artifact_path_or_uri: str = Field(..., description="Relative or absolute path/URI to preserved raw capture artifact file")
    artifact_sha256: str = Field(..., min_length=64, max_length=64, description="SHA-256 digest of preserved raw capture artifact file")
    raw_output_sha256: str = Field(..., min_length=64, max_length=64, description="SHA-256 digest of raw output stream extracted from artifact")
    operator_identity: str = Field(..., description="Authenticated operator username or key label")
    captured_at: datetime = Field(..., description="Timestamp when artifact was preserved")

    @field_validator("artifact_sha256", "raw_output_sha256")
    @classmethod
    def clean_hash_lowercase(cls, v: str) -> str:
        return v.strip().lower()


class AnswerObservation(BaseModel):
    """
    Immutable observation record capturing a raw answer surface response from a named model.
    Binds directly to an approved TargetQuery, QueryMap hash, Manifest hash, and frozen Source Ledger hash.
    Optionally binds an immutable CaptureArtifact for artifact-backed provenance verification.
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

    # Optional bound transcript/export capture artifact
    capture_artifact: Optional[CaptureArtifact] = Field(
        default=None, description="Bound raw transcript export or screenshot capture artifact"
    )

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

    @property
    def is_artifact_backed(self) -> bool:
        """
        Returns True if observation has a valid bound CaptureArtifact.
        """
        return self.capture_artifact is not None

    def verify_integrity(self) -> bool:
        """
        Re-verifies raw_answer_sha256 against raw_answer_text.
        If capture_artifact is bound, performs strict fail-closed verification:
        1. Checks capture_artifact.raw_output_sha256 == self.raw_answer_sha256.
        2. Fails closed if artifact_path_or_uri is missing or unreadable on disk.
        3. Verifies file_bytes SHA-256 == capture_artifact.artifact_sha256.
        4. Parses raw transcript content using TranscriptParser and verifies parsed output SHA-256 == self.raw_answer_sha256.
        5. Verifies parsed query_id, provider_name, and model_identifier match observation metadata.
        6. Verifies parsed operator_identity and session_id match capture_artifact metadata.
        7. Verifies parsed timestamp equals capture_timestamp and captured_at after UTC normalization.
        Returns True if all checks pass, False if any check fails or is missing.
        """
        calculated_hash = hashlib.sha256(self.raw_answer_text.encode("utf-8")).hexdigest()
        if self.raw_answer_sha256.lower() != calculated_hash.lower():
            return False

        if self.capture_artifact is not None:
            # Check 1: Declared raw_output_sha256 must match observation's raw_answer_sha256
            if self.capture_artifact.raw_output_sha256.lower() != self.raw_answer_sha256.lower():
                return False

            # Check 2: File must exist on disk (fail closed!)
            from pathlib import Path
            art_path = Path(self.capture_artifact.artifact_path_or_uri)
            if not (art_path.exists() and art_path.is_file()):
                return False

            # Check 3: File content SHA-256 must match artifact_sha256
            file_bytes = art_path.read_bytes()
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            if file_hash.lower() != self.capture_artifact.artifact_sha256.lower():
                return False

            # Check 4-7: Parse transcript and verify content + metadata + timestamp matching
            try:
                from datetime import timezone
                from ..collector.transcript_parser import TranscriptParser
                parsed_text = file_bytes.decode("utf-8")
                parsed = TranscriptParser.parse_transcript(parsed_text)

                if parsed.raw_output_sha256.lower() != self.raw_answer_sha256.lower():
                    return False
                if parsed.query_id != self.query_id:
                    return False
                if parsed.provider_name != self.provider_name:
                    return False
                if parsed.model_identifier != self.model_identifier:
                    return False
                if parsed.operator_identity != self.capture_artifact.operator_identity:
                    return False
                if parsed.session_id != self.capture_artifact.session_id:
                    return False

                # Timezone-normalized timestamp comparison
                parsed_utc = parsed.timestamp.astimezone(timezone.utc)
                obs_utc = self.capture_timestamp.astimezone(timezone.utc)
                art_utc = self.capture_artifact.captured_at.astimezone(timezone.utc)

                if parsed_utc != obs_utc or parsed_utc != art_utc:
                    return False

            except Exception:
                return False

        return True
