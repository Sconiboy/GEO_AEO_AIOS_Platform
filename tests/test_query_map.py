"""
Unit Tests for QueryMap, Dataset Manifests, and Controlled Allowlist Execution
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.collector.query_map_runner import DatasetManifest, ManifestSourceCandidate, QueryMapRunner
from src.domain.enums import HumanApprovalState, QueryIntent, SourceType, VerificationStatus
from src.domain.query_map import CollectionPolicyProfile, QueryMap, SourceScope, TargetQuery


def make_sample_query_map() -> QueryMap:
    return QueryMap(
        query_map_id="qm-test-01",
        entity_name="Python Software Foundation",
        category="Programming Languages",
        target_buyer_persona="Systems Architect",
        policy_profile=CollectionPolicyProfile(
            profile_id="pol-01",
            source_scope=SourceScope(
                scope_id="scope-01",
                allowed_domains=["python.org", "w3.org"],
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

    # Since q-proposed is not APPROVED, zero claims and zero verified evidence should be built
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
                url="https://unapproved-domain-example.com/article",  # NOT in ['python.org', 'w3.org']
                candidate_excerpt="Some candidate excerpt text here.",
            )
        ],
    )

    runner = QueryMapRunner()
    audit_run = runner.run_query_map_audit(qm, manifest)

    # Claim cannot be built because unapproved-domain candidate was blocked
    assert len(audit_run.claims) == 0
    assert len(audit_run.evidence_ledger) == 1

    blocked_record = list(audit_run.evidence_ledger.values())[0]
    assert blocked_record.verification_status == VerificationStatus.INACCESSIBLE
    assert "not in pre-approved allowed_domains whitelist" in blocked_record.failure_reason


def test_query_map_runner_end_to_end(tmp_path: Path):
    """Hermetic test: Verifies end-to-end QueryMap execution on approved query and domain."""
    qm = make_sample_query_map()
    manifest = DatasetManifest(
        manifest_id="man-test-03",
        description="Test manifest with valid domain",
        candidates=[
            ManifestSourceCandidate(
                query_id="q-approved",
                url="https://www.python.org/doc/blurb/",
                candidate_excerpt="Python is an interpreted, object-oriented language.",
            )
        ],
    )

    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.info.return_value = {"Content-Type": "text/html"}
    mock_response.read.return_value = b"<html><body><p>Python is an interpreted, object-oriented language.</p></body></html>"
    mock_response.__enter__.return_value = mock_response

    runner = QueryMapRunner()

    with patch("urllib.request.build_opener") as mock_build_opener:
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        audit_run = runner.run_query_map_audit(qm, manifest)

    assert len(audit_run.claims) == 1
    assert audit_run.claims[0].claim_id == "claim-q-approved"
    assert len(audit_run.claims[0].evidence_ids) == 1

    ev_id = audit_run.claims[0].evidence_ids[0]
    ev = audit_run.evidence_ledger[ev_id]
    assert ev.verification_status == VerificationStatus.OPENED_VERIFIED
    assert ev.verification_artifact is not None
    assert ev.verification_artifact.quote_exact_match is True
