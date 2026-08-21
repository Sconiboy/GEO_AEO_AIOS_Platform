"""
Unit Tests for Domain Contracts and Deterministic Confidence Scoring
"""

import pytest
from src.domain.enums import ConfidenceRating, SourceType, VerificationStatus
from src.domain.models import AuditRun, ClaimRecord, ConfidenceScore, EvidenceRecord


def test_evidence_record_validation():
    """Test EvidenceRecord creation and excerpt validation."""
    record = EvidenceRecord(
        evidence_id="ev-101",
        url="https://techcrunch.com/article-1",
        opened_excerpt="Competitor A features deep API integrations with Shopify.",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
    )
    assert record.evidence_id == "ev-101"
    assert record.is_independent is True
    assert record.source_type == SourceType.INDEPENDENT_EDITORIAL


def test_empty_excerpt_raises_error():
    """Test that empty or whitespace excerpts raise Pydantic validation errors."""
    with pytest.raises(ValueError):
        EvidenceRecord(
            evidence_id="ev-102",
            url="https://example.com",
            opened_excerpt="   ",
        )


def test_deterministic_confidence_score_calculation():
    """Test that confidence score is calculated deterministically from inputs."""
    ev1 = EvidenceRecord(
        evidence_id="ev-1",
        url="https://techcrunch.com/review",
        opened_excerpt="Brand X is rated #1 for enterprise scalability.",
        source_type=SourceType.INDEPENDENT_EDITORIAL,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
    )
    ev2 = EvidenceRecord(
        evidence_id="ev-2",
        url="https://reddit.com/r/marketing/comments/123",
        opened_excerpt="We switched to Brand X and saw 40% faster performance.",
        source_type=SourceType.COMMUNITY_FORUM,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_independent=True,
    )

    confidence = ConfidenceScore.compute(evidence_list=[ev1, ev2])
    assert confidence.verified_sources_count == 2
    assert confidence.independent_sources_count == 2
    assert confidence.distinct_source_types == 2
    assert confidence.rating in [ConfidenceRating.HIGH, ConfidenceRating.MEDIUM]
    assert 0.5 <= confidence.score <= 1.0


def test_confidence_score_penalty_for_circular_duplication():
    """Test that circular syndicated content reduces confidence score."""
    ev1 = EvidenceRecord(
        evidence_id="ev-1",
        url="https://site1.com",
        opened_excerpt="Same copied text snippet across network.",
        source_type=SourceType.AFFILIATE_CONTENT,
        verification_status=VerificationStatus.OPENED_VERIFIED,
        is_syndicated_duplicate=True,
    )
    confidence = ConfidenceScore.compute(evidence_list=[ev1])
    assert confidence.has_circular_duplication is True
    # Base 0.3 + 0.1 - 0.2 penalty = 0.20
    assert confidence.score < 0.5
