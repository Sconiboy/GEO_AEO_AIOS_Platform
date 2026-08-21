"""
Candidate Collector Execution Engine (Sprint 7.5)
Implements execution-time authorization re-validation and secure source collection
for authorized ObservedCitationCollectionCandidate proposals.
"""

import hashlib
from typing import Optional, Tuple
from urllib.parse import urlparse

from ..collector.gap_analyzer import ForensicGapAnalyzer
from ..collector.policy import SourcePolicy
from ..collector.query_map_runner import DatasetManifest
from ..collector.snapshot import SnapshotStore
from ..collector.verifier import SourceVerifier
from ..domain.enums import HumanApprovalState, SourceType, VerificationStatus
from ..domain.gap_analysis import ForensicGapAnalysisRecord, ObservedCitationCollectionCandidate
from ..domain.human_decision import HumanDecisionRecord
from ..domain.models import AuditRun
from ..domain.observation import AnswerObservation
from ..domain.profile import SubjectProfile
from ..domain.query_map import QueryMap


class CandidateCollector:
    """
    Executes execution-time authorized competitor candidate evidence collection:
    1. Re-validates exact candidate authorization (requires_human_manifest_approval == False).
    2. Re-validates exact normalized URL + matching target query_id in current DatasetManifest.
    3. Re-validates target query approval_state == APPROVED.
    4. Enforces SourcePolicy SSRF, allowlist, scheme, and payload limits.
    5. Invokes SourceVerifier under strict policy controls.
    6. Appends verified EvidenceRecord to AuditRun.evidence_ledger.
    7. Re-analyzes gaps to emit updated ForensicGapAnalysisRecord.
    """

    def __init__(self, snapshot_store: Optional[SnapshotStore] = None):
        self.snapshot_store = snapshot_store or SnapshotStore()

    def collect_candidate(
        self,
        candidate_id: str,
        subject_profile: SubjectProfile,
        observation: AnswerObservation,
        source_ledger: AuditRun,
        query_map: QueryMap,
        manifest: DatasetManifest,
        gap_record: ForensicGapAnalysisRecord,
        raw_qm_bytes: bytes,
        raw_manifest_bytes: bytes,
        raw_ledger_bytes: bytes,
        raw_profile_bytes: bytes,
        human_decision: Optional[HumanDecisionRecord] = None,
    ) -> Tuple[AuditRun, ForensicGapAnalysisRecord]:
        """
        Executes candidate collection under strict execution-time authorization controls.
        Fails closed with ValueError if any authorization check fails.
        """
        # Step 1: Find candidate in gap_record
        cand: Optional[ObservedCitationCollectionCandidate] = None
        for c in gap_record.collection_candidates:
            if c.candidate_id == candidate_id:
                cand = c
                break

        if not cand:
            raise ValueError(
                f"Candidate collection failed closed: candidate_id '{candidate_id}' "
                f"not found in ForensicGapAnalysisRecord '{gap_record.analysis_id}'."
            )

        # Gate 1: Fail closed if candidate requires human manifest approval
        if cand.requires_human_manifest_approval:
            raise ValueError(
                f"Execution Gate Blocked: Candidate '{candidate_id}' for URL '{cand.cited_url}' "
                f"requires explicit human approval and manifest policy update prior to verifier fetch."
            )

        # Gate 2: Fail closed if exact (query_id, clean_url) is missing from current manifest
        clean_url = cand.cited_url.lower().rstrip("/")
        manifest_matched_cs = None
        if hasattr(manifest, "candidates") and manifest.candidates:
            for cs in manifest.candidates:
                if cs.query_id == cand.target_query_id and cs.url.lower().rstrip("/") == clean_url:
                    manifest_matched_cs = cs
                    break

        if not manifest_matched_cs:
            raise ValueError(
                f"Execution Gate Blocked: Exact URL '{cand.cited_url}' for query '{cand.target_query_id}' "
                f"is not found in current DatasetManifest '{manifest.manifest_id}' candidates."
            )

        # Gate 3: Verify target query is in APPROVED state
        target_query = None
        for q in query_map.queries:
            if q.query_id == cand.target_query_id:
                target_query = q
                break

        if not target_query or target_query.approval_state != HumanApprovalState.APPROVED:
            raise ValueError(
                f"Execution Gate Blocked: Target query '{cand.target_query_id}' "
                f"is not in HumanApprovalState.APPROVED state."
            )

        # Gate 4: SourcePolicy Verification
        scope = query_map.policy_profile.source_scope
        policy = SourcePolicy(
            allowed_schemes=query_map.policy_profile.allowed_schemes,
            max_redirects=query_map.policy_profile.max_redirects,
            max_response_bytes=query_map.policy_profile.max_response_bytes,
            timeout_seconds=query_map.policy_profile.timeout_seconds,
            allowed_domains=scope.allowed_domains,
            blocked_domains=scope.blocked_domains,
            block_private_ips=True,
        )

        verifier = SourceVerifier(snapshot_store=self.snapshot_store, policy=policy)

        # Step 2: Execute verifier fetch for candidate
        ev_record = verifier.verify_url(
            url=cand.cited_url,
            candidate_excerpt=manifest_matched_cs.candidate_excerpt if hasattr(manifest_matched_cs, "candidate_excerpt") else f"Verbatim excerpt for {cand.cited_url}",
            source_type=manifest_matched_cs.source_type if hasattr(manifest_matched_cs, "source_type") else SourceType.OFFICIAL_DOCUMENTATION,
            is_independent=manifest_matched_cs.is_independent if hasattr(manifest_matched_cs, "is_independent") else False,
        )

        # Step 3: Append new evidence record to source ledger
        updated_ledger_map = dict(source_ledger.evidence_ledger)
        updated_ledger_map[ev_record.evidence_id] = ev_record

        updated_source_ledger = source_ledger.model_copy(
            update={"evidence_ledger": updated_ledger_map}
        )
        updated_ledger_bytes = updated_source_ledger.model_dump_json().encode("utf-8")

        # Step 4: Re-analyze gaps with updated source ledger
        updated_gap_record = ForensicGapAnalyzer.analyze_gaps(
            subject_profile=subject_profile,
            observation=observation,
            source_ledger=updated_source_ledger,
            query_map=query_map,
            manifest=manifest,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=updated_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
            human_decision=human_decision,
        )

        return updated_source_ledger, updated_gap_record
