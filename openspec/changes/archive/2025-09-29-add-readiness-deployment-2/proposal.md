## Why
Release governance tasks (manifests, approval gates, rollback drills) exist in documentation but not in canonical specs. Without a governed capability, deployment automation under `.github/readiness/` and readiness scorecards cannot be audited consistently, putting Module 7 governance and Module 9 SLO commitments at risk.

## What Changes
- Add readiness deployment requirements covering release manifest structure, approval SLAs, rollback rehearsal cadence, and governance event logging.
- Implement manifest emission tooling, CI gate enforcement, rollback rehearsal automation, and readiness status reporting tied to the governance registry.
- Update runbooks and documentation to reflect governed release workflows, including waiver handling and action-item tracking.

## Impact
- Affected specs: `readiness/spec.md`, `governance/spec.md`
- Affected code: `.github/readiness/**`, `.github/workflows/readiness.yml`, readiness automation scripts
- Affected docs: `docs/deployment_readiness.md`, `docs/readiness.md`
- Tests: readiness workflow smoke tests, manifest/scorecard unit tests, CI gating checks
