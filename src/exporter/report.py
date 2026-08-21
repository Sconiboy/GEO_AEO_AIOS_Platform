"""
Auditable Report, Source Ledger, and Observation Record Exporter
"""

from typing import List
from ..domain.enums import VerificationStatus
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
        """
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

        lines: List[str] = [
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
        ]

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
