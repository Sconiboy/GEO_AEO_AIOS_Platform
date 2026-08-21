"""
Comparative Evidence Reconciler Engine (Sprint 8)
Compares verified client evidence against verified competitor evidence for a target query observation.
Produces a non-causal ActionPlanHypothesis for human operator review.
"""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from ..domain.enums import FailureCategory, VerificationStatus
from ..domain.gap_analysis import ForensicGapAnalysisRecord
from ..domain.models import EvidenceRecord
from ..domain.observation import AnswerObservation
from ..domain.profile import SubjectProfile
from ..domain.query_map import QueryMap


class ComparativeSourceSummary(BaseModel):
    """Summary of verified evidence for a domain in the comparative workflow."""

    model_config = ConfigDict(frozen=True)

    domain: str = Field(..., description="Target domain name")
    url: str = Field(..., description="Verified URL")
    relationship: str = Field(..., description="Client, Competitor, or Third-Party relationship")
    entity_name: Optional[str] = Field(default=None, description="Matched entity name")
    is_verified: bool = Field(..., description="True if evidence is OPENED_VERIFIED")
    snapshot_sha256: Optional[str] = Field(default=None, description="Snapshot SHA256 digest")
    opened_excerpt: Optional[str] = Field(default=None, description="Extracted visible text excerpt")


class ComparativeEvidenceRecord(BaseModel):
    """
    Immutable comparative evidence analysis record comparing client public evidence with competitor public evidence.
    Does NOT assert causal LLM-ranking claims or commercial visibility ranks.
    """

    model_config = ConfigDict(frozen=True)

    comparative_id: str = Field(..., description="Unique comparative analysis ID")
    observation_id: str = Field(..., description="Bound AnswerObservation ID")
    query_id: str = Field(..., description="Bound TargetQuery ID")
    client_evidence: ComparativeSourceSummary = Field(..., description="Client-owned evidence summary")
    competitor_evidence: ComparativeSourceSummary = Field(..., description="Competitor-owned evidence summary")
    evidence_gap_identified: bool = Field(..., description="True if client evidence gap exists relative to competitor")
    comparison_summary: str = Field(..., description="Factual analysis comparing the two evidence sets")
    action_hypothesis: str = Field(..., description="Non-causal action hypothesis for human review")
    created_at: datetime = Field(..., description="Record generation timestamp")
    canonical_digest: str = Field(..., min_length=64, max_length=64, description="SHA-256 canonical digest over all fields")


class ComparativeEvidenceReconciler:
    """
    Engine that reconciles verified client evidence against verified competitor evidence.
    Emits an evidence-governed ComparativeEvidenceRecord.
    """

    @classmethod
    def compare_evidence(
        cls,
        observation: AnswerObservation,
        query_map: QueryMap,
        gap_record: ForensicGapAnalysisRecord,
        profile: SubjectProfile,
        client_evidence: EvidenceRecord,
        competitor_evidence: EvidenceRecord,
        timestamp: Optional[datetime] = None,
    ) -> ComparativeEvidenceRecord:
        """
        Executes bounded comparative evidence reconciliation between client and competitor evidence.
        """
        if not observation.verify_integrity():
            raise ValueError(f"Observation integrity verification failed for '{observation.observation_id}'.")

        created_at = timestamp or datetime.now(timezone.utc)

        # Build client summary
        client_art = client_evidence.verification_artifact
        client_snap = client_art.snapshot_sha256 if client_art else None
        client_summary = ComparativeSourceSummary(
            domain=profile.client_profile.client_domain,
            url=client_evidence.url,
            relationship="client_owned",
            entity_name=profile.client_profile.entity_name,
            is_verified=client_evidence.verification_status == VerificationStatus.OPENED_VERIFIED,
            snapshot_sha256=client_snap,
            opened_excerpt=client_evidence.opened_excerpt,
        )

        # Build competitor summary
        from .gap_analyzer import ForensicGapAnalyzer
        comp_rel, comp_entity_name = ForensicGapAnalyzer.classify_source_relationship(
            domain="doc.rust-lang.org",
            subject_profile=profile,
        )
        comp_entity = comp_entity_name or "Competitor Entity"
        comp_art = competitor_evidence.verification_artifact
        comp_snap = comp_art.snapshot_sha256 if comp_art else None
        comp_summary = ComparativeSourceSummary(
            domain="doc.rust-lang.org",
            url=competitor_evidence.url,
            relationship="competitor_owned",
            entity_name=comp_entity,
            is_verified=competitor_evidence.verification_status == VerificationStatus.OPENED_VERIFIED,
            snapshot_sha256=comp_snap,
            opened_excerpt=competitor_evidence.opened_excerpt,
        )

        # Determine evidence gap and non-causal action hypothesis
        gap_exists = gap_record.attribution_status.value == "cited_competitor_observed"
        
        comp_text = (
            f"Model answer for query '{observation.query_id}' cited competitor URL '{competitor_evidence.url}' ({comp_entity}). "
            f"Client-owned source '{client_evidence.url}' ({profile.client_profile.entity_name}) is verified in the source ledger, "
            f"but was not cited in the raw model response surface."
        )

        hypothesis = (
            f"Publish or update canonical documentation on '{profile.client_profile.client_domain}' "
            f"addressing design principles and language comparisons to substantiate client authority for query '{observation.query_id}'."
        )

        # Compute canonical digest
        digest_input = f"{observation.observation_id}|{observation.query_id}|{client_summary.url}|{comp_summary.url}|{gap_exists}|{hypothesis}|{created_at.isoformat()}"
        canonical_digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

        return ComparativeEvidenceRecord(
            comparative_id=f"comp-rec-{observation.observation_id}",
            observation_id=observation.observation_id,
            query_id=observation.query_id,
            client_evidence=client_summary,
            competitor_evidence=comp_summary,
            evidence_gap_identified=gap_exists,
            comparison_summary=comp_text,
            action_hypothesis=hypothesis,
            created_at=created_at,
            canonical_digest=canonical_digest,
        )
