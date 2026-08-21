"""
Comparative Evidence Domain Contracts (Sprint 8.1)
Defines immutable models for claim-to-excerpt semantic assessments, comparative source summaries,
and content-addressed ComparativeEvidenceRecord with complete 9-hash context binding and integrity verification.
"""

import hashlib
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from .enums import ReconciliationStatus, SourceRelationship
from .gap_analysis import FindingBasis


class ClaimExcerptAssessment(BaseModel):
    """
    Semantic truth evaluation mapping a raw model statement proposal directly to a verified source excerpt.
    """

    model_config = ConfigDict(frozen=True)

    statement_id: str = Field(..., description="Bound statement ID from AnswerObservation")
    statement_text: str = Field(..., description="Raw text of statement proposal")
    evidence_id: Optional[str] = Field(default=None, description="Bound EvidenceRecord ID if evidence present")
    evidence_url: Optional[str] = Field(default=None, description="Bound EvidenceRecord URL if evidence present")
    opened_excerpt: Optional[str] = Field(default=None, description="Verified visible text excerpt from source")
    assessment_status: ReconciliationStatus = Field(
        ..., description="Semantic evaluation: SUPPORTED, UNSUPPORTED, CONTRADICTED, or NOT_ASSESSABLE"
    )
    semantic_rationale: str = Field(..., min_length=5, description="Technical rationale explaining semantic assessment")


class ComparativeSourceSummary(BaseModel):
    """Summary of verified evidence for a domain in the comparative workflow."""

    model_config = ConfigDict(frozen=True)

    domain: str = Field(..., description="Target domain name")
    url: str = Field(..., description="Verified URL")
    evidence_id: str = Field(..., description="Bound EvidenceRecord ID")
    verifier_run_id: str = Field(..., description="Bound verifier run ID")
    execution_id: str = Field(..., description="Bound CollectionExecutionRecord ID")
    relationship: SourceRelationship = Field(..., description="CLIENT_OWNED or COMPETITOR_OWNED relationship")
    entity_name: Optional[str] = Field(default=None, description="Matched entity name")
    is_verified: bool = Field(..., description="True if evidence is OPENED_VERIFIED")
    snapshot_sha256: str = Field(..., min_length=1, description="Snapshot SHA256 digest or 'unknown'")
    opened_excerpt: str = Field(..., description="Extracted visible text excerpt")


class ComparativeEvidenceRecord(BaseModel):
    """
    Content-addressed, immutable comparative evidence analysis record comparing client evidence with competitor evidence.
    Binds observation_id, raw_answer_sha256, profile_id, profile_sha256, query_map_sha256, manifest_sha256,
    source_ledger_run_id, source_ledger_sha256, client/competitor evidence IDs, snapshot hashes, verifier runs, and collection execution IDs.
    Does NOT assert causal LLM-ranking claims or commercial visibility ranks.
    """

    model_config = ConfigDict(frozen=True)

    comparative_id: str = Field(..., description="Unique comparative analysis ID")
    observation_id: str = Field(..., description="Bound AnswerObservation ID")
    raw_answer_sha256: str = Field(..., min_length=64, max_length=64, description="Bound raw answer SHA-256 digest")
    profile_id: str = Field(..., description="Bound SubjectProfile ID")
    profile_sha256: str = Field(..., min_length=64, max_length=64, description="Bound SHA-256 digest of SubjectProfile")
    query_map_sha256: str = Field(..., min_length=64, max_length=64, description="Bound SHA-256 digest of QueryMap")
    manifest_sha256: str = Field(..., min_length=64, max_length=64, description="Bound SHA-256 digest of DatasetManifest")
    source_ledger_run_id: str = Field(..., description="Bound Source Ledger AuditRun ID")
    source_ledger_sha256: str = Field(..., min_length=64, max_length=64, description="Bound raw SHA-256 digest of Source Ledger")

    query_id: str = Field(..., description="Bound TargetQuery ID")
    client_evidence: ComparativeSourceSummary = Field(..., description="Client-owned evidence summary")
    competitor_evidence: ComparativeSourceSummary = Field(..., description="Competitor-owned evidence summary")

    client_claim_assessments: List[ClaimExcerptAssessment] = Field(
        default_factory=list, description="Semantic claim assessments against client evidence"
    )
    competitor_claim_assessments: List[ClaimExcerptAssessment] = Field(
        default_factory=list, description="Semantic claim assessments against competitor evidence"
    )

    evidence_gap_identified: bool = Field(..., description="True if client evidence gap exists relative to competitor")
    comparison_summary: str = Field(..., min_length=10, description="Factual analysis comparing the two evidence sets")
    action_hypothesis: str = Field(..., min_length=10, description="Non-causal action hypothesis for human review")
    finding_basis: FindingBasis = Field(..., description="Explicit finding basis trace")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    human_review_required: bool = Field(default=True, description="Always True for evidence hypotheses")

    created_at: datetime = Field(..., description="Record generation timestamp")
    canonical_digest: str = Field(..., min_length=64, max_length=64, description="SHA-256 canonical digest over all fields")

    @classmethod
    def compute_canonical_digest(
        cls,
        comparative_id: str,
        observation_id: str,
        raw_answer_sha256: str,
        profile_id: str,
        profile_sha256: str,
        query_map_sha256: str,
        manifest_sha256: str,
        source_ledger_run_id: str,
        source_ledger_sha256: str,
        query_id: str,
        client_evidence: ComparativeSourceSummary,
        competitor_evidence: ComparativeSourceSummary,
        client_claim_assessments: List[ClaimExcerptAssessment],
        competitor_claim_assessments: List[ClaimExcerptAssessment],
        evidence_gap_identified: bool,
        comparison_summary: str,
        action_hypothesis: str,
        confidence_score: float,
        human_review_required: bool,
        created_at: datetime,
    ) -> str:
        """Computes deterministic SHA-256 canonical digest over ALL context bindings and assessments."""
        payload = {
            "comparative_id": comparative_id,
            "observation_id": observation_id,
            "raw_answer_sha256": raw_answer_sha256.lower(),
            "profile_id": profile_id,
            "profile_sha256": profile_sha256.lower(),
            "query_map_sha256": query_map_sha256.lower(),
            "manifest_sha256": manifest_sha256.lower(),
            "source_ledger_run_id": source_ledger_run_id,
            "source_ledger_sha256": source_ledger_sha256.lower(),
            "query_id": query_id,
            "client_evidence": {
                "domain": client_evidence.domain,
                "url": client_evidence.url,
                "evidence_id": client_evidence.evidence_id,
                "verifier_run_id": client_evidence.verifier_run_id,
                "execution_id": client_evidence.execution_id,
                "relationship": client_evidence.relationship.value,
                "entity_name": client_evidence.entity_name,
                "is_verified": client_evidence.is_verified,
                "snapshot_sha256": client_evidence.snapshot_sha256.lower(),
                "opened_excerpt": client_evidence.opened_excerpt,
            },
            "competitor_evidence": {
                "domain": competitor_evidence.domain,
                "url": competitor_evidence.url,
                "evidence_id": competitor_evidence.evidence_id,
                "verifier_run_id": competitor_evidence.verifier_run_id,
                "execution_id": competitor_evidence.execution_id,
                "relationship": competitor_evidence.relationship.value,
                "entity_name": competitor_evidence.entity_name,
                "is_verified": competitor_evidence.is_verified,
                "snapshot_sha256": competitor_evidence.snapshot_sha256.lower(),
                "opened_excerpt": competitor_evidence.opened_excerpt,
            },
            "client_claim_assessments": [
                {
                    "statement_id": ca.statement_id,
                    "evidence_id": ca.evidence_id,
                    "assessment_status": ca.assessment_status.value,
                    "semantic_rationale": ca.semantic_rationale,
                }
                for ca in sorted(client_claim_assessments, key=lambda x: x.statement_id)
            ],
            "competitor_claim_assessments": [
                {
                    "statement_id": ca.statement_id,
                    "evidence_id": ca.evidence_id,
                    "assessment_status": ca.assessment_status.value,
                    "semantic_rationale": ca.semantic_rationale,
                }
                for ca in sorted(competitor_claim_assessments, key=lambda x: x.statement_id)
            ],
            "evidence_gap_identified": evidence_gap_identified,
            "comparison_summary": comparison_summary,
            "action_hypothesis": action_hypothesis,
            "confidence_score": round(confidence_score, 4),
            "human_review_required": human_review_required,
            "created_at": created_at.isoformat(),
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verifies that canonical_digest matches expected calculation over all 9 artifact hashes and assessments."""
        expected = self.compute_canonical_digest(
            comparative_id=self.comparative_id,
            observation_id=self.observation_id,
            raw_answer_sha256=self.raw_answer_sha256,
            profile_id=self.profile_id,
            profile_sha256=self.profile_sha256,
            query_map_sha256=self.query_map_sha256,
            manifest_sha256=self.manifest_sha256,
            source_ledger_run_id=self.source_ledger_run_id,
            source_ledger_sha256=self.source_ledger_sha256,
            query_id=self.query_id,
            client_evidence=self.client_evidence,
            competitor_evidence=self.competitor_evidence,
            client_claim_assessments=self.client_claim_assessments,
            competitor_claim_assessments=self.competitor_claim_assessments,
            evidence_gap_identified=self.evidence_gap_identified,
            comparison_summary=self.comparison_summary,
            action_hypothesis=self.action_hypothesis,
            confidence_score=self.confidence_score,
            human_review_required=self.human_review_required,
            created_at=self.created_at,
        )
        return self.canonical_digest.lower() == expected.lower()
