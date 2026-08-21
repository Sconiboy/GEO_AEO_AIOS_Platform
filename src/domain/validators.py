"""
Evidence Ledger Runtime Validation Logic
"""

from typing import List
from .enums import VerificationStatus
from .models import AuditRun, ClaimRecord, ConfidenceScore, EvidenceRecord


class EvidenceLedgerValidationError(Exception):
    """Raised when an AuditRun fails runtime evidence validation prior to report export."""

    def __init__(self, message: str, ungrounded_claims: List[str]):
        super().__init__(message)
        self.message = message
        self.ungrounded_claims = ungrounded_claims


def validate_evidence_record(evidence_id: str, audit_run: AuditRun, is_counter: bool = False) -> EvidenceRecord:
    """
    Validates a single evidence record ID against the audit_run ledger.
    Raises ValueError if missing, invalid status, or missing verification artifact.
    """
    if evidence_id not in audit_run.evidence_ledger:
        raise ValueError(f"Evidence ID '{evidence_id}' is missing from evidence_ledger.")

    evidence = audit_run.evidence_ledger[evidence_id]

    if evidence.verification_status != VerificationStatus.OPENED_VERIFIED:
        raise ValueError(
            f"Evidence '{evidence_id}' ({evidence.url}) has status '{evidence.verification_status.value}', expected '{VerificationStatus.OPENED_VERIFIED.value}'."
        )

    if not evidence.verification_artifact:
        raise ValueError(
            f"Evidence '{evidence_id}' ({evidence.url}) is marked OPENED_VERIFIED but lacks a VerificationArtifact."
        )

    if not evidence.verification_artifact.quote_exact_match:
        raise ValueError(
            f"Evidence '{evidence_id}' ({evidence.url}) VerificationArtifact has quote_exact_match=False."
        )

    return evidence


def validate_audit_run_ledger(audit_run: AuditRun) -> AuditRun:
    """
    Validates that every ClaimRecord in the AuditRun has verified evidence.
    Computes deterministic ConfidenceScore for each valid claim.

    Strict Validation Rules (P0):
    1. Every claim MUST have at least 1 supporting evidence ID.
    2. ALL referenced supporting evidence IDs MUST exist and be OPENED_VERIFIED with a valid VerificationArtifact.
       (If ANY supporting evidence ID is missing or invalid, the claim FAILS validation).
    3. ALL referenced counter-evidence IDs MUST exist and be OPENED_VERIFIED.
       (If ANY counter-evidence ID is missing or invalid, the claim FAILS validation).
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
                f"Claim '{claim.claim_id}' ('{claim.statement}') has zero linked supporting evidence IDs."
            )
            continue

        supporting_evidence_items: List[EvidenceRecord] = []
        claim_failed = False
        claim_errors: List[str] = []

        # Validate ALL supporting evidence IDs (Strict Rule: All must pass)
        for eid in claim.evidence_ids:
            try:
                ev = validate_evidence_record(eid, audit_run, is_counter=False)
                supporting_evidence_items.append(ev)
            except ValueError as ve:
                claim_failed = True
                claim_errors.append(str(ve))

        # Validate ALL counter-evidence IDs if provided (Strict Rule: All must pass)
        counter_evidence_items: List[EvidenceRecord] = []
        for ceid in claim.counter_evidence_ids:
            try:
                cev = validate_evidence_record(ceid, audit_run, is_counter=True)
                counter_evidence_items.append(cev)
            except ValueError as ve:
                claim_failed = True
                claim_errors.append(f"Counter-evidence error: {ve}")

        if claim_failed:
            failed_claim_ids.append(claim.claim_id)
            notes_str = " | ".join(claim_errors)
            error_messages.append(
                f"Claim '{claim.claim_id}' failed strict evidence validation. Details: {notes_str}"
            )
        else:
            # Compute deterministic confidence score
            claim.confidence = ConfidenceScore.compute(
                evidence_list=supporting_evidence_items,
                counter_evidence_list=counter_evidence_items,
            )

    if failed_claim_ids:
        summary_msg = (
            f"AuditRun '{audit_run.run_id}' failed strict evidence validation. "
            f"{len(failed_claim_ids)} claim(s) rejected:\n"
            + "\n".join(f"- {msg}" for msg in error_messages)
        )
        raise EvidenceLedgerValidationError(
            message=summary_msg, ungrounded_claims=failed_claim_ids
        )

    return audit_run
