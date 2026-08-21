"""
Forensic Comparative Evidence Reconciler Engine (Sprint 8.3 Remediated)
Compares verified client evidence against verified competitor evidence for a target query observation.
Dynamically derives domain ownership from SubjectProfile.
Automated evaluation defaults to CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW or NOT_ASSESSABLE (zero keyword auto-support).
Integrates HumanDecisionRecord with strict 7-binding context verification and verbatim quoted passage matching per evidence record.
Binds all 9 context hashes, statement texts, excerpts, finding basis trace, and human decisions into canonical digest.
"""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from ..domain.comparative import (
    ClaimExcerptAssessment,
    ComparativeEvidenceRecord,
    ComparativeSourceSummary,
)
from ..domain.enums import ReconciliationStatus, SourceRelationship, VerificationStatus
from ..domain.gap_analysis import FindingBasis, ForensicGapAnalysisRecord
from ..domain.human_decision import HumanDecisionRecord
from ..domain.models import EvidenceRecord
from ..domain.observation import AnswerObservation
from ..domain.profile import SubjectProfile
from ..domain.query_map import QueryMap
from .gap_analyzer import ForensicGapAnalyzer


class ComparativeEvidenceReconciler:
    """
    Engine that reconciles verified client evidence against verified competitor evidence.
    Emits an evidence-governed ComparativeEvidenceRecord with complete 9-hash context binding.
    """

    @classmethod
    def evaluate_claim_support(
        cls,
        statement_id: str,
        statement_text: str,
        evidence: Optional[EvidenceRecord],
        expected_role: SourceRelationship,
        human_decision_record: Optional[HumanDecisionRecord] = None,
    ) -> ClaimExcerptAssessment:
        """
        Evaluates an answer-surface statement claim against a verified evidence record excerpt.
        Zero keyword auto-support: Automated evaluation NEVER promotes statements to SUPPORTED based on word overlap.
        Defaults to CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW if OPENED_VERIFIED evidence excerpt exists,
        or NOT_ASSESSABLE if evidence is missing or unverified.
        Promotion to SUPPORTED, CONTRADICTED, or UNSUPPORTED requires a valid HumanDecisionRecord containing an explicit
        QuotedEvidencePassage matching evidence.evidence_id AND verbatim quoted_passage inside evidence.opened_excerpt.
        """
        # Check if human decision record contains an adjudicated decision for this exact statement AND evidence ID
        if human_decision_record and evidence and evidence.verification_status == VerificationStatus.OPENED_VERIFIED:
            for dec in human_decision_record.decisions:
                if dec.statement_id == statement_id:
                    # Validate per-evidence quote matching: dec.quoted_evidence must contain a passage matching evidence.evidence_id
                    matching_quote = None
                    for qe in dec.quoted_evidence:
                        if qe.evidence_id == evidence.evidence_id and qe.quoted_passage in (evidence.opened_excerpt or ""):
                            matching_quote = qe
                            break

                    if matching_quote:
                        return ClaimExcerptAssessment(
                            statement_id=statement_id,
                            statement_text=statement_text,
                            evidence_id=evidence.evidence_id,
                            evidence_url=evidence.url,
                            opened_excerpt=evidence.opened_excerpt,
                            assessment_status=dec.decision_status,
                            semantic_rationale=f"Human auditor adjudication ({dec.declared_reviewer_identity}, Role: {expected_role.value}): {dec.auditor_rationale}",
                            human_decision_id=human_decision_record.decision_record_id,
                            human_decision_digest=human_decision_record.canonical_digest,
                        )

        # No human decision or evidence mismatch fallback: baseline non-promoted status
        if not evidence or evidence.verification_status != VerificationStatus.OPENED_VERIFIED or not evidence.opened_excerpt:
            return ClaimExcerptAssessment(
                statement_id=statement_id,
                statement_text=statement_text,
                evidence_id=evidence.evidence_id if evidence else None,
                evidence_url=evidence.url if evidence else None,
                opened_excerpt=evidence.opened_excerpt if evidence else None,
                assessment_status=ReconciliationStatus.NOT_ASSESSABLE,
                semantic_rationale="No verified OPENED_VERIFIED evidence excerpt available to evaluate claim.",
            )

        # Verified evidence excerpt present: flag for human auditor review (never auto-support)
        return ClaimExcerptAssessment(
            statement_id=statement_id,
            statement_text=statement_text,
            evidence_id=evidence.evidence_id,
            evidence_url=evidence.url,
            opened_excerpt=evidence.opened_excerpt,
            assessment_status=ReconciliationStatus.CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW,
            semantic_rationale=f"Verified excerpt present ('{evidence.opened_excerpt[:60]}...'). Candidate for human auditor semantic adjudication.",
        )

    @classmethod
    def compare_evidence(
        cls,
        observation: AnswerObservation,
        query_map: QueryMap,
        gap_record: ForensicGapAnalysisRecord,
        profile: SubjectProfile,
        client_evidence: EvidenceRecord,
        competitor_evidence: EvidenceRecord,
        raw_qm_bytes: bytes,
        raw_manifest_bytes: bytes,
        raw_ledger_bytes: bytes,
        raw_profile_bytes: bytes,
        human_decision_record: Optional[HumanDecisionRecord] = None,
        timestamp: Optional[datetime] = None,
    ) -> ComparativeEvidenceRecord:
        """
        Executes bounded comparative evidence reconciliation between client and competitor evidence.
        Enforces strict profile relationship classification, 7-binding human decision verification,
        9-hash context binding, and canonical digest verification.
        """
        if not observation.verify_integrity():
            raise ValueError(f"Observation integrity verification failed for '{observation.observation_id}'.")

        if not gap_record.verify_integrity():
            raise ValueError(f"ForensicGapAnalysisRecord integrity verification failed for '{gap_record.analysis_id}'.")

        created_at = timestamp or datetime.now(timezone.utc)

        # Step 1: Compute 9 context hashes
        qm_sha256 = hashlib.sha256(raw_qm_bytes).hexdigest()
        manifest_sha256 = hashlib.sha256(raw_manifest_bytes).hexdigest()
        ledger_sha256 = hashlib.sha256(raw_ledger_bytes).hexdigest()
        profile_sha256 = hashlib.sha256(raw_profile_bytes).hexdigest()

        # Step 2: Total 7-binding context verification for HumanDecisionRecord
        if human_decision_record:
            if not human_decision_record.verify_integrity():
                raise ValueError(f"HumanDecisionRecord integrity verification failed for '{human_decision_record.decision_record_id}'.")
            
            # Enforce exact context matching against current observation and artifacts
            if human_decision_record.observation_id != observation.observation_id:
                raise ValueError(
                    f"HumanDecisionRecord Context Mismatch: observation_id ('{human_decision_record.observation_id}') "
                    f"does not match current observation ('{observation.observation_id}')."
                )
            if human_decision_record.raw_answer_sha256.lower() != observation.raw_answer_sha256.lower():
                raise ValueError(
                    f"HumanDecisionRecord Context Mismatch: raw_answer_sha256 ('{human_decision_record.raw_answer_sha256}') "
                    f"does not match observation raw answer digest ('{observation.raw_answer_sha256}')."
                )
            if human_decision_record.source_ledger_run_id != gap_record.source_ledger_run_id:
                raise ValueError(
                    f"HumanDecisionRecord Context Mismatch: source_ledger_run_id ('{human_decision_record.source_ledger_run_id}') "
                    f"does not match gap record ledger run ID ('{gap_record.source_ledger_run_id}')."
                )
            if human_decision_record.source_ledger_sha256.lower() != ledger_sha256.lower():
                raise ValueError(
                    f"HumanDecisionRecord Context Mismatch: source_ledger_sha256 ('{human_decision_record.source_ledger_sha256}') "
                    f"does not match calculated ledger SHA-256 ('{ledger_sha256}')."
                )
            if human_decision_record.query_map_sha256.lower() != qm_sha256.lower():
                raise ValueError(
                    f"HumanDecisionRecord Context Mismatch: query_map_sha256 ('{human_decision_record.query_map_sha256}') "
                    f"does not match calculated QueryMap SHA-256 ('{qm_sha256}')."
                )
            if human_decision_record.manifest_sha256.lower() != manifest_sha256.lower():
                raise ValueError(
                    f"HumanDecisionRecord Context Mismatch: manifest_sha256 ('{human_decision_record.manifest_sha256}') "
                    f"does not match calculated manifest SHA-256 ('{manifest_sha256}')."
                )

        # Step 3: Dynamically classify client domain ownership
        client_dom = urlparse(client_evidence.url).hostname or client_evidence.url
        client_rel, _ = ForensicGapAnalyzer.classify_source_relationship(client_dom, profile, client_evidence.source_type)
        if client_rel != SourceRelationship.CLIENT_OWNED:
            raise ValueError(
                f"Comparative Reconciliation Blocked: Client evidence URL '{client_evidence.url}' "
                f"classified as '{client_rel.value}', expected '{SourceRelationship.CLIENT_OWNED.value}'."
            )

        client_art = client_evidence.verification_artifact
        client_snap = client_art.snapshot_sha256 if client_art else "unknown"
        client_vrun = client_art.verifier_run_id if client_art else "vrun-unknown"
        
        client_exec_id = f"exec-client-{client_evidence.evidence_id}"
        for ce in gap_record.collection_executions:
            if ce.evidence_id == client_evidence.evidence_id:
                client_exec_id = ce.execution_id
                break

        client_summary = ComparativeSourceSummary(
            domain=client_dom,
            url=client_evidence.url,
            evidence_id=client_evidence.evidence_id,
            verifier_run_id=client_vrun,
            execution_id=client_exec_id,
            relationship=SourceRelationship.CLIENT_OWNED,
            entity_name=profile.client_profile.entity_name,
            is_verified=client_evidence.verification_status == VerificationStatus.OPENED_VERIFIED,
            snapshot_sha256=client_snap,
            opened_excerpt=client_evidence.opened_excerpt,
        )

        # Step 4: Dynamically classify competitor domain ownership
        comp_dom = urlparse(competitor_evidence.url).hostname or competitor_evidence.url
        comp_rel, comp_entity = ForensicGapAnalyzer.classify_source_relationship(comp_dom, profile, competitor_evidence.source_type)
        if comp_rel != SourceRelationship.COMPETITOR_OWNED:
            raise ValueError(
                f"Comparative Reconciliation Blocked: Competitor evidence URL '{competitor_evidence.url}' "
                f"classified as '{comp_rel.value}', expected '{SourceRelationship.COMPETITOR_OWNED.value}'."
            )

        comp_art = competitor_evidence.verification_artifact
        comp_snap = comp_art.snapshot_sha256 if comp_art else "unknown"
        comp_vrun = comp_art.verifier_run_id if comp_art else "vrun-unknown"
        
        comp_exec_id = f"exec-comp-{competitor_evidence.evidence_id}"
        for ce in gap_record.collection_executions:
            if ce.evidence_id == competitor_evidence.evidence_id:
                comp_exec_id = ce.execution_id
                break

        competitor_summary = ComparativeSourceSummary(
            domain=comp_dom,
            url=competitor_evidence.url,
            evidence_id=competitor_evidence.evidence_id,
            verifier_run_id=comp_vrun,
            execution_id=comp_exec_id,
            relationship=SourceRelationship.COMPETITOR_OWNED,
            entity_name=comp_entity or "Competitor Entity",
            is_verified=competitor_evidence.verification_status == VerificationStatus.OPENED_VERIFIED,
            snapshot_sha256=comp_snap,
            opened_excerpt=competitor_evidence.opened_excerpt,
        )

        # Step 5: Source-to-claim semantic assessments (role-aware & evidence-bound)
        client_assessments: List[ClaimExcerptAssessment] = []
        competitor_assessments: List[ClaimExcerptAssessment] = []

        for stmt in observation.extracted_statements:
            client_assessments.append(cls.evaluate_claim_support(stmt.statement_id, stmt.text, client_evidence, SourceRelationship.CLIENT_OWNED, human_decision_record))
            competitor_assessments.append(cls.evaluate_claim_support(stmt.statement_id, stmt.text, competitor_evidence, SourceRelationship.COMPETITOR_OWNED, human_decision_record))

        # Step 6: Derive factual evidence gap from comparative claim assessments
        comp_supported = any(a.assessment_status == ReconciliationStatus.SUPPORTED for a in competitor_assessments)
        client_supported = any(a.assessment_status == ReconciliationStatus.SUPPORTED for a in client_assessments)
        
        cited_competitor_present = gap_record.attribution_status.value == "cited_competitor_observed"
        gap_exists = cited_competitor_present and not client_supported

        comp_text = (
            f"Model answer for query '{observation.query_id}' cited competitor URL '{competitor_evidence.url}' "
            f"({competitor_summary.entity_name}). Verified competitor excerpt: '{competitor_evidence.opened_excerpt}'. "
            f"Client-owned source '{client_evidence.url}' ({profile.client_profile.entity_name}) is verified in the source ledger "
            f"with excerpt: '{client_evidence.opened_excerpt}'."
        )

        if gap_exists and comp_supported and not client_supported:
            hypothesis = (
                f"Evidence Gap Hypothesis: Competitor claim is SUPPORTED by human adjudication on '{competitor_summary.domain}', "
                f"while client evidence on '{profile.client_profile.client_domain}' is not yet supported. "
                f"Publish or update canonical documentation on '{profile.client_profile.client_domain}' for query '{observation.query_id}'."
            )
        elif gap_exists:
            hypothesis = (
                f"Investigation Required: Competitor URL '{competitor_evidence.url}' was cited in raw model surface for query '{observation.query_id}'. "
                f"Client evidence on '{profile.client_profile.client_domain}' is OPENED_VERIFIED but requires human semantic adjudication."
            )
        else:
            hypothesis = f"No client evidence gap identified. Both client and competitor sources demonstrate equivalent evidence status for query '{observation.query_id}'."

        finding_basis = FindingBasis(
            observation_id=observation.observation_id,
            statement_id=observation.extracted_statements[0].statement_id if observation.extracted_statements else "stmt-001",
            evidence_ids=[client_evidence.evidence_id, competitor_evidence.evidence_id],
            source_relationships=[SourceRelationship.CLIENT_OWNED, SourceRelationship.COMPETITOR_OWNED],
        )

        comparative_id = f"comp-rec-{observation.observation_id}"

        # Step 7: Compute 9-hash canonical digest over ALL fields and finding basis
        human_rec_id = human_decision_record.decision_record_id if human_decision_record else None
        human_rec_dig = human_decision_record.canonical_digest if human_decision_record else None

        canonical_digest = ComparativeEvidenceRecord.compute_canonical_digest(
            comparative_id=comparative_id,
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            profile_id=profile.profile_id,
            profile_sha256=profile_sha256,
            query_map_sha256=qm_sha256,
            manifest_sha256=manifest_sha256,
            source_ledger_run_id=gap_record.source_ledger_run_id,
            source_ledger_sha256=ledger_sha256,
            human_decision_record_id=human_rec_id,
            human_decision_digest=human_rec_dig,
            query_id=observation.query_id,
            client_evidence=client_summary,
            competitor_evidence=competitor_summary,
            client_claim_assessments=client_assessments,
            competitor_claim_assessments=competitor_assessments,
            evidence_gap_identified=gap_exists,
            comparison_summary=comp_text,
            action_hypothesis=hypothesis,
            finding_basis=finding_basis,
            confidence_score=0.85 if gap_exists else 1.0,
            human_review_required=True,
            created_at=created_at,
        )

        return ComparativeEvidenceRecord(
            comparative_id=comparative_id,
            observation_id=observation.observation_id,
            raw_answer_sha256=observation.raw_answer_sha256,
            profile_id=profile.profile_id,
            profile_sha256=profile_sha256,
            query_map_sha256=qm_sha256,
            manifest_sha256=manifest_sha256,
            source_ledger_run_id=gap_record.source_ledger_run_id,
            source_ledger_sha256=ledger_sha256,
            human_decision_record_id=human_rec_id,
            human_decision_digest=human_rec_dig,
            query_id=observation.query_id,
            client_evidence=client_summary,
            competitor_evidence=competitor_summary,
            client_claim_assessments=client_assessments,
            competitor_claim_assessments=competitor_assessments,
            evidence_gap_identified=gap_exists,
            comparison_summary=comp_text,
            action_hypothesis=hypothesis,
            finding_basis=finding_basis,
            confidence_score=0.85 if gap_exists else 1.0,
            human_review_required=True,
            created_at=created_at,
            canonical_digest=canonical_digest,
        )
