"""
Live Source Collector & Content-Addressed Snapshot Store
"""

from .snapshot import SnapshotStore
from .verifier import SourceVerifier

__all__ = ["SnapshotStore", "SourceVerifier"]
