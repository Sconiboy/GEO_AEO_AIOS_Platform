"""
Forensic Comparative Evidence Reconciler Engine (Sprint 8.5.1 Remediated)
Compares verified client evidence against verified competitor evidence for a target query observation.
Dynamically derives domain ownership from SubjectProfile.
Parses immutable Source Ledger (AuditRun) directly from raw_ledger_bytes (guaranteeing byte-level identity).
Requires verified CollectionExecutionRecord integrity and exact binding equality against raw artifacts.
Automated evaluation defaults to CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW or NOT_ASSESSABLE (zero keyword auto-support).
Integrates HumanDecisionRecord with strict 7-binding context verification, 6-binding per-evidence quote matching,
and complete execution provenance verification.
Binds all 9 context hashes, statement texts, excerpts, finding basis trace, and human decisions into canonical digest.
"""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from ..domain.candidate_collection import CollectionExecutionRecord
from ..domain.comparative import (
    ClaimExcerptAssessment,
    ComparativeEvidenceRecord,
    ComparativeSourceSummary,
)
from ..domain.enums import HumanApprovalState, ReconciliationStatus, SourceRelationship, VerificationStatus
from ..domain.gap_analysis import FindingBasis, ForensicGapAnalysisRecord
from ..domain.human_decision import HumanDecisionRecord
from ..domain.models import AuditRun, EvidenceRecord
from ..domain.observation import AnswerObservation
from ..domain.profile import SubjectProfile
from ..domain.query_map import QueryMap
from .gap_analyzer import ForensicGapAnalyzer
from .execution_registry import CollectorExecutionRegistry
from .query_map_runner import DatasetManifest
from .snapshot import SnapshotStore


class ComparativeEvidenceReconciler:
    """
    Engine that reconciles verified client evidence against verified competitor evidence.
    Parses evidence directly from raw_ledger_bytes to guarantee 100% byte-level identity.
    Emits an evidence-governed ComparativeEvidenceRecord with complete 9-hash context binding.
    """

    def __init__(self) -> None:
        """Resolves the platform-trusted issuer from protected runtime configuration."""
        self._trusted_execution_registry = CollectorExecutionRegistry.from_runtime_environment()

    @staticmethod
    def _normalize_url(url: str) -> str:
        return url.lower().rstrip("/")

    @classmethod
    def _validate_execution_authority(
        cls,
        execution: CollectionExecutionRecord,
        gap_record: ForensicGapAnalysisRecord,
        observation: AnswerObservation,
        query_map: QueryMap,
        manifest: DatasetManifest,
    ) -> None:
        """Proves that an integrity-valid execution originated from an authorized candidate."""
        candidate = next(
            (item for item in gap_record.collection_candidates if item.candidate_id == execution.candidate_id),
            None,
        )
        if not candidate:
            raise ValueError(
                f"Comparative Reconciliation Blocked: execution '{execution.execution_id}' references "
                f"unauthorized candidate '{execution.candidate_id}'."
            )
        if candidate.requires_human_manifest_approval:
            raise ValueError(
                f"Comparative Reconciliation Blocked: candidate '{candidate.candidate_id}' still requires human manifest approval."
            )
        if candidate.target_query_id != observation.query_id or execution.target_query_id != observation.query_id:
            raise ValueError(
                f"Comparative Reconciliation Blocked: execution '{execution.execution_id}' target query is not "
                f"the current observation query '{observation.query_id}'."
            )
        if execution.target_query_id != candidate.target_query_id:
            raise ValueError(
                f"Comparative Reconciliation Blocked: execution '{execution.execution_id}' target query does not "
                "match its authorized candidate."
            )
        if cls._normalize_url(execution.cited_url) != cls._normalize_url(candidate.cited_url):
            raise ValueError(
                f"Comparative Reconciliation Blocked: execution '{execution.execution_id}' URL does not match "
                "its authorized candidate."
            )

        target_query = next((item for item in query_map.queries if item.query_id == execution.target_query_id), None)
        if not target_query or target_query.approval_state != HumanApprovalState.APPROVED:
            raise ValueError(
                f"Comparative Reconciliation Blocked: execution '{execution.execution_id}' lacks an approved target query."
            )

        manifest_match = next(
            (
                item
                for item in manifest.candidates
                if item.query_id == execution.target_query_id
                and cls._normalize_url(item.url) == cls._normalize_url(execution.cited_url)
            ),
            None,
        )
        if not manifest_match:
            raise ValueError(
                f"Comparative Reconciliation Blocked: execution '{execution.execution_id}' URL/query is not "
                "authorized in the current manifest."
            )

    @staticmethod
    def _verify_retained_snapshot(
        evidence: EvidenceRecord,
        execution: CollectionExecutionRecord,
        snapshot_store: Optional[SnapshotStore],
    ) -> None:
        """Requires reloadable snapshot bytes before a human decision can promote a claim."""
        artifact = evidence.verification_artifact
        if not artifact or not evidence.snapshot_id:
            raise ValueError(
                f"Comparative Reconciliation Blocked: evidence '{evidence.evidence_id}' has no retained snapshot reference."
            )
        expected_snapshot_id = f"snap-{artifact.snapshot_sha256[:16]}"
        if evidence.snapshot_id != expected_snapshot_id:
            raise ValueError(
                f"Comparative Reconciliation Blocked: evidence '{evidence.evidence_id}' snapshot ID does not match its digest."
            )
        if not snapshot_store:
            raise ValueError("Comparative Reconciliation Blocked: no approved snapshot resolver was provided for human promotion.")
        try:
            retained_bytes = snapshot_store.load_snapshot(artifact.snapshot_sha256)
        except FileNotFoundError as exc:
            raise ValueError(
                f"Comparative Reconciliation Blocked: retained snapshot is unavailable for evidence '{evidence.evidence_id}'."
            ) from exc
        retained_sha256 = hashlib.sha256(retained_bytes).hexdigest()
        if retained_sha256.lower() != artifact.snapshot_sha256.lower():
            raise ValueError(
                f"Comparative Reconciliation Blocked: retained snapshot bytes do not match evidence '{evidence.evidence_id}' digest."
            )
        if execution.snapshot_sha256.lower() != retained_sha256.lower():
            raise ValueError(
                f"Comparative Reconciliation Blocked: execution '{execution.execution_id}' snapshot digest does not match retained bytes."
            )

    def evaluate_claim_support(
        self,
        statement_id: str,
        statement_text: str,
        evidence: Optional[EvidenceRecord],
        execution: Optional[CollectionExecutionRecord],
        expected_role: SourceRelationship,
        human_decision_record: Optional[HumanDecisionRecord] = None,
        snapshot_store: Optional[SnapshotStore] = None,
    ) -> ClaimExcerptAssessment:
        """
        Evaluates an answer-surface statement claim against a verified evidence record excerpt resolved from the source ledger.
        Zero keyword auto-support: Automated evaluation NEVER promotes statements to SUPPORTED based on word overlap.
        Defaults to CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW if OPENED_VERIFIED evidence excerpt exists,
        or NOT_ASSESSABLE if evidence is missing or unverified.
        Promotion to SUPPORTED, CONTRADICTED, or UNSUPPORTED requires a valid HumanDecisionRecord containing an explicit
        QuotedEvidencePassage matching evidence.evidence_id, evidence_url, snapshot_sha256, verifier_run_id,
        collection_execution_id, AND verbatim quoted_passage in evidence.opened_excerpt.
        """
        # Check if human decision record contains an adjudicated decision for this exact statement, evidence ID, execution, & snapshot
        if (
            human_decision_record
            and evidence
            and evidence.verification_status == VerificationStatus.OPENED_VERIFIED
            and evidence.verification_artifact
            and execution
        ):
            for dec in human_decision_record.decisions:
                if dec.statement_id == statement_id:
                    # Validate all 6 quote bindings: evidence_id, evidence_url, snapshot_sha256, verifier_run_id, collection_execution_id, quoted_passage
                    matching_quote = None
                    for qe in dec.quoted_evidence:
                        if (
                            qe.evidence_id == evidence.evidence_id
                            and qe.evidence_url == evidence.url
                            and qe.snapshot_sha256.lower() == evidence.verification_artifact.snapshot_sha256.lower()
                            and qe.verifier_run_id == evidence.verification_artifact.verifier_run_id
                            and qe.collection_execution_id == execution.execution_id
                            and qe.quoted_passage in (evidence.opened_excerpt or "")
                        ):
                            matching_quote = qe
                            break

                    if matching_quote:
                        if not self._trusted_execution_registry:
                            raise ValueError(
                                "Comparative Reconciliation Blocked: no configured trusted collector issuer is available for human promotion."
                            )
                        self._trusted_execution_registry.verify_issued(execution)
                        self._verify_retained_snapshot(evidence, execution, snapshot_store)
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

    def compare_evidence(
        self,
        observation: AnswerObservation,
        query_map: QueryMap,
        gap_record: ForensicGapAnalysisRecord,
        profile: SubjectProfile,
        client_evidence_id: str,
        competitor_evidence_id: str,
        raw_qm_bytes: bytes,
        raw_manifest_bytes: bytes,
        raw_ledger_bytes: bytes,
        raw_profile_bytes: bytes,
        human_decision_record: Optional[HumanDecisionRecord] = None,
        timestamp: Optional[datetime] = None,
        snapshot_store: Optional[SnapshotStore] = None,
    ) -> ComparativeEvidenceRecord:
        """
        Executes bounded comparative evidence reconciliation parsing AuditRun directly from raw_ledger_bytes.
        Enforces strict profile relationship classification, 7-binding human decision verification,
        execution integrity & field equality proof, 9-hash context binding, and canonical digest verification.
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

        # P0: All caller-supplied artifact models must match the authoritative raw
        # bytes. Relationship classification and candidate authorization below use
        # the parsed objects, never a potentially substituted in-memory model.
        try:
            parsed_profile = SubjectProfile.model_validate_json(raw_profile_bytes)
            parsed_query_map = QueryMap.model_validate_json(raw_qm_bytes)
            parsed_manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
        except Exception as exc:
            raise ValueError(f"Comparative Reconciliation Blocked: Canonical artifact parsing failed: {exc}") from exc

        supplied_artifacts = (
            ("SubjectProfile", profile, parsed_profile),
            ("QueryMap", query_map, parsed_query_map),
        )
        for artifact_name, supplied, parsed in supplied_artifacts:
            if supplied.model_dump(mode="json") != parsed.model_dump(mode="json"):
                raise ValueError(
                    f"Comparative Reconciliation Blocked: supplied {artifact_name} does not match its raw bytes."
                )

        profile = parsed_profile
        query_map = parsed_query_map
        manifest = parsed_manifest

        # Step 2: Validate gap_record binding to raw_ledger_bytes
        if gap_record.source_ledger_sha256.lower() != ledger_sha256.lower():
            raise ValueError(
                f"Comparative Reconciliation Blocked: Gap record source_ledger_sha256 ('{gap_record.source_ledger_sha256}') "
                f"does not match calculated raw ledger SHA-256 ('{ledger_sha256}')."
            )

        # Step 3: Parse AuditRun directly from raw_ledger_bytes (guaranteeing byte-level identity)
        try:
            source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
        except Exception as e:
            raise ValueError(f"Comparative Reconciliation Blocked: Failed to parse raw_ledger_bytes into AuditRun: {e}")

        if source_ledger.run_id != gap_record.source_ledger_run_id:
            raise ValueError(
                f"Comparative Reconciliation Blocked: Parsed raw ledger run ID ('{source_ledger.run_id}') "
                f"does not match gap record ledger run ID ('{gap_record.source_ledger_run_id}')."
            )

        # Step 4: Resolve Evidence Records directly from immutable Source Ledger
        if client_evidence_id not in source_ledger.evidence_ledger:
            raise ValueError(f"Comparative Reconciliation Blocked: Client evidence ID '{client_evidence_id}' not found in source ledger.")

        if competitor_evidence_id not in source_ledger.evidence_ledger:
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor evidence ID '{competitor_evidence_id}' not found in source ledger.")

        client_evidence = source_ledger.evidence_ledger[client_evidence_id]
        competitor_evidence = source_ledger.evidence_ledger[competitor_evidence_id]

        # Step 5: Total 7-binding context verification for HumanDecisionRecord
        if human_decision_record:
            if not human_decision_record.verify_integrity():
                raise ValueError(f"HumanDecisionRecord integrity verification failed for '{human_decision_record.decision_record_id}'.")
            
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

        # Step 6: Dynamically classify client domain ownership & mandatory verifier artifact proof
        client_dom = urlparse(client_evidence.url).hostname or client_evidence.url
        client_rel, _ = ForensicGapAnalyzer.classify_source_relationship(client_dom, profile, client_evidence.source_type)
        if client_rel != SourceRelationship.CLIENT_OWNED:
            raise ValueError(
                f"Comparative Reconciliation Blocked: Client evidence URL '{client_evidence.url}' "
                f"classified as '{client_rel.value}', expected '{SourceRelationship.CLIENT_OWNED.value}'."
            )

        if client_evidence.verification_status != VerificationStatus.OPENED_VERIFIED:
            raise ValueError(f"Comparative Reconciliation Blocked: Client evidence '{client_evidence.evidence_id}' status is '{client_evidence.verification_status.value}', expected 'opened_verified'.")

        if not client_evidence.verification_artifact:
            raise ValueError(f"Comparative Reconciliation Blocked: Client evidence '{client_evidence.evidence_id}' lacks verification artifact.")

        client_art = client_evidence.verification_artifact
        if not client_art.snapshot_sha256 or client_art.snapshot_sha256 == "unknown":
            raise ValueError(f"Comparative Reconciliation Blocked: Client evidence '{client_evidence.evidence_id}' snapshot SHA256 is missing or 'unknown'.")

        if not client_art.verifier_run_id or client_art.verifier_run_id == "vrun-unknown":
            raise ValueError(f"Comparative Reconciliation Blocked: Client evidence '{client_evidence.evidence_id}' verifier run ID is missing or 'vrun-unknown'.")

        # Require matching CollectionExecutionRecord with verified integrity and field equality
        client_exec = next((ce for ce in gap_record.collection_executions if ce.evidence_id == client_evidence.evidence_id), None)
        if not client_exec:
            raise ValueError(f"Comparative Reconciliation Blocked: Client evidence '{client_evidence.evidence_id}' has no matching CollectionExecutionRecord in gap record.")

        if not client_exec.verify_integrity():
            raise ValueError(f"Comparative Reconciliation Blocked: Client CollectionExecutionRecord '{client_exec.execution_id}' failed integrity verification.")

        if client_exec.cited_url != client_evidence.url:
            raise ValueError(f"Comparative Reconciliation Blocked: Client execution cited_url ('{client_exec.cited_url}') != evidence URL ('{client_evidence.url}').")

        if client_exec.verifier_run_id != client_art.verifier_run_id:
            raise ValueError(f"Comparative Reconciliation Blocked: Client execution verifier_run_id ('{client_exec.verifier_run_id}') != artifact verifier_run_id ('{client_art.verifier_run_id}').")

        if client_exec.snapshot_sha256.lower() != client_art.snapshot_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Client execution snapshot_sha256 ('{client_exec.snapshot_sha256}') != artifact snapshot_sha256 ('{client_art.snapshot_sha256}').")

        if client_exec.source_ledger_sha256.lower() != ledger_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Client execution source_ledger_sha256 ('{client_exec.source_ledger_sha256}') != raw ledger SHA-256 ('{ledger_sha256}').")

        if client_exec.observation_id != observation.observation_id:
            raise ValueError(f"Comparative Reconciliation Blocked: Client execution observation_id ('{client_exec.observation_id}') != observation ID ('{observation.observation_id}').")

        if client_exec.raw_answer_sha256.lower() != observation.raw_answer_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Client execution raw_answer_sha256 ('{client_exec.raw_answer_sha256}') != observation raw answer SHA-256 ('{observation.raw_answer_sha256}').")

        if client_exec.profile_id != profile.profile_id:
            raise ValueError(f"Comparative Reconciliation Blocked: Client execution profile_id ('{client_exec.profile_id}') != profile ID ('{profile.profile_id}').")

        if client_exec.profile_sha256.lower() != profile_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Client execution profile_sha256 ('{client_exec.profile_sha256}') != raw profile SHA-256 ('{profile_sha256}').")

        if client_exec.manifest_sha256.lower() != manifest_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Client execution manifest_sha256 ('{client_exec.manifest_sha256}') != raw manifest SHA-256 ('{manifest_sha256}').")

        if client_exec.query_map_sha256.lower() != qm_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Client execution query_map_sha256 ('{client_exec.query_map_sha256}') != raw query_map SHA-256 ('{qm_sha256}').")

        self._validate_execution_authority(client_exec, gap_record, observation, query_map, manifest)

        client_summary = ComparativeSourceSummary(
            domain=client_dom,
            url=client_evidence.url,
            evidence_id=client_evidence.evidence_id,
            verifier_run_id=client_art.verifier_run_id,
            execution_id=client_exec.execution_id,
            relationship=SourceRelationship.CLIENT_OWNED,
            entity_name=profile.client_profile.entity_name,
            is_verified=True,
            snapshot_sha256=client_art.snapshot_sha256,
            opened_excerpt=client_evidence.opened_excerpt,
        )

        # Step 7: Dynamically classify competitor domain ownership & mandatory verifier artifact proof
        comp_dom = urlparse(competitor_evidence.url).hostname or competitor_evidence.url
        comp_rel, comp_entity = ForensicGapAnalyzer.classify_source_relationship(comp_dom, profile, competitor_evidence.source_type)
        if comp_rel != SourceRelationship.COMPETITOR_OWNED:
            raise ValueError(
                f"Comparative Reconciliation Blocked: Competitor evidence URL '{competitor_evidence.url}' "
                f"classified as '{comp_rel.value}', expected '{SourceRelationship.COMPETITOR_OWNED.value}'."
            )

        if competitor_evidence.verification_status != VerificationStatus.OPENED_VERIFIED:
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor evidence '{competitor_evidence.evidence_id}' status is '{competitor_evidence.verification_status.value}', expected 'opened_verified'.")

        if not competitor_evidence.verification_artifact:
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor evidence '{competitor_evidence.evidence_id}' lacks verification artifact.")

        comp_art = competitor_evidence.verification_artifact
        if not comp_art.snapshot_sha256 or comp_art.snapshot_sha256 == "unknown":
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor evidence '{competitor_evidence.evidence_id}' snapshot SHA256 is missing or 'unknown'.")

        if not comp_art.verifier_run_id or comp_art.verifier_run_id == "vrun-unknown":
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor evidence '{competitor_evidence.evidence_id}' verifier run ID is missing or 'vrun-unknown'.")

        comp_exec = next((ce for ce in gap_record.collection_executions if ce.evidence_id == competitor_evidence.evidence_id), None)
        if not comp_exec:
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor evidence '{competitor_evidence.evidence_id}' has no matching CollectionExecutionRecord in gap record.")

        if not comp_exec.verify_integrity():
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor CollectionExecutionRecord '{comp_exec.execution_id}' failed integrity verification.")

        if comp_exec.cited_url != competitor_evidence.url:
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor execution cited_url ('{comp_exec.cited_url}') != evidence URL ('{competitor_evidence.url}').")

        if comp_exec.verifier_run_id != comp_art.verifier_run_id:
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor execution verifier_run_id ('{comp_exec.verifier_run_id}') != artifact verifier_run_id ('{comp_art.verifier_run_id}').")

        if comp_exec.snapshot_sha256.lower() != comp_art.snapshot_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor execution snapshot_sha256 ('{comp_exec.snapshot_sha256}') != artifact snapshot_sha256 ('{comp_art.snapshot_sha256}').")

        if comp_exec.source_ledger_sha256.lower() != ledger_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor execution source_ledger_sha256 ('{comp_exec.source_ledger_sha256}') != raw ledger SHA-256 ('{ledger_sha256}').")

        if comp_exec.observation_id != observation.observation_id:
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor execution observation_id ('{comp_exec.observation_id}') != observation ID ('{observation.observation_id}').")

        if comp_exec.raw_answer_sha256.lower() != observation.raw_answer_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor execution raw_answer_sha256 ('{comp_exec.raw_answer_sha256}') != observation raw answer SHA-256 ('{observation.raw_answer_sha256}').")

        if comp_exec.profile_id != profile.profile_id:
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor execution profile_id ('{comp_exec.profile_id}') != profile ID ('{profile.profile_id}').")

        if comp_exec.profile_sha256.lower() != profile_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor execution profile_sha256 ('{comp_exec.profile_sha256}') != raw profile SHA-256 ('{profile_sha256}').")

        if comp_exec.manifest_sha256.lower() != manifest_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor execution manifest_sha256 ('{comp_exec.manifest_sha256}') != raw manifest SHA-256 ('{manifest_sha256}').")

        if comp_exec.query_map_sha256.lower() != qm_sha256.lower():
            raise ValueError(f"Comparative Reconciliation Blocked: Competitor execution query_map_sha256 ('{comp_exec.query_map_sha256}') != raw query_map SHA-256 ('{qm_sha256}').")

        self._validate_execution_authority(comp_exec, gap_record, observation, query_map, manifest)

        competitor_summary = ComparativeSourceSummary(
            domain=comp_dom,
            url=competitor_evidence.url,
            evidence_id=competitor_evidence.evidence_id,
            verifier_run_id=comp_art.verifier_run_id,
            execution_id=comp_exec.execution_id,
            relationship=SourceRelationship.COMPETITOR_OWNED,
            entity_name=comp_entity or "Competitor Entity",
            is_verified=True,
            snapshot_sha256=comp_art.snapshot_sha256,
            opened_excerpt=competitor_evidence.opened_excerpt,
        )

        # Step 8: Source-to-claim semantic assessments (role-aware & evidence-bound with full execution proof)
        client_assessments: List[ClaimExcerptAssessment] = []
        competitor_assessments: List[ClaimExcerptAssessment] = []

        for stmt in observation.extracted_statements:
            client_assessments.append(
                self.evaluate_claim_support(
                    statement_id=stmt.statement_id,
                    statement_text=stmt.text,
                    evidence=client_evidence,
                    execution=client_exec,
                    expected_role=SourceRelationship.CLIENT_OWNED,
                    human_decision_record=human_decision_record,
                    snapshot_store=snapshot_store,
                )
            )
            competitor_assessments.append(
                self.evaluate_claim_support(
                    statement_id=stmt.statement_id,
                    statement_text=stmt.text,
                    evidence=competitor_evidence,
                    execution=comp_exec,
                    expected_role=SourceRelationship.COMPETITOR_OWNED,
                    human_decision_record=human_decision_record,
                    snapshot_store=snapshot_store,
                )
            )

        # Step 9: Derive factual evidence gap from comparative claim assessments
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

        # Step 10: Compute 9-hash canonical digest over ALL fields and finding basis
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
