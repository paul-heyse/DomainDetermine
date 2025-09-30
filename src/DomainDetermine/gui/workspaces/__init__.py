from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from nicegui import ui

from ..stubs import WORKSPACE_METRICS


@dataclass(frozen=True)
class Workspace:
    slug: str
    title: str
    description: str


WORKSPACES: Sequence[Workspace] = (
    Workspace("ingestion", "Ingestion", "Manage KOS snapshots and connectors."),
    Workspace("coverage", "Coverage Planner", "Allocate quotas and review diagnostics."),
    Workspace("mapping", "Mapping", "Review mapping batches and rationales."),
    Workspace("overlay", "Overlay", "Vet overlay proposals."),
    Workspace("auditor", "Auditor", "Inspect certificates and waivers."),
    Workspace("eval", "Eval Suite", "Configure and monitor evaluation suites."),
    Workspace("readiness", "Readiness", "Track readiness gates and attestations."),
    Workspace("prompt-pack", "Prompt Pack", "Monitor prompt templates and calibration."),
    Workspace("governance", "Governance", "Operate manifests and waivers."),
    Workspace("service", "Service Ops", "Observe job queues and incidents."),
)


def render_workspace(workspace: Workspace) -> None:
    metrics = WORKSPACE_METRICS.get(workspace.slug, [])

    with ui.column().classes("gap-4"):
        ui.label(workspace.title).classes("text-2xl font-semibold")
        ui.label(workspace.description).classes("text-gray-600")

        if not metrics:
            ui.label("No metrics available yet.").classes("text-gray-400")
            return

        with ui.table(columns=["Metric", "Value", "Updated"], rows=metrics).classes("w-full"):
            pass
