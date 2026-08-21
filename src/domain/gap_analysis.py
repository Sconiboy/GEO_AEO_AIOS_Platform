"""
Forensic Competitor Evidence-Gap Analysis Domain Contracts (Sprint 7.4 Remediated)
Defines immutable models for competitor citation patterns, client evidence gaps,
finding bases, attribution statuses, collection candidate proposals, and prioritized action hypotheses with complete canonical digest protection.
"""

import hashlib
import json
from typing import List, Optional
from pydantic import BaseModel, Field

from .enums import ActionSeverity, AttributionStatus, GapCategory, SourceRelationship, SourceType, StatementEvidenceState


class AnswerCitation(BaseModel):
    """
    Explicit citation extracted directly from raw model answer text.
    Classified directly against SubjectProfile.
    """

    model_config = {"frozen": True}

    url: str = Field(..., description="Cited URL extracted from raw model answer")
    domain: str = Field(..., description="Domain name parsed from cited URL")
    is_explicit_citation: bool = Field(default=True, description="Whether URL was explicitly cited in model text")
    source_relationship: SourceRelationship = Field(
        default=SourceRelationship.UNKNOWN, description="Ownership relationship classification against SubjectProfile"
    )
    matched_competitor_entity: Optional[str] = Field(
        default=None, description="Name of matched competitor entity if competitor owned"
    )


class FindingBasis(BaseModel):
    """
    Immutable finding basis detailing exact observation, statement, evidence IDs,
    and source relationships supporting a gap, collection candidate, or action recommendation.
    """

    model_config = {"frozen": True}

    observation_id: str = Field(..., description="Bound AnswerObservation ID")
    statement_id: str = Field(..., description="Bound statement ID")
    evidence_ids: List[str] = Field(default_factory=list, description="Bound EvidenceRecord IDs")
    source_relationships: List[SourceRelationship] = Field(
        default_factory=list, description="Bound domain source relationships"
    )


class CompetitorCitation(BaseModel):
    """
    Domain citation details captured from model answers or evidence ledgers.
    """

    model_config = {"frozen": True}

    domain: str = Field(..., description="Cited domain name, e.g. python.org")
    citation_count: int = Field(..., ge=1, description="Number of citations found across ledgers")
    source_type: SourceType = Field(default=SourceType.UNKNOWN, description="Source classification type")
    source_relationship: SourceRelationship = Field(
        default=SourceRelationship.UNKNOWN, description="Ownership relationship classification"
    )


class CompetitorCitationPattern(BaseModel):
    """
    Citation distribution pattern observed for a target buyer query.
    """

    model_config = {"frozen": True}

    pattern_id: str = Field(..., description="Unique pattern identifier")
    target_query_id: str = Field(..., description="Target query ID")
    total_sources_evaluated: int = Field(..., ge=0)
    top_cited_domains: List[CompetitorCitation] = Field(default_factory=list)
    client_domain_cited: bool = Field(..., description="Whether client's owned domain was cited")
    answer_citations: List[AnswerCitation] = Field(
        default_factory=list, description="Actual citations extracted from raw model answer text"
    )
    attribution_status: AttributionStatus = Field(
        default=AttributionStatus.NO_ANSWER_CITATIONS_NOT_ASSESSABLE,
        description="Competitor attribution status for answer surface",
    )


class ObservedCitationCollectionCandidate(BaseModel):
    """
    Typed collection candidate proposal for an observed raw-answer URL missing from the source ledger.
    Requires explicit human review and manifest policy update prior to verifier collection.
    """

    model_config = {"frozen": True}

    candidate_id: str = Field(..., description="Unique collection candidate identifier")
    target_query_id: str = Field(..., description="Target query ID")
    cited_url: str = Field(..., description="Exact raw-answer cited URL requiring collection")
    cited_domain: str = Field(..., description="Domain name parsed from cited URL")
    source_relationship: SourceRelationship = Field(..., description="Relationship classification against SubjectProfile")
    matched_competitor_entity: Optional[str] = Field(default=None, description="Matched competitor entity name if competitor owned")
    requires_human_manifest_approval: bool = Field(
        default=True, description="Whether explicit human approval and manifest addition is required prior to fetch"
    )
    finding_basis: FindingBasis = Field(..., description="Explicit observation and raw-answer citation basis")
    action_hypothesis: str = Field(..., min_length=10, description="Collection candidate proposal recommendation")


class ClientEvidenceGap(BaseModel):
    """
    Identified evidence gap backed by explicit finding basis and statement evidence state.
    """

    model_config = {"frozen": True}

    gap_id: str = Field(..., description="Unique gap identifier")
    target_query_id: str = Field(..., description="Target query ID")
    gap_category: GapCategory = Field(..., description="Classification category of evidence gap")
    statement_evidence_state: StatementEvidenceState = Field(
        default=StatementEvidenceState.CANDIDATE_EVIDENCE_GAP,
        description="Three-way statement evidence evaluation state",
    )
    affected_statement_ids: List[str] = Field(..., min_length=1, description="Statement IDs impacted by this gap")
    description: str = Field(..., min_length=10, description="Detailed technical description of evidence gap")
    severity: ActionSeverity = Field(..., description="Severity level of the evidence gap")
    finding_basis: FindingBasis = Field(..., description="Explicit evidence and observation basis for gap")


class PrioritizedActionPlan(BaseModel):
    """
    Confidence-bounded action hypothesis recommended for client evidence generation.
    Framed explicitly as an action hypothesis for review.
    Must be bound to a valid ClientEvidenceGap ID.
    """

    model_config = {"frozen": True}

    action_id: str = Field(..., description="Unique action plan identifier")
    gap_id: str = Field(..., description="Bound ClientEvidenceGap ID")
    recommended_action: str = Field(..., min_length=10, description="Explicit action hypothesis recommendation")
    target_domain: str = Field(..., description="Target domain for action publishing")
    suggested_source_type: SourceType = Field(..., description="Source quality type to create")
    expected_evidence_impact: str = Field(..., description="Expected impact on evidence ledger completeness")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for recommendation")
    confidence_explanation: str = Field(..., min_length=10, description="Detailed explanation for confidence rating")
    ethical_boundary_notes: str = Field(
        default="Action creates genuine, verifiable public evidence. Non-manipulative, no keyword stuffing, no automated synthetic spam.",
        description="Explicit ethical governance boundary",
    )
    finding_basis: FindingBasis = Field(..., description="Explicit evidence and observation basis for action")


class ForensicGapAnalysisRecord(BaseModel):
    """
    Content-addressed, immutable record of forensic evidence-gap analysis.
    Binds observation ID, raw answer SHA-256, source ledger run ID, raw ledger SHA-256, query map SHA-256, manifest SHA-256, AND profile SHA-256.
    Every rendered field (profile SHA-256, attribution status, collection candidates, descriptions, evidence bases, ethical notes, total counts, impact statements) participates in canonical_digest.
    """

    model_config = {"frozen": True}

    analysis_id: str = Field(..., description="Unique analysis record ID")
    observation_id: str = Field(..., description="Bound AnswerObservation ID")
    raw_answer_sha256: str = Field(..., description="Bound raw answer SHA-256 digest")
    source_ledger_run_id: str = Field(..., description="Bound Source Ledger AuditRun ID")
    source_ledger_sha256: str = Field(..., description="Bound raw SHA-256 digest of Source Ledger")
    query_map_sha256: str = Field(..., description="Bound SHA-256 digest of QueryMap")
    manifest_sha256: str = Field(..., description="Bound SHA-256 digest of DatasetManifest")
    profile_id: str = Field(..., description="Bound SubjectProfile ID")
    profile_sha256: str = Field(..., description="Bound raw SHA-256 digest of SubjectProfile")
    attribution_status: AttributionStatus = Field(
        default=AttributionStatus.NO_ANSWER_CITATIONS_NOT_ASSESSABLE,
        description="Overall competitor attribution status",
    )
    competitor_patterns: List[CompetitorCitationPattern] = Field(default_factory=list)
    collection_candidates: List[ObservedCitationCollectionCandidate] = Field(default_factory=list)
    evidence_gaps: List[ClientEvidenceGap] = Field(default_factory=list)
    prioritized_actions: List[PrioritizedActionPlan] = Field(default_factory=list)
    canonical_digest: str = Field(..., description="Content-addressed SHA-256 digest over ALL context bindings and findings")

    @classmethod
    def compute_canonical_digest(
        cls,
        analysis_id: str,
        observation_id: str,
        raw_answer_sha256: str,
        source_ledger_run_id: str,
        source_ledger_sha256: str,
        query_map_sha256: str,
        manifest_sha256: str,
        profile_id: str,
        profile_sha256: str,
        attribution_status: AttributionStatus,
        competitor_patterns: List[CompetitorCitationPattern],
        collection_candidates: List[ObservedCitationCollectionCandidate],
        evidence_gaps: List[ClientEvidenceGap],
        prioritized_actions: List[PrioritizedActionPlan],
    ) -> str:
        """Computes deterministic SHA-256 canonical digest over ALL context bindings including profile_sha256, attribution_status, collection_candidates, total counts, descriptions, evidence bases, impact statements, and ethical notes."""
        payload = {
            "analysis_id": analysis_id,
            "observation_id": observation_id,
            "raw_answer_sha256": raw_answer_sha256.lower(),
            "source_ledger_run_id": source_ledger_run_id,
            "source_ledger_sha256": source_ledger_sha256.lower(),
            "query_map_sha256": query_map_sha256.lower(),
            "manifest_sha256": manifest_sha256.lower(),
            "profile_id": profile_id,
            "profile_sha256": profile_sha256.lower(),
            "attribution_status": attribution_status.value,
            "competitor_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "target_query_id": p.target_query_id,
                    "total_sources_evaluated": p.total_sources_evaluated,
                    "client_domain_cited": p.client_domain_cited,
                    "attribution_status": p.attribution_status.value,
                    "top_cited_domains": [
                        {
                            "domain": c.domain,
                            "citation_count": c.citation_count,
                            "source_type": c.source_type.value,
                            "source_relationship": c.source_relationship.value,
                        }
                        for c in sorted(p.top_cited_domains, key=lambda x: x.domain)
                    ],
                    "answer_citations": [
                        {
                            "domain": ac.domain,
                            "url": ac.url,
                            "is_explicit_citation": ac.is_explicit_citation,
                            "source_relationship": ac.source_relationship.value,
                            "matched_competitor_entity": ac.matched_competitor_entity,
                        }
                        for ac in sorted(p.answer_citations, key=lambda x: x.url)
                    ],
                }
                for p in sorted(competitor_patterns, key=lambda x: x.pattern_id)
            ],
            "collection_candidates": [
                {
                    "candidate_id": cc.candidate_id,
                    "target_query_id": cc.target_query_id,
                    "cited_url": cc.cited_url,
                    "cited_domain": cc.cited_domain,
                    "source_relationship": cc.source_relationship.value,
                    "matched_competitor_entity": cc.matched_competitor_entity,
                    "requires_human_manifest_approval": cc.requires_human_manifest_approval,
                    "action_hypothesis": cc.action_hypothesis,
                    "finding_basis": {
                        "observation_id": cc.finding_basis.observation_id,
                        "statement_id": cc.finding_basis.statement_id,
                        "evidence_ids": sorted(cc.finding_basis.evidence_ids),
                        "source_relationships": sorted([r.value for r in cc.finding_basis.source_relationships]),
                    },
                }
                for cc in sorted(collection_candidates, key=lambda x: x.candidate_id)
            ],
            "evidence_gaps": [
                {
                    "gap_id": g.gap_id,
                    "target_query_id": g.target_query_id,
                    "gap_category": g.gap_category.value,
                    "statement_evidence_state": g.statement_evidence_state.value,
                    "affected_statement_ids": sorted(g.affected_statement_ids),
                    "description": g.description,
                    "severity": g.severity.value,
                    "finding_basis": {
                        "observation_id": g.finding_basis.observation_id,
                        "statement_id": g.finding_basis.statement_id,
                        "evidence_ids": sorted(g.finding_basis.evidence_ids),
                        "source_relationships": sorted([r.value for r in g.finding_basis.source_relationships]),
                    },
                }
                for g in sorted(evidence_gaps, key=lambda x: x.gap_id)
            ],
            "prioritized_actions": [
                {
                    "action_id": a.action_id,
                    "gap_id": a.gap_id,
                    "recommended_action": a.recommended_action,
                    "target_domain": a.target_domain,
                    "suggested_source_type": a.suggested_source_type.value,
                    "expected_evidence_impact": a.expected_evidence_impact,
                    "confidence_score": round(a.confidence_score, 4),
                    "confidence_explanation": a.confidence_explanation,
                    "ethical_boundary_notes": a.ethical_boundary_notes,
                    "finding_basis": {
                        "observation_id": a.finding_basis.observation_id,
                        "statement_id": a.finding_basis.statement_id,
                        "evidence_ids": sorted(a.finding_basis.evidence_ids),
                        "source_relationships": sorted([r.value for r in a.finding_basis.source_relationships]),
                    },
                }
                for a in sorted(prioritized_actions, key=lambda x: x.action_id)
            ],
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verifies that canonical_digest matches expected calculation including profile_sha256 and attribution_status."""
        expected = self.compute_canonical_digest(
            analysis_id=self.analysis_id,
            observation_id=self.observation_id,
            raw_answer_sha256=self.raw_answer_sha256,
            source_ledger_run_id=self.source_ledger_run_id,
            source_ledger_sha256=self.source_ledger_sha256,
            query_map_sha256=self.query_map_sha256,
            manifest_sha256=self.manifest_sha256,
            profile_id=self.profile_id,
            profile_sha256=self.profile_sha256,
            attribution_status=self.attribution_status,
            competitor_patterns=self.competitor_patterns,
            collection_candidates=self.collection_candidates,
            evidence_gaps=self.evidence_gaps,
            prioritized_actions=self.prioritized_actions,
        )
        return self.canonical_digest.lower() == expected.lower()
