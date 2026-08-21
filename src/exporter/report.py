"""
Auditable Report Exporter with Runtime Evidence Validation
"""

from typing import Dict, Any
from ..domain.models import AuditRun
from ..domain.validators import validate_audit_run_ledger


class ReportExporter:
    """
    Exports verified audit reports to Markdown format.
    Enforces strict runtime evidence ledger validation before rendering.
    """

    @classmethod
    def export_to_markdown(cls, audit_run: AuditRun) -> str:
        """
        Validates audit_run and renders a Markdown audit report.
        Raises EvidenceLedgerValidationError if any claim lacks verified evidence.
        """
        # Step 1: Enforce runtime evidence ledger validation
        validated_run = validate_audit_run_ledger(audit_run)

        # Step 2: Render Markdown Report
        lines = [
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
        ]

        for i, claim in enumerate(validated_run.claims, 1):
            conf = claim.confidence
            rating_badge = f"[{conf.rating.value.upper()}]" if conf else "[UNKNOWN]"
            score_str = f"{conf.score:.2f}" if conf else "0.0"

            lines.append(f"### Claim {i}: {claim.statement}")
            lines.append(f"- **Confidence**: **{rating_badge}** (Score: `{score_str}`)")
            lines.append(
                f"- **Verified Sources Count**: {conf.verified_sources_count if conf else 0}"
            )
            lines.append(
                f"- **Independent Sources**: {conf.independent_sources_count if conf else 0}"
            )

            if claim.uncertainty_notes:
                lines.append(f"- **Uncertainty Notes**: {claim.uncertainty_notes}")

            lines.append("")
            lines.append("#### Linked Evidence Records:")
            for eid in claim.evidence_ids:
                evidence = validated_run.evidence_ledger[eid]
                indep_label = "Independent" if evidence.is_independent else "Non-Independent"
                lines.append(
                    f"1. **[{evidence.source_type.value}]** [{evidence.url}]({evidence.url}) "
                    f"({indep_label}, Status: `{evidence.verification_status.value}`)\n"
                    f"   > *\"{evidence.opened_excerpt}\"*"
                )

            if claim.counter_evidence_ids:
                lines.append("")
                lines.append("#### Counter-Evidence Records:")
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
