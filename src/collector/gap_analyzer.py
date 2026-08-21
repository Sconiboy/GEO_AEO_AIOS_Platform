"""
Forensic Competitor Evidence-Gap Analyzer Engine (Sprint 7.1 Remediated)
Analyzes raw model answer surface observations, competitor citation patterns,
subject profiles, and source ledgers to detect client evidence gaps and generate
evidence-backed action hypotheses with complete canonical digest protection.
"""

import hashlib
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

from ..collector.query_map_runner import DatasetManifest
from ..domain.enums import ActionSeverity, GapCategory, ReconciliationStatus, SourceRelationship, SourceType
from ..domain.gap_analysis import (
    AnswerCitation,
    ClientEvidenceGap,
    CompetitorCitation,
    CompetitorCitationPattern,
    FindingBasis,
    ForensicGapAnalysisRecord,
    PrioritizedActionPlan,
)
from ..domain.human_decision import HumanDecisionRecord
from ..domain.models import AuditRun
from ..domain.observation import AnswerObservation
from ..domain.profile import SubjectProfile
from ..domain.query_map import QueryMap
from ..domain.reconciliation import ObservationReconciliation


class ForensicGapAnalyzer:
    """
    Forensic analysis engine identifying competitor citation patterns,
    client evidence gaps, and evidence-backed priority action hypotheses.
    """

    @classmethod
    def classify_source_relationship(
        cls, domain: str, subject_profile: SubjectProfile, source_type: SourceType
    ) -> SourceRelationship:
        """
        Classifies domain source relationship using explicit SubjectProfile contracts.
        Does NOT infer client ownership from collection allowlists.
        """
        dom_lower = domain.lower()

        client_domains = {
            d.lower() for d in subject_profile.client_profile.owned_domains
        }
        client_domains.add(subject_profile.client_profile.client_domain.lower())

        if any(dom_lower == cd or dom_lower.endswith("." + cd) for cd in client_domains):
            return SourceRelationship.CLIENT_OWNED

        for comp in subject_profile.competitor_profiles:
            comp_domains = {d.lower() for d in comp.competitor_domains}
            if any(dom_lower == cd or dom_lower.endswith("." + cd) for cd in comp_domains):
                return SourceRelationship.COMPETITOR_OWNED

        if source_type == SourceType.OFFICIAL_DOCUMENTATION:
            return SourceRelationship.OFFICIAL_REFERENCE
        elif source_type == SourceType.INDEPENDENT_EDITORIAL:
            return SourceRelationship.INDEPENDENT_EDITORIAL
        elif source_type == SourceType.REVIEW_AGGREGATOR:
            return SourceRelationship.REVIEW_PLATFORM
        elif source_type == SourceType.COMMUNITY_FORUM:
            return SourceRelationship.COMMUNITY
        else:
            return SourceRelationship.UNKNOWN

    @classmethod
    def extract_answer_citations(cls, raw_answer_text: str) -> List[AnswerCitation]:
        """Extracts explicit HTTP/HTTPS URLs cited directly in raw model answer text."""
        url_pattern = r'https?://[^\s<>"]+'
        urls = re.findall(url_pattern, raw_answer_text)
        citations: List[AnswerCitation] = []
        seen_urls: Set[str] = set()

        for u in urls:
            clean_url = u.rstrip(".,);]")
            if clean_url not in seen_urls:
                seen_urls.add(clean_url)
                parsed = urlparse(clean_url)
                dom = parsed.hostname.lower() if parsed.hostname else clean_url
                citations.append(
                    AnswerCitation(
                        url=clean_url,
                        domain=dom,
                        is_explicit_citation=True,
                    )
                )

        return citations

    @classmethod
    def analyze_gaps(
        cls,
        subject_profile: SubjectProfile,
        observation: AnswerObservation,
        source_ledger: AuditRun,
        query_map: QueryMap,
        manifest: DatasetManifest,
        raw_qm_bytes: bytes,
        raw_manifest_bytes: bytes,
        raw_ledger_bytes: bytes,
        raw_profile_bytes: bytes,
        human_decision: Optional[HumanDecisionRecord] = None,
        reconciliation: Optional[ObservationReconciliation] = None,
    ) -> ForensicGapAnalysisRecord:
        """
        Executes forensic gap analysis:
        1. Classifies domain relationships using explicit SubjectProfile.
        2. Extracts actual citations from raw model answer text.
        3. Respects human decision/reconciliation: skips false gaps for SUPPORTED statements.
        4. Generates evidence-backed Action Hypotheses with explicit finding bases.
        5. Calculates content-addressed canonical SHA-256 digest covering ALL fields.
        """
        qm_sha256 = hashlib.sha256(raw_qm_bytes).hexdigest()
        manifest_sha256 = hashlib.sha256(raw_manifest_bytes).hexdigest()
        ledger_sha256 = hashlib.sha256(raw_ledger_bytes).hexdigest()
        profile_sha256 = hashlib.sha256(raw_profile_bytes).hexdigest()

        # Step 1: Extract answer citations
        answer_citations = cls.extract_answer_citations(observation.raw_answer_text)

        # Step 2: Source Ledger Domain & Relationship Classification
        domain_counts: Dict[str, int] = {}
        domain_types: Dict[str, SourceType] = {}
        domain_relationships: Dict[str, SourceRelationship] = {}

        for ev in source_ledger.evidence_ledger.values():
            if ev.verification_status.value == "opened_verified":
                parsed = urlparse(ev.url)
                dom = parsed.hostname.lower() if parsed.hostname else ev.url
                domain_counts[dom] = domain_counts.get(dom, 0) + 1
                domain_types[dom] = ev.source_type
                domain_relationships[dom] = cls.classify_source_relationship(
                    domain=dom,
                    subject_profile=subject_profile,
                    source_type=ev.source_type,
                )

        top_citations: List[CompetitorCitation] = [
            CompetitorCitation(
                domain=d,
                citation_count=cnt,
                source_type=domain_types.get(d, SourceType.UNKNOWN),
                source_relationship=domain_relationships.get(d, SourceRelationship.UNKNOWN),
            )
            for d, cnt in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        client_domain_cited = any(
            rel == SourceRelationship.CLIENT_OWNED for rel in domain_relationships.values()
        )

        pattern = CompetitorCitationPattern(
            pattern_id=f"pat-{observation.query_id}",
            target_query_id=observation.query_id,
            total_sources_evaluated=len(source_ledger.evidence_ledger),
            top_cited_domains=top_citations,
            client_domain_cited=client_domain_cited,
            answer_citations=answer_citations,
        )

        # Step 3: Respect Human Decisions & Automated Reconciliations
        supported_statement_ids: Set[str] = set()

        if human_decision:
            for dec in human_decision.decisions:
                if dec.decision_status == ReconciliationStatus.SUPPORTED:
                    supported_statement_ids.add(dec.statement_id)

        if reconciliation:
            for rec in reconciliation.reconciliations:
                if rec.status == ReconciliationStatus.SUPPORTED:
                    supported_statement_ids.add(rec.statement_id)

        # Identify ungrounded/unsupported statements (excluding supported ones!)
        unsupported_stmts = [
            s.statement_id
            for s in observation.extracted_statements
            if s.statement_id not in supported_statement_ids
        ]

        gaps: List[ClientEvidenceGap] = []
        actions: List[PrioritizedActionPlan] = []

        if unsupported_stmts:
            gap_id = f"gap-{observation.query_id}-001"
            basis_ev_ids = [
                ev_id
                for ev_id, ev in source_ledger.evidence_ledger.items()
                if ev.verification_status.value == "opened_verified"
            ]
            basis_rels = list({
                cls.classify_source_relationship(
                    domain=urlparse(ev.url).hostname or ev.url,
                    subject_profile=subject_profile,
                    source_type=ev.source_type,
                )
                for ev in source_ledger.evidence_ledger.values()
                if ev.verification_status.value == "opened_verified"
            })

            gap_basis = FindingBasis(
                observation_id=observation.observation_id,
                statement_id=unsupported_stmts[0],
                evidence_ids=basis_ev_ids,
                source_relationships=basis_rels,
            )

            desc = (
                f"Model response extracted {len(unsupported_stmts)} statement proposal(s) "
                f"({', '.join(unsupported_stmts)}) lacking client-owned opened evidence in source ledger."
            )

            gaps.append(
                ClientEvidenceGap(
                    gap_id=gap_id,
                    target_query_id=observation.query_id,
                    gap_category=GapCategory.MISSING_OFFICIAL_DOCS,
                    affected_statement_ids=unsupported_stmts,
                    description=desc,
                    severity=ActionSeverity.HIGH if client_domain_cited else ActionSeverity.CRITICAL,
                    finding_basis=gap_basis,
                )
            )

            # Formulate evidence-backed action hypothesis
            client_dom = subject_profile.client_profile.client_domain
            act_id = f"act-{observation.query_id}-001"

            act_rec = (
                f"Hypothesis for Review: Publishing official technical specification and documentation "
                f"on client-owned domain '{client_dom}' for statements {unsupported_stmts} "
                f"may establish OPENED_VERIFIED evidence status."
            )

            actions.append(
                PrioritizedActionPlan(
                    action_id=act_id,
                    gap_id=gap_id,
                    recommended_action=act_rec,
                    target_domain=client_dom,
                    suggested_source_type=SourceType.OFFICIAL_DOCUMENTATION,
                    expected_evidence_impact="Expected to create client-owned OPENED_VERIFIED evidence record in ledger.",
                    confidence_score=0.80,
                    confidence_explanation="Confidence rating derived from absence of client-owned documentation for target query statements.",
                    ethical_boundary_notes="Action hypothesis creates genuine, verifiable public documentation. Non-manipulative, no keyword stuffing, no automated synthetic spam.",
                    finding_basis=gap_basis,
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
            profile_id=subject_profile.profile_id,
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
            profile_id=subject_profile.profile_id,
            competitor_patterns=[pattern],
            evidence_gaps=gaps,
            prioritized_actions=actions,
            canonical_digest=canonical_digest,
        )
