"""
Unit Tests for Hermetic Source Verifier and Snapshot Engine
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error

import pytest
from src.collector.policy import SourcePolicy
from src.collector.snapshot import SnapshotStore
from src.collector.verifier import SourceVerifier
from src.domain.enums import SourceType, VerificationStatus


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
    """Hermetic test: Verifies exact quote match on mocked HTTP response."""
    store = SnapshotStore(base_dir=tmp_path)
    policy = SourcePolicy(allowed_schemes={"http", "https"}, block_private_ips=False)
    verifier = SourceVerifier(snapshot_store=store, policy=policy)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.geturl.return_value = "http://test-server.local/page"
    mock_response.info.return_value = {"Content-Type": "text/html; charset=utf-8"}
    mock_response.read.return_value = b"<html><body><h1>Searchbloom AEO Report</h1><p>Searchbloom doubles Perplexity citations in 90 days.</p></body></html>"
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        record = verifier.verify_url(
            url="http://test-server.local/page",
            candidate_excerpt="Searchbloom doubles Perplexity citations in 90 days.",
            source_type=SourceType.COMMUNITY_FORUM,
        )

    assert record.verification_status == VerificationStatus.OPENED_VERIFIED
    assert record.verification_artifact is not None
    assert record.verification_artifact.quote_exact_match is True
    assert record.verification_artifact.http_status == 200
    assert record.verification_artifact.content_type == "text/html; charset=utf-8"


def test_hermetic_verifier_quote_mismatch(tmp_path: Path):
    """Hermetic test: Verifies quote mismatch when excerpt is absent in response bytes."""
    store = SnapshotStore(base_dir=tmp_path)
    policy = SourcePolicy(allowed_schemes={"http", "https"}, block_private_ips=False)
    verifier = SourceVerifier(snapshot_store=store, policy=policy)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.geturl.return_value = "http://test-server.local/page"
    mock_response.info.return_value = {"Content-Type": "text/html"}
    mock_response.read.return_value = b"<html><body><p>Generic marketing text without matching quote.</p></body></html>"
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        record = verifier.verify_url(
            url="http://test-server.local/page",
            candidate_excerpt="Exact quote that does not exist in response.",
        )

    assert record.verification_status == VerificationStatus.QUOTE_MISMATCH
    assert record.verification_artifact is not None
    assert record.verification_artifact.quote_exact_match is False


def test_hermetic_verifier_ssrf_prohibited_target():
    """Hermetic test: Rejects SSRF target (169.254.169.254) before issuing HTTP request."""
    policy = SourcePolicy(allowed_schemes={"http", "https"}, block_private_ips=True)
    verifier = SourceVerifier(policy=policy)

    with patch("urllib.request.urlopen") as mock_urlopen:
        record = verifier.verify_url(
            url="https://169.254.169.254/latest/meta-data/",
            candidate_excerpt="AWS Metadata Excerpt",
        )
        mock_urlopen.assert_not_called()

    assert record.verification_status == VerificationStatus.INACCESSIBLE
    assert record.verification_artifact is None


def test_hermetic_verifier_http_error_returns_inaccessible():
    """Hermetic test: Handles HTTP 404 / 500 error gracefully."""
    policy = SourcePolicy(allowed_schemes={"http", "https"}, block_private_ips=False)
    verifier = SourceVerifier(policy=policy)

    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("http://test.local", 404, "Not Found", None, None)):
        record = verifier.verify_url(
            url="http://test.local/missing",
            candidate_excerpt="Some excerpt",
        )

    assert record.verification_status == VerificationStatus.INACCESSIBLE
    assert record.verification_artifact is None
