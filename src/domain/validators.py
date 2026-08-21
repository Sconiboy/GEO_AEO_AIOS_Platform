"""
Evidence Ledger Runtime Validation Logic
"""

from typing import List
from .enums import VerificationStatus
from .models import AuditRun, ClaimRecord, ConfidenceScore


class EvidenceLedgerValidationError(Exception):
    """Raised when an AuditRun fails runtime evidence validation prior to report export."""

    def __init__(self, message: str, ungrounded_claims: List[str]):
        super().__init__(message)
        self.message = message
        self.ungrounded_claims = ungrounded_claims


def validate_audit_run_ledger(audit_run: AuditRun) -> AuditRun:
    """
    Validates that every ClaimRecord in the AuditRun has verified evidence.
    Computes deterministic ConfidenceScore for each valid claim.

    Raises EvidenceLedgerValidationError if any claim:
    1. Has no evidence IDs linked.
    2. References evidence IDs missing from the evidence_ledger.
    3. References evidence IDs that are not OPENED_VERIFIED (e.g. Inaccessible or Quote Mismatch).
    """
    if not audit_run.claims:
        raise EvidenceLedgerValidationError(
            message="AuditRun contains no claim records to validate.",
            ungrounded_claims=[],
        )

    failed_claim_ids: List[str] = []
    error_messages: List[str] = []

    for claim in audit_run.claims:
        if not claim.evidence_ids:
            failed_claim_ids.append(claim.claim_id)
            error_messages.append(
                f"Claim '{claim.claim_id}' ('{claim.statement}') has zero linked evidence IDs."
            )
            continue

        valid_evidence_items = []
        invalid_evidence_notes = []

        for eid in claim.evidence_ids:
            if eid not in audit_run.evidence_ledger:
                invalid_evidence_notes.append(
                    f"Evidence ID '{eid}' is missing from the evidence_ledger."
                )
                continue

            evidence_item = audit_run.evidence_ledger[eid]
            if evidence_item.verification_status != VerificationStatus.OPENED_VERIFIED:
                invalid_evidence_notes.append(
                    f"Evidence '{eid}' ({evidence_item.url}) has status '{evidence_item.verification_status.value}', expected '{VerificationStatus.OPENED_VERIFIED.value}'."
                )
                continue

            valid_evidence_items.append(evidence_item)

        if not valid_evidence_items:
            failed_claim_ids.append(claim.claim_id)
            notes_str = " ".join(invalid_evidence_notes)
            error_messages.append(
                f"Claim '{claim.claim_id}' lacks verified evidence. Reasons: {notes_str}"
            )
        else:
            # Gather counter-evidence if present
            counter_evidence_items = [
                audit_run.evidence_ledger[ceid]
                for ceid in claim.counter_evidence_ids
                if ceid in audit_run.evidence_ledger
            ]
            # Compute deterministic confidence score
            claim.confidence = ConfidenceScore.compute(
                evidence_list=valid_evidence_items,
                counter_evidence_list=counter_evidence_items,
            )

    if failed_claim_ids:
        summary_msg = (
            f"AuditRun '{audit_run.run_id}' failed evidence validation. "
            f"{len(failed_claim_ids)} ungrounded claim(s) detected:\n"
            + "\n".join(f"- {msg}" for msg in error_messages)
        )
        raise EvidenceLedgerValidationError(
            message=summary_msg, ungrounded_claims=failed_claim_ids
        )

    return audit_run
