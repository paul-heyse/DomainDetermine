"""Structural and referential integrity checks for Coverage Plans."""

from __future__ import annotations

from typing import Mapping, Sequence

from DomainDetermine.auditor.models import AuditFinding, GateLevel, MetricStatus
from DomainDetermine.auditor.utils import copy_record, to_records


def validate_structural_integrity(
    plan,
    concepts,
    *,
    facet_domains: Mapping[str, Sequence[str]],
    quota_column: str,
) -> tuple[list[Mapping[str, object]], list[AuditFinding]]:
    """Validate structural constraints and return per-row statuses."""

    statuses: list[str] = []
    reasons_col: list[list[str]] = []
    findings: list[AuditFinding] = []
    plan_records = to_records(plan)
    concept_index = {
        record["concept_id"]: {
            "is_deprecated": record.get("is_deprecated", False),
            "path_to_root": record.get("path_to_root", ()),
        }
        for record in to_records(concepts)
    }
    for record in plan_records:
        row_reasons: list[str] = []
        concept_id = record.get("concept_id")
        concept_info = concept_index.get(concept_id)
        if concept_info is None:
            row_reasons.append("UNKNOWN_CONCEPT")
        else:
            if concept_info["is_deprecated"]:
                row_reasons.append("DEPRECATED_CONCEPT")
            _validate_path(record, concept_info["path_to_root"], row_reasons)
        quota_value = record.get(quota_column)
        if quota_value is None or quota_value < 0:
            row_reasons.append("NEGATIVE_OR_MISSING_QUOTA")
        _validate_facets(record, facet_domains, row_reasons)
        status = MetricStatus.PASS if not row_reasons else MetricStatus.FAIL
        statuses.append(status.value)
        reasons_col.append(row_reasons)
        findings.append(
            AuditFinding(
                concept_id=str(concept_id),
                status=status,
                reasons=tuple(row_reasons),
                gate_level=GateLevel.BLOCKING,
            )
        )
    dataset = []
    for record, status, reasons in zip(plan_records, statuses, reasons_col):
        enriched = copy_record(record)
        enriched["structural_status"] = status
        enriched["structural_reasons"] = tuple(reasons)
        dataset.append(enriched)
    return dataset, findings


def _validate_path(record: Mapping[str, object], reference_path: Sequence[str], reasons: list[str]) -> None:
    """Ensure path_to_root is consistent with the authoritative graph."""

    plan_path = record.get("path_to_root", ())
    if not isinstance(plan_path, (list, tuple)):
        reasons.append("INVALID_PATH_TYPE")
        return
    if not reference_path:
        return
    if tuple(plan_path) != tuple(reference_path):
        reasons.append("PATH_MISMATCH")
    concept_id = record.get("concept_id")
    if not plan_path or plan_path[-1] != concept_id:
        reasons.append("PATH_TERMINATION_MISMATCH")


def _validate_facets(
    record: Mapping[str, object],
    facet_domains: Mapping[str, Sequence[str]],
    reasons: list[str],
) -> None:
    """Validate that facet values belong to configured domains."""

    for facet_name, allowed_values in facet_domains.items():
        value = record.get(facet_name)
        if allowed_values and value not in allowed_values:
            reasons.append(f"INVALID_FACET_VALUE::{facet_name}")


__all__ = ["validate_structural_integrity"]
