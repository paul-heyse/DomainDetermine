## 1. Service Jobs & Quotas
- [x] 1.1 Integrate async job runner (Celery/RQ/Prefect) with tagging for tenant/project
- [x] 1.2 Implement job submission/status APIs with log retrieval and retry policy
- [x] 1.3 Build quota manager enforcing per-tenant compute/cost budgets and early rejection
- [x] 1.4 Wire OpenTelemetry traces/metrics for API + job execution, SPARQL/cache metrics
- [x] 1.5 Document operations and validate with `openspec validate add-service-jobs-and-quota --strict`
