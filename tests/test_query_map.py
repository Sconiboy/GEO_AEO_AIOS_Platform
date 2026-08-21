"""
Unit Tests for QueryMap, Dataset Manifests, and Controlled Allowlist Execution (Sprint 3.1 Policy Enforcement)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.collector.query_map_runner import DatasetManifest, ManifestSourceCandidate, QueryMapRunner
from src.domain.enums import FailureCategory, HumanApprovalState, QueryIntent, SourceType, VerificationStatus
from src.domain.query_map import CollectionPolicyProfile, QueryMap, SourceScope, TargetQuery


def make_sample_query_map(max_sources: int = 5, blocked_domains: list = None) -> QueryMap:
    blocked_domains = blocked_domains or []
    return QueryMap(
        query_map_id="qm-test-01",
        entity_name="Python Software Foundation",
        category="Programming Languages",
        target_buyer_persona="Systems Architect",
        policy_profile=CollectionPolicyProfile(
            profile_id="pol-01",
            source_scope=SourceScope(
                scope_id="scope-01",
                allowed_domains=["python.org", "w3.org", "httpbin.org"],
                blocked_domains=blocked_domains,
                max_sources_per_query=max_sources,
            ),
        ),
        queries=[
            TargetQuery(
                query_id="q-approved",
                text="What is Python design philosophy?",
                intent=QueryIntent.INFORMATIONAL_EVALUATION,
                rationale="Evaluates core language design principles.",
                approval_state=HumanApprovalState.APPROVED,
            ),
            TargetQuery(
                query_id="q-proposed",
                text="Unapproved query text example",
                intent=QueryIntent.COMMERCIAL_BUYER_INTENT,
                rationale="Unapproved query that should be ignored.",
                approval_state=HumanApprovalState.PROPOSED,
            ),
        ],
    )


def test_query_map_unapproved_queries_ignored():
    """Test that queries with approval_state != APPROVED are ignored by QueryMapRunner."""
    qm = make_sample_query_map()
    manifest = DatasetManifest(
        manifest_id="man-test-01",
        description="Test manifest",
        candidates=[
            ManifestSourceCandidate(
                query_id="q-proposed",  # Unapproved query!
                url="https://www.python.org/page",
                candidate_excerpt="Some candidate excerpt for unapproved query.",
            )
        ],
    )

    runner = QueryMapRunner()
    audit_run = runner.run_query_map_audit(qm, manifest)
    assert len(audit_run.claims) == 0


def test_query_map_unapproved_domain_blocked():
    """Test that candidate URLs outside allowed_domains are rejected immediately."""
    qm = make_sample_query_map()
    manifest = DatasetManifest(
        manifest_id="man-test-02",
        description="Test manifest with unapproved domain",
        candidates=[
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://unapproved-domain-example.com/article",  # NOT in allowed_domains
                candidate_excerpt="Some candidate excerpt text here.",
            )
        ],
    )

    runner = QueryMapRunner()
    audit_run = runner.run_query_map_audit(qm, manifest)

    assert len(audit_run.claims) == 0
    assert len(audit_run.evidence_ledger) == 1

    blocked_record = list(audit_run.evidence_ledger.values())[0]
    assert blocked_record.verification_status == VerificationStatus.INACCESSIBLE
    assert blocked_record.failure_category == FailureCategory.SSRF_BLOCKED


def test_is_non_client_spike_false_raises_value_error():
    """P0 GATE TEST: Test that DatasetManifest with is_non_client_spike=False raises ValueError immediately."""
    qm = make_sample_query_map()
    manifest = DatasetManifest(
        manifest_id="man-test-false",
        description="Invalid manifest attempting client mode",
        is_non_client_spike=False,  # False!
        candidates=[
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://www.python.org/doc",
                candidate_excerpt="Valid excerpt text",
            )
        ],
    )

    runner = QueryMapRunner()
    with pytest.raises(ValueError, match="is_non_client_spike must be True"):
        runner.run_query_map_audit(qm, manifest)


def test_max_sources_per_query_cap_enforced():
    """P0 TEST: Test that max_sources_per_query cap is strictly enforced."""
    qm = make_sample_query_map(max_sources=1)  # Cap = 1!
    manifest = DatasetManifest(
        manifest_id="man-test-cap",
        description="Test manifest with multiple candidates",
        candidates=[
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://www.python.org/page1",
                candidate_excerpt="Excerpt 1 text",
            ),
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://www.python.org/page2",
                candidate_excerpt="Excerpt 2 text",
            ),
        ],
    )

    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.info.return_value = {"Content-Type": "text/html"}
    mock_response.read.return_value = b"<html><body><p>Excerpt 1 text</p></body></html>"
    mock_response.__enter__.return_value = mock_response

    runner = QueryMapRunner()
    with patch("urllib.request.build_opener") as mock_build_opener:
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        audit_run = runner.run_query_map_audit(qm, manifest)

        # Verifier should be called AT MOST ONCE due to cap=1
        assert mock_opener.open.call_count == 1

    # Second candidate must be recorded as cap exceeded
    assert len(audit_run.evidence_ledger) == 2
    exceeded_records = [
        r for r in audit_run.evidence_ledger.values()
        if r.failure_category == FailureCategory.PAYLOAD_TOO_LARGE
    ]
    assert len(exceeded_records) == 1
    assert "Exceeded max_sources_per_query cap" in exceeded_records[0].failure_reason


def test_blocked_domains_precedence():
    """P0 TEST: Test that blocked_domains takes precedence over allowed_domains."""
    # Domain python.org is in both allowed and blocked lists
    qm = make_sample_query_map(blocked_domains=["python.org"])
    manifest = DatasetManifest(
        manifest_id="man-test-blocked",
        description="Test manifest with blocked domain",
        candidates=[
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://www.python.org/page1",
                candidate_excerpt="Excerpt text",
            )
        ],
    )

    runner = QueryMapRunner()
    with patch("urllib.request.build_opener") as mock_build_opener:
        audit_run = runner.run_query_map_audit(qm, manifest)
        mock_build_opener.assert_not_called()  # MUST make ZERO network calls!

    assert len(audit_run.evidence_ledger) == 1
    record = list(audit_run.evidence_ledger.values())[0]
    assert record.verification_status == VerificationStatus.INACCESSIBLE
    assert record.failure_category == FailureCategory.SSRF_BLOCKED
    assert "explicitly in blocked_domains list" in record.failure_reason


def test_multiple_blocked_candidates_have_unique_ledger_ids():
    """P1 TEST: Test that multiple blocked candidates for the same query get distinct ledger IDs."""
    qm = make_sample_query_map()
    manifest = DatasetManifest(
        manifest_id="man-test-multi-blocked",
        description="Test manifest with multiple blocked candidates",
        candidates=[
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://unapproved1.com/page",
                candidate_excerpt="Excerpt 1 text",
            ),
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://unapproved2.com/page",
                candidate_excerpt="Excerpt 2 text",
            ),
        ],
    )

    runner = QueryMapRunner()
    audit_run = runner.run_query_map_audit(qm, manifest)

    # Both blocked records must exist with distinct IDs
    assert len(audit_run.evidence_ledger) == 2
    ledger_ids = list(audit_run.evidence_ledger.keys())
    assert ledger_ids[0] != ledger_ids[1]
