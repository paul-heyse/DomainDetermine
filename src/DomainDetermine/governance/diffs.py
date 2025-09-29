"""Diff generation for governed artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, MutableMapping, Optional


@dataclass(frozen=True)
class DiffResult:
    """Represents a diff between two artifact revisions."""

    artifact_type: str
    machine_readable: Mapping[str, object]
    summary_markdown: str
    status: str


class DiffEngine:
    """Generates human- and machine-readable diffs for governed artifacts."""

    def __init__(self, *, thresholds: Optional[Mapping[str, Mapping[str, float]]] = None) -> None:
        self._thresholds = thresholds or {}
        self._strategies: Mapping[str, Callable[[Mapping[str, object], Mapping[str, object]], DiffResult]] = {
            "kos_snapshot": self._diff_kos_snapshot,
            "coverage_plan": self._diff_coverage_plan,
            "mapping": self._diff_mapping,
            "overlay": self._diff_overlay,
            "eval_suite": self._diff_eval_suite,
            "prompt_pack": self._diff_prompt_pack,
            "run_bundle": self._diff_run_bundle,
            "certificate": self._diff_certificate,
        }

    def generate_diff(
        self,
        artifact_type: str,
        old: Mapping[str, object],
        new: Mapping[str, object],
    ) -> DiffResult:
        if artifact_type not in self._strategies:
            raise ValueError(f"Unsupported artifact type '{artifact_type}'")
        return self._strategies[artifact_type](old, new)

    # ---- Strategy helpers -------------------------------------------------

    def _diff_kos_snapshot(
        self,
        old: Mapping[str, object],
        new: Mapping[str, object],
    ) -> DiffResult:
        old_concepts = set(old.get("concepts", []))
        new_concepts = set(new.get("concepts", []))
        added = sorted(new_concepts - old_concepts)
        removed = sorted(old_concepts - new_concepts)
        renamed = []
        if "labels" in old and "labels" in new:
            old_labels = old["labels"]
            new_labels = new["labels"]
            renamed = [cid for cid in new_labels if cid in old_labels and new_labels[cid] != old_labels[cid]]
        machine = {
            "added_concepts": added,
            "removed_concepts": removed,
            "renamed_concepts": renamed,
            "license_changes": new.get("license") != old.get("license"),
        }
        summary = ["### KOS Snapshot Diff", f"- Added concepts: {len(added)}", f"- Removed concepts: {len(removed)}"]
        if renamed:
            summary.append(f"- Renamed concepts: {len(renamed)}")
        status = "pass"
        return DiffResult("kos_snapshot", machine, "\n".join(summary), status)

    def _diff_coverage_plan(
        self,
        old: Mapping[str, object],
        new: Mapping[str, object],
    ) -> DiffResult:
        old_rows = {row["id"]: row for row in old.get("strata", []) if "id" in row}
        new_rows = {row["id"]: row for row in new.get("strata", []) if "id" in row}
        added_ids = sorted(set(new_rows) - set(old_rows))
        removed_ids = sorted(set(old_rows) - set(new_rows))
        quota_delta_by_branch: MutableMapping[str, float] = {}
        for row_id, row in new_rows.items():
            branch = row.get("branch", "unknown")
            new_quota = float(row.get("quota", 0) or 0)
            old_quota = float(old_rows.get(row_id, {}).get("quota", 0) or 0)
            quota_delta_by_branch[branch] = quota_delta_by_branch.get(branch, 0.0) + (new_quota - old_quota)
        old_metrics = old.get("metrics", {})
        new_metrics = new.get("metrics", {})
        metric_deltas = {
            metric: new_metrics.get(metric, 0) - old_metrics.get(metric, 0) for metric in set(new_metrics) | set(old_metrics)
        }
        fairness_delta = abs(metric_deltas.get("entropy", 0))
        threshold = self._thresholds.get("coverage_plan", {}).get("max_fairness_delta", 0.1)
        status = "pass"
        alerts = []
        if fairness_delta > threshold:
            status = "block"
            alerts.append({"type": "fairness_drift", "delta": fairness_delta, "threshold": threshold})
        machine = {
            "added_strata": added_ids,
            "removed_strata": removed_ids,
            "quota_delta_by_branch": quota_delta_by_branch,
            "metric_deltas": metric_deltas,
            "alerts": alerts,
        }
        summary_lines = [
            "### Coverage Plan Diff",
            f"- Added strata: {len(added_ids)}",
            f"- Removed strata: {len(removed_ids)}",
        ]
        if quota_delta_by_branch:
            summary_lines.append("- Quota delta by branch:" + " ".join(f" {branch}:{delta:+.1f}" for branch, delta in quota_delta_by_branch.items()))
        if metric_deltas:
            summary_lines.append("- Fairness metric deltas:" + " ".join(f" {metric}:{delta:+.3f}" for metric, delta in metric_deltas.items()))
        if alerts:
            summary_lines.append("- Alerts: fairness drift exceeds threshold")
        return DiffResult("coverage_plan", machine, "\n".join(summary_lines), status)

    def _diff_mapping(
        self,
        old: Mapping[str, object],
        new: Mapping[str, object],
    ) -> DiffResult:
        old_records = {rec["id"]: rec for rec in old.get("records", []) if "id" in rec}
        new_records = {rec["id"]: rec for rec in new.get("records", []) if "id" in rec}
        added = sorted(set(new_records) - set(old_records))
        removed = sorted(set(old_records) - set(new_records))
        overrides = [rid for rid in new_records if rid in old_records and new_records[rid].get("concept_id") != old_records[rid].get("concept_id")]
        churn_by_branch: MutableMapping[str, int] = {}
        for rid in overrides:
            branch = new_records[rid].get("branch", "unknown")
            churn_by_branch[branch] = churn_by_branch.get(branch, 0) + 1
        machine = {
            "added_decisions": added,
            "removed_decisions": removed,
            "overridden_decisions": overrides,
            "churn_by_branch": churn_by_branch,
        }
        summary = [
            "### Mapping Diff",
            f"- Added decisions: {len(added)}",
            f"- Removed decisions: {len(removed)}",
            f"- Overrides: {len(overrides)}",
        ]
        status = "pass"
        return DiffResult("mapping", machine, "\n".join(summary), status)

    def _diff_overlay(
        self,
        old: Mapping[str, object],
        new: Mapping[str, object],
    ) -> DiffResult:
        old_nodes = set(old.get("nodes", []))
        new_nodes = set(new.get("nodes", []))
        added = sorted(new_nodes - old_nodes)
        removed = sorted(old_nodes - new_nodes)
        machine = {
            "added_nodes": added,
            "removed_nodes": removed,
            "coverage_gain": new.get("coverage_gain", 0) - old.get("coverage_gain", 0),
        }
        summary = [
            "### Overlay Diff",
            f"- Added nodes: {len(added)}",
            f"- Removed nodes: {len(removed)}",
            f"- Coverage gain delta: {machine['coverage_gain']:+.2f}",
        ]
        status = "pass"
        return DiffResult("overlay", machine, "\n".join(summary), status)

    def _diff_eval_suite(
        self,
        old: Mapping[str, object],
        new: Mapping[str, object],
    ) -> DiffResult:
        old_slices = set(old.get("slices", []))
        new_slices = set(new.get("slices", []))
        added_slices = sorted(new_slices - old_slices)
        removed_slices = sorted(old_slices - new_slices)
        threshold_changes = {}
        old_thresholds = old.get("thresholds", {})
        new_thresholds = new.get("thresholds", {})
        for key in set(new_thresholds) | set(old_thresholds):
            delta = new_thresholds.get(key, 0) - old_thresholds.get(key, 0)
            if delta:
                threshold_changes[key] = delta
        machine = {
            "added_slices": added_slices,
            "removed_slices": removed_slices,
            "threshold_changes": threshold_changes,
        }
        summary = [
            "### Eval Suite Diff",
            f"- Added slices: {len(added_slices)}",
            f"- Removed slices: {len(removed_slices)}",
        ]
        if threshold_changes:
            summary.append("- Threshold changes:" + " ".join(f" {k}:{v:+.3f}" for k, v in threshold_changes.items()))
        status = "pass"
        return DiffResult("eval_suite", machine, "\n".join(summary), status)

    def _diff_prompt_pack(
        self,
        old: Mapping[str, object],
        new: Mapping[str, object],
    ) -> DiffResult:
        old_prompts = set(old.get("templates", []))
        new_prompts = set(new.get("templates", []))
        added = sorted(new_prompts - old_prompts)
        removed = sorted(old_prompts - new_prompts)
        policy_changes = new.get("retrieval_policy") != old.get("retrieval_policy")
        machine = {
            "added_templates": added,
            "removed_templates": removed,
            "retrieval_policy_changed": policy_changes,
            "schema_changed": new.get("schema") != old.get("schema"),
        }
        summary = [
            "### Prompt Pack Diff",
            f"- Added templates: {len(added)}",
            f"- Removed templates: {len(removed)}",
        ]
        if policy_changes:
            summary.append("- Retrieval policy updated")
        status = "pass"
        return DiffResult("prompt_pack", machine, "\n".join(summary), status)

    def _diff_run_bundle(
        self,
        old: Mapping[str, object],
        new: Mapping[str, object],
    ) -> DiffResult:
        old_scores = old.get("scores", {})
        new_scores = new.get("scores", {})
        score_deltas = {
            model: new_scores.get(model, 0) - old_scores.get(model, 0)
            for model in set(new_scores) | set(old_scores)
        }
        cost_delta = new.get("cost", 0) - old.get("cost", 0)
        latency_delta = new.get("latency_ms", 0) - old.get("latency_ms", 0)
        machine = {
            "score_deltas": score_deltas,
            "cost_delta": cost_delta,
            "latency_delta": latency_delta,
        }
        status = "pass"
        summary = [
            "### Run Bundle Diff",
            "- Score deltas:" + " ".join(f" {model}:{delta:+.3f}" for model, delta in score_deltas.items()),
            f"- Cost delta: {cost_delta:+.2f}",
            f"- Latency delta: {latency_delta:+.1f} ms",
        ]
        return DiffResult("run_bundle", machine, "\n".join(summary), status)

    def _diff_certificate(
        self,
        old: Mapping[str, object],
        new: Mapping[str, object],
    ) -> DiffResult:
        old_metrics = old.get("metrics", {})
        new_metrics = new.get("metrics", {})
        metric_deltas = {
            name: new_metrics.get(name, 0) - old_metrics.get(name, 0) for name in set(new_metrics) | set(old_metrics)
        }
        summary_lines = ["### Certificate Diff"]
        if metric_deltas:
            summary_lines.append("- Metric deltas:" + " ".join(f" {name}:{delta:+.3f}" for name, delta in metric_deltas.items()))
        machine = {"metric_deltas": metric_deltas}
        status = "pass"
        return DiffResult("certificate", machine, "\n".join(summary_lines), status)


class DiffStorage:
    """Persists diffs in machine-readable and human-readable formats."""

    def __init__(self, base_path: str) -> None:
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def persist(self, artifact_id: str, version: str, diff: DiffResult) -> Mapping[str, str]:
        safe_artifact_id = self._sanitize(artifact_id)
        safe_version = self._sanitize(version)
        folder = self._base_path / safe_artifact_id / safe_version
        folder.mkdir(parents=True, exist_ok=True)
        machine_path = folder / "diff.json"
        summary_path = folder / "summary.md"
        with machine_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "artifact_type": diff.artifact_type,
                    "status": diff.status,
                    "payload": diff.machine_readable,
                },
                handle,
                indent=2,
                sort_keys=True,
            )
        summary_path.write_text(diff.summary_markdown)
        return {"machine": str(machine_path), "summary": str(summary_path)}

    @staticmethod
    def _sanitize(value: str) -> str:
        sanitized = [ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value]
        collapsed = "".join(sanitized).strip("-")
        return collapsed or "artifact"


__all__ = ["DiffEngine", "DiffResult", "DiffStorage"]
