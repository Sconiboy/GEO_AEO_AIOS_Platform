"""
Content-Addressed Snapshot Store
Saves immutable raw content bytes and computes SHA-256 hashes.
"""

import hashlib
from pathlib import Path
from typing import Tuple


class SnapshotStore:
    """
    Immutable content-addressed snapshot repository.
    Stores raw source bytes under data/snapshots/<sha256>.txt
    """

    def __init__(self, base_dir: Path = Path("data/snapshots")):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, raw_bytes: bytes) -> Tuple[str, str, Path]:
        """
        Saves raw bytes to disk keyed by its SHA-256 digest.
        Returns: (snapshot_id, sha256_hash, snapshot_path)
        """
        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
        snapshot_id = f"snap-{sha256_hash[:16]}"
        snapshot_path = self.base_dir / f"{sha256_hash}.txt"

        if not snapshot_path.exists():
            with open(snapshot_path, "wb") as f:
                f.write(raw_bytes)

        return snapshot_id, sha256_hash, snapshot_path

    def load_snapshot(self, sha256_hash: str) -> bytes:
        """Loads snapshot bytes by SHA-256 digest."""
        snapshot_path = self.base_dir / f"{sha256_hash}.txt"
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found for hash: {sha256_hash}")
        with open(snapshot_path, "rb") as f:
            return f.read()
