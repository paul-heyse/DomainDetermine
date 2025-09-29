"""Policy compliance and drift analysis utilities."""

from __future__ import annotations

from typing import Mapping, Optional

from DomainDetermine.auditor.models import (
    AuditFinding,
    AuditMetric,
    GateLevel,
    MetricStatus,
    PolicyPack,
)
from DomainDetermine.auditor.utils import to_records


def evaluate_policy_compliance(
    plan,
    *,
    policy_pack: PolicyPack,
    locale_column: str,
) -> tuple[list[AuditFinding], list[AuditMetric]]:
    """Apply policy pack rules to the coverage plan."""

    findings: list[AuditFinding] = []
    metrics: list[AuditMetric] = []
    forbidden = set(policy_pack.forbidden_concepts)
    for record in to_records(plan):
        reasons: list[str] = []
        concept_id = str(record.get("concept_id"))
        if concept_id in forbidden:
            reasons.append("FORBIDDEN_CONCEPT")
        jurisdiction_values = policy_pack.jurisdiction_rules.get(concept_id)
        locale_value = record.get(locale_column)
        if jurisdiction_values and locale_value not in jurisdiction_values:
            reasons.append("JURISDICTION_MISMATCH")
        if reasons:
            findings.append(
                AuditFinding(
                    concept_id=concept_id,
                    status=MetricStatus.FAIL,
                    reasons=tuple(reasons),
                    gate_level=GateLevel.BLOCKING,
                )
            )
    metrics.append(
        _build_simple_metric(
            name="forbidden_concept_count",
            value=float(sum(1 for f in findings if "FORBIDDEN_CONCEPT" in f.reasons)),
            gate_level=GateLevel.BLOCKING,
            rationale="Forbidden concepts present",
        )
    )
    return findings, metrics


def verify_licensing(plan, *, policy_pack: PolicyPack) -> AuditMetric:
    """Validate licensing restrictions for audit outputs."""

    restricted_sources = [
        source for source, fields in policy_pack.licensing_restrictions.items() if fields
    ]
    status = MetricStatus.PASS if not restricted_sources else MetricStatus.WARN
    rationale = "Restricted sources require redaction" if restricted_sources else "No restrictions"
    return AuditMetric(
        name="licensing_restrictions",
        value=float(len(restricted_sources)),
        threshold=0.0,
        comparator="<=",
        status=status,
        gate_level=GateLevel.ADVISORY,
        rationale=rationale,
        owner="legal",
    )


def verify_pii_flags(plan, *, policy_pack: PolicyPack) -> AuditMetric:
    """Ensure PII/PHI slices have required redaction flags."""

    required_flags = set(policy_pack.pii_required_flags)
    missing_rows = 0
    if required_flags:
        for record in to_records(plan):
            flags = set(record.get("policy_flags", []) or [])
            if flags.intersection(required_flags):
                if "redacted" not in flags:
                    missing_rows += 1
    status = MetricStatus.PASS if missing_rows == 0 else MetricStatus.WARN
    return AuditMetric(
        name="pii_redaction_compliance",
        value=float(missing_rows),
        threshold=0.0,
        comparator="<=",
        status=status,
        gate_level=GateLevel.ADVISORY,
        rationale="Ensure redaction for sensitive slices",
        owner="trust-safety",
    )


def analyze_drift(
    current_plan,
    baseline_plan: Optional[object],
    *,
    quota_column: str,
) -> Mapping[str, object]:
    """Compare the current plan against a baseline and summarise differences."""

    current_records = to_records(current_plan)
    baseline_records = to_records(baseline_plan) if baseline_plan is not None else []
    if not baseline_records:
        return {"status": "no_baseline", "added": [], "removed": [], "quota_delta": {}}
    current_ids = {str(record.get("concept_id")) for record in current_records}
    baseline_ids = {str(record.get("concept_id")) for record in baseline_records}
    added = sorted(current_ids - baseline_ids)
    removed = sorted(baseline_ids - current_ids)
    baseline_map = {
        str(record.get("concept_id")): float(record.get(quota_column, 0) or 0)
        for record in baseline_records
    }
    quota_delta: dict[str, float] = {}
    for record in current_records:
        concept_id = str(record.get("concept_id"))
        current_quota = float(record.get(quota_column, 0) or 0)
        delta = current_quota - baseline_map.get(concept_id, 0.0)
        if delta:
            quota_delta[concept_id] = delta
    return {
        "status": "baseline_compared",
        "added": added,
        "removed": removed,
        "quota_delta": quota_delta,
    }


def _build_simple_metric(
    *,
    name: str,
    value: float,
    gate_level: GateLevel,
    rationale: str,
) -> AuditMetric:
    status = MetricStatus.PASS if value == 0 else MetricStatus.FAIL
    return AuditMetric(
        name=name,
        value=value,
        threshold=0.0,
        comparator="<=",
        status=status,
        gate_level=gate_level,
        rationale=rationale,
        owner="policy",
    )


__all__ = [
    "analyze_drift",
    "evaluate_policy_compliance",
    "verify_licensing",
    "verify_pii_flags",
]
