"""
Auditable Report and Source Ledger Exporter
"""

from typing import List
from ..domain.enums import VerificationStatus
from ..domain.models import AuditRun
from ..domain.validators import validate_audit_run_ledger


class ReportExporter:
    """
    Exports verified audit reports and controlled source ledgers to Markdown format.
    """

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
