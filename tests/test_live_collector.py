"""
Unit Tests for Hermetic Source Verifier and Snapshot Engine (Sprint 2.2 Hardening)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error

import pytest
from src.collector.policy import SourcePolicy
from src.collector.snapshot import SnapshotStore
from src.collector.verifier import SourceVerifier
from src.domain.enums import FailureCategory, SourceType, VerificationStatus


def test_snapshot_store(tmp_path: Path):
    """Test saving raw content bytes and computing SHA-256 digest."""
    store = SnapshotStore(base_dir=tmp_path)
    sample_bytes = b"Hello GEO AEO Evidence Store"

    snapshot_id, sha256_hash, snapshot_path = store.save_snapshot(sample_bytes)

    assert snapshot_id.startswith("snap-")
    assert len(sha256_hash) == 64
    assert snapshot_path.exists()

    loaded = store.load_snapshot(sha256_hash)
    assert loaded == sample_bytes


def test_hermetic_verifier_quote_match(tmp_path: Path):
    """Hermetic test: Verifies exact quote match on mocked HTML response."""
    store = SnapshotStore(base_dir=tmp_path)
    policy = SourcePolicy(allowed_schemes={"http", "https"}, block_private_ips=False)
    verifier = SourceVerifier(snapshot_store=store, policy=policy)

    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.info.return_value = {"Content-Type": "text/html; charset=utf-8"}
    mock_response.read.return_value = b"<html><body><h1>Searchbloom AEO Report</h1><p>Searchbloom doubles Perplexity citations in 90 days.</p></body></html>"
    mock_response.__enter__.return_value = mock_response

    with patch.object(verifier.opener, "open", return_value=mock_response):
        record = verifier.verify_url(
            url="https://test-server.example.com/page",
            candidate_excerpt="Searchbloom doubles Perplexity citations in 90 days.",
            source_type=SourceType.COMMUNITY_FORUM,
        )

    assert record.verification_status == VerificationStatus.OPENED_VERIFIED
    assert record.verification_artifact is not None
    assert record.verification_artifact.quote_exact_match is True
    assert record.verification_artifact.verifier_method == "PARSED_VISIBLE_TEXT_BS4"


def test_hermetic_verifier_script_tag_false_positive_rejected(tmp_path: Path):
    """STRICT RULE: Test that quotes hidden inside <script> tags do NOT pass visible text quote matching."""
    store = SnapshotStore(base_dir=tmp_path)
    policy = SourcePolicy(allowed_schemes={"http", "https"}, block_private_ips=False)
    verifier = SourceVerifier(snapshot_store=store, policy=policy)

    # Quote exists ONLY inside <script> tag, not in visible <body> HTML text
    html_with_hidden_script = b"""
    <html>
      <head>
        <script>
          var text = "Hidden fake excerpt inside script tag only.";
        </script>
      </head>
      <body>
        <p>Visible page content without the script text.</p>
      </body>
    </html>
    """

    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.info.return_value = {"Content-Type": "text/html"}
    mock_response.read.return_value = html_with_hidden_script
    mock_response.__enter__.return_value = mock_response

    with patch.object(verifier.opener, "open", return_value=mock_response):
        record = verifier.verify_url(
            url="https://test-server.example.com/script-page",
            candidate_excerpt="Hidden fake excerpt inside script tag only.",
        )

    # Must be QUOTE_MISMATCH because script tags are stripped during visible text extraction
    assert record.verification_status == VerificationStatus.QUOTE_MISMATCH
    assert record.failure_category == FailureCategory.QUOTE_NOT_FOUND
    assert record.verification_artifact is not None
    assert record.verification_artifact.quote_exact_match is False


def test_hermetic_verifier_unsafe_redirect_blocked():
    """STRICT RULE: Test pre-hop validation blocks redirect to loopback/private IP (127.0.0.1)."""
    policy = SourcePolicy(allowed_schemes={"http", "https"}, block_private_ips=True)
    verifier = SourceVerifier(policy=policy)

    mock_302_response = MagicMock()
    mock_302_response.getcode.return_value = 302
    mock_302_response.info.return_value = {"Location": "http://127.0.0.1/admin"}
    mock_302_response.__enter__.return_value = mock_302_response

    with patch.object(verifier.opener, "open", return_value=mock_302_response):
        record = verifier.verify_url(
            url="https://example.com/redirect",
            candidate_excerpt="Some excerpt",
        )

    assert record.verification_status == VerificationStatus.INACCESSIBLE
    assert record.failure_category in (FailureCategory.SSRF_BLOCKED, FailureCategory.UNSAFE_REDIRECT)
    assert "Pre-hop" in record.failure_reason if record.failure_reason else True


def test_hermetic_verifier_payload_too_large():
    """Test that response payload exceeding max_response_bytes is rejected with PAYLOAD_TOO_LARGE."""
    policy = SourcePolicy(allowed_schemes={"http", "https"}, max_response_bytes=1024, block_private_ips=False)
    verifier = SourceVerifier(policy=policy)

    mock_large_response = MagicMock()
    mock_large_response.getcode.return_value = 200
    mock_large_response.info.return_value = {"Content-Type": "text/html"}
    mock_large_response.read.return_value = b"X" * 2000  # Exceeds 1024 bytes!
    mock_large_response.__enter__.return_value = mock_large_response

    with patch.object(verifier.opener, "open", return_value=mock_large_response):
        record = verifier.verify_url(
            url="https://example.com/large-page",
            candidate_excerpt="Some excerpt",
        )

    assert record.verification_status == VerificationStatus.INACCESSIBLE
    assert record.failure_category == FailureCategory.PAYLOAD_TOO_LARGE
