"""
QueryMap Runner and Dataset Manifest Verification Engine
Enforces pre-approved domain allowlists, human query approval states, and SourcePolicy rules.
"""

from typing import Dict, List, Optional
import urllib.parse
from pydantic import BaseModel, Field

from ..domain.enums import FailureCategory, HumanApprovalState, SourceType, VerificationStatus
from ..domain.models import AuditRun, ClaimRecord, EvidenceRecord
from ..domain.query_map import QueryMap, TargetQuery
from .policy import SourcePolicy, SourcePolicyViolationError
from .snapshot import SnapshotStore
from .verifier import SourceVerifier


class ManifestSourceCandidate(BaseModel):
    """
    Candidate public source item from a controlled non-client dataset manifest.
    """

    query_id: str = Field(..., description="Target query ID this candidate supports")
    url: str = Field(..., description="Public URL to verify")
    candidate_excerpt: str = Field(..., min_length=5, description="Verbatim quote excerpt to verify")
    source_type: SourceType = Field(default=SourceType.INDEPENDENT_EDITORIAL)
    is_independent: bool = Field(default=True)


class DatasetManifest(BaseModel):
    """
    Manifest defining a controlled, pre-approved dataset of public non-client sources.
    """

    manifest_id: str = Field(..., description="Unique manifest identifier")
    description: str = Field(..., description="Description of non-client public dataset")
    is_non_client_spike: bool = Field(default=True)
    candidates: List[ManifestSourceCandidate] = Field(..., min_length=1)


class QueryMapRunner:
    """
    Executes controlled source verification against pre-approved QueryMap and DatasetManifest.
    Refuses any source outside the pre-approved domain allowlist or unapproved query set.
    """

    def __init__(
        self,
        snapshot_store: Optional[SnapshotStore] = None,
    ):
        self.snapshot_store = snapshot_store or SnapshotStore()

    def run_query_map_audit(
        self,
        query_map: QueryMap,
        manifest: DatasetManifest,
    ) -> AuditRun:
        """
        Executes query map verification pipeline:
        1. Filters queries to APPROVED state only.
        2. Configures SourcePolicy with explicit allowed_domains whitelist.
        3. Enforces domain whitelist & manifest bounds on candidate URLs.
        4. Verifies approved sources and constructs Source Ledger AuditRun.
        """
        # Step 1: Filter to approved queries only
        approved_queries_map: Dict[str, TargetQuery] = {
            q.query_id: q
            for q in query_map.queries
            if q.approval_state == HumanApprovalState.APPROVED
        }

        # Step 2: Configure SourcePolicy with domain allowlist
        allowed_domains = query_map.policy_profile.source_scope.allowed_domains
        policy = SourcePolicy(
            allowed_schemes=query_map.policy_profile.allowed_schemes,
            max_redirects=query_map.policy_profile.max_redirects,
            max_response_bytes=query_map.policy_profile.max_response_bytes,
            timeout_seconds=query_map.policy_profile.timeout_seconds,
            allowed_domains=allowed_domains,
            block_private_ips=True,
        )

        verifier = SourceVerifier(snapshot_store=self.snapshot_store, policy=policy)

        evidence_ledger: Dict[str, EvidenceRecord] = {}
        query_evidence_ids: Dict[str, List[str]] = {qid: [] for qid in approved_queries_map}

        # Step 3: Verify candidate sources
        for candidate in manifest.candidates:
            # Check if query is approved
            if candidate.query_id not in approved_queries_map:
                continue  # Skip candidates for unapproved queries

            # Check domain allowlist
            parsed = urllib.parse.urlparse(candidate.url)
            hostname = parsed.hostname.lower() if parsed.hostname else ""

            if not any(
                hostname == d.lower() or hostname.endswith(f".{d.lower()}")
                for d in allowed_domains
            ):
                # Domain is outside allowlist: Record explicit failure
                ev_id = f"ev-blocked-{candidate.query_id}"
                evidence_ledger[ev_id] = EvidenceRecord(
                    evidence_id=ev_id,
                    url=candidate.url,
                    opened_excerpt=candidate.candidate_excerpt,
                    source_type=candidate.source_type,
                    verification_status=VerificationStatus.INACCESSIBLE,
                    failure_category=FailureCategory.SSRF_BLOCKED,
                    failure_reason=f"Domain '{hostname}' is not in pre-approved allowed_domains whitelist: {allowed_domains}",
                    is_independent=candidate.is_independent,
                )
                continue

            # Run verifier under policy
            ev_record = verifier.verify_url(
                url=candidate.url,
                candidate_excerpt=candidate.candidate_excerpt,
                source_type=candidate.source_type,
                is_independent=candidate.is_independent,
            )

            evidence_ledger[ev_record.evidence_id] = ev_record
            if ev_record.verification_status == VerificationStatus.OPENED_VERIFIED:
                query_evidence_ids[candidate.query_id].append(ev_record.evidence_id)

        # Step 4: Construct AuditRun Claims for approved queries
        claims: List[ClaimRecord] = []
        for qid, q in approved_queries_map.items():
            ev_ids = query_evidence_ids.get(qid, [])
            if ev_ids:  # Only build claims for queries with verified evidence
                claims.append(
                    ClaimRecord(
                        claim_id=f"claim-{qid}",
                        statement=f"Verified public source evidence exists for query '{q.text}' (Intent: {q.intent.value}).",
                        evidence_ids=ev_ids,
                        uncertainty_notes=f"Controlled non-client public dataset run. Rationale: {q.rationale}",
                    )
                )

        return AuditRun(
            run_id=f"run-qm-{query_map.query_map_id}",
            client_domain=query_map.entity_name,
            category=query_map.category,
            is_synthetic_fixture=True,
            notice="CONTROLLED NON-CLIENT DATASET SPIKE - NOT A COMMERCIAL CLIENT AUDIT",
            evidence_ledger=evidence_ledger,
            claims=claims,
        )
