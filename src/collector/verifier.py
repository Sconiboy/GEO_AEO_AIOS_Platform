"""
Live Source Verifier with Manual Pre-Hop Redirect Validation, Anti-SSRF Protection, and Visible Text Extraction
"""

import re
import time
import uuid
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple
from bs4 import BeautifulSoup

from ..domain.enums import FailureCategory, SourceType, VerificationStatus
from ..domain.models import EvidenceRecord, VerificationArtifact
from .policy import SourcePolicy, SourcePolicyViolationError, UnsafeSourceAddressError
from .snapshot import SnapshotStore


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom urllib HTTPRedirectHandler that prevents automatic HTTP redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore
        return None  # Disable automatic redirect following


class SourceVerifier:
    """
    Controlled source verifier enforcing strict pre-hop redirect validation,
    SSRF protection, content-type constraints, and BeautifulSoup visible-text quote matching.
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

        # Build custom opener that disables automatic redirects
        self.opener = urllib.request.build_opener(NoRedirectHandler())

    def _extract_visible_text_html(self, raw_html: str) -> str:
        """
        Parses HTML and extracts visible text content only.
        Strips script, style, noscript, and iframe tags to prevent script-only quote matches.
        """
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())

    def verify_url(
        self,
        url: str,
        candidate_excerpt: str,
        source_type: SourceType = SourceType.INDEPENDENT_EDITORIAL,
        is_independent: bool = True,
        evidence_id: Optional[str] = None,
    ) -> EvidenceRecord:
        """
        Executes live source verification under strict pre-hop validation rules:
        1. Manual redirect loop up to policy.max_redirects.
        2. Pre-hop validation of scheme, host, and resolved IP safety (SSRF check) BEFORE fetching.
        3. Response payload size ceiling and Content-Type whitelist enforcement.
        4. Save immutable content-addressed snapshot bytes.
        5. Verify quote match ONLY against parsed visible text (for HTML).
        6. Return fully structured EvidenceRecord with FailureCategory if failed.
        """
        evidence_id = evidence_id or f"ev-{uuid.uuid4().hex[:12]}"
        policy_warnings: List[str] = []
        current_url = url
        redirect_count = 0
        final_response = None
        content_bytes = b""
        duration_ms = 0.0

        start_time = time.perf_counter()

        # Step 1: Manual Redirect Processing with Pre-Hop Policy & SSRF Checks
        while True:
            # Pre-hop validation
            try:
                parsed = self.policy.validate_url_scheme_and_domain(current_url)
                if parsed.hostname:
                    self.policy.validate_ip_address_safety(parsed.hostname)
            except UnsafeSourceAddressError as e:
                return EvidenceRecord(
                    evidence_id=evidence_id,
                    url=url,
                    opened_excerpt=candidate_excerpt,
                    source_type=source_type,
                    verification_status=VerificationStatus.INACCESSIBLE,
                    failure_category=FailureCategory.SSRF_BLOCKED,
                    failure_reason=f"Pre-hop SSRF validation failed for target '{current_url}': {e}",
                    is_independent=is_independent,
                )
            except SourcePolicyViolationError as e:
                return EvidenceRecord(
                    evidence_id=evidence_id,
                    url=url,
                    opened_excerpt=candidate_excerpt,
                    source_type=source_type,
                    verification_status=VerificationStatus.INACCESSIBLE,
                    failure_category=FailureCategory.UNSAFE_REDIRECT if redirect_count > 0 else FailureCategory.SSRF_BLOCKED,
                    failure_reason=f"Pre-hop policy validation failed for target '{current_url}': {e}",
                    is_independent=is_independent,
                )

            req = urllib.request.Request(
                current_url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
                },
            )

            try:
                resp = self.opener.open(req, timeout=self.policy.timeout_seconds)
                status_code = resp.getcode()
                headers = resp.info()

                # Handle HTTP Redirects (301, 302, 303, 307, 308)
                if status_code in (301, 302, 303, 307, 308):
                    location = headers.get("Location")
                    if not location:
                        return EvidenceRecord(
                            evidence_id=evidence_id,
                            url=url,
                            opened_excerpt=candidate_excerpt,
                            source_type=source_type,
                            verification_status=VerificationStatus.INACCESSIBLE,
                            failure_category=FailureCategory.HTTP_STATUS_ERROR,
                            failure_reason=f"Redirect response {status_code} missing Location header.",
                            is_independent=is_independent,
                        )

                    redirect_count += 1
                    if redirect_count > self.policy.max_redirects:
                        return EvidenceRecord(
                            evidence_id=evidence_id,
                            url=url,
                            opened_excerpt=candidate_excerpt,
                            source_type=source_type,
                            verification_status=VerificationStatus.INACCESSIBLE,
                            failure_category=FailureCategory.REDIRECT_LIMIT_EXCEEDED,
                            failure_reason=f"Exceeded max_redirects limit ({self.policy.max_redirects}).",
                            is_independent=is_independent,
                        )

                    current_url = urllib.parse.urljoin(current_url, location)
                    policy_warnings.append(f"Followed redirect {redirect_count}: {current_url}")
                    continue

                # 200 OK Response
                final_response = resp
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                content_type = headers.get("Content-Type", "text/html")

                # Validate Content-Type
                try:
                    clean_content_type = self.policy.validate_content_type(content_type)
                except SourcePolicyViolationError as e:
                    return EvidenceRecord(
                        evidence_id=evidence_id,
                        url=url,
                        opened_excerpt=candidate_excerpt,
                        source_type=source_type,
                        verification_status=VerificationStatus.INACCESSIBLE,
                        failure_category=FailureCategory.CONTENT_TYPE_DISALLOWED,
                        failure_reason=str(e),
                        is_independent=is_independent,
                    )

                # Enforce max payload size
                content_bytes = resp.read(self.policy.max_response_bytes + 1)
                if len(content_bytes) > self.policy.max_response_bytes:
                    return EvidenceRecord(
                        evidence_id=evidence_id,
                        url=url,
                        opened_excerpt=candidate_excerpt,
                        source_type=source_type,
                        verification_status=VerificationStatus.INACCESSIBLE,
                        failure_category=FailureCategory.PAYLOAD_TOO_LARGE,
                        failure_reason=f"Response payload exceeds maximum allowed size ({self.policy.max_response_bytes} bytes).",
                        is_independent=is_independent,
                    )

                break

            except urllib.error.HTTPError as e:
                # Catch 3xx if returned as HTTPError by opener
                if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                    location = e.headers.get("Location")
                    redirect_count += 1
                    if redirect_count > self.policy.max_redirects:
                        return EvidenceRecord(
                            evidence_id=evidence_id,
                            url=url,
                            opened_excerpt=candidate_excerpt,
                            source_type=source_type,
                            verification_status=VerificationStatus.INACCESSIBLE,
                            failure_category=FailureCategory.REDIRECT_LIMIT_EXCEEDED,
                            failure_reason=f"Exceeded max_redirects limit ({self.policy.max_redirects}).",
                            is_independent=is_independent,
                        )
                    current_url = urllib.parse.urljoin(current_url, location)
                    policy_warnings.append(f"Followed redirect {redirect_count}: {current_url}")
                    continue

                return EvidenceRecord(
                    evidence_id=evidence_id,
                    url=url,
                    opened_excerpt=candidate_excerpt,
                    source_type=source_type,
                    verification_status=VerificationStatus.INACCESSIBLE,
                    failure_category=FailureCategory.HTTP_STATUS_ERROR,
                    failure_reason=f"HTTP GET failed with status code {e.code}: {e.reason}",
                    is_independent=is_independent,
                )
            except urllib.error.URLError as e:
                return EvidenceRecord(
                    evidence_id=evidence_id,
                    url=url,
                    opened_excerpt=candidate_excerpt,
                    source_type=source_type,
                    verification_status=VerificationStatus.INACCESSIBLE,
                    failure_category=FailureCategory.DNS_RESOLUTION_FAILED,
                    failure_reason=f"Network URL Error: {e.reason}",
                    is_independent=is_independent,
                )
            except Exception as e:
                return EvidenceRecord(
                    evidence_id=evidence_id,
                    url=url,
                    opened_excerpt=candidate_excerpt,
                    source_type=source_type,
                    verification_status=VerificationStatus.INACCESSIBLE,
                    failure_category=FailureCategory.UNKNOWN_ERROR,
                    failure_reason=f"Unexpected collection error: {str(e)}",
                    is_independent=is_independent,
                )

        # Step 2: Save Snapshot Bytes to Immutable Store
        snapshot_id, sha256_hash, _ = self.snapshot_store.save_snapshot(content_bytes)

        # Step 3: Text Extraction and Quote Alignment Verification
        decoded_content = content_bytes.decode("utf-8", errors="ignore")
        clean_excerpt = candidate_excerpt.strip()

        if "html" in clean_content_type.lower() or "xml" in clean_content_type.lower():
            extraction_method = "PARSED_VISIBLE_TEXT_BS4"
            searchable_text = self._extract_visible_text_html(decoded_content)
        else:
            extraction_method = "RAW_TEXT_PLAIN"
            searchable_text = " ".join(decoded_content.split())

        quote_matches = (
            clean_excerpt in searchable_text
            or clean_excerpt.lower() in searchable_text.lower()
        )

        status = (
            VerificationStatus.OPENED_VERIFIED
            if quote_matches
            else VerificationStatus.QUOTE_MISMATCH
        )

        failure_cat = None if quote_matches else FailureCategory.QUOTE_NOT_FOUND
        failure_reas = (
            None
            if quote_matches
            else f"Candidate excerpt was not found in parsed visible text ({extraction_method})."
        )

        artifact = VerificationArtifact(
            verifier_run_id=f"verifier-run-{uuid.uuid4().hex[:8]}",
            verification_timestamp=datetime.now(timezone.utc),
            verifier_method=extraction_method,
            snapshot_sha256=sha256_hash,
            quote_exact_match=quote_matches,
            final_url=current_url,
            http_status=status_code,
            content_type=clean_content_type,
            content_length_bytes=len(content_bytes),
            retrieval_duration_ms=duration_ms,
            policy_warnings=policy_warnings,
            failure_category=failure_cat,
            failure_reason=failure_reas,
            limitations=f"Manual pre-hop redirect validation under SourcePolicy rules ({extraction_method})",
        )

        return EvidenceRecord(
            evidence_id=evidence_id,
            url=url,
            opened_excerpt=candidate_excerpt,
            source_type=source_type,
            verification_status=status,
            failure_category=failure_cat,
            failure_reason=failure_reas,
            retrieval_timestamp=datetime.now(timezone.utc),
            snapshot_id=snapshot_id,
            is_independent=is_independent,
            verification_artifact=artifact,
        )
