"""Human-readable report generation utilities."""

from __future__ import annotations

from typing import Mapping, Sequence

from DomainDetermine.auditor.models import AuditFinding, AuditMetric, AuditRunConfig


def build_report(
    *,
    config: AuditRunConfig,
    metrics: Sequence[AuditMetric],
    findings: Sequence[AuditFinding],
    drift_summary: Mapping[str, object],
    asset_paths: Sequence[str],
) -> Mapping[str, object]:
    """Return a structured report that can be rendered to HTML/PDF."""

    executive = _build_executive_summary(metrics)
    methodology = {
        "plan_version": config.plan_version,
        "kos_snapshot_id": config.kos_snapshot_id,
        "policy_pack_version": config.policy_pack_version,
        "allocation_method": "see_coverage_plan",
    }
    findings_section = {
        "total_findings": len(findings),
        "blocking_failures": [
            _serialize_finding(f)
            for f in findings
            if f.gate_level.value == "blocking" and f.status != "pass"
        ],
        "advisories": [
            _serialize_finding(f) for f in findings if f.gate_level.value == "advisory"
        ],
    }
    appendices = {
        "drift_summary": drift_summary,
        "linked_assets": list(asset_paths),
    }
    return {
        "executive_summary": executive,
        "methodology": methodology,
        "findings": findings_section,
        "appendices": appendices,
    }


def _build_executive_summary(metrics: Sequence[AuditMetric]) -> Mapping[str, object]:
    grouped: dict[str, list[AuditMetric]] = {"blocking": [], "advisory": []}
    for metric in metrics:
        grouped[metric.gate_level.value].append(metric)
    return {
        "blocking": [
            {"name": metric.name, "status": metric.status.value, "value": metric.value}
            for metric in grouped["blocking"]
        ],
        "advisory": [
            {"name": metric.name, "status": metric.status.value, "value": metric.value}
            for metric in grouped["advisory"]
        ],
    }


def _serialize_finding(finding: AuditFinding) -> Mapping[str, object]:
    return {
        "concept_id": finding.concept_id,
        "status": finding.status.value,
        "gate_level": finding.gate_level.value,
        "reasons": list(finding.reasons),
    }


__all__ = ["build_report"]
