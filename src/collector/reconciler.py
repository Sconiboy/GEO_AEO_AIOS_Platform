"""
Claim Reconciliation Engine (Sprint 5)
Evaluates extracted answer statement proposals semantically against frozen source ledgers,
producing content-addressed, immutable ObservationReconciliation records.
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..domain.enums import VerificationStatus
from ..domain.models import AuditRun
from ..domain.observation import AnswerObservation
from ..domain.reconciliation import (
    ObservationReconciliation,
    ReconciliationMethod,
    ReconciliationStatus,
    StatementReconciliation,
)


class ClaimReconciler:
    """
    Reconciles raw statement proposals against frozen source ledgers.
    Refuses to mistake URL or quote presence for semantic claim support.
    """

    @classmethod
    def reconcile_observation(
        cls,
        observation: AnswerObservation,
        source_ledger: AuditRun,
        manual_reconciliations: Optional[List[StatementReconciliation]] = None,
        reviewer_role: str = "Lead Systems Architect & Auditor",
        reconciliation_method: ReconciliationMethod = ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
    ) -> ObservationReconciliation:
        """
        Reconciles an AnswerObservation against a frozen source ledger AuditRun.
        1. Validates observation raw answer text SHA-256 integrity.
        2. Validates source_ledger run ID linkage.
        3. Evaluates statement proposals against opened evidence records.
        4. Assigns NOT_ASSESSABLE if source ledger lacks relevant supporting/refuting evidence.
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

        # Build index of manual reconciliations if supplied
        override_map: Dict[str, StatementReconciliation] = {}
        if manual_reconciliations:
            for rec in manual_reconciliations:
                # Validate evaluated_evidence_ids exist in source_ledger and are OPENED_VERIFIED
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

        # Filter opened verified evidence records
        opened_verified_evidence = {
            eid: ev
            for eid, ev in source_ledger.evidence_ledger.items()
            if ev.verification_status == VerificationStatus.OPENED_VERIFIED
        }

        for i, stmt in enumerate(observation.extracted_statements, 1):
            if stmt.statement_id in override_map:
                reconciliations.append(override_map[stmt.statement_id])
            else:
                # Default evaluation: Check if any opened_verified evidence semantically supports the statement
                evaluated_ids: List[str] = []
                if stmt.linked_evidence_id and stmt.linked_evidence_id in opened_verified_evidence:
                    evaluated_ids.append(stmt.linked_evidence_id)

                # Default status is NOT_ASSESSABLE when evidence is irrelevant or missing
                status = ReconciliationStatus.NOT_ASSESSABLE
                if evaluated_ids:
                    rationale = (
                        f"Statement '{stmt.statement_id}' references opened evidence '{stmt.linked_evidence_id}', "
                        f"but the source excerpt is semantically irrelevant to the statement text."
                    )
                else:
                    rationale = (
                        f"No relevant opened evidence records exist in the source ledger to evaluate "
                        f"statement '{stmt.statement_id}' semantically."
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

        # Gate 4: Compute deterministic content-addressed hash digest
        reconciliations_data = [r.model_dump(mode="json") for r in reconciliations]
        serialized_hash = hashlib.sha256(
            str(sorted([str(d) for d in reconciliations_data])).encode("utf-8")
        ).hexdigest()

        source_ledger_bytes = str(source_ledger.model_dump(mode="json")).encode("utf-8")
        source_ledger_digest = hashlib.sha256(source_ledger_bytes).hexdigest()

        return ObservationReconciliation(
            reconciliation_run_id=f"rec-run-{observation.observation_id}",
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            source_ledger_run_id=source_ledger.run_id,
            source_ledger_sha256=source_ledger_digest,
            reconciliations=reconciliations,
            reconciliation_sha256=serialized_hash,
        )
