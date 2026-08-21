"""
Domain Pydantic Models for Evidence Ledger and Audit Runs
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from .enums import ConfidenceRating, SourceType, VerificationStatus


class VerificationArtifact(BaseModel):
    """
    Concrete proof artifact generated when an evidence source is verified.
    No EvidenceRecord can be marked OPENED_VERIFIED without a valid VerificationArtifact.
    """

    verifier_run_id: str = Field(..., description="Run ID of the verification agent")
    verification_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when source was opened and verified",
    )
    verifier_method: str = Field(
        ..., description="Method used (e.g. DIRECT_HTTP_SNAPSHOT, PLAYWRIGHT_HEADLESS)"
    )
    snapshot_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 hash of captured HTML/markdown content"
    )
    quote_exact_match: bool = Field(
        ..., description="True if opened_excerpt matches snapshot text verbatim"
    )
    final_url: Optional[str] = Field(
        default=None, description="Final canonical URL after redirects"
    )
    http_status: Optional[int] = Field(
        default=None, description="HTTP status code (e.g. 200)"
    )
    content_type: Optional[str] = Field(
        default=None, description="Response Content-Type header"
    )
    content_length_bytes: Optional[int] = Field(
        default=None, description="Response payload size in bytes"
    )
    retrieval_duration_ms: Optional[float] = Field(
        default=None, description="HTTP request duration in milliseconds"
    )
    policy_warnings: List[str] = Field(
        default_factory=list, description="Non-fatal policy warnings during retrieval"
    )
    limitations: Optional[str] = Field(
        default=None, description="Known limitations (e.g. paywall, geo-location restriction)"
    )


class EvidenceRecord(BaseModel):
    """
    Represents an evidence source item.
    No claim can exist in an audit report without a linked, verified EvidenceRecord.
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
    verification_artifact: Optional[VerificationArtifact] = Field(
        default=None,
        description="Concrete verification metadata required when status is OPENED_VERIFIED",
    )

    @field_validator("url")
    @classmethod
    def validate_url_syntax(cls, v: str) -> str:
        url_regex = re.compile(
            r"^https?://"
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
            r"localhost|"
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
            r"(?::\d+)?"
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        cleaned = v.strip()
        if not url_regex.match(cleaned):
            raise ValueError(f"Invalid URL syntax: '{v}'")
        return cleaned

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
    Exposes input factors and formula parameters for transparency.
    """

    score: float = Field(
        ..., ge=0.0, le=1.0, description="Calculated score between 0.0 and 1.0"
    )
    rating: ConfidenceRating = Field(
        ..., description="Categorical rating based on calculated score"
    )
    formula_version: str = Field(
        default="provisional_v1.0",
        description="Version tag of the confidence scoring formula",
    )
    verified_sources_count: int = Field(default=0, ge=0)
    independent_sources_count: int = Field(default=0, ge=0)
    distinct_source_types: int = Field(default=0, ge=0)
    has_circular_duplication: bool = Field(default=False)
    has_unresolved_counter_evidence: bool = Field(default=False)
    input_breakdown: Dict[str, str] = Field(
        default_factory=dict,
        description="Detailed text explanation of factors driving this score",
    )

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
                formula_version="provisional_v1.0",
                verified_sources_count=0,
                independent_sources_count=0,
                distinct_source_types=0,
                has_circular_duplication=False,
                has_unresolved_counter_evidence=len(counter_evidence_list) > 0,
                input_breakdown={"reason": "No OPENED_VERIFIED evidence records found."},
            )

        independent_count = sum(1 for e in verified if e.is_independent)
        source_types = {e.source_type for e in verified}
        distinct_types_count = len(source_types)

        has_circular = any(e.is_syndicated_duplicate for e in verified)
        has_counter = len(counter_evidence_list) > 0

        # Base scoring calculation
        base = 0.3
        verified_bonus = min(0.3, verified_count * 0.1)
        indep_bonus = min(0.2, independent_count * 0.1)
        diversity_bonus = min(0.1, (distinct_types_count - 1) * 0.05)

        circ_penalty = 0.2 if has_circular else 0.0
        counter_penalty = 0.15 if has_counter else 0.0

        calculated_score = base + verified_bonus + indep_bonus + diversity_bonus - circ_penalty - counter_penalty
        final_score = max(0.0, min(1.0, round(calculated_score, 2)))

        if final_score >= 0.8:
            rating = ConfidenceRating.HIGH
        elif final_score >= 0.5:
            rating = ConfidenceRating.MEDIUM
        elif final_score > 0.0:
            rating = ConfidenceRating.LOW
        else:
            rating = ConfidenceRating.UNGROUNDED

        breakdown = {
            "base_credit": f"+{base:.2f}",
            "verified_count_credit": f"+{verified_bonus:.2f} ({verified_count} verified sources)",
            "independence_credit": f"+{indep_bonus:.2f} ({independent_count} independent sources)",
            "diversity_credit": f"+{diversity_bonus:.2f} ({distinct_types_count} distinct source types)",
            "duplication_penalty": f"-{circ_penalty:.2f}" if has_circular else "None",
            "counter_evidence_penalty": f"-{counter_penalty:.2f}" if has_counter else "None",
            "formula_status": "Provisional formula (Subject to client evaluation calibration)",
        }

        return cls(
            score=final_score,
            rating=rating,
            formula_version="provisional_v1.0",
            verified_sources_count=verified_count,
            independent_sources_count=independent_count,
            distinct_source_types=distinct_types_count,
            has_circular_duplication=has_circular,
            has_unresolved_counter_evidence=has_counter,
            input_breakdown=breakdown,
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
        ..., min_length=1, description="List of linked EvidenceRecord IDs supporting this claim"
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
    is_synthetic_fixture: bool = Field(
        default=False,
        description="True if run is synthetic fixture data for testing only",
    )
    notice: Optional[str] = Field(
        default=None,
        description="Notice header (e.g. SYNTHETIC FIXTURE DATA - NOT A REAL CLIENT AUDIT)",
    )
    evidence_ledger: Dict[str, EvidenceRecord] = Field(
        default_factory=dict,
        description="Map of evidence_id -> EvidenceRecord",
    )
    claims: List[ClaimRecord] = Field(
        default_factory=list, description="List of audit claim records"
    )
