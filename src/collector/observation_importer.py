"""
Answer-Surface Observation Importer and Pipeline Validator (Sprint 4.1 Remediation)
Enforces immutable hash integrity, artifact digest bindings, query approval binding,
and evidence-verified statement linkage.
"""

import hashlib
import json
from typing import Any, Dict, Optional

from ..domain.enums import HumanApprovalState, VerificationStatus
from ..domain.models import AuditRun
from ..domain.observation import AnswerObservation, ExtractionStatus, ExtractedStatement
from ..domain.query_map import QueryMap, TargetQuery
from .query_map_runner import DatasetManifest


class ObservationImporter:
    """
    Imports and validates manual answer-surface observations against approved QueryMaps,
    DatasetManifests, and frozen Source Ledger artifacts.
    """

    @classmethod
    def compute_artifact_hash(cls, model_data: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 digest of serialized model JSON dict."""
        serialized = json.dumps(model_data, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def import_observation(
        cls,
        observation: AnswerObservation,
        query_map: QueryMap,
        manifest: DatasetManifest,
        source_ledger: AuditRun,
        raw_qm_bytes: Optional[bytes] = None,
        raw_manifest_bytes: Optional[bytes] = None,
        raw_ledger_bytes: Optional[bytes] = None,
    ) -> AnswerObservation:
        """
        Validates observation pipeline integrity:
        1. Re-verifies raw_answer_text SHA-256 integrity (must pass verify_integrity()).
        2. Validates QueryMap SHA-256 hash binding.
        3. Validates DatasetManifest SHA-256 hash binding.
        4. Validates Source Ledger SHA-256 hash binding.
        5. Validates query_id is in QueryMap and is APPROVED.
        6. Forces extracted statements to PROPOSED_UNVERIFIED unless linked to OPENED_VERIFIED evidence.
        """
        # Gate 1: Re-verify raw answer hash integrity
        if not observation.verify_integrity():
            raise ValueError(
                f"Integrity failure: raw_answer_sha256 ('{observation.raw_answer_sha256}') does not match calculated digest of raw_answer_text."
            )

        # Gate 2: Compute/validate artifact SHA-256 hashes
        qm_hash = (
            hashlib.sha256(raw_qm_bytes).hexdigest()
            if raw_qm_bytes
            else cls.compute_artifact_hash(query_map.model_dump(mode="json"))
        )
        manifest_hash = (
            hashlib.sha256(raw_manifest_bytes).hexdigest()
            if raw_manifest_bytes
            else cls.compute_artifact_hash(manifest.model_dump(mode="json"))
        )
        ledger_hash = (
            hashlib.sha256(raw_ledger_bytes).hexdigest()
            if raw_ledger_bytes
            else cls.compute_artifact_hash(source_ledger.model_dump(mode="json"))
        )

        if observation.query_map_sha256.lower() != qm_hash.lower():
            raise ValueError(
                f"Artifact mismatch: Observation query_map_sha256 ('{observation.query_map_sha256}') does not match bound QueryMap digest ('{qm_hash}')."
            )

        if observation.manifest_sha256.lower() != manifest_hash.lower():
            raise ValueError(
                f"Artifact mismatch: Observation manifest_sha256 ('{observation.manifest_sha256}') does not match bound DatasetManifest digest ('{manifest_hash}')."
            )

        if observation.source_ledger_sha256.lower() != ledger_hash.lower():
            raise ValueError(
                f"Artifact mismatch: Observation source_ledger_sha256 ('{observation.source_ledger_sha256}') does not match bound Source Ledger digest ('{ledger_hash}')."
            )

        # Gate 3: Check ID linkage
        if observation.query_map_id != query_map.query_map_id:
            raise ValueError(
                f"ID mismatch: Observation query_map_id ('{observation.query_map_id}') does not match QueryMap ID ('{query_map.query_map_id}')."
            )

        if observation.source_ledger_run_id != source_ledger.run_id:
            raise ValueError(
                f"ID mismatch: Observation source_ledger_run_id ('{observation.source_ledger_run_id}') does not match Source Ledger Run ID ('{source_ledger.run_id}')."
            )

        # Gate 4: Check TargetQuery is APPROVED
        approved_queries: Dict[str, TargetQuery] = {
            q.query_id: q
            for q in query_map.queries
            if q.approval_state == HumanApprovalState.APPROVED
        }

        if observation.query_id not in approved_queries:
            raise ValueError(
                f"Cannot import observation for query '{observation.query_id}': Query is unapproved or missing from QueryMap."
            )

        # Gate 5: Validate Extracted Statements (FORCE PROPOSED_UNVERIFIED for ALL imported statements)
        validated_statements = []
        for stmt in observation.extracted_statements:
            linked_ev_id = None
            if stmt.linked_evidence_id:
                if stmt.linked_evidence_id not in source_ledger.evidence_ledger:
                    raise ValueError(
                        f"Statement '{stmt.statement_id}' references linked_evidence_id '{stmt.linked_evidence_id}' which does not exist in Source Ledger."
                    )
                ev = source_ledger.evidence_ledger[stmt.linked_evidence_id]
                if ev.verification_status != VerificationStatus.OPENED_VERIFIED:
                    raise ValueError(
                        f"Statement '{stmt.statement_id}' references evidence '{stmt.linked_evidence_id}' which is status '{ev.verification_status.value}', not OPENED_VERIFIED."
                    )
                linked_ev_id = stmt.linked_evidence_id

            # STRICT RULE: Force ALL imported statements to PROPOSED_UNVERIFIED
            validated_statements.append(
                ExtractedStatement(
                    statement_id=stmt.statement_id,
                    text=stmt.text,
                    extraction_status=ExtractionStatus.PROPOSED_UNVERIFIED,
                    linked_evidence_id=linked_ev_id,
                    human_notes=stmt.human_notes,
                )
            )

        # Return new validated observation instance with enforced statement statuses
        return AnswerObservation(
            observation_id=observation.observation_id,
            query_id=observation.query_id,
            query_map_id=observation.query_map_id,
            source_ledger_run_id=observation.source_ledger_run_id,
            query_map_sha256=observation.query_map_sha256,
            manifest_sha256=observation.manifest_sha256,
            source_ledger_sha256=observation.source_ledger_sha256,
            provider_name=observation.provider_name,
            model_identifier=observation.model_identifier,
            capture_timestamp=observation.capture_timestamp,
            capture_method=observation.capture_method,
            raw_answer_text=observation.raw_answer_text,
            raw_answer_sha256=observation.raw_answer_sha256,
            extracted_statements=validated_statements,
            operator_notes=observation.operator_notes,
            locale=observation.locale,
            region=observation.region,
        )
