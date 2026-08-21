"""
Domain Enumerations for Evidence-Governed Auditing
"""

from enum import Enum


class SourceType(str, Enum):
    """Classification of evidence source quality and independence."""

    INDEPENDENT_EDITORIAL = "independent_editorial"
    COMMUNITY_FORUM = "community_forum"
    REVIEW_AGGREGATOR = "review_aggregator"
    OFFICIAL_DOCUMENTATION = "official_documentation"
    AFFILIATE_CONTENT = "affiliate_content"
    VENDOR_MARKETING = "vendor_marketing"
    UNKNOWN = "unknown"


class VerificationStatus(str, Enum):
    """Deterministic verification state of an evidence source."""

    OPENED_VERIFIED = "opened_verified"
    INACCESSIBLE = "inaccessible"
    QUOTE_MISMATCH = "quote_mismatch"
    CIRCULAR_SYNDICATED = "circular_syndicated"
    UNVERIFIED_STALE = "unverified_stale"


class ConfidenceRating(str, Enum):
    """Derived confidence classification for client findings."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNGROUNDED = "ungrounded"
