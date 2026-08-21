"""
Human Semantic Decision Domain Contracts (Sprint 6.4.1)
Defines immutable, content-addressed decision records representing human auditor governance.
Enforces verbatim quote validation against opened evidence excerpts, quote-evidence pairing,
declared reviewer identity, and timestamp digest binding.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

from .enums import ReconciliationMethod, ReconciliationStatus


class QuotedEvidencePassage(BaseModel):
    """
    Explicit binding between a cited evidence record and a verbatim quoted passage.
    """

    model_config = {"frozen": True}

    evidence_id: str = Field(..., description="Cited EvidenceRecord ID from Source Ledger")
    quoted_passage: str = Field(..., min_length=1, description="Verbatim passage extracted from evidence opened_excerpt")
    snapshot_sha256: Optional[str] = Field(default=None, description="Durable snapshot SHA-256 reference digest")


class HumanStatementDecision(BaseModel):
    """
    Immutable human auditor decision for a single extracted statement proposal.
    """

    model_config = {"frozen": True}

    decision_id: str = Field(..., description="Unique decision identifier, e.g. hdec-stmt-001")
    statement_id: str = Field(..., description="Target statement ID from AnswerObservation")
    decision_status: ReconciliationStatus = Field(..., description="Human-adjudicated status")
    quoted_evidence: List[QuotedEvidencePassage] = Field(..., min_length=1, description="Explicit quote-evidence pairings")
    auditor_rationale: str = Field(..., min_length=10, description="Detailed technical rationale for human decision")
    declared_reviewer_identity: str = Field(default="Lead Systems Architect & Auditor", description="Declared identity of reviewer")
    decision_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of human decision")
    reconciliation_method: ReconciliationMethod = Field(default=ReconciliationMethod.HUMAN_AUDITOR_REVIEW)


class HumanDecisionRecord(BaseModel):
    """
    Content-addressed, immutable record of human governance decisions over an AnswerObservation reconciliation.
    Binds exact observation ID, raw answer SHA-256, source ledger run ID, raw ledger SHA-256, query map SHA-256, and manifest SHA-256.
    Includes decision timestamps, reconciliation methods, and quoted evidence bindings in canonical digest.
    """

    model_config = {"frozen": True}

    decision_record_id: str = Field(..., description="Unique decision record identifier")
    observation_id: str = Field(..., description="Bound AnswerObservation ID")
    raw_answer_sha256: str = Field(..., description="Bound SHA-256 digest of raw answer text")
    source_ledger_run_id: str = Field(..., description="Bound AuditRun source ledger run ID")
    source_ledger_sha256: str = Field(..., description="Bound raw SHA-256 digest of source ledger artifact")
    query_map_sha256: str = Field(..., description="Bound SHA-256 digest of QueryMap artifact")
    manifest_sha256: str = Field(..., description="Bound SHA-256 digest of DatasetManifest artifact")
    decisions: List[HumanStatementDecision] = Field(..., min_length=1, description="List of human statement decisions")
    canonical_digest: str = Field(..., description="Content-addressed SHA-256 digest over all context bindings and decisions")

    @classmethod
    def compute_canonical_digest(
        cls,
        decision_record_id: str,
        observation_id: str,
        raw_answer_sha256: str,
        source_ledger_run_id: str,
        source_ledger_sha256: str,
        query_map_sha256: str,
        manifest_sha256: str,
        decisions: List[HumanStatementDecision],
    ) -> str:
        """
        Computes deterministic SHA-256 canonical digest covering all context bindings,
        timestamps, methods, declared reviewer identity, and paired quoted evidence.
        """
        payload = {
            "decision_record_id": decision_record_id,
            "observation_id": observation_id,
            "raw_answer_sha256": raw_answer_sha256.lower(),
            "source_ledger_run_id": source_ledger_run_id,
            "source_ledger_sha256": source_ledger_sha256.lower(),
            "query_map_sha256": query_map_sha256.lower(),
            "manifest_sha256": manifest_sha256.lower(),
            "decisions": [
                {
                    "decision_id": d.decision_id,
                    "statement_id": d.statement_id,
                    "decision_status": d.decision_status.value,
                    "quoted_evidence": [
                        {
                            "evidence_id": q.evidence_id,
                            "quoted_passage": q.quoted_passage,
                            "snapshot_sha256": q.snapshot_sha256,
                        }
                        for q in sorted(d.quoted_evidence, key=lambda x: (x.evidence_id, x.quoted_passage))
                    ],
                    "auditor_rationale": d.auditor_rationale,
                    "declared_reviewer_identity": d.declared_reviewer_identity,
                    "decision_timestamp": d.decision_timestamp.isoformat(),
                    "reconciliation_method": d.reconciliation_method.value,
                }
                for d in sorted(decisions, key=lambda x: x.statement_id)
            ],
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verifies that canonical_digest matches the calculated hash over current data."""
        expected = self.compute_canonical_digest(
            decision_record_id=self.decision_record_id,
            observation_id=self.observation_id,
            raw_answer_sha256=self.raw_answer_sha256,
            source_ledger_run_id=self.source_ledger_run_id,
            source_ledger_sha256=self.source_ledger_sha256,
            query_map_sha256=self.query_map_sha256,
            manifest_sha256=self.manifest_sha256,
            decisions=self.decisions,
        )
        return self.canonical_digest.lower() == expected.lower()
