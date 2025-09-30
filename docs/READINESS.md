## Deployment Gates

- The readiness workflow publishes scorecards and telemetry artifacts which feed the deployment gate service.
- Gate queries OTEL metrics (`readiness.passed`, latency, error rate, flake rate) and readiness scorecard before approving production.
- On rejection, gate emits OTEL span `deployment.gate` and persists decision into the governance registry with trace references.
