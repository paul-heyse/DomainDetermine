from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable


def _ago(minutes: int) -> str:
    return (datetime.utcnow() - timedelta(minutes=minutes)).isoformat(timespec="seconds") + "Z"


DASHBOARD_SUMMARY = (
    {"title": "Active Jobs", "value": "12", "updated": _ago(1)},
    {"title": "Pending Approvals", "value": "4", "updated": _ago(3)},
    {"title": "Incidents", "value": "0", "updated": _ago(8)},
)


COMMAND_PALETTE_ACTIONS: tuple[dict[str, str], ...] = (
    {"label": "Open Dashboard", "path": "/", "category": "Navigation"},
    {"label": "Launch Ingestion", "path": "/workspaces/ingestion", "category": "Navigation"},
    {"label": "Launch Coverage Planner", "path": "/workspaces/coverage", "category": "Navigation"},
    {"label": "Launch Mapping", "path": "/workspaces/mapping", "category": "Navigation"},
    {"label": "Launch Overlay", "path": "/workspaces/overlay", "category": "Navigation"},
    {"label": "Open Notification Center", "path": "#notifications", "category": "Utility"},
    {"label": "Open Preferences", "path": "#preferences", "category": "Utility"},
)


NOTIFICATION_FEED: tuple[dict[str, str], ...] = (
    {
        "id": "notif-1",
        "title": "Coverage waiver awaiting approval",
        "body": "Plan v2025.09.30 requests fairness waiver for EU competition law branch.",
        "severity": "warning",
        "timestamp": _ago(12),
    },
    {
        "id": "notif-2",
        "title": "Readiness gate succeeded",
        "body": "Eval suite 2025.09.29 passed readiness gate for Tenant ACME.",
        "severity": "success",
        "timestamp": _ago(25),
    },
    {
        "id": "notif-3",
        "title": "LLM cost threshold nearing limit",
        "body": "Monthly cost burn at 82% for Tenant Globex. Review dashboards for mitigation.",
        "severity": "danger",
        "timestamp": _ago(47),
    },
)

WORKSPACE_METRICS: dict[str, list[dict[str, str]]] = {
    "ingestion": [
        {"Metric": "Snapshots", "Value": "5", "Updated": _ago(8)},
        {"Metric": "Pending Jobs", "Value": "2", "Updated": _ago(3)},
    ],
    "coverage": [
        {"Metric": "Plans", "Value": "3", "Updated": _ago(12)},
        {"Metric": "Warnings", "Value": "1", "Updated": _ago(12)},
    ],
    "mapping": [
        {"Metric": "Batches", "Value": "8", "Updated": _ago(5)},
        {"Metric": "Deferred", "Value": "4", "Updated": _ago(5)},
    ],
    "overlay": [
        {"Metric": "Proposals", "Value": "6", "Updated": _ago(20)},
    ],
    "auditor": [
        {"Metric": "Certificates", "Value": "2", "Updated": _ago(15)},
        {"Metric": "Waivers", "Value": "0", "Updated": _ago(15)},
    ],
    "eval": [
        {"Metric": "Suites", "Value": "4", "Updated": _ago(9)},
    ],
    "readiness": [
        {"Metric": "Gates", "Value": "3", "Updated": _ago(7)},
    ],
    "prompt-pack": [
        {"Metric": "Templates", "Value": "12", "Updated": _ago(10)},
        {"Metric": "Calibrations", "Value": "2", "Updated": _ago(10)},
    ],
    "governance": [
        {"Metric": "Manifests", "Value": "11", "Updated": _ago(18)},
        {"Metric": "Pending Waivers", "Value": "1", "Updated": _ago(18)},
    ],
    "service": [
        {"Metric": "Active Incidents", "Value": "0", "Updated": _ago(2)},
        {"Metric": "Feature Flags", "Value": "5", "Updated": _ago(2)},
    ],
}
