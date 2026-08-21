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


class FailureCategory(str, Enum):
    """Structured failure categories for source verification and policy violations."""

    SSRF_BLOCKED = "ssrf_blocked"
    REDIRECT_LIMIT_EXCEEDED = "redirect_limit_exceeded"
    UNSAFE_REDIRECT = "unsafe_redirect"
    CONTENT_TYPE_DISALLOWED = "content_type_disallowed"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    HTTP_STATUS_ERROR = "http_status_error"
    DNS_RESOLUTION_FAILED = "dns_resolution_failed"
    QUOTE_NOT_FOUND = "quote_not_found"
    UNKNOWN_ERROR = "unknown_error"


class QueryIntent(str, Enum):
    """Categorization of commercial and buyer evaluation intent."""

    COMMERCIAL_BUYER_INTENT = "commercial_buyer_intent"
    FEATURE_COMPARISON = "feature_comparison"
    PRICING_EVALUATION = "pricing_evaluation"
    ALTERNATIVE_REPLACEMENT = "alternative_replacement"
    INFORMATIONAL_EVALUATION = "informational_evaluation"


class HumanApprovalState(str, Enum):
    """Human governance approval state for target queries and source manifests."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class CaptureMethod(str, Enum):
    """Method used to capture evidence."""

    MANUAL_PASTE = "manual_paste"
    HUMAN_OPERATOR_CONSOLE = "human_operator_console"
    API_DIRECT_RESPONSE = "api_direct_response"
    AUTOMATED_HEADLESS_BROWSER = "automated_headless_browser"
    SYNTHETIC_FIXTURE_IMPORT = "synthetic_fixture_import"


class ReconciliationStatus(str, Enum):
    """Semantic truth evaluation status of a statement against evidence."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    NOT_ASSESSABLE = "not_assessable"
    CANDIDATE_FOR_HUMAN_SEMANTIC_REVIEW = "candidate_for_human_semantic_review"


class ReconciliationMethod(str, Enum):
    """Method used to reconcile statement against source evidence."""

    HUMAN_AUDITOR_REVIEW = "human_auditor_review"
    HEURISTIC_EXACT_FACT_MATCH = "heuristic_exact_fact_match"
    STRUCTURED_LLM_ASSISTED_REVIEW = "structured_llm_assisted_review"


class GapCategory(str, Enum):
    """Classification of client evidence gaps."""

    MISSING_OFFICIAL_DOCS = "missing_official_docs"
    MISSING_THIRD_PARTY_COMPARISON = "missing_third_party_comparison"
    UNGROUNDED_MODEL_CLAIM = "ungrounded_model_claim"
    COMPETITOR_DOMINANCE = "competitor_dominance"
    SEMANTIC_REVIEW_PENDING = "semantic_review_pending"
    UNCOLLECTED_COMPETITOR_CITATION = "uncollected_competitor_citation"


class ActionSeverity(str, Enum):
    """Priority severity classification for recommended client actions."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceRelationship(str, Enum):
    """Ownership and independence relationship classification of an evidence domain."""

    CLIENT_OWNED = "client_owned"
    COMPETITOR_OWNED = "competitor_owned"
    INDEPENDENT_EDITORIAL = "independent_editorial"
    REVIEW_PLATFORM = "review_platform"
    DIRECTORY = "directory"
    COMMUNITY = "community"
    OFFICIAL_REFERENCE = "official_reference"
    UNKNOWN = "unknown"


class AttributionStatus(str, Enum):
    """Competitor attribution evaluation status for an observed model response surface."""

    CITED_COMPETITOR_OBSERVED = "cited_competitor_observed"
    NO_ANSWER_CITATIONS_NOT_ASSESSABLE = "no_answer_citations_not_assessable"
    CLIENT_ONLY_CITATIONS = "client_only_citations"
    THIRD_PARTY_ONLY_CITATIONS = "third_party_only_citations"


class StatementEvidenceState(str, Enum):
    """Three-way evidence evaluation state for a statement proposal."""

    SUPPORTED = "supported"
    SEMANTIC_REVIEW_PENDING = "semantic_review_pending"
    CANDIDATE_EVIDENCE_GAP = "candidate_evidence_gap"
