"""Trusted issuer-bound authenticity registry for collector-created executions."""

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..domain.candidate_collection import CollectionExecutionRecord


class CollectorExecutionRegistry:
    """Issues append-only execution attestations for one configured, trusted issuer."""

    def __init__(self, signing_key: bytes, issuer_id: str, base_dir: Optional[Path] = None) -> None:
        if len(signing_key) < 32:
            raise ValueError("CollectorExecutionRegistry signing key must contain at least 32 bytes.")
        if not issuer_id.strip():
            raise ValueError("CollectorExecutionRegistry issuer_id must be non-empty.")
        self._signing_key = signing_key
        self.issuer_id = issuer_id
        self._base_dir = base_dir
        self._records: Dict[str, Tuple[CollectionExecutionRecord, str]] = {}
        if self._base_dir:
            self._base_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def ephemeral(cls) -> "CollectorExecutionRegistry":
        """Creates a process-local issuer for non-promoting controlled offline runs."""
        signing_key = os.urandom(32)
        issuer_id = f"ephemeral-{hashlib.sha256(signing_key).hexdigest()[:16]}"
        return cls(signing_key=signing_key, issuer_id=issuer_id)

    @classmethod
    def from_runtime_environment(cls) -> Optional["CollectorExecutionRegistry"]:
        """Loads the platform-trusted issuer only from protected runtime configuration.

        Promotion callers never provide this registry. Absence is valid for collection and
        non-promoting analysis, but causes a human promotion to fail closed.
        """
        issuer_id = os.environ.get("GEO_AEO_TRUSTED_ISSUER_ID")
        signing_key_hex = os.environ.get("GEO_AEO_TRUSTED_ISSUER_KEY_HEX")
        if not issuer_id and not signing_key_hex:
            return None
        if not issuer_id or not signing_key_hex:
            raise ValueError("Trusted issuer runtime configuration is incomplete.")
        try:
            signing_key = bytes.fromhex(signing_key_hex)
        except ValueError as exc:
            raise ValueError("Trusted issuer signing key must be hex encoded.") from exc
        directory = os.environ.get("GEO_AEO_EXECUTION_REGISTRY_DIR")
        return cls(signing_key=signing_key, issuer_id=issuer_id, base_dir=Path(directory) if directory else None)

    def _signature(self, execution: CollectionExecutionRecord) -> str:
        message = f"{self.issuer_id}:{execution.canonical_digest.lower()}".encode("utf-8")
        return hmac.new(self._signing_key, message, hashlib.sha256).hexdigest()

    def _record_path(self, execution_id: str) -> Path:
        if not self._base_dir:
            raise ValueError("CollectorExecutionRegistry has no durable storage directory.")
        safe_id = hashlib.sha256(execution_id.encode("utf-8")).hexdigest()
        return self._base_dir / f"{safe_id}.json"

    def _issued_execution(self, execution: CollectionExecutionRecord) -> CollectionExecutionRecord:
        digest = CollectionExecutionRecord.compute_canonical_digest(
            execution_id=execution.execution_id,
            candidate_id=execution.candidate_id,
            target_query_id=execution.target_query_id,
            cited_url=execution.cited_url,
            observation_id=execution.observation_id,
            raw_answer_sha256=execution.raw_answer_sha256,
            profile_id=execution.profile_id,
            profile_sha256=execution.profile_sha256,
            manifest_sha256=execution.manifest_sha256,
            query_map_sha256=execution.query_map_sha256,
            source_ledger_sha256=execution.source_ledger_sha256,
            evidence_id=execution.evidence_id,
            verifier_run_id=execution.verifier_run_id,
            snapshot_sha256=execution.snapshot_sha256,
            execution_timestamp=execution.execution_timestamp,
            issuer_id=self.issuer_id,
        )
        unsigned = execution.model_copy(
            update={"issuer_id": self.issuer_id, "issuer_attestation": None, "canonical_digest": digest}
        )
        return unsigned.model_copy(update={"issuer_attestation": self._signature(unsigned)})

    def issue(self, execution: CollectionExecutionRecord) -> CollectionExecutionRecord:
        """Issues an immutable attested execution under this registry's configured issuer identity."""
        if not execution.verify_integrity():
            raise ValueError(f"Cannot issue authenticity proof for invalid execution '{execution.execution_id}'.")
        issued = self._issued_execution(execution)
        existing = self.resolve(issued.execution_id, allow_missing=True)
        if existing:
            stored_execution, _signature = existing
            if stored_execution.model_dump(mode="json") != issued.model_dump(mode="json"):
                raise ValueError(f"Execution registry is append-only: '{issued.execution_id}' already has different bytes.")
            return stored_execution

        assert issued.issuer_attestation is not None
        self._records[issued.execution_id] = (issued, issued.issuer_attestation)
        if self._base_dir:
            payload = {"execution": issued.model_dump(mode="json"), "signature": issued.issuer_attestation}
            destination = self._record_path(issued.execution_id)
            temporary = destination.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            os.replace(temporary, destination)
        return issued

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
        """Proves the exact execution was attested by this configured issuer—not a caller registry."""
        if execution.issuer_id != self.issuer_id:
            raise ValueError(
                f"Collector execution '{execution.execution_id}' issuer '{execution.issuer_id}' is not trusted."
            )
        if not execution.issuer_attestation:
            raise ValueError(f"Collector execution '{execution.execution_id}' has no issuer attestation.")
        stored = self.resolve(execution.execution_id)
        assert stored is not None
        stored_execution, recorded_signature = stored
        if stored_execution.model_dump(mode="json") != execution.model_dump(mode="json"):
            raise ValueError(f"Collector execution '{execution.execution_id}' bytes do not match its issued registry record.")
        expected_signature = self._signature(stored_execution)
        if not hmac.compare_digest(recorded_signature, expected_signature):
            raise ValueError(f"Collector execution '{execution.execution_id}' registry attestation is invalid.")
        if not hmac.compare_digest(execution.issuer_attestation, expected_signature):
            raise ValueError(f"Collector execution '{execution.execution_id}' issuer attestation is invalid.")
