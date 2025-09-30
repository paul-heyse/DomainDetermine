"""Default job handlers for the service layer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from .jobs import JobManager, JobRecord


def _format_log(message: str, *, job: JobRecord, extra: Optional[dict] = None) -> str:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_id": job.job_id,
        "job_type": job.request.job_type,
        "tenant": job.request.tenant,
        "project": job.request.project,
        "message": message,
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, sort_keys=True)


def handle_plan_build(job: JobRecord, manager: JobManager) -> str:
    """Simulate plan build execution."""

    plan_id = job.request.payload.get("plan", "unknown")
    log_line = _format_log(
        "plan build completed",
        job=job,
        extra={"plan": plan_id},
    )
    return log_line


def handle_eval_run(job: JobRecord, manager: JobManager) -> str:
    suite = job.request.payload.get("suite", "default")
    log_line = _format_log(
        "evaluation suite executed",
        job=job,
        extra={"suite": suite},
    )
    return log_line


def handle_audit(job: JobRecord, manager: JobManager) -> str:
    report = job.request.payload.get("report", "audit")
    log_line = _format_log(
        "audit report generated",
        job=job,
        extra={"report": report},
    )
    return log_line


def register_default_handlers(manager: JobManager) -> None:
    manager.register_handler("plan-build", handle_plan_build)
    manager.register_handler("eval-run", handle_eval_run)
    manager.register_handler("audit-report", handle_audit)


__all__ = [
    "handle_plan_build",
    "handle_eval_run",
    "handle_audit",
    "register_default_handlers",
]
