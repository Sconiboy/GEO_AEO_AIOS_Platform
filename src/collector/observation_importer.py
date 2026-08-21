"""
Answer-Surface Observation Importer and Pipeline Validator
Enforces query approval binding, raw text SHA-256 integrity, source-ledger linkage,
and unverified statement defaults.
"""

import hashlib
from typing import Dict

from ..domain.enums import HumanApprovalState
from ..domain.models import AuditRun
from ..domain.observation import AnswerObservation, ExtractionStatus
from ..domain.query_map import QueryMap, TargetQuery


class ObservationImporter:
    """
    Imports and validates manual answer-surface observations against approved QueryMaps and Source Ledgers.
    Refuses any observation for an unapproved query, invalid hash, or unlinked ledger.
    """

    @classmethod
    def import_observation(
        cls,
        observation: AnswerObservation,
        query_map: QueryMap,
        source_ledger: AuditRun,
    ) -> AnswerObservation:
        """
        Validates observation pipeline integrity:
        1. Binds query_id to an APPROVED TargetQuery in QueryMap.
        2. Validates query_map_id and source_ledger_run_id linkage.
        3. Re-verifies SHA-256 digest of raw_answer_text.
        4. Guarantees extracted statements start as PROPOSED_UNVERIFIED unless linked.
        """
        # Gate 1: Check Query Map ID
        if observation.query_map_id != query_map.query_map_id:
            raise ValueError(
                f"Mismatch: Observation query_map_id ('{observation.query_map_id}') does not match QueryMap ID ('{query_map.query_map_id}')."
            )

        # Gate 2: Check Source Ledger Run ID
        if observation.source_ledger_run_id != source_ledger.run_id:
            raise ValueError(
                f"Mismatch: Observation source_ledger_run_id ('{observation.source_ledger_run_id}') does not match Source Ledger Run ID ('{source_ledger.run_id}')."
            )

        # Gate 3: Check TargetQuery exists and is APPROVED
        approved_queries: Dict[str, TargetQuery] = {
            q.query_id: q
            for q in query_map.queries
            if q.approval_state == HumanApprovalState.APPROVED
        }

        if observation.query_id not in approved_queries:
            raise ValueError(
                f"Cannot import observation for query '{observation.query_id}': Query is unapproved or missing from QueryMap."
            )

        # Gate 4: Verify SHA-256 Hash Integrity
        calculated_hash = hashlib.sha256(observation.raw_answer_text.encode("utf-8")).hexdigest()
        if observation.raw_answer_sha256.lower() != calculated_hash.lower():
            raise ValueError(
                f"Integrity failure: raw_answer_sha256 ('{observation.raw_answer_sha256}') does not match calculated digest ('{calculated_hash}')."
            )

        # Gate 5: Validate Extracted Statements
        for stmt in observation.extracted_statements:
            if stmt.linked_evidence_id:
                if stmt.linked_evidence_id not in source_ledger.evidence_ledger:
                    raise ValueError(
                        f"Statement '{stmt.statement_id}' references linked_evidence_id '{stmt.linked_evidence_id}' which does not exist in Source Ledger."
                    )
            else:
                # Unlinked statements MUST remain PROPOSED_UNVERIFIED
                if stmt.extraction_status != ExtractionStatus.PROPOSED_UNVERIFIED:
                    stmt.extraction_status = ExtractionStatus.PROPOSED_UNVERIFIED

        return observation
