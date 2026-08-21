"""
Auditable Report, Source Ledger, and Observation Record Exporter
"""

from typing import List
from ..domain.enums import VerificationStatus, CaptureMethod
from ..domain.gap_analysis import ForensicGapAnalysisRecord
from ..domain.human_decision import HumanDecisionRecord
from ..domain.models import AuditRun
from ..domain.observation import AnswerObservation
from ..domain.query_map import QueryMap
from ..domain.reconciliation import ObservationReconciliation
from ..domain.validators import validate_audit_run_ledger


class ReportExporter:
    """
    Exports verified audit reports, controlled source ledgers, answer observations,
    and claim reconciliation records to Markdown.
    """

    @classmethod
    def export_reconciliation_record(
        cls,
        reconciliation: ObservationReconciliation,
        observation: AnswerObservation,
        query_map: QueryMap,
        source_ledger: AuditRun,
    ) -> str:
        """
        Renders a Claim Reconciliation Record Markdown document.
        Displays semantic evaluations (supported, unsupported, contradicted, not_assessable)
        against frozen source evidence. Does NOT output commercial rank/visibility claims.
        Fails closed if observation or reconciliation fails SHA-256 integrity verification.
        """
        if not observation.verify_integrity():
            raise ValueError(
                f"Integrity failure: observation raw_answer_sha256 ('{observation.raw_answer_sha256}') does not match raw_answer_text digest."
            )

        if not reconciliation.verify_integrity():
            raise ValueError(
                f"Integrity failure: reconciliation_sha256 digest ('{reconciliation.reconciliation_sha256}') does not match canonical calculation over metadata and decisions."
            )

        query_text = "Unknown Query"
        for q in query_map.queries:
            if q.query_id == observation.query_id:
                query_text = q.text
                break

        lines: List[str] = [
            "> [!NOTE]",
            "> **CLAIM RECONCILIATION RECORD**",
            "> Semantic truth evaluation of raw model statement proposals against frozen source evidence.",
            "> Contains no commercial visibility scores, rank recommendations, or client audit claims.",
            "",
            f"# ⚖️ Claim Reconciliation Record",
            f"**Subject Entity**: `{query_map.entity_name}`  ",
            f"**Target Query**: *\"{query_text}\"* (`{observation.query_id}`)  ",
            f"**Model Provider / Identifier**: `{observation.provider_name}` (`{observation.model_identifier}`)  ",
            f"**Raw Answer Digest**: `{observation.raw_answer_sha256[:16]}...`  ",
            f"**Source Ledger Run ID**: `{source_ledger.run_id}`  ",
            f"**Reconciliation Run ID**: `{reconciliation.reconciliation_run_id}`  ",
            f"**Reconciliation Digest**: `{reconciliation.reconciliation_sha256[:16]}...`",
            "",
            "---",
            "",
            "## 📝 Evaluated Raw Model Answer",
            "```text",
            observation.raw_answer_text,
            "```",
            "",
            "---",
            "",
            "## 🎯 Statement Reconciliation Decisions",
            "",
        ]

        if not reconciliation.reconciliations:
            lines.append("*No statement reconciliation decisions present in this record.*")
        else:
            lines.append(
                "| Statement ID | Extracted Statement | Decision | Evaluated Evidence | Semantic Rationale |"
            )
            lines.append("|---|---|---|---|---|")

            # Build map of statement text from observation
            stmt_text_map = {
                s.statement_id: s.text for s in observation.extracted_statements
            }

            for rec in reconciliation.reconciliations:
                text = stmt_text_map.get(rec.statement_id, "Unknown Statement")
                ev_str = (
                    ", ".join([f"`{eid}`" for eid in rec.evaluated_evidence_ids])
                    if rec.evaluated_evidence_ids
                    else "*None (No relevant evidence)*"
                )
                badge = f"**`[{rec.status.value.upper()}]`**"
                lines.append(
                    f"| `{rec.statement_id}` | \"{text}\" | {badge} | {ev_str} | {rec.semantic_rationale} |"
                )

        lines.append("")
        lines.append("---")
        return "\n".join(lines)

    @classmethod
    def export_human_decision_record(
        cls,
        decision_record: HumanDecisionRecord,
        observation: AnswerObservation,
        query_map: QueryMap,
        source_ledger: AuditRun,
    ) -> str:
        """
        Renders a Human Semantic Decision Record Markdown document.
        Displays human auditor governance decisions, cited verbatim evidence passages,
        and content-addressed context bindings.
        Fails closed if decision_record or observation fails SHA-256 integrity verification.
        """
        if not observation.verify_integrity():
            raise ValueError(
                f"Integrity failure: observation raw_answer_sha256 ('{observation.raw_answer_sha256}') does not match raw_answer_text digest."
            )

        if not decision_record.verify_integrity():
            raise ValueError(
                f"Integrity failure: HumanDecisionRecord canonical_digest ('{decision_record.canonical_digest}') does not match calculated digest."
            )

        query_text = "Unknown Query"
        for q in query_map.queries:
            if q.query_id == observation.query_id:
                query_text = q.text
                break

        lines: List[str] = [
            "> [!IMPORTANT]",
            "> **HUMAN SEMANTIC DECISION RECORD**",
            "> Formal human auditor governance adjudication transitioning statement proposals to verified semantic status.",
            "> Contains content-addressed artifact bindings, auditor identity, and quoted evidence passages.",
            "",
            f"# 🏛️ Human Semantic Decision Record",
            f"**Subject Entity**: `{query_map.entity_name}`  ",
            f"**Target Query**: *\"{query_text}\"* (`{observation.query_id}`)  ",
            f"**Model Provider / Identifier**: `{observation.provider_name}` (`{observation.model_identifier}`)  ",
            f"**Decision Record ID**: `{decision_record.decision_record_id}`  ",
            f"**Canonical Decision Digest**: `{decision_record.canonical_digest[:16]}...`",
            "",
            "---",
            "",
            "## 🔒 Content-Addressed Artifact Bindings",
            f"- **Observation ID**: `{decision_record.observation_id}` (Raw Answer SHA256: `{decision_record.raw_answer_sha256[:16]}...`)",
            f"- **Source Ledger Run ID**: `{decision_record.source_ledger_run_id}` (Raw Ledger SHA256: `{decision_record.source_ledger_sha256[:16]}...`)",
            f"- **QueryMap SHA256**: `{decision_record.query_map_sha256[:16]}...`",
            f"- **Dataset Manifest SHA256**: `{decision_record.manifest_sha256[:16]}...`",
            "",
            "---",
            "",
            "## 📝 Evaluated Model Response Text",
            "```text",
            observation.raw_answer_text,
            "```",
            "",
            "---",
            "",
            "## 🎯 Human Auditor Adjudication Decisions",
            "",
        ]

        stmt_map = {s.statement_id: s.text for s in observation.extracted_statements}

        for dec in decision_record.decisions:
            stmt_text = stmt_map.get(dec.statement_id, "Unknown Statement")
            badge = f"**`[{dec.decision_status.value.upper()}]`**"

            lines.append(f"### Statement `{dec.statement_id}`: \"{stmt_text}\"")
            lines.append(f"- **Final Adjudicated Decision**: {badge}")
            lines.append(f"- **Declared Reviewer Identity**: `{dec.declared_reviewer_identity}`")
            lines.append(f"- **Adjudication Timestamp**: `{dec.decision_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
            lines.append(f"- **Reconciliation Method**: `{dec.reconciliation_method.value}`")
            lines.append(f"- **Auditor Technical Rationale**: {dec.auditor_rationale}")
            lines.append(f"- **Verified Quoted Evidence Passages**:")
            for qe in dec.quoted_evidence:
                snap_str = f" (Snapshot: `{qe.snapshot_sha256[:12]}...`)" if qe.snapshot_sha256 else ""
                lines.append(f"  - **Evidence ID**: `{qe.evidence_id}`{snap_str}")
                lines.append(f"    > *\"{qe.quoted_passage}\"*")
            lines.append("")

        lines.append("---")
        return "\n".join(lines)

    @classmethod
    def export_gap_analysis_record(
        cls,
        gap_record: ForensicGapAnalysisRecord,
        observation: AnswerObservation,
        query_map: QueryMap,
        source_ledger: AuditRun,
    ) -> str:
        """
        Renders a Forensic Competitor Evidence-Gap Analysis Record Markdown document.
        Displays competitor citation patterns, identified client evidence gaps,
        finding bases, and evidence-backed action hypotheses.
        Fails closed if gap_record or observation fails SHA-256 integrity verification.
        """
        if not observation.verify_integrity():
            raise ValueError(
                f"Integrity failure: observation raw_answer_sha256 ('{observation.raw_answer_sha256}') does not match raw_answer_text digest."
            )

        if not gap_record.verify_integrity():
            raise ValueError(
                f"Integrity failure: ForensicGapAnalysisRecord canonical_digest ('{gap_record.canonical_digest}') does not match calculated digest."
            )

        query_text = "Unknown Query"
        for q in query_map.queries:
            if q.query_id == observation.query_id:
                query_text = q.text
                break

        lines: List[str] = []

        if observation.capture_method == CaptureMethod.SYNTHETIC_FIXTURE_IMPORT:
            lines.extend([
                "> [!WARNING]",
                "> **SYNTHETIC FIXTURE OBSERVATION - NOT AN AUTHENTIC MODEL CAPTURE**",
                "> This observation text was imported from a synthetic test fixture and does not represent an authentic live model response.",
                "",
            ])

        lines.extend([
            "> [!NOTE]",
            "> **FORENSIC COMPETITOR EVIDENCE-GAP ANALYSIS RECORD**",
            "> Identifies model citation patterns, client evidence gaps, and confidence-bounded ethical priority action hypotheses.",
            "> All action recommendations create genuine, verifiable public evidence. Non-manipulative.",
            "",
            f"# 🎯 Forensic Competitor Evidence-Gap Analysis",
            f"**Subject Entity**: `{query_map.entity_name}`  ",
            f"**Target Query**: *\"{query_text}\"* (`{observation.query_id}`)  ",
            f"**Model Provider / Identifier**: `{observation.provider_name}` (`{observation.model_identifier}`)  ",
            f"**Subject Profile ID**: `{gap_record.profile_id}`  ",
            f"**Analysis Record ID**: `{gap_record.analysis_id}`  ",
            f"**Canonical Analysis Digest**: `{gap_record.canonical_digest[:16]}...`",
            "",
            "---",
            "",
            "## 🔒 Content-Addressed Artifact Bindings",
            f"- **Observation ID**: `{gap_record.observation_id}` (Raw Answer SHA256: `{gap_record.raw_answer_sha256[:16]}...`)",
            f"- **Source Ledger Run ID**: `{gap_record.source_ledger_run_id}` (Raw Ledger SHA256: `{gap_record.source_ledger_sha256[:16]}...`)",
            f"- **QueryMap SHA256**: `{gap_record.query_map_sha256[:16]}...`",
            f"- **Dataset Manifest SHA256**: `{gap_record.manifest_sha256[:16]}...`",
            f"- **Subject Profile SHA256**: `{gap_record.profile_sha256[:16]}...`",
            f"- **Competitor Attribution Status**: `{gap_record.attribution_status.value}`",
            "",
            "---",
            "",
            "## 📊 Competitor & Domain Citation Distribution",
            "",
        ])

        for pat in gap_record.competitor_patterns:
            cited_str = "Yes" if pat.client_domain_cited else "No (Client Evidence Gap)"
            lines.append(f"- **Total Sources Evaluated**: {pat.total_sources_evaluated}")
            lines.append(f"- **Client Domain Cited**: `{cited_str}`")
            lines.append("- **Top Cited Domains**:")
            for cit in pat.top_cited_domains:
                lines.append(
                    f"  - `{cit.domain}`: {cit.citation_count} citation(s) "
                    f"(`{cit.source_type.value}`, Relationship: `{cit.source_relationship.value}`)"
                )
            lines.append("")

            if pat.answer_citations:
                lines.append("- **Actual Raw Model Answer Citations**:")
                for ac in pat.answer_citations:
                    comp_info = f" (Competitor Entity: `{ac.matched_competitor_entity}`)" if ac.matched_competitor_entity else ""
                    lines.append(
                        f"  - [{ac.url}]({ac.url}) (`{ac.domain}`, Relationship: `{ac.source_relationship.value}`{comp_info})"
                    )
                lines.append("")
            else:
                lines.append("- **Actual Raw Model Answer Citations**: *None (No explicit URLs in model response)*")
                lines.append("")

        lines.extend([
            "---",
            "",
            "## 📥 Observed Citation Collection Candidates (Human Manifest Authorization Required)",
            "",
        ])

        if not gap_record.collection_candidates:
            lines.append("*No uncollected answer-surface citations observed.*")
            lines.append("")
        else:
            for cc in gap_record.collection_candidates:
                approval_badge = (
                    "**`[REQUIRES HUMAN MANIFEST APPROVAL]`**"
                    if cc.requires_human_manifest_approval
                    else "**`[AUTHORIZED IN MANIFEST]`**"
                )
                comp_entity = f" (Entity: `{cc.matched_competitor_entity}`)" if cc.matched_competitor_entity else ""
                lines.append(f"### Candidate `{cc.candidate_id}`: [{cc.cited_url}]({cc.cited_url}) {approval_badge}")
                lines.append(f"- **Target Query**: `{cc.target_query_id}`")
                lines.append(f"- **Domain**: `{cc.cited_domain}`")
                lines.append(f"- **Source Relationship**: `{cc.source_relationship.value}`{comp_entity}")
                lines.append(f"- **Manifest Approval Required**: `{cc.requires_human_manifest_approval}`")
                if cc.matched_manifest_query_id:
                    lines.append(f"- **Matched Manifest Query ID**: `{cc.matched_manifest_query_id}`")
                lines.append(f"- **Action Hypothesis**: {cc.action_hypothesis}")
                lines.append("")

        if gap_record.collection_executions:
            lines.extend([
                "---",
                "",
                "## 📜 Executed Candidate Collections (Provenance Tracing)",
                "",
            ])
            for ce in gap_record.collection_executions:
                snap_fmt = f"`{ce.snapshot_sha256[:16]}...`"
                dig_fmt = f"`{ce.canonical_digest[:16]}...`"
                lines.append(f"### Execution `{ce.execution_id}` (Candidate: `{ce.candidate_id}`)")
                lines.append(f"- **Target Query**: `{ce.target_query_id}`")
                lines.append(f"- **Collected URL**: [{ce.cited_url}]({ce.cited_url})")
                lines.append(f"- **Bound Observation ID**: `{ce.observation_id}`")
                lines.append(f"- **Evidence Record ID**: `{ce.evidence_id}`")
                lines.append(f"- **Verifier Run ID**: `{ce.verifier_run_id}`")
                lines.append(f"- **Snapshot Hash**: {snap_fmt}")
                lines.append(f"- **Execution Timestamp**: `{ce.execution_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
                lines.append(f"- **Canonical Digest**: {dig_fmt}")
                lines.append("")

        if gap_record.collection_attempts:
            lines.extend([
                "---",
                "",
                "## 🚫 Failed Candidate Collection Attempts",
                "",
            ])
            for ca in gap_record.collection_attempts:
                cat_str = f" ({ca.failure_category.value})" if ca.failure_category else ""
                reason_str = f" Reason: *\"{ca.failure_reason}\"*" if ca.failure_reason else ""
                dig_fmt = f"`{ca.canonical_digest[:16]}...`"
                lines.append(f"### Attempt `{ca.attempt_id}` (Candidate: `{ca.candidate_id}`)")
                lines.append(f"- **Target Query**: `{ca.target_query_id}`")
                lines.append(f"- **Target URL**: [{ca.cited_url}]({ca.cited_url})")
                lines.append(f"- **Bound Observation ID**: `{ca.observation_id}`")
                lines.append(f"- **Evidence Record ID**: `{ca.evidence_id}`")
                lines.append(f"- **Verification Status**: `{ca.verification_status.value}`{cat_str}")
                if reason_str:
                    lines.append(f"- **Failure Details**:{reason_str}")
                lines.append(f"- **Attempt Timestamp**: `{ca.attempt_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
                lines.append(f"- **Canonical Digest**: {dig_fmt}")
                lines.append("")

        lines.extend([
            "---",
            "",
            "## 🚨 Identified Client Evidence Gaps",
            "",
        ])

        if not gap_record.evidence_gaps:
            lines.append("*No client evidence gaps identified for this observation. Statement proposals supported by evidence or human decision.*")
            lines.append("")
        else:
            for gap in gap_record.evidence_gaps:
                badge = f"**`[{gap.severity.value.upper()}]`**"
                stmts_str = ", ".join([f"`{sid}`" for sid in gap.affected_statement_ids])
                fb = gap.finding_basis
                ev_str = ", ".join([f"`{eid}`" for eid in fb.evidence_ids]) if fb.evidence_ids else "*None*"
                rel_str = ", ".join([f"`{r.value}`" for r in fb.source_relationships]) if fb.source_relationships else "*None*"

                lines.append(f"### Gap `{gap.gap_id}`: {gap.gap_category.value} {badge}")
                lines.append(f"- **Target Query**: `{gap.target_query_id}`")
                lines.append(f"- **Affected Statement Proposals**: {stmts_str}")
                lines.append(f"- **Description**: {gap.description}")
                lines.append(f"- **Finding Basis Trace**:")
                lines.append(f"  - **Bound Observation**: `{fb.observation_id}`")
                lines.append(f"  - **Bound Statement**: `{fb.statement_id}`")
                lines.append(f"  - **Bound Evidence IDs**: {ev_str}")
                lines.append(f"  - **Observed Source Relationships**: {rel_str}")
                lines.append("")

        lines.extend([
            "---",
            "",
            "## ⚡ Prioritized Ethical Action Plan (Hypotheses for Review)",
            "",
        ])

        if not gap_record.prioritized_actions:
            lines.append("*No priority actions required. Client evidence status complete.*")
            lines.append("")
        else:
            for act in gap_record.prioritized_actions:
                score_fmt = f"{act.confidence_score:.2f}"
                fb = act.finding_basis
                ev_str = ", ".join([f"`{eid}`" for eid in fb.evidence_ids]) if fb.evidence_ids else "*None*"

                lines.append(f"### Action Hypothesis `{act.action_id}` (Bound Gap: `{act.gap_id}`)")
                lines.append(f"- **Recommended Action**: **{act.recommended_action}**")
                lines.append(f"- **Target Publishing Domain**: `{act.target_domain}`")
                lines.append(f"- **Suggested Source Type**: `{act.suggested_source_type.value}`")
                lines.append(f"- **Expected Evidence Impact**: {act.expected_evidence_impact}")
                lines.append(f"- **Confidence Rating**: `{score_fmt}` (*{act.confidence_explanation}*)")
                lines.append(f"- **Finding Basis Evidence**: {ev_str}")
                lines.append(f"- **Ethical Boundary Notes**: *\"{act.ethical_boundary_notes}\"*")
                lines.append("")

        lines.append("---")
        return "\n".join(lines)

    @classmethod
    def export_observation_record(
        cls, observation: AnswerObservation, query_map: QueryMap
    ) -> str:
        """
        Renders an Answer-Surface Observation Record Markdown document.
        Does NOT output visibility scores, commercial recommendation shares, or rank claims.
        """
        if not observation.verify_integrity():
            raise ValueError(
                f"Integrity failure: observation raw_answer_sha256 ('{observation.raw_answer_sha256}') does not match raw_answer_text digest."
            )

        query_text = "Unknown Query"
        for q in query_map.queries:
            if q.query_id == observation.query_id:
                query_text = q.text
                break

        locale_str = observation.locale if observation.locale else "Unknown"
        region_str = observation.region if observation.region else "Unknown"

        lines: List[str] = []

        if observation.capture_method == CaptureMethod.SYNTHETIC_FIXTURE_IMPORT:
            lines.extend([
                "> [!WARNING]",
                "> **SYNTHETIC FIXTURE OBSERVATION - NOT AN AUTHENTIC MODEL CAPTURE**",
                "> This observation text was imported from a synthetic test fixture and does not represent an authentic live model response.",
                "",
            ])

        lines.extend([
            "> [!NOTE]",
            "> **MANUAL ANSWER-SURFACE OBSERVATION RECORD**",
            "> Factual record of raw model response capture. Contains no commercial visibility scores or audit claims.",
            "",
            f"# 🔬 Answer-Surface Observation Record",
            f"**Subject Entity**: `{query_map.entity_name}`  ",
            f"**Target Query**: *\"{query_text}\"* (`{observation.query_id}`)  ",
            f"**Model Provider**: `{observation.provider_name}`  ",
            f"**Model Identifier**: `{observation.model_identifier}`  ",
            f"**Capture Method**: `{observation.capture_method.value}`  ",
            f"**Capture Timestamp**: `{observation.capture_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`  ",
            f"**Locale / Region**: `{locale_str}` / `{region_str}`  ",
            f"**Raw Answer Digest**: `{observation.raw_answer_sha256[:16]}...`",
            "",
            "---",
            "",
            "## 📝 Unmodified Raw Model Answer",
            "```text",
            observation.raw_answer_text,
            "```",
            "",
            "---",
            "",
            "## 🧪 Extracted Statement Proposals",
            "",
        ])

        if not observation.extracted_statements:
            lines.append("*No extracted statements proposed for this observation.*")
        else:
            lines.append("| Statement ID | Extracted Statement | Status | Linked Evidence |")
            lines.append("|---|---|---|---|")
            for stmt in observation.extracted_statements:
                ev_link = f"`{stmt.linked_evidence_id}`" if stmt.linked_evidence_id else "*None*"
                lines.append(
                    f"| `{stmt.statement_id}` | \"{stmt.text}\" | `{stmt.extraction_status.value}` | {ev_link} |"
                )

        lines.append("")
        lines.append("---")
        return "\n".join(lines)

    @classmethod
    def export_source_ledger(cls, audit_run: AuditRun) -> str:
        """
        Renders a Controlled Source Ledger Markdown document.
        Does NOT use commercial client-audit wording ('Client Domain', 'Claims', or 'Confidence Ranks').
        Exposes verified public sources, snapshot hashes, and policy-filtered exclusions.
        """
        lines: List[str] = [
            "> [!NOTE]",
            "> **CONTROLLED NON-CLIENT DATASET SPIKE**",
            "> This source ledger documents public test evidence and policy verification results.",
            "",
            f"# 📜 Controlled Source Ledger",
            f"**Subject Entity**: `{audit_run.client_domain}`  ",
            f"**Category**: `{audit_run.category}`  ",
            f"**Run ID**: `{audit_run.run_id}`  ",
            f"**Generated**: `{audit_run.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`",
            "",
            "---",
            "",
            "## 🔍 Verified Public Sources",
            "",
        ]

        verified_records = [
            ev
            for ev in audit_run.evidence_ledger.values()
            if ev.verification_status == VerificationStatus.OPENED_VERIFIED
        ]

        if not verified_records:
            lines.append("*No OPENED_VERIFIED source records found in this run.*")
        else:
            for i, ev in enumerate(verified_records, 1):
                indep_label = "Independent" if ev.is_independent else "Non-Independent"
                art = ev.verification_artifact
                art_hash = f"`{art.snapshot_sha256[:16]}...`" if art else "`N/A`"
                method = art.verifier_method if art else "N/A"

                lines.append(f"### Source {i}: [{ev.url}]({ev.url})")
                lines.append(f"- **Type**: `{ev.source_type.value}` ({indep_label})")
                lines.append(f"- **Status**: `{ev.verification_status.value}`")
                lines.append(f"- **Snapshot Hash**: {art_hash}")
                lines.append(f"- **Verifier Method**: `{method}`")
                lines.append(f"- **Excerpt**: *\"{ev.opened_excerpt}\"*")
                lines.append("")

        excluded_records = [
            ev
            for ev in audit_run.evidence_ledger.values()
            if ev.verification_status != VerificationStatus.OPENED_VERIFIED
        ]

        if excluded_records:
            lines.extend([
                "---",
                "",
                "## 🚫 Policy-Filtered / Excluded Candidates",
                "",
            ])
            for i, ev in enumerate(excluded_records, 1):
                cat = ev.failure_category.value if ev.failure_category else "excluded"
                reason = ev.failure_reason or "Source failed policy checks."
                lines.append(f"{i}. **[{cat}]** [{ev.url}]({ev.url})")
                lines.append(f"   > *Reason: {reason}*")
                lines.append("")

        lines.append("---")
        return "\n".join(lines)

    @classmethod
    def export_to_markdown(cls, audit_run: AuditRun) -> str:
        """
        Validates audit_run and renders a Markdown audit report.
        Raises EvidenceLedgerValidationError if any claim fails evidence validation.
        """
        # Step 1: Enforce runtime evidence ledger validation
        validated_run = validate_audit_run_ledger(audit_run)

        # Step 2: Render Markdown Report
        lines: List[str] = []

        if validated_run.is_synthetic_fixture:
            lines.extend([
                "> [!WARNING]",
                "> **SYNTHETIC FIXTURE DATA - NOT A REAL CLIENT AUDIT**",
                "> This report was generated from internal synthetic test data for pipeline verification.",
                "",
            ])

        lines.extend([
            f"# 📊 GEO/AEO Evidence-Governed Audit Report",
            f"**Client Domain**: `{validated_run.client_domain}`  ",
            f"**Category**: `{validated_run.category}`  ",
            f"**Run ID**: `{validated_run.run_id}`  ",
            f"**Generated**: `{validated_run.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`",
            "",
            "---",
            "",
            "## 🎯 Audit Findings & Claims",
            "",
        ])

        for i, claim in enumerate(validated_run.claims, 1):
            conf = claim.confidence
            rating_badge = f"[{conf.rating.value.upper()}]" if conf else "[UNKNOWN]"
            score_str = f"{conf.score:.2f}" if conf else "0.0"

            lines.append(f"### Claim {i}: {claim.statement}")
            lines.append(f"- **Confidence**: **{rating_badge}** (Score: `{score_str}`, Formula: `{conf.formula_version if conf else 'N/A'}`)")
            lines.append(
                f"- **Verified Sources Count**: {conf.verified_sources_count if conf else 0}"
            )
            lines.append(
                f"- **Independent Sources**: {conf.independent_sources_count if conf else 0}"
            )

            if conf and conf.input_breakdown:
                lines.append(f"- **Score Factor Breakdown**:")
                for k, v in conf.input_breakdown.items():
                    lines.append(f"  - `{k}`: {v}")

            if claim.uncertainty_notes:
                lines.append(f"- **Uncertainty Notes**: {claim.uncertainty_notes}")

            lines.append("")
            lines.append("#### Verified Supporting Evidence Records:")
            for eid in claim.evidence_ids:
                evidence = validated_run.evidence_ledger[eid]
                indep_label = "Independent" if evidence.is_independent else "Non-Independent"
                art = evidence.verification_artifact
                art_info = f" (Snapshot Hash: `{art.snapshot_sha256[:12]}...`, Verifier: `{art.verifier_method}`)" if art else ""

                lines.append(
                    f"1. **[{evidence.source_type.value}]** [{evidence.url}]({evidence.url}) "
                    f"({indep_label}, Status: `{evidence.verification_status.value}`){art_info}\n"
                    f"   > *\"{evidence.opened_excerpt}\"*"
                )

            if claim.counter_evidence_ids:
                lines.append("")
                lines.append("#### Verified Counter-Evidence Records:")
                for ceid in claim.counter_evidence_ids:
                    ce = validated_run.evidence_ledger[ceid]
                    lines.append(
                        f"1. **[COUNTER]** [{ce.url}]({ce.url})\n"
                        f"   > *\"{ce.opened_excerpt}\"*"
                    )

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)
