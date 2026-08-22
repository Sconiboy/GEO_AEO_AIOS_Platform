"""
Candidate Collection Execution Domain Contracts (Sprint 7.5.1)
Immutable, content-addressed records tracing candidate-to-evidence collection provenance.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from .enums import FailureCategory, VerificationStatus


class CollectionExecutionRecord(BaseModel):
    """
    Content-addressed, immutable record of an executed candidate evidence collection.
    Binds candidate ID, originating observation ID, raw answer SHA-256, profile ID/digest,
    manifest digest, query map digest, source ledger digest, evidence ID, verifier run ID,
    snapshot SHA-256, and execution timestamp.
    """

    model_config = {"frozen": True}

    execution_id: str = Field(..., description="Unique execution record ID (e.g. cer-occ-q-001-...)")
    candidate_id: str = Field(..., description="Bound ObservedCitationCollectionCandidate ID")
    target_query_id: str = Field(..., description="Bound target query ID")
    cited_url: str = Field(..., description="Exact authorized collected URL")
    observation_id: str = Field(..., description="Bound AnswerObservation ID")
    raw_answer_sha256: str = Field(..., description="Bound raw answer SHA-256 digest")
    profile_id: str = Field(..., description="Bound SubjectProfile ID")
    profile_sha256: str = Field(..., description="Bound raw SubjectProfile SHA-256 digest")
    manifest_sha256: str = Field(..., description="Bound raw DatasetManifest SHA-256 digest")
    query_map_sha256: str = Field(..., description="Bound raw QueryMap SHA-256 digest")
    source_ledger_sha256: str = Field(..., description="Bound raw Source Ledger SHA-256 digest")
    evidence_id: str = Field(..., description="Generated EvidenceRecord ID in ledger")
    verifier_run_id: str = Field(..., description="Verifier run ID")
    snapshot_sha256: str = Field(..., description="Saved HTML snapshot SHA-256 digest")
    issuer_id: str = Field(default="", description="Configured collector issuer identity bound into the execution digest")
    issuer_attestation: Optional[str] = Field(default=None, description="Detached authenticity proof issued by the configured collector")
    execution_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Explicit UTC timestamp of collection execution",
    )
    canonical_digest: str = Field(..., description="Content-addressed SHA-256 digest over all context bindings and evidence metadata")

    @classmethod
    def compute_canonical_digest(
        cls,
        execution_id: str,
        candidate_id: str,
        target_query_id: str,
        cited_url: str,
        observation_id: str,
        raw_answer_sha256: str,
        profile_id: str,
        profile_sha256: str,
        manifest_sha256: str,
        query_map_sha256: str,
        source_ledger_sha256: str,
        evidence_id: str,
        verifier_run_id: str,
        snapshot_sha256: str,
        execution_timestamp: datetime,
        issuer_id: str = "",
    ) -> str:
        """Computes deterministic SHA-256 digest over all execution context bindings."""
        payload: Dict[str, Any] = {
            "execution_id": execution_id,
            "candidate_id": candidate_id,
            "target_query_id": target_query_id,
            "cited_url": cited_url,
            "observation_id": observation_id,
            "raw_answer_sha256": raw_answer_sha256.lower(),
            "profile_id": profile_id,
            "profile_sha256": profile_sha256.lower(),
            "manifest_sha256": manifest_sha256.lower(),
            "query_map_sha256": query_map_sha256.lower(),
            "source_ledger_sha256": source_ledger_sha256.lower(),
            "evidence_id": evidence_id,
            "verifier_run_id": verifier_run_id,
            "snapshot_sha256": snapshot_sha256.lower(),
            "issuer_id": issuer_id,
            "execution_timestamp": execution_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verifies that canonical_digest matches expected calculation."""
        expected = self.compute_canonical_digest(
            execution_id=self.execution_id,
            candidate_id=self.candidate_id,
            target_query_id=self.target_query_id,
            cited_url=self.cited_url,
            observation_id=self.observation_id,
            raw_answer_sha256=self.raw_answer_sha256,
            profile_id=self.profile_id,
            profile_sha256=self.profile_sha256,
            manifest_sha256=self.manifest_sha256,
            query_map_sha256=self.query_map_sha256,
            source_ledger_sha256=self.source_ledger_sha256,
            evidence_id=self.evidence_id,
            verifier_run_id=self.verifier_run_id,
            snapshot_sha256=self.snapshot_sha256,
            execution_timestamp=self.execution_timestamp,
            issuer_id=self.issuer_id,
        )
        return self.canonical_digest.lower() == expected.lower()


class CollectionAttemptRecord(BaseModel):
    """
    Content-addressed, immutable record of a failed candidate collection attempt.
    Tracks failure_category, failure_reason, and verification_status without false success claims or dummy snapshot hashes.
    """

    model_config = {"frozen": True}

    attempt_id: str = Field(..., description="Unique attempt record ID (e.g. car-occ-q-001-...)")
    candidate_id: str = Field(..., description="Bound ObservedCitationCollectionCandidate ID")
    target_query_id: str = Field(..., description="Bound target query ID")
    cited_url: str = Field(..., description="Exact target URL attempted")
    observation_id: str = Field(..., description="Bound AnswerObservation ID")
    raw_answer_sha256: str = Field(..., description="Bound raw answer SHA-256 digest")
    profile_id: str = Field(..., description="Bound SubjectProfile ID")
    profile_sha256: str = Field(..., description="Bound raw SubjectProfile SHA-256 digest")
    manifest_sha256: str = Field(..., description="Bound raw DatasetManifest SHA-256 digest")
    query_map_sha256: str = Field(..., description="Bound raw QueryMap SHA-256 digest")
    source_ledger_sha256: str = Field(..., description="Bound raw Source Ledger SHA-256 digest")
    evidence_id: str = Field(..., description="Generated EvidenceRecord ID in ledger")
    verification_status: VerificationStatus = Field(..., description="Failed verification status (e.g. INACCESSIBLE)")
    failure_category: Optional[FailureCategory] = Field(default=None, description="Typed failure category if available")
    failure_reason: Optional[str] = Field(default=None, description="Detailed failure reason string")
    attempt_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Explicit UTC timestamp of collection attempt",
    )
    canonical_digest: str = Field(..., description="Content-addressed SHA-256 digest over all attempt bindings and failure metadata")

    @classmethod
    def compute_canonical_digest(
        cls,
        attempt_id: str,
        candidate_id: str,
        target_query_id: str,
        cited_url: str,
        observation_id: str,
        raw_answer_sha256: str,
        profile_id: str,
        profile_sha256: str,
        manifest_sha256: str,
        query_map_sha256: str,
        source_ledger_sha256: str,
        evidence_id: str,
        verification_status: VerificationStatus,
        failure_category: Optional[FailureCategory],
        failure_reason: Optional[str],
        attempt_timestamp: datetime,
    ) -> str:
        """Computes deterministic SHA-256 digest over all attempt context bindings."""
        payload: Dict[str, Any] = {
            "attempt_id": attempt_id,
            "candidate_id": candidate_id,
            "target_query_id": target_query_id,
            "cited_url": cited_url,
            "observation_id": observation_id,
            "raw_answer_sha256": raw_answer_sha256.lower(),
            "profile_id": profile_id,
            "profile_sha256": profile_sha256.lower(),
            "manifest_sha256": manifest_sha256.lower(),
            "query_map_sha256": query_map_sha256.lower(),
            "source_ledger_sha256": source_ledger_sha256.lower(),
            "evidence_id": evidence_id,
            "verification_status": verification_status.value,
            "failure_category": failure_category.value if failure_category else None,
            "failure_reason": failure_reason,
            "attempt_timestamp": attempt_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verifies that canonical_digest matches expected calculation."""
        expected = self.compute_canonical_digest(
            attempt_id=self.attempt_id,
            candidate_id=self.candidate_id,
            target_query_id=self.target_query_id,
            cited_url=self.cited_url,
            observation_id=self.observation_id,
            raw_answer_sha256=self.raw_answer_sha256,
            profile_id=self.profile_id,
            profile_sha256=self.profile_sha256,
            manifest_sha256=self.manifest_sha256,
            query_map_sha256=self.query_map_sha256,
            source_ledger_sha256=self.source_ledger_sha256,
            evidence_id=self.evidence_id,
            verification_status=self.verification_status,
            failure_category=self.failure_category,
            failure_reason=self.failure_reason,
            attempt_timestamp=self.attempt_timestamp,
        )
        return self.canonical_digest.lower() == expected.lower()
