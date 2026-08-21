"""
Forensic Competitor Evidence-Gap Analysis Domain Contracts (Sprint 7)
Defines immutable models for competitor citation patterns, client evidence gaps,
and prioritized ethical action recommendations with content-addressed SHA-256 digests.
"""

import hashlib
import json
from typing import List, Optional
from pydantic import BaseModel, Field

from .enums import ActionSeverity, GapCategory, SourceType


class CompetitorCitation(BaseModel):
    """
    Domain citation details captured from model answers or evidence ledgers.
    """

    model_config = {"frozen": True}

    domain: str = Field(..., description="Cited domain name, e.g. python.org")
    citation_count: int = Field(..., ge=1, description="Number of citations found across ledgers")
    source_type: SourceType = Field(default=SourceType.UNKNOWN, description="Source classification type")


class CompetitorCitationPattern(BaseModel):
    """
    Citation distribution pattern observed for a target buyer query.
    """

    model_config = {"frozen": True}

    pattern_id: str = Field(..., description="Unique pattern identifier")
    target_query_id: str = Field(..., description="Target query ID")
    total_sources_evaluated: int = Field(..., ge=0)
    top_cited_domains: List[CompetitorCitation] = Field(default_factory=list)
    client_domain_cited: bool = Field(..., description="Whether client's domain was cited")


class ClientEvidenceGap(BaseModel):
    """
    Identified evidence gap where client evidence is missing or model claims are ungrounded.
    """

    model_config = {"frozen": True}

    gap_id: str = Field(..., description="Unique gap identifier")
    target_query_id: str = Field(..., description="Target query ID")
    gap_category: GapCategory = Field(..., description="Classification category of evidence gap")
    affected_statement_ids: List[str] = Field(..., min_length=1, description="Statement IDs impacted by this gap")
    description: str = Field(..., min_length=10, description="Detailed technical description of evidence gap")
    severity: ActionSeverity = Field(..., description="Severity level of the evidence gap")


class PrioritizedActionPlan(BaseModel):
    """
    Confidence-bounded, ethical priority action recommended for client evidence generation.
    """

    model_config = {"frozen": True}

    action_id: str = Field(..., description="Unique action plan identifier")
    gap_id: str = Field(..., description="Bound ClientEvidenceGap ID")
    recommended_action: str = Field(..., min_length=10, description="Explicit publishing or verification recommendation")
    target_domain: str = Field(..., description="Target domain for action publishing")
    suggested_source_type: SourceType = Field(..., description="Source quality type to create")
    expected_evidence_impact: str = Field(..., description="Expected impact on evidence ledger completeness")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for recommendation")
    ethical_boundary_notes: str = Field(
        default="Action creates genuine, verifiable public evidence. Non-manipulative, no keyword stuffing, no automated synthetic spam.",
        description="Explicit ethical governance boundary",
    )


class ForensicGapAnalysisRecord(BaseModel):
    """
    Content-addressed, immutable record of forensic evidence-gap analysis.
    Binds observation ID, raw answer SHA-256, source ledger run ID, raw ledger SHA-256, query map SHA-256, and manifest SHA-256.
    """

    model_config = {"frozen": True}

    analysis_id: str = Field(..., description="Unique analysis record ID")
    observation_id: str = Field(..., description="Bound AnswerObservation ID")
    raw_answer_sha256: str = Field(..., description="Bound raw answer SHA-256 digest")
    source_ledger_run_id: str = Field(..., description="Bound Source Ledger AuditRun ID")
    source_ledger_sha256: str = Field(..., description="Bound raw SHA-256 digest of Source Ledger")
    query_map_sha256: str = Field(..., description="Bound SHA-256 digest of QueryMap")
    manifest_sha256: str = Field(..., description="Bound SHA-256 digest of DatasetManifest")
    competitor_patterns: List[CompetitorCitationPattern] = Field(default_factory=list)
    evidence_gaps: List[ClientEvidenceGap] = Field(default_factory=list)
    prioritized_actions: List[PrioritizedActionPlan] = Field(default_factory=list)
    canonical_digest: str = Field(..., description="Content-addressed SHA-256 digest over context bindings and findings")

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
        competitor_patterns: List[CompetitorCitationPattern],
        evidence_gaps: List[ClientEvidenceGap],
        prioritized_actions: List[PrioritizedActionPlan],
    ) -> str:
        """Computes deterministic SHA-256 canonical digest over all context bindings and analysis findings."""
        payload = {
            "analysis_id": analysis_id,
            "observation_id": observation_id,
            "raw_answer_sha256": raw_answer_sha256.lower(),
            "source_ledger_run_id": source_ledger_run_id,
            "source_ledger_sha256": source_ledger_sha256.lower(),
            "query_map_sha256": query_map_sha256.lower(),
            "manifest_sha256": manifest_sha256.lower(),
            "competitor_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "target_query_id": p.target_query_id,
                    "client_domain_cited": p.client_domain_cited,
                    "top_cited_domains": [
                        {"domain": c.domain, "citation_count": c.citation_count, "source_type": c.source_type.value}
                        for c in sorted(p.top_cited_domains, key=lambda x: x.domain)
                    ],
                }
                for p in sorted(competitor_patterns, key=lambda x: x.pattern_id)
            ],
            "evidence_gaps": [
                {
                    "gap_id": g.gap_id,
                    "target_query_id": g.target_query_id,
                    "gap_category": g.gap_category.value,
                    "affected_statement_ids": sorted(g.affected_statement_ids),
                    "severity": g.severity.value,
                }
                for g in sorted(evidence_gaps, key=lambda x: x.gap_id)
            ],
            "prioritized_actions": [
                {
                    "action_id": a.action_id,
                    "gap_id": a.gap_id,
                    "recommended_action": a.recommended_action,
                    "target_domain": a.target_domain,
                    "confidence_score": round(a.confidence_score, 4),
                }
                for a in sorted(prioritized_actions, key=lambda x: x.action_id)
            ],
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verifies that canonical_digest matches expected calculation."""
        expected = self.compute_canonical_digest(
            analysis_id=self.analysis_id,
            observation_id=self.observation_id,
            raw_answer_sha256=self.raw_answer_sha256,
            source_ledger_run_id=self.source_ledger_run_id,
            source_ledger_sha256=self.source_ledger_sha256,
            query_map_sha256=self.query_map_sha256,
            manifest_sha256=self.manifest_sha256,
            competitor_patterns=self.competitor_patterns,
            evidence_gaps=self.evidence_gaps,
            prioritized_actions=self.prioritized_actions,
        )
        return self.canonical_digest.lower() == expected.lower()
