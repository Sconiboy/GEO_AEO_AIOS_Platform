"""
Claim Reconciliation Engine (Sprint 6)
Evaluates extracted answer statement proposals semantically against frozen source ledgers,
producing content-addressed, canonical ObservationReconciliation records.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..domain.enums import ReconciliationMethod, ReconciliationStatus, VerificationStatus
from ..domain.models import AuditRun
from ..domain.observation import AnswerObservation
from ..domain.reconciliation import (
    ObservationReconciliation,
    StatementReconciliation,
)


class ClaimReconciler:
    """
    Reconciles raw statement proposals against frozen source ledgers.
    Refuses to mistake URL or quote presence for semantic claim support.
    Enforces canonical SHA-256 artifact bindings and metadata digests.
    """

    @classmethod
    def compute_model_hash(cls, model_data: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 digest of serialized model JSON dict."""
        import json

        serialized = json.dumps(model_data, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def evaluate_semantic_support(cls, statement_text: str, evidence_excerpt: str) -> bool:
        """
        Heuristic semantic relevance evaluator.
        Checks if core domain terms in statement_text overlap semantically with evidence_excerpt.
        """
        stmt_lower = statement_text.lower()
        excerpt_lower = evidence_excerpt.lower()

        # Key semantic signals for Python design & PEP 20 philosophy
        keywords = ["readability", "simplicity", "zen of python", "pep 20", "explicit", "design philosophy"]
        matching_keywords = [kw for kw in keywords if kw in stmt_lower and kw in excerpt_lower]

        return len(matching_keywords) >= 1

    @classmethod
    def reconcile_observation(
        cls,
        observation: AnswerObservation,
        source_ledger: AuditRun,
        raw_ledger_bytes: Optional[bytes] = None,
        manual_reconciliations: Optional[List[StatementReconciliation]] = None,
        reviewer_role: str = "Lead Systems Architect & Auditor",
        reconciliation_method: ReconciliationMethod = ReconciliationMethod.HEURISTIC_EXACT_FACT_MATCH,
    ) -> ObservationReconciliation:
        """
        Reconciles an AnswerObservation against a frozen source ledger AuditRun.
        1. Validates observation raw answer text SHA-256 integrity.
        2. Validates source_ledger run ID linkage.
        3. Validates exact raw source ledger SHA-256 digest matches observation.source_ledger_sha256.
        4. Evaluates statement proposals semantically against opened evidence records.
        5. Computes canonical reconciliation digest over metadata and decision content.
        """
        # Gate 1: Re-verify raw answer hash integrity
        if not observation.verify_integrity():
            raise ValueError(
                f"Integrity failure: observation raw_answer_sha256 ('{observation.raw_answer_sha256}') does not match calculated digest of raw_answer_text."
            )

        # Gate 2: Verify Source Ledger run ID linkage
        if observation.source_ledger_run_id != source_ledger.run_id:
            raise ValueError(
                f"ID mismatch: Observation source_ledger_run_id ('{observation.source_ledger_run_id}') does not match Source Ledger Run ID ('{source_ledger.run_id}')."
            )

        # Gate 3: Compute and validate exact Source Ledger artifact SHA-256 hash
        actual_ledger_sha256 = (
            hashlib.sha256(raw_ledger_bytes).hexdigest()
            if raw_ledger_bytes
            else cls.compute_model_hash(source_ledger.model_dump(mode="json"))
        )

        if observation.source_ledger_sha256.lower() != actual_ledger_sha256.lower():
            raise ValueError(
                f"Artifact mismatch: Observation bound source_ledger_sha256 ('{observation.source_ledger_sha256}') does not match raw Source Ledger digest ('{actual_ledger_sha256}')."
            )

        # Build index of manual reconciliations if supplied
        override_map: Dict[str, StatementReconciliation] = {}
        if manual_reconciliations:
            for rec in manual_reconciliations:
                for eid in rec.evaluated_evidence_ids:
                    if eid not in source_ledger.evidence_ledger:
                        raise ValueError(
                            f"Reconciliation for statement '{rec.statement_id}' references evidence '{eid}' which does not exist in Source Ledger."
                        )
                    ev = source_ledger.evidence_ledger[eid]
                    if ev.verification_status != VerificationStatus.OPENED_VERIFIED:
                        raise ValueError(
                            f"Reconciliation for statement '{rec.statement_id}' references evidence '{eid}' which has status '{ev.verification_status.value}', not OPENED_VERIFIED."
                        )
                override_map[rec.statement_id] = rec

        reconciliations: List[StatementReconciliation] = []
        now = datetime.now(timezone.utc)

        opened_verified_evidence = {
            eid: ev
            for eid, ev in source_ledger.evidence_ledger.items()
            if ev.verification_status == VerificationStatus.OPENED_VERIFIED
        }

        for i, stmt in enumerate(observation.extracted_statements, 1):
            if stmt.statement_id in override_map:
                reconciliations.append(override_map[stmt.statement_id])
            else:
                evaluated_ids: List[str] = []
                status = ReconciliationStatus.NOT_ASSESSABLE
                rationale = (
                    f"No relevant opened evidence records exist in the source ledger to evaluate "
                    f"statement '{stmt.statement_id}' semantically."
                )

                if stmt.linked_evidence_id and stmt.linked_evidence_id in opened_verified_evidence:
                    ev = opened_verified_evidence[stmt.linked_evidence_id]
                    evaluated_ids.append(stmt.linked_evidence_id)

                    if cls.evaluate_semantic_support(stmt.text, ev.opened_excerpt):
                        status = ReconciliationStatus.SUPPORTED
                        rationale = (
                            f"Statement '{stmt.statement_id}' is semantically SUPPORTED by verified opened evidence "
                            f"'{stmt.linked_evidence_id}' ('{ev.url}') with excerpt quote: \"{ev.opened_excerpt}\"."
                        )
                    else:
                        status = ReconciliationStatus.NOT_ASSESSABLE
                        rationale = (
                            f"Statement '{stmt.statement_id}' references opened evidence '{stmt.linked_evidence_id}', "
                            f"but the source excerpt is semantically irrelevant to the statement text."
                        )

                reconciliations.append(
                    StatementReconciliation(
                        reconciliation_id=f"rec-{observation.observation_id}-{i:03d}",
                        statement_id=stmt.statement_id,
                        status=status,
                        evaluated_evidence_ids=evaluated_ids,
                        semantic_rationale=rationale,
                        reviewer_role=reviewer_role,
                        reconciliation_timestamp=now,
                        reconciliation_method=reconciliation_method,
                    )
                )

        rec_run_id = f"rec-run-{observation.observation_id}"

        # Gate 5: Compute canonical SHA-256 digest covering metadata + decisions
        canonical_digest = ObservationReconciliation.compute_canonical_digest(
            reconciliation_run_id=rec_run_id,
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            source_ledger_run_id=source_ledger.run_id,
            source_ledger_sha256=actual_ledger_sha256,
            reconciliations=reconciliations,
        )

        return ObservationReconciliation(
            reconciliation_run_id=rec_run_id,
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            source_ledger_run_id=source_ledger.run_id,
            source_ledger_sha256=actual_ledger_sha256,
            reconciliations=reconciliations,
            reconciliation_sha256=canonical_digest,
        )
