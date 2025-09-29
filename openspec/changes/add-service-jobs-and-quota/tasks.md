## 1. Service Jobs & Quotas
- [ ] 1.1 Integrate async job runner (Celery/RQ/Prefect) with tagging for tenant/project
- [ ] 1.2 Implement job submission/status APIs with log retrieval and retry policy
- [ ] 1.3 Build quota manager enforcing per-tenant compute/cost budgets and early rejection
- [ ] 1.4 Wire OpenTelemetry traces/metrics for API + job execution, SPARQL/cache metrics
- [ ] 1.5 Document operations and validate with `openspec validate add-service-jobs-and-quota --strict`
