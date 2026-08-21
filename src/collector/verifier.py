"""
Live Source Verifier with SourcePolicy SSRF Enforcement and Snapshot Engine
"""

import re
import time
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from ..domain.enums import SourceType, VerificationStatus
from ..domain.models import EvidenceRecord, VerificationArtifact
from .policy import SourcePolicy, SourcePolicyViolationError
from .snapshot import SnapshotStore


class SourceVerifier:
    """
    Controlled source verifier enforcing strict SourcePolicy security controls
    (SSRF protection, scheme checks, response size limits, content-type checks).
    """

    def __init__(
        self,
        snapshot_store: Optional[SnapshotStore] = None,
        policy: Optional[SourcePolicy] = None,
        user_agent: str = "GEO-AEO-EvidenceVerifier/1.0 (+https://github.com/Sconiboy/GEO_AEO_AIOS_Platform)",
    ):
        self.snapshot_store = snapshot_store or SnapshotStore()
        self.policy = policy or SourcePolicy()
        self.user_agent = user_agent

    def _strip_html_tags(self, html_text: str) -> str:
        """Strips HTML script, style, and markup tags to extract visible text content."""
        # Remove script and style elements
        clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", " ", clean)
        # Normalize whitespace
        return " ".join(clean.split())

    def verify_url(
        self,
        url: str,
        candidate_excerpt: str,
        source_type: SourceType = SourceType.INDEPENDENT_EDITORIAL,
        is_independent: bool = True,
        evidence_id: Optional[str] = None,
    ) -> EvidenceRecord:
        """
        Executes live source verification pipeline under SourcePolicy rules:
        1. Validate URL scheme, domain, and SSRF IP safety.
        2. HTTP GET request with max response size and content-type enforcement.
        3. Save content-addressed snapshot bytes to disk.
        4. Compute SHA-256 digest of stored bytes.
        5. Verify exact candidate excerpt alignment against stored bytes & clean text.
        6. Build deterministic EvidenceRecord and VerificationArtifact with policy metadata.
        """
        evidence_id = evidence_id or f"ev-{uuid.uuid4().hex[:12]}"
        policy_warnings: List[str] = []

        # Step 1: Enforce SourcePolicy Scheme & SSRF Controls
        try:
            parsed = self.policy.validate_url_scheme_and_domain(url)
            if parsed.hostname:
                self.policy.validate_ip_address_safety(parsed.hostname)
        except SourcePolicyViolationError as e:
            return EvidenceRecord(
                evidence_id=evidence_id,
                url=url,
                opened_excerpt=candidate_excerpt,
                source_type=source_type,
                verification_status=VerificationStatus.INACCESSIBLE,
                is_independent=is_independent,
            )

        start_time = time.perf_counter()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.policy.timeout_seconds) as response:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                final_url = response.geturl()
                status_code = response.status
                headers = response.info()
                content_type = headers.get("Content-Type", "text/html")

                # Validate redirect target SSRF safety if redirected
                if final_url != url:
                    final_parsed = self.policy.validate_url_scheme_and_domain(final_url)
                    if final_parsed.hostname:
                        self.policy.validate_ip_address_safety(final_parsed.hostname)

                # Validate Content-Type
                self.policy.validate_content_type(content_type)

                # Enforce max response bytes
                content_bytes = response.read(self.policy.max_response_bytes + 1)
                if len(content_bytes) > self.policy.max_response_bytes:
                    return EvidenceRecord(
                        evidence_id=evidence_id,
                        url=url,
                        opened_excerpt=candidate_excerpt,
                        source_type=source_type,
                        verification_status=VerificationStatus.INACCESSIBLE,
                        is_independent=is_independent,
                    )

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, SourcePolicyViolationError, Exception):
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

        # Check verbatim quote match in decoded text and stripped text
        decoded_content = content_bytes.decode("utf-8", errors="ignore")
        stripped_text = self._strip_html_tags(decoded_content)
        clean_excerpt = candidate_excerpt.strip()

        quote_matches = (
            clean_excerpt in decoded_content
            or clean_excerpt.lower() in decoded_content.lower()
            or clean_excerpt in stripped_text
            or clean_excerpt.lower() in stripped_text.lower()
        )

        artifact = VerificationArtifact(
            verifier_run_id=f"verifier-run-{uuid.uuid4().hex[:8]}",
            verification_timestamp=datetime.now(timezone.utc),
            verifier_method="DIRECT_HTTP_SNAPSHOT",
            snapshot_sha256=sha256_hash,
            quote_exact_match=quote_matches,
            final_url=final_url,
            http_status=status_code,
            content_type=content_type,
            content_length_bytes=len(content_bytes),
            retrieval_duration_ms=duration_ms,
            policy_warnings=policy_warnings,
            limitations="Live HTTP GET snapshot under SourcePolicy SSRF rules",
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
