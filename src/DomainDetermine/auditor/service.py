"""Coverage auditor orchestration logic."""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional, Sequence

from DomainDetermine.auditor import structural
from DomainDetermine.auditor.compliance import (
    analyze_drift,
    evaluate_policy_compliance,
    verify_licensing,
    verify_pii_flags,
)
from DomainDetermine.auditor.fairness import compute_fairness_metrics
from DomainDetermine.auditor.governance import GovernanceNotifier
from DomainDetermine.auditor.models import (
    AuditArtifactPaths,
    AuditCertificate,
    AuditFinding,
    AuditMetric,
    AuditResult,
    AuditRunConfig,
    GateLevel,
    MetricStatus,
    PolicyPack,
    default_metadata,
    generate_signature,
)
from DomainDetermine.auditor.report import build_report
from DomainDetermine.auditor.storage import AuditStorage
from DomainDetermine.auditor.telemetry import AuditTelemetry
from DomainDetermine.auditor.utils import copy_record


class CoverageAuditor:
    """Runs structural, fairness, and compliance checks for a Coverage Plan."""

    def __init__(
        self,
        config: AuditRunConfig,
        policy_pack: PolicyPack,
        *,
        storage: Optional[AuditStorage] = None,
        governance_notifier: Optional[GovernanceNotifier] = None,
    ) -> None:
        self._config = config
        self._policy_pack = policy_pack
        self._telemetry = AuditTelemetry()
        self._storage = storage
        self._governance = governance_notifier

    def run(
        self,
        *,
        coverage_plan,
        concept_table,
        baseline_plan: Optional[object] = None,
    ) -> AuditResult:
        structural_dataset, structural_findings = structural.validate_structural_integrity(
            coverage_plan,
            concept_table,
            facet_domains=self._config.facet_domains,
            quota_column=self._config.quota_column,
        )
        self._record_findings("structural", structural_findings)
        fairness_metrics, fairness_findings, fairness_dataset, assets = compute_fairness_metrics(
            structural_dataset,
            policy_pack=self._policy_pack,
            branch_column=self._config.branch_column,
            quota_column=self._config.quota_column,
            facet_columns=(self._config.locale_column, self._config.difficulty_column),
        )
        for metric in fairness_metrics:
            self._record_metric(metric)
        self._record_findings("fairness", fairness_findings)
        policy_findings, policy_metrics = evaluate_policy_compliance(
            fairness_dataset,
            policy_pack=self._policy_pack,
            locale_column=self._config.locale_column,
        )
        self._record_findings("policy", policy_findings)
        for metric in policy_metrics:
            self._record_metric(metric)
        licensing_metric = verify_licensing(fairness_dataset, policy_pack=self._policy_pack)
        pii_metric = verify_pii_flags(fairness_dataset, policy_pack=self._policy_pack)
        self._record_metric(licensing_metric)
        self._record_metric(pii_metric)
        drift_summary = analyze_drift(
            fairness_dataset,
            baseline_plan,
            quota_column=self._config.quota_column,
        )
        all_findings: list[AuditFinding] = list(structural_findings) + list(fairness_findings) + list(policy_findings)
        metrics: list[AuditMetric] = (
            fairness_metrics + policy_metrics + [licensing_metric, pii_metric]
        )
        certificate = self._build_certificate(metrics, all_findings)
        report = build_report(
            config=self._config,
            metrics=metrics,
            findings=all_findings,
            drift_summary=drift_summary,
            asset_paths=assets,
        )
        asset_paths = [str(asset.get("path")) for asset in assets]
        artifact_paths = AuditArtifactPaths(
            dataset_uri=_build_uri(self._config, "audit_dataset.json"),
            certificate_uri=_build_uri(self._config, "certificate.json"),
            report_uri=_build_uri(self._config, "report.json"),
            assets=tuple(asset_paths),
        )
        dataset = [copy_record(record) for record in fairness_dataset]
        policy_map = {finding.concept_id: finding.reasons for finding in policy_findings}
        for record in dataset:
            concept_id = str(record.get("concept_id"))
            record["policy_findings"] = tuple(policy_map.get(concept_id, tuple()))
        if self._storage:
            artifact_paths = self._storage.persist_all(
                dataset=dataset,
                certificate=certificate,
                report=report,
                artifact_paths=artifact_paths,
                assets=assets,
            )
        if self._governance:
            summary = {
                "audit_run_id": self._config.audit_run_id,
                "plan_version": self._config.plan_version,
                "kos_snapshot_id": self._config.kos_snapshot_id,
                "certificate_signature": certificate.signature,
                "findings_summary": dict(certificate.findings_summary),
                "artifact_paths": asdict(artifact_paths),
                "metrics": [
                    {
                        "name": metric.name,
                        "status": metric.status.value,
                        "gate_level": metric.gate_level.value,
                        "value": metric.value,
                    }
                    for metric in metrics
                ],
            }
            self._governance.notify(summary)
        return AuditResult(
            audit_dataset=dataset,
            metrics=metrics,
            findings=all_findings,
            certificate=certificate,
            report=report,
            artifact_paths=artifact_paths,
            telemetry_events=self._telemetry.events(),
        )

    def _build_certificate(
        self,
        metrics: Sequence[AuditMetric],
        findings: Sequence[AuditFinding],
    ) -> AuditCertificate:
        metadata = default_metadata(self._config)
        findings_summary = {
            "blocking_failures": sum(
                1 for finding in findings if finding.gate_level is GateLevel.BLOCKING and finding.status != MetricStatus.PASS
            ),
            "advisory_warnings": sum(
                1 for finding in findings if finding.gate_level is GateLevel.ADVISORY and finding.status != MetricStatus.PASS
            ),
        }
        payload = {
            "metadata": metadata,
            "metrics": [asdict(metric) for metric in metrics],
            "findings_summary": findings_summary,
            "waivers": [],
        }
        signature = generate_signature(payload, signer_key_id=self._config.signer_key_id)
        return AuditCertificate(
            metadata=metadata,
            metrics=metrics,
            findings_summary=findings_summary,
            waivers=tuple(),
            signature=signature,
        )

    def _record_metric(self, metric: AuditMetric) -> None:
        self._telemetry.record(
            metric_name=metric.name,
            value=metric.value,
            threshold=metric.threshold,
            status=metric.status.value,
            context={
                "plan_version": self._config.plan_version,
                "audit_run_id": self._config.audit_run_id,
                "gate_level": metric.gate_level.value,
            },
        )

    def _record_findings(self, prefix: str, findings: Sequence[AuditFinding]) -> None:
        for finding in findings:
            self._telemetry.record(
                metric_name=f"{prefix}_finding",
                value=finding.concept_id,
                threshold=None,
                status=finding.status.value,
                context={
                    "plan_version": self._config.plan_version,
                    "audit_run_id": self._config.audit_run_id,
                    "gate_level": finding.gate_level.value,
                },
            )


def _build_uri(config: AuditRunConfig, filename: str) -> str:
    return (
        f"audits/{config.kos_snapshot_id}/{config.plan_version}/"
        f"{config.audit_run_id}/{filename}"
    )


__all__ = ["CoverageAuditor"]
