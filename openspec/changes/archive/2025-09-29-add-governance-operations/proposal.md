## Why
Governance must deliver observability, tenancy, licensing enforcement, and disaster recovery to make the registry reliable. We need event logging, RBAC, backup policies, and telemetry for publication lead times and rollback frequency.

## What Changes
- Implement append-only event log with signed entries for proposals, approvals, waivers, publishes, and rollbacks.
- Define observability metrics (lead time, audit failure rate, rollback frequency, registry latency) and dashboards/alerts.
- Establish RBAC, tenancy separation, and licensing enforcement for artifact access/export, including overlay vs KOS permissions.
- Document backup/restore requirements, cross-region replication, and replay recipes for run bundles and other large artifacts.

## Impact
- Affected specs: governance
- Affected code: event log writer, telemetry emitters, RBAC middleware, tenancy isolation controls, backup automation scripts, licensing filters
