"""
Unit tests for Sprint 7.4 Forensic Competitor Evidence-Gap Analysis Workflow
Tests typed ObservedCitationCollectionCandidate emission, manifest authorization validation (requires_human_manifest_approval),
exact URL verification matching (path-sensitive), elimination of orphan action plans, complete canonical digest tamper protection, and CLI analyze-gaps execution.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from pydantic import ValidationError
import pytest

from src.cli import run_cli_analyze_gaps
from src.collector.gap_analyzer import ForensicGapAnalyzer
from src.collector.query_map_runner import DatasetManifest, ManifestSourceCandidate
from src.domain.enums import (
    ActionSeverity,
    AttributionStatus,
    GapCategory,
    ReconciliationMethod,
    ReconciliationStatus,
    SourceRelationship,
    SourceType,
    StatementEvidenceState,
)
from src.domain.gap_analysis import (
    AnswerCitation,
    ClientEvidenceGap,
    CompetitorCitation,
    CompetitorCitationPattern,
    FindingBasis,
    ForensicGapAnalysisRecord,
    ObservedCitationCollectionCandidate,
    PrioritizedActionPlan,
)
from src.domain.human_decision import HumanDecisionRecord, HumanStatementDecision, QuotedEvidencePassage
from src.domain.models import AuditRun, EvidenceRecord, VerificationArtifact, VerificationStatus
from src.domain.observation import AnswerObservation
from src.domain.profile import ClientProfile, CompetitorProfile, SubjectProfile
from src.domain.query_map import QueryMap


@pytest.fixture
def sample_subject_profile() -> SubjectProfile:
    """Fixture providing a sample SubjectProfile."""
    return SubjectProfile(
        profile_id="prof-001",
        client_profile=ClientProfile(
            entity_name="Python Software Foundation",
            client_domain="python.org",
            owned_domains=["python.org", "peps.python.org", "docs.python.org"],
            offering_category="Core Programming Language",
            geography="Global",
        ),
        competitor_profiles=[
            CompetitorProfile(
                competitor_entity_name="Rust Foundation",
                competitor_domains=["rust-lang.org"],
            )
        ],
    )


def test_gap_analysis_models_are_frozen_and_immutable(sample_subject_profile: SubjectProfile) -> None:
    """Proves that gap analysis models are frozen and reject direct attribute mutation."""
    citation = CompetitorCitation(
        domain="python.org",
        citation_count=2,
        source_type=SourceType.OFFICIAL_DOCUMENTATION,
        source_relationship=SourceRelationship.CLIENT_OWNED,
    )
    with pytest.raises(ValidationError):
        citation.domain = "other.org"  # type: ignore[misc]

    basis = FindingBasis(
        observation_id="obs-01",
        statement_id="stmt-01",
        evidence_ids=["ev-01"],
        source_relationships=[SourceRelationship.CLIENT_OWNED],
    )

    gap = ClientEvidenceGap(
        gap_id="gap-01",
        target_query_id="q-001",
        gap_category=GapCategory.MISSING_OFFICIAL_DOCS,
        statement_evidence_state=StatementEvidenceState.CANDIDATE_EVIDENCE_GAP,
        affected_statement_ids=["stmt-01"],
        description="Detailed description of missing evidence",
        severity=ActionSeverity.HIGH,
        finding_basis=basis,
    )
    with pytest.raises(ValidationError):
        gap.severity = ActionSeverity.LOW  # type: ignore[misc]


def test_deceptive_subdomain_rejected(sample_subject_profile: SubjectProfile) -> None:
    """Proves that deceptive domain names (notrust-lang.org, rust-lang.org.evil.com) are rejected."""
    rel_exact, comp_exact = ForensicGapAnalyzer.classify_source_relationship(
        domain="rust-lang.org", subject_profile=sample_subject_profile
    )
    assert rel_exact == SourceRelationship.COMPETITOR_OWNED
    assert comp_exact == "Rust Foundation"

    rel_sub, comp_sub = ForensicGapAnalyzer.classify_source_relationship(
        domain="docs.rust-lang.org", subject_profile=sample_subject_profile
    )
    assert rel_sub == SourceRelationship.COMPETITOR_OWNED
    assert comp_sub == "Rust Foundation"

    rel_fake1, comp_fake1 = ForensicGapAnalyzer.classify_source_relationship(
        domain="notrust-lang.org", subject_profile=sample_subject_profile
    )
    assert rel_fake1 != SourceRelationship.COMPETITOR_OWNED
    assert comp_fake1 is None

    rel_fake2, comp_fake2 = ForensicGapAnalyzer.classify_source_relationship(
        domain="rust-lang.org.evil.com", subject_profile=sample_subject_profile
    )
    assert rel_fake2 != SourceRelationship.COMPETITOR_OWNED
    assert comp_fake2 is None


def test_unapproved_observed_url_requires_human_manifest_approval(
    sample_subject_profile: SubjectProfile,
) -> None:
    """Proves that an unapproved observed competitor URL produces ObservedCitationCollectionCandidate with requires_human_manifest_approval=True and NO orphan action plan."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    raw_obs_bytes = obs_path.read_bytes()
    orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

    competitor_answer_text = (
        orig_obs.raw_answer_text + "\n\nFor speed comparison, see https://rust-lang.org official documentation."
    )
    competitor_obs = orig_obs.model_copy(
        update={
            "raw_answer_text": competitor_answer_text,
            "raw_answer_sha256": hashlib.sha256(competitor_answer_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    assert record.attribution_status == AttributionStatus.CITED_COMPETITOR_OBSERVED

    # Verify collection candidate
    assert len(record.collection_candidates) == 1
    cand = record.collection_candidates[0]
    assert cand.cited_url == "https://rust-lang.org"
    assert cand.cited_domain == "rust-lang.org"
    assert cand.matched_competitor_entity == "Rust Foundation"
    assert cand.requires_human_manifest_approval is True
    assert "requires explicit human approval and manifest policy update" in cand.action_hypothesis

    # Verify NO orphan action plans in prioritized_actions!
    assert len(record.prioritized_actions) == 0


def test_manifest_approved_url_authorizes_collection_candidate(
    sample_subject_profile: SubjectProfile,
) -> None:
    """Proves that if an observed URL is authorized in manifest.candidate_sources, requires_human_manifest_approval=False."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    orig_manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)

    # Create manifest authorizing https://rust-lang.org in candidates
    authorized_manifest = orig_manifest.model_copy(
        update={
            "candidates": orig_manifest.candidates + [
                ManifestSourceCandidate(
                    url="https://rust-lang.org",
                    candidate_excerpt="Rust official site",
                    source_type=SourceType.OFFICIAL_DOCUMENTATION,
                    query_id="q-001",
                )
            ]
        }
    )
    auth_manifest_bytes = authorized_manifest.model_dump_json().encode("utf-8")

    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    raw_obs_bytes = obs_path.read_bytes()
    orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

    competitor_answer_text = (
        orig_obs.raw_answer_text + "\n\nFor speed comparison, see https://rust-lang.org official documentation."
    )
    competitor_obs = orig_obs.model_copy(
        update={
            "raw_answer_text": competitor_answer_text,
            "raw_answer_sha256": hashlib.sha256(competitor_answer_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=authorized_manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=auth_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    assert len(record.collection_candidates) == 1
    cand = record.collection_candidates[0]
    assert cand.requires_human_manifest_approval is False
    assert cand.matched_manifest_query_id == "q-001"
    assert "is authorized in dataset manifest for query 'q-001'" in cand.action_hypothesis


def test_same_domain_different_path_rejected(sample_subject_profile: SubjectProfile) -> None:
    """Proves that a manifest candidate for https://rust-lang.org/about does NOT authorize https://rust-lang.org/learn (emits requires_human_manifest_approval=True)."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    orig_manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)

    # Manifest candidate for /about on query q-001
    manifest_with_about = orig_manifest.model_copy(
        update={
            "candidates": orig_manifest.candidates + [
                ManifestSourceCandidate(
                    url="https://rust-lang.org/about",
                    candidate_excerpt="Rust about page",
                    source_type=SourceType.OFFICIAL_DOCUMENTATION,
                    query_id="q-001",
                )
            ]
        }
    )
    manifest_bytes = manifest_with_about.model_dump_json().encode("utf-8")

    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    raw_obs_bytes = obs_path.read_bytes()
    orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

    # Answer cites /learn (different path!)
    competitor_answer_text = orig_obs.raw_answer_text + "\n\nLearn Rust at https://rust-lang.org/learn."
    competitor_obs = orig_obs.model_copy(
        update={
            "raw_answer_text": competitor_answer_text,
            "raw_answer_sha256": hashlib.sha256(competitor_answer_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest_with_about,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    # Different path MUST be rejected (requires approval!)
    assert len(record.collection_candidates) == 1
    cand = record.collection_candidates[0]
    assert cand.cited_url == "https://rust-lang.org/learn"
    assert cand.requires_human_manifest_approval is True
    assert cand.matched_manifest_query_id is None


def test_same_url_different_query_rejected(sample_subject_profile: SubjectProfile) -> None:
    """Proves that a manifest candidate for https://rust-lang.org on query q-unrelated does NOT authorize https://rust-lang.org on query q-001."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    orig_manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)

    # Manifest candidate for query q-unrelated
    manifest_with_other_q = orig_manifest.model_copy(
        update={
            "candidates": orig_manifest.candidates + [
                ManifestSourceCandidate(
                    url="https://rust-lang.org",
                    candidate_excerpt="Rust official site",
                    source_type=SourceType.OFFICIAL_DOCUMENTATION,
                    query_id="q-unrelated-999",
                )
            ]
        }
    )
    manifest_bytes = manifest_with_other_q.model_dump_json().encode("utf-8")

    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    raw_obs_bytes = obs_path.read_bytes()
    orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

    # Answer for query q-001 cites https://rust-lang.org
    competitor_answer_text = orig_obs.raw_answer_text + "\n\nSee https://rust-lang.org."
    competitor_obs = orig_obs.model_copy(
        update={
            "raw_answer_text": competitor_answer_text,
            "raw_answer_sha256": hashlib.sha256(competitor_answer_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest_with_other_q,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    # Different query ID MUST be rejected (requires approval!)
    assert len(record.collection_candidates) == 1
    cand = record.collection_candidates[0]
    assert cand.cited_url == "https://rust-lang.org"
    assert cand.requires_human_manifest_approval is True
    assert cand.matched_manifest_query_id is None


def test_neutral_editorial_citation_classification(sample_subject_profile: SubjectProfile) -> None:
    """Proves that citing a neutral editorial URL yields THIRD_PARTY_ONLY_CITATIONS."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    raw_obs_bytes = obs_path.read_bytes()
    orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

    editorial_answer_text = orig_obs.raw_answer_text + "\n\nSee also https://en.wikipedia.org/wiki/Python."
    editorial_obs = orig_obs.model_copy(
        update={
            "raw_answer_text": editorial_answer_text,
            "raw_answer_sha256": hashlib.sha256(editorial_answer_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=editorial_obs,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    assert record.attribution_status == AttributionStatus.THIRD_PARTY_ONLY_CITATIONS


def test_client_ledger_evidence_is_not_mistaken_for_client_answer_citation(
    sample_subject_profile: SubjectProfile,
) -> None:
    """A client-owned source in the ledger cannot make a competitor-only answer look client-cited."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    original_observation = AnswerObservation.model_validate_json(obs_path.read_bytes())

    competitor_only_text = "See https://rust-lang.org/learn for the Rust reference."
    competitor_only_observation = original_observation.model_copy(
        update={
            "raw_answer_text": competitor_only_text,
            "raw_answer_sha256": hashlib.sha256(competitor_only_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")
    record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=competitor_only_observation,
        source_ledger=source_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=raw_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    assert record.attribution_status == AttributionStatus.CITED_COMPETITOR_OBSERVED
    assert record.competitor_patterns[0].client_domain_cited is False


def test_exact_url_verification_matching_not_domain_only(
    sample_subject_profile: SubjectProfile,
) -> None:
    """Proves that an observed URL (https://rust-lang.org/learn) is NOT treated as verified just because a different path (https://rust-lang.org/about) exists in the ledger."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    raw_manifest_bytes = manifest_path.read_bytes()
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
    raw_ledger_bytes = ledger_path.read_bytes()
    orig_ledger = AuditRun.model_validate_json(raw_ledger_bytes)

    # Add a ledger record for https://rust-lang.org/about (different path!)
    updated_ledger = orig_ledger.model_copy(
        update={
            "evidence_ledger": {
                **orig_ledger.evidence_ledger,
                "ev-rust-about": EvidenceRecord(
                    evidence_id="ev-rust-about",
                    url="https://rust-lang.org/about",
                    opened_excerpt="Rust is a language empowering everyone to build reliable and efficient software.",
                    verification_status=VerificationStatus.OPENED_VERIFIED,
                    source_type=SourceType.OFFICIAL_DOCUMENTATION,
                    is_independent=False,
                    retrieval_timestamp=datetime(2026, 8, 21, 0, 0, 0, tzinfo=timezone.utc),
                    verification_artifact=VerificationArtifact(
                        verifier_run_id="run-001",
                        verifier_method="DIRECT_HTTP_SNAPSHOT",
                        snapshot_sha256="a" * 64,
                        quote_exact_match=True,
                    ),
                ),
            }
        }
    )
    upd_ledger_bytes = updated_ledger.model_dump_json().encode("utf-8")

    raw_obs_bytes = obs_path.read_bytes()
    orig_obs = AnswerObservation.model_validate_json(raw_obs_bytes)

    # Answer cites https://rust-lang.org/learn (different path than /about!)
    competitor_answer_text = orig_obs.raw_answer_text + "\n\nLearn Rust at https://rust-lang.org/learn."
    competitor_obs = orig_obs.model_copy(
        update={
            "raw_answer_text": competitor_answer_text,
            "raw_answer_sha256": hashlib.sha256(competitor_answer_text.encode("utf-8")).hexdigest(),
        }
    )

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    record = ForensicGapAnalyzer.analyze_gaps(
        subject_profile=sample_subject_profile,
        observation=competitor_obs,
        source_ledger=updated_ledger,
        query_map=query_map,
        manifest=manifest,
        raw_qm_bytes=raw_qm_bytes,
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_bytes=upd_ledger_bytes,
        raw_profile_bytes=raw_profile_bytes,
    )

    # https://rust-lang.org/learn is NOT in ledger (only /about is), so it MUST emit a collection candidate!
    assert len(record.collection_candidates) == 1
    assert record.collection_candidates[0].cited_url == "https://rust-lang.org/learn"


def test_profile_sha256_digest_tamper_detection(sample_subject_profile: SubjectProfile) -> None:
    """Proves that profile_sha256 is bound and changing raw profile content invalidates verify_integrity()."""
    pattern = CompetitorCitationPattern(
        pattern_id="pat-01",
        target_query_id="q-001",
        total_sources_evaluated=1,
        top_cited_domains=[
            CompetitorCitation(
                domain="python.org",
                citation_count=1,
                source_type=SourceType.OFFICIAL_DOCUMENTATION,
                source_relationship=SourceRelationship.CLIENT_OWNED,
            )
        ],
        client_domain_cited=True,
        attribution_status=AttributionStatus.NO_ANSWER_CITATIONS_NOT_ASSESSABLE,
    )

    digest = ForensicGapAnalysisRecord.compute_canonical_digest(
        analysis_id="fga-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        profile_id="prof-001",
        profile_sha256="e" * 64,
        attribution_status=AttributionStatus.NO_ANSWER_CITATIONS_NOT_ASSESSABLE,
        competitor_patterns=[pattern],
        collection_candidates=[],
        collection_executions=[],
        collection_attempts=[],
        evidence_gaps=[],
        prioritized_actions=[],
    )

    record = ForensicGapAnalysisRecord(
        analysis_id="fga-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        profile_id="prof-001",
        profile_sha256="e" * 64,
        attribution_status=AttributionStatus.NO_ANSWER_CITATIONS_NOT_ASSESSABLE,
        competitor_patterns=[pattern],
        collection_candidates=[],
        evidence_gaps=[],
        prioritized_actions=[],
        canonical_digest=digest,
    )

    assert record.verify_integrity() is True

    # Test digest tampering with profile_sha256
    tampered_record = ForensicGapAnalysisRecord(
        analysis_id="fga-rec-001",
        observation_id="obs-001",
        raw_answer_sha256="a" * 64,
        source_ledger_run_id="run-001",
        source_ledger_sha256="b" * 64,
        query_map_sha256="c" * 64,
        manifest_sha256="d" * 64,
        profile_id="prof-001",
        profile_sha256="f" * 64,  # Altered profile SHA-256!
        attribution_status=AttributionStatus.NO_ANSWER_CITATIONS_NOT_ASSESSABLE,
        competitor_patterns=[pattern],
        collection_candidates=[],
        evidence_gaps=[],
        prioritized_actions=[],
        canonical_digest=digest,
    )
    assert tampered_record.verify_integrity() is False


def test_replayed_human_decision_context_mismatch_rejected(sample_subject_profile: SubjectProfile) -> None:
    """Proves that a human decision replayed from another context is rejected by 6-binding verification."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")

    raw_qm_bytes = qm_path.read_bytes()
    query_map = QueryMap.model_validate_json(raw_qm_bytes)
    qm_sha256 = "ce5d03d441eefcca1cb9cfefbeab1a6572eb0cae0e27fe8a32a67bc644b9cfcf"

    raw_manifest_bytes = manifest_path.read_bytes()
    manifest = DatasetManifest.model_validate_json(raw_manifest_bytes)
    manifest_sha256 = "71333fd91a3081676d1e43ee6df9fbbca7b0b691bf39ce8a6e87bc12d0909562"

    raw_ledger_bytes = ledger_path.read_bytes()
    source_ledger = AuditRun.model_validate_json(raw_ledger_bytes)
    ledger_sha256 = "1e5e4563feca841e065bc3bbcfd1cd195ecfb38bfb67fa9faac1a58eb87eb60c"

    raw_obs_bytes = obs_path.read_bytes()
    observation = AnswerObservation.model_validate_json(raw_obs_bytes)

    raw_profile_bytes = sample_subject_profile.model_dump_json().encode("utf-8")

    dec1 = HumanStatementDecision(
        decision_id="hdec-stmt-001",
        statement_id="stmt-001",
        decision_status=ReconciliationStatus.SUPPORTED,
        quoted_evidence=[
            QuotedEvidencePassage(
                evidence_id="ev-b6868a371278",
                evidence_url="https://peps.python.org/pep-0020/",
                snapshot_sha256="1e2b8d7404d38ac66e3f685c06490787fdd60391b79c338f20b390901aab899d",
                verifier_run_id="vrun-001",
                collection_execution_id="cer-001",
                quoted_passage="Readability counts.",
            )
        ],
        auditor_rationale="Verified readability quote.",
        declared_reviewer_identity="Lead Auditor",
        decision_timestamp=datetime(2026, 8, 21, 0, 0, 0, tzinfo=timezone.utc),
        reconciliation_method=ReconciliationMethod.HUMAN_AUDITOR_REVIEW,
    )

    replayed_hdec = HumanDecisionRecord(
        decision_record_id="hdec-rec-replayed",
        observation_id="obs-REPLAYED-OTHER-RUN",  # Mismatched observation ID!
        raw_answer_sha256=observation.raw_answer_sha256,
        source_ledger_run_id=source_ledger.run_id,
        source_ledger_sha256=ledger_sha256,
        query_map_sha256=qm_sha256,
        manifest_sha256=manifest_sha256,
        decisions=[dec1],
        canonical_digest="0" * 64,
    )

    with pytest.raises(ValueError, match="Context mismatch: HumanDecisionRecord observation_id"):
        ForensicGapAnalyzer.analyze_gaps(
            subject_profile=sample_subject_profile,
            observation=observation,
            source_ledger=source_ledger,
            query_map=query_map,
            manifest=manifest,
            raw_qm_bytes=raw_qm_bytes,
            raw_manifest_bytes=raw_manifest_bytes,
            raw_ledger_bytes=raw_ledger_bytes,
            raw_profile_bytes=raw_profile_bytes,
            human_decision=replayed_hdec,
        )


def test_no_orphan_action_plans_emitted(sample_subject_profile: SubjectProfile) -> None:
    """Proves that prioritized_actions ONLY contains actions with a valid gap_id present in evidence_gaps."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")
    profile_path = Path("data/fixtures/pep20_subject_profile.json")

    out_json = Path("data/fixtures/test_no_orphan.json")

    run_cli_analyze_gaps(
        query_map_path=qm_path,
        manifest_path=manifest_path,
        source_ledger_path=ledger_path,
        observation_path=obs_path,
        profile_path=profile_path,
        output_json_path=out_json,
    )

    record = ForensicGapAnalysisRecord.model_validate_json(out_json.read_bytes())
    gap_ids = {g.gap_id for g in record.evidence_gaps}

    for action in record.prioritized_actions:
        assert action.gap_id in gap_ids, f"Orphaned action found: {action.action_id} points to missing gap_id {action.gap_id}"

    if out_json.exists():
        out_json.unlink()


def test_cli_analyze_gaps_execution_with_profile(tmp_path: Path) -> None:
    """Tests full CLI analyze-gaps execution against live emitted PEP 20 dataset with SubjectProfile."""
    qm_path = Path("data/fixtures/sample_query_map.json")
    manifest_path = Path("data/fixtures/live_pep20_manifest.json")
    ledger_path = Path("data/fixtures/emitted_pep20_source_ledger.json")
    obs_path = Path("data/fixtures/emitted_pep20_observation.json")
    profile_path = Path("data/fixtures/pep20_subject_profile.json")
    hdec_path = Path("data/fixtures/emitted_pep20_human_decision.json")

    out_json = tmp_path / "gap_analysis.json"
    out_md = tmp_path / "gap_analysis.md"

    exit_code = run_cli_analyze_gaps(
        query_map_path=qm_path,
        manifest_path=manifest_path,
        source_ledger_path=ledger_path,
        observation_path=obs_path,
        profile_path=profile_path,
        human_decision_path=hdec_path,
        output_json_path=out_json,
        output_path=out_md,
    )

    assert exit_code == 0
    assert out_json.exists()
    assert out_md.exists()

    md_content = out_md.read_text(encoding="utf-8")
    assert "FORENSIC COMPETITOR EVIDENCE-GAP ANALYSIS RECORD" in md_content
    assert "Subject Profile SHA256" in md_content
    assert "Observed Citation Collection Candidates" in md_content
