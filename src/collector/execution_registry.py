"""Collector-controlled, append-only authenticity registry for collection executions."""

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..domain.candidate_collection import CollectionExecutionRecord


class CollectorExecutionRegistry:
    """Issues and resolves HMAC attestations for executions created by CandidateCollector."""

    def __init__(self, signing_key: bytes, base_dir: Optional[Path] = None) -> None:
        if len(signing_key) < 32:
            raise ValueError("CollectorExecutionRegistry signing key must contain at least 32 bytes.")
        self._signing_key = signing_key
        self._base_dir = base_dir
        self._records: Dict[str, Tuple[CollectionExecutionRecord, str]] = {}
        if self._base_dir:
            self._base_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def ephemeral(cls) -> "CollectorExecutionRegistry":
        """Creates a process-local registry for controlled offline collection runs."""
        return cls(signing_key=os.urandom(32))

    def _signature(self, execution: CollectionExecutionRecord) -> str:
        return hmac.new(
            self._signing_key,
            execution.canonical_digest.lower().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _record_path(self, execution_id: str) -> Path:
        if not self._base_dir:
            raise ValueError("CollectorExecutionRegistry has no durable storage directory.")
        safe_id = hashlib.sha256(execution_id.encode("utf-8")).hexdigest()
        return self._base_dir / f"{safe_id}.json"

    def issue(self, execution: CollectionExecutionRecord) -> str:
        """Records a collector-created execution once and returns its secret-key attestation."""
        if not execution.verify_integrity():
            raise ValueError(f"Cannot issue authenticity proof for invalid execution '{execution.execution_id}'.")
        existing = self.resolve(execution.execution_id, allow_missing=True)
        if existing:
            stored_execution, _signature = existing
            if stored_execution.model_dump(mode="json") != execution.model_dump(mode="json"):
                raise ValueError(f"Execution registry is append-only: '{execution.execution_id}' already has different bytes.")
            return _signature

        signature = self._signature(execution)
        self._records[execution.execution_id] = (execution, signature)
        if self._base_dir:
            payload = {"execution": execution.model_dump(mode="json"), "signature": signature}
            destination = self._record_path(execution.execution_id)
            temporary = destination.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            os.replace(temporary, destination)
        return signature

    def resolve(
        self,
        execution_id: str,
        allow_missing: bool = False,
    ) -> Optional[Tuple[CollectionExecutionRecord, str]]:
        """Loads a previously issued execution without trusting caller-supplied bytes."""
        if execution_id in self._records:
            return self._records[execution_id]
        if self._base_dir:
            path = self._record_path(execution_id)
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                execution = CollectionExecutionRecord.model_validate(payload["execution"])
                signature = str(payload["signature"])
                if execution.execution_id != execution_id:
                    raise ValueError("Execution registry record ID does not match its requested ID.")
                self._records[execution_id] = (execution, signature)
                return self._records[execution_id]
        if allow_missing:
            return None
        raise ValueError(f"Collector execution '{execution_id}' is not registered.")

    def verify_issued(self, execution: CollectionExecutionRecord) -> None:
        """Proves this exact execution was issued by the collector rather than rehashed by a caller."""
        stored = self.resolve(execution.execution_id)
        assert stored is not None
        stored_execution, recorded_signature = stored
        if stored_execution.model_dump(mode="json") != execution.model_dump(mode="json"):
            raise ValueError(f"Collector execution '{execution.execution_id}' bytes do not match its issued registry record.")
        expected_signature = self._signature(stored_execution)
        if not hmac.compare_digest(recorded_signature, expected_signature):
            raise ValueError(f"Collector execution '{execution.execution_id}' authenticity proof is invalid.")
