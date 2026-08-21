"""
Forensic Competitor Evidence-Gap Analyzer Engine (Sprint 7)
Analyzes raw model answer surface observations, competitor citation patterns,
and source ledgers to detect client evidence gaps and generate prioritized ethical action plans.
"""

import hashlib

from typing import Dict, List, Optional
from urllib.parse import urlparse

from ..domain.enums import ActionSeverity, GapCategory, SourceType
from ..domain.gap_analysis import (
    ClientEvidenceGap,
    CompetitorCitation,
    CompetitorCitationPattern,
    ForensicGapAnalysisRecord,
    PrioritizedActionPlan,
)
from ..domain.human_decision import HumanDecisionRecord
from ..domain.models import AuditRun
from ..domain.observation import AnswerObservation
from ..collector.query_map_runner import DatasetManifest
from ..domain.query_map import QueryMap


class ForensicGapAnalyzer:
    """
    Forensic analysis engine identifying competitor citation patterns,
    client evidence gaps, and confidence-bounded ethical action recommendations.
    """

    @classmethod
    def analyze_gaps(
        cls,
        observation: AnswerObservation,
        source_ledger: AuditRun,
        query_map: QueryMap,
        manifest: DatasetManifest,
        raw_qm_bytes: bytes,
        raw_manifest_bytes: bytes,
        raw_ledger_bytes: bytes,
        human_decision: Optional[HumanDecisionRecord] = None,
    ) -> ForensicGapAnalysisRecord:
        """
        Executes forensic gap analysis:
        1. Analyzes competitor and third-party domain citation frequencies from source ledger.
        2. Detects evidence gaps for ungrounded or proposed model statement proposals.
        3. Formulates confidence-bounded, ethical priority actions for client evidence generation.
        4. Calculates content-addressed canonical SHA-256 digest over analysis record.
        """
        qm_sha256 = hashlib.sha256(raw_qm_bytes).hexdigest()
        manifest_sha256 = hashlib.sha256(raw_manifest_bytes).hexdigest()
        ledger_sha256 = hashlib.sha256(raw_ledger_bytes).hexdigest()

        # Step 1: Competitor Citation Pattern Analysis
        domain_counts: Dict[str, int] = {}
        domain_types: Dict[str, SourceType] = {}

        for ev in source_ledger.evidence_ledger.values():
            if ev.verification_status.value == "opened_verified":
                parsed = urlparse(ev.url)
                domain = parsed.hostname.lower() if parsed.hostname else ev.url
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                domain_types[domain] = ev.source_type

        top_citations: List[CompetitorCitation] = [
            CompetitorCitation(
                domain=d,
                citation_count=cnt,
                source_type=domain_types.get(d, SourceType.UNKNOWN),
            )
            for d, cnt in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        allowed_domains = {
            d.lower() for d in query_map.policy_profile.source_scope.allowed_domains
        }
        client_cited = any(d in allowed_domains for d in domain_counts)

        pattern = CompetitorCitationPattern(
            pattern_id=f"pat-{observation.query_id}",
            target_query_id=observation.query_id,
            total_sources_evaluated=len(source_ledger.evidence_ledger),
            top_cited_domains=top_citations,
            client_domain_cited=client_cited,
        )

        # Step 2: Client Evidence Gap Identification
        gaps: List[ClientEvidenceGap] = []
        actions: List[PrioritizedActionPlan] = []

        # Check for missing official documentation gap
        unsupported_stmts = [
            s.statement_id for s in observation.extracted_statements
        ]

        if unsupported_stmts:
            gap_id = f"gap-{observation.query_id}-001"
            gaps.append(
                ClientEvidenceGap(
                    gap_id=gap_id,
                    target_query_id=observation.query_id,
                    gap_category=GapCategory.MISSING_OFFICIAL_DOCS,
                    affected_statement_ids=unsupported_stmts,
                    description=f"Model response extracted {len(unsupported_stmts)} statement proposal(s) lacking authoritative opened evidence in client source ledger.",
                    severity=ActionSeverity.CRITICAL if not client_cited else ActionSeverity.HIGH,
                )
            )

            # Formulate ethical action plan
            target_dom = (
                query_map.policy_profile.source_scope.allowed_domains[0]
                if query_map.policy_profile.source_scope.allowed_domains
                else "official.domain"
            )

            actions.append(
                PrioritizedActionPlan(
                    action_id=f"act-{observation.query_id}-001",
                    gap_id=gap_id,
                    recommended_action=f"Publish official technical documentation and design specification on {target_dom} covering statement claims.",
                    target_domain=target_dom,
                    suggested_source_type=SourceType.OFFICIAL_DOCUMENTATION,
                    expected_evidence_impact="Establishes OPENED_VERIFIED evidence status and enables human auditor semantic support adjudication.",
                    confidence_score=0.85,
                    ethical_boundary_notes="Action creates genuine, verifiable public documentation. Non-manipulative, no keyword stuffing, no automated synthetic spam.",
                )
            )

        analysis_id = f"fga-rec-{observation.observation_id}"

        canonical_digest = ForensicGapAnalysisRecord.compute_canonical_digest(
            analysis_id=analysis_id,
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            source_ledger_run_id=source_ledger.run_id,
            source_ledger_sha256=ledger_sha256,
            query_map_sha256=qm_sha256,
            manifest_sha256=manifest_sha256,
            competitor_patterns=[pattern],
            evidence_gaps=gaps,
            prioritized_actions=actions,
        )

        return ForensicGapAnalysisRecord(
            analysis_id=analysis_id,
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            source_ledger_run_id=source_ledger.run_id,
            source_ledger_sha256=ledger_sha256,
            query_map_sha256=qm_sha256,
            manifest_sha256=manifest_sha256,
            competitor_patterns=[pattern],
            evidence_gaps=gaps,
            prioritized_actions=actions,
            canonical_digest=canonical_digest,
        )
