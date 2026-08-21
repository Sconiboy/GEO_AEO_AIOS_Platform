"""
Unit Tests for Controlled Live-Collection Spike & Source Verifier
"""

from pathlib import Path
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


def test_verifier_inaccessible_url():
    """Test that a non-existent/inaccessible URL returns INACCESSIBLE status."""
    verifier = SourceVerifier(timeout_seconds=2.0)
    record = verifier.verify_url(
        url="https://httpbin.org/status/404",
        candidate_excerpt="This excerpt should fail because URL is 404.",
    )

    assert record.verification_status == VerificationStatus.INACCESSIBLE
    assert record.verification_artifact is None


def test_verifier_quote_mismatch(tmp_path: Path):
    """Test that an existing page with a non-matching excerpt returns QUOTE_MISMATCH."""
    store = SnapshotStore(base_dir=tmp_path)
    verifier = SourceVerifier(snapshot_store=store, timeout_seconds=5.0)

    # Public W3C homepage or httpbin html page
    record = verifier.verify_url(
        url="https://httpbin.org/html",
        candidate_excerpt="Nonexistent fake quote snippet that does not appear in httpbin HTML.",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
    )

    assert record.verification_status == VerificationStatus.QUOTE_MISMATCH
    assert record.verification_artifact is not None
    assert record.verification_artifact.quote_exact_match is False


def test_verifier_exact_quote_match(tmp_path: Path):
    """Test that an existing page with a matching excerpt returns OPENED_VERIFIED."""
    store = SnapshotStore(base_dir=tmp_path)
    verifier = SourceVerifier(snapshot_store=store, timeout_seconds=5.0)

    record = verifier.verify_url(
        url="https://httpbin.org/html",
        candidate_excerpt="Herman Melville - Moby-Dick",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
    )

    assert record.verification_status == VerificationStatus.OPENED_VERIFIED
    assert record.verification_artifact is not None
    assert record.verification_artifact.quote_exact_match is True
    assert len(record.verification_artifact.snapshot_sha256) == 64
