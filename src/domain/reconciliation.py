"""
Domain Models for Claim Reconciliation Contracts (Sprint 5.1 Remediation)
Evaluates extracted statement proposals semantically against frozen source ledgers with canonical digest bindings.
"""

import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import ReconciliationMethod, ReconciliationStatus

__all__ = [
    "ReconciliationStatus",
    "ReconciliationMethod",
    "StatementReconciliation",
    "ObservationReconciliation",
]


class StatementReconciliation(BaseModel):
    """
    Immutable semantic decision for an individual extracted statement.
    Binds directly to statement_id, evaluated evidence IDs, and semantic rationale.
    """

    model_config = ConfigDict(frozen=True)

    reconciliation_id: str = Field(..., description="Unique reconciliation decision ID")
    statement_id: str = Field(..., description="ID of ExtractedStatement evaluated")
    status: ReconciliationStatus = Field(..., description="Semantic evaluation decision")
    evaluated_evidence_ids: List[str] = Field(
        default_factory=list, description="IDs of EvidenceRecords evaluated for this decision"
    )
    semantic_rationale: str = Field(
        ..., min_length=10, description="Explicit human or assisted semantic explanation"
    )
    reviewer_role: str = Field(..., description="Role of reviewer or method (e.g. Lead Auditor)")
    reconciliation_timestamp: datetime = Field(
        ..., description="Timestamp when reconciliation decision was recorded"
    )
    reconciliation_method: ReconciliationMethod = Field(
        ..., description="Method used for reconciliation"
    )


class ObservationReconciliation(BaseModel):
    """
    Immutable reconciliation run record evaluating all statements in an AnswerObservation.
    Binds content-addressed SHA-256 hashes of observation, query map, manifest, and source ledger.
    """

    model_config = ConfigDict(frozen=True)

    reconciliation_run_id: str = Field(..., description="Unique reconciliation run ID")
    observation_id: str = Field(..., description="ID of bound AnswerObservation")
    raw_answer_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 hash of raw_answer_text"
    )
    source_ledger_run_id: str = Field(..., description="ID of bound Source Ledger AuditRun")
    source_ledger_sha256: str = Field(
        ..., min_length=64, max_length=64, description="SHA-256 hash of bound Source Ledger artifact"
    )
    reconciliations: List[StatementReconciliation] = Field(
        default_factory=list, description="List of individual statement reconciliation decisions"
    )
    reconciliation_sha256: str = Field(
        ..., min_length=64, max_length=64, description="Canonical SHA-256 digest of full reconciliation record"
    )

    @field_validator("raw_answer_sha256", "source_ledger_sha256", "reconciliation_sha256")
    @classmethod
    def clean_hash_lowercase(cls, v: str) -> str:
        return v.strip().lower()

    @classmethod
    def compute_canonical_digest(
        cls,
        reconciliation_run_id: str,
        observation_id: str,
        raw_answer_sha256: str,
        source_ledger_run_id: str,
        source_ledger_sha256: str,
        reconciliations: List[StatementReconciliation],
    ) -> str:
        """
        Computes a deterministic canonical SHA-256 digest covering all run metadata and statement decisions.
        """
        payload: Dict[str, Any] = {
            "reconciliation_run_id": reconciliation_run_id,
            "observation_id": observation_id,
            "raw_answer_sha256": raw_answer_sha256.lower(),
            "source_ledger_run_id": source_ledger_run_id,
            "source_ledger_sha256": source_ledger_sha256.lower(),
            "reconciliations": [r.model_dump(mode="json") for r in reconciliations],
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """
        Re-verifies that reconciliation_sha256 matches the calculated canonical digest over metadata & decisions.
        Returns True if intact, False if mutated or tampered.
        """
        computed = self.compute_canonical_digest(
            reconciliation_run_id=self.reconciliation_run_id,
            observation_id=self.observation_id,
            raw_answer_sha256=self.raw_answer_sha256,
            source_ledger_run_id=self.source_ledger_run_id,
            source_ledger_sha256=self.source_ledger_sha256,
            reconciliations=self.reconciliations,
        )
        return self.reconciliation_sha256.lower() == computed.lower()
