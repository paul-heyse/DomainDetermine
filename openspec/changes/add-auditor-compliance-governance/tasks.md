## 1. Policy Validation
- [x] 1.1 Evaluate forbidden concepts and jurisdictional filters against Coverage Plan rows and policy packs
- [x] 1.2 Check licensing restrictions and ensure sensitive fields are masked in audit outputs
- [x] 1.3 Verify PII/PHI redaction flags and compliance metadata presence per stratum

## 2. Drift Analysis
- [x] 2.1 Compare current plan vs. selected baseline, computing added/removed concepts and quota deltas
- [x] 2.2 Assess metric drift (fairness indices, allocation method changes) and attribute drivers (overlay, policy, cost)

## 3. Quality Gates & Waivers
- [x] 3.1 Implement blocking/advisory gate evaluation with waiver approval workflow and owner roles
- [x] 3.2 Persist waiver decisions, reviewer identities, and timestamps in audit manifests and certificates

## 4. Governance & Audit Trail
- [x] 4.1 Record policy pack versions, compliance notes, and legal review status in audit outputs
- [x] 4.2 Emit structured logs and telemetry for compliance checks with OpenTelemetry attributes
