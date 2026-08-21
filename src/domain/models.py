"""
Domain Pydantic Models for Evidence Ledger and Audit Runs
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator

from .enums import ConfidenceRating, SourceType, VerificationStatus


class EvidenceRecord(BaseModel):
    """
    Represents a verified, opened-source evidence item.
    No model claim can exist in an audit report without a linked EvidenceRecord.
    """

    evidence_id: str = Field(
        ..., description="Unique deterministic ID (e.g. SHA-256 hash or UUID)"
    )
    url: str = Field(..., description="Canonical source URL")
    opened_excerpt: str = Field(
        ..., min_length=10, description="Exact opened-source text excerpt"
    )
    source_type: SourceType = Field(
        default=SourceType.UNKNOWN, description="Quality classification"
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED_STALE,
        description="Verification state",
    )
    retrieval_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of source retrieval",
    )
    snapshot_id: Optional[str] = Field(
        default=None, description="Reference ID to saved HTML/Markdown snapshot"
    )
    is_independent: bool = Field(
        default=False,
        description="True if source is an independent party (not vendor/affiliate)",
    )
    is_syndicated_duplicate: bool = Field(
        default=False, description="True if content is copied/syndicated"
    )

    @field_validator("opened_excerpt")
    @classmethod
    def excerpt_must_not_be_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Opened excerpt cannot be empty or whitespace only")
        return cleaned


class ConfidenceScore(BaseModel):
    """
    Deterministically derived confidence score based on concrete evidence metrics.
    Confidence is NOT a free-text model feeling; it is computed from visible inputs.
    """

    score: float = Field(
        ..., ge=0.0, le=1.0, description="Calculated score between 0.0 and 1.0"
    )
    rating: ConfidenceRating = Field(
        ..., description="Categorical rating based on calculated score"
    )
    verified_sources_count: int = Field(default=0, ge=0)
    independent_sources_count: int = Field(default=0, ge=0)
    distinct_source_types: int = Field(default=0, ge=0)
    has_circular_duplication: bool = Field(default=False)
    has_unresolved_counter_evidence: bool = Field(default=False)

    @classmethod
    def compute(
        cls,
        evidence_list: List[EvidenceRecord],
        counter_evidence_list: Optional[List[EvidenceRecord]] = None,
    ) -> "ConfidenceScore":
        """
        Computes a deterministic confidence score based on evidence metrics.
        """
        counter_evidence_list = counter_evidence_list or []

        verified = [
            e
            for e in evidence_list
            if e.verification_status == VerificationStatus.OPENED_VERIFIED
        ]
        verified_count = len(verified)

        if verified_count == 0:
            return cls(
                score=0.0,
                rating=ConfidenceRating.UNGROUNDED,
                verified_sources_count=0,
                independent_sources_count=0,
                distinct_source_types=0,
                has_circular_duplication=False,
                has_unresolved_counter_evidence=len(counter_evidence_list) > 0,
            )

        independent_count = sum(1 for e in verified if e.is_independent)
        source_types = {e.source_type for e in verified}
        distinct_types_count = len(source_types)

        has_circular = any(e.is_syndicated_duplicate for e in verified)
        has_counter = len(counter_evidence_list) > 0

        # Base scoring calculation
        calculated_score = 0.3  # Base score for having verified evidence
        calculated_score += min(0.3, verified_count * 0.1)  # Up to +0.3 for count
        calculated_score += min(0.2, independent_count * 0.1)  # Up to +0.2 for independence
        calculated_score += min(0.1, (distinct_types_count - 1) * 0.05)  # Diversity bonus

        if has_circular:
            calculated_score -= 0.2  # Penalty for circular duplication

        if has_counter:
            calculated_score -= 0.15  # Penalty for unresolved counter-evidence

        final_score = max(0.0, min(1.0, round(calculated_score, 2)))

        if final_score >= 0.8:
            rating = ConfidenceRating.HIGH
        elif final_score >= 0.5:
            rating = ConfidenceRating.MEDIUM
        elif final_score > 0.0:
            rating = ConfidenceRating.LOW
        else:
            rating = ConfidenceRating.UNGROUNDED

        return cls(
            score=final_score,
            rating=rating,
            verified_sources_count=verified_count,
            independent_sources_count=independent_count,
            distinct_source_types=distinct_types_count,
            has_circular_duplication=has_circular,
            has_unresolved_counter_evidence=has_counter,
        )


class ClaimRecord(BaseModel):
    """
    Represents an audit finding or conclusion statement.
    Must link to at least one verified EvidenceRecord ID.
    """

    claim_id: str = Field(..., description="Unique claim identifier")
    statement: str = Field(
        ..., min_length=5, description="The audit claim statement"
    )
    evidence_ids: List[str] = Field(
        ..., description="List of linked EvidenceRecord IDs supporting this claim"
    )
    counter_evidence_ids: List[str] = Field(
        default_factory=list,
        description="Optional list of EvidenceRecord IDs presenting counter-evidence",
    )
    uncertainty_notes: Optional[str] = Field(
        default=None, description="Explicit notes detailing source disagreement or gaps"
    )
    confidence: Optional[ConfidenceScore] = Field(
        default=None, description="Computed confidence score"
    )


class AuditRun(BaseModel):
    """
    Represents a complete audit execution session containing the evidence ledger
    and client claims.
    """

    run_id: str = Field(..., description="Unique audit run identifier")
    client_domain: str = Field(..., description="Target client domain (e.g. example.com)")
    category: str = Field(..., description="Target product/service category")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    evidence_ledger: Dict[str, EvidenceRecord] = Field(
        default_factory=dict,
        description="Map of evidence_id -> EvidenceRecord",
    )
    claims: List[ClaimRecord] = Field(
        default_factory=list, description="List of audit claim records"
    )
