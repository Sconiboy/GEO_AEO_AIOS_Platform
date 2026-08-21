"""
Domain Models for Claim Reconciliation Contracts (Sprint 5)
Evaluates extracted statement proposals semantically against frozen source ledgers.
"""

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReconciliationStatus(str, Enum):
    """Semantic truth evaluation status of a statement against evidence."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    NOT_ASSESSABLE = "not_assessable"


class ReconciliationMethod(str, Enum):
    """Method used to reconcile statement against source evidence."""

    HUMAN_AUDITOR_REVIEW = "human_auditor_review"
    HEURISTIC_EXACT_FACT_MATCH = "heuristic_exact_fact_match"
    STRUCTURED_LLM_ASSISTED_REVIEW = "structured_llm_assisted_review"


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
        ..., min_length=64, max_length=64, description="SHA-256 digest of reconciliation content"
    )

    @field_validator("raw_answer_sha256", "source_ledger_sha256", "reconciliation_sha256")
    @classmethod
    def clean_hash_lowercase(cls, v: str) -> str:
        return v.strip().lower()

    def verify_integrity(self) -> bool:
        """Re-verifies that reconciliation_sha256 matches calculated digest of statement decisions."""
        statements_data = [r.model_dump(mode="json") for r in self.reconciliations]
        serialized = hashlib.sha256(
            str(sorted([str(d) for d in statements_data])).encode("utf-8")
        ).hexdigest()
        return self.reconciliation_sha256.lower() == serialized.lower()
