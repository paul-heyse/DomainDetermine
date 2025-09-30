## Why
We must continuously measure prompt quality—constraint adherence, grounding fidelity, hallucination rate, acceptance, cost—for each template. Calibration sets, judge yardsticks, and reporting pipelines are needed to maintain safety and performance.

## What Changes
- Assemble calibration datasets and yardsticks for key templates (judges, mapping proposals, critiques).
- Implement automated validation: schema adherence, citation checks, hallucination detection, grounding fidelity scoring.
- Build metrics collection jobs storing per-template KPIs (acceptance rate, constraint adherence, cost/latency) over time.
- Create dashboards/reports surfacing quality metrics, alert thresholds, and drift detection for prompt outputs.

## Impact
- Affected specs: prompt-pack
- Affected code: evaluation pipelines, metrics store integration, reporting scripts
