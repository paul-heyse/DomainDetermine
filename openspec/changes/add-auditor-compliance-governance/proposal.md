## Why
Coverage auditing must enforce licensing, jurisdictional, and safety policies before a plan is approved. We need formal compliance validators, waiver governance, and drift analysis to explain changes versus prior plans.

## What Changes
- Implement policy validation modules checking forbidden concepts, jurisdictional restrictions, licensing export limits, and PII/PHI redaction flags.
- Add drift analyzer comparing current vs. prior plans (differences in concepts, quotas, allocation methods, fairness metrics) with explanations referencing overlays or policy updates.
- Extend quality gate handling to track blocking/advisory statuses with waiver workflows and governance registry integration.
- Capture audit trail metadata (who approved, waivers, policy pack version) in certificates and manifests.

## Impact
- Affected specs: auditor
- Affected code: policy validators, drift analyzers, waiver registries, governance manifest writers, compliance logs
