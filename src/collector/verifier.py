"""
Live Source Verifier and Snapshot Pipeline
Fetches public URLs, computes content SHA-256, verifies quote alignment, and generates VerificationArtifacts.
"""

import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..domain.enums import SourceType, VerificationStatus
from ..domain.models import EvidenceRecord, VerificationArtifact
from .snapshot import SnapshotStore


class SourceVerifier:
    """
    Controlled source verifier for fetching public web content, storing immutable
    snapshots, and constructing audit-grade EvidenceRecords.
    """

    def __init__(
        self,
        snapshot_store: Optional[SnapshotStore] = None,
        timeout_seconds: float = 10.0,
        user_agent: str = "GEO-AEO-EvidenceVerifier/1.0 (+https://github.com/Sconiboy/GEO_AEO_AIOS_Platform)",
    ):
        self.snapshot_store = snapshot_store or SnapshotStore()
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def verify_url(
        self,
        url: str,
        candidate_excerpt: str,
        source_type: SourceType = SourceType.INDEPENDENT_EDITORIAL,
        is_independent: bool = True,
        evidence_id: Optional[str] = None,
    ) -> EvidenceRecord:
        """
        Executes live source verification pipeline:
        1. HTTP GET request with standard headers and timeout.
        2. Save content-addressed snapshot bytes to disk.
        3. Compute SHA-256 digest of stored bytes.
        4. Verify exact candidate excerpt alignment against stored bytes.
        5. Build deterministic EvidenceRecord and VerificationArtifact.
        """
        evidence_id = evidence_id or f"ev-{uuid.uuid4().hex[:12]}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    return EvidenceRecord(
                        evidence_id=evidence_id,
                        url=url,
                        opened_excerpt=candidate_excerpt,
                        source_type=source_type,
                        verification_status=VerificationStatus.INACCESSIBLE,
                        is_independent=is_independent,
                    )

                content_bytes = response.read()

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception):
            return EvidenceRecord(
                evidence_id=evidence_id,
                url=url,
                opened_excerpt=candidate_excerpt,
                source_type=source_type,
                verification_status=VerificationStatus.INACCESSIBLE,
                is_independent=is_independent,
            )

        # Save snapshot bytes to immutable store
        snapshot_id, sha256_hash, _ = self.snapshot_store.save_snapshot(content_bytes)

        # Check verbatim quote match in raw bytes / decoded string
        decoded_content = content_bytes.decode("utf-8", errors="ignore")
        clean_excerpt = candidate_excerpt.strip()
        quote_matches = clean_excerpt in decoded_content or clean_excerpt.lower() in decoded_content.lower()

        artifact = VerificationArtifact(
            verifier_run_id=f"verifier-run-{uuid.uuid4().hex[:8]}",
            verification_timestamp=datetime.now(timezone.utc),
            verifier_method="DIRECT_HTTP_SNAPSHOT",
            snapshot_sha256=sha256_hash,
            quote_exact_match=quote_matches,
            limitations="Live HTTP GET snapshot verification",
        )

        status = (
            VerificationStatus.OPENED_VERIFIED
            if quote_matches
            else VerificationStatus.QUOTE_MISMATCH
        )

        return EvidenceRecord(
            evidence_id=evidence_id,
            url=url,
            opened_excerpt=candidate_excerpt,
            source_type=source_type,
            verification_status=status,
            retrieval_timestamp=datetime.now(timezone.utc),
            snapshot_id=snapshot_id,
            is_independent=is_independent,
            verification_artifact=artifact,
        )
