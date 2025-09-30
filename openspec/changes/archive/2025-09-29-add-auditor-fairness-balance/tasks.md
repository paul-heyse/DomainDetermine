## 1. Metric Computation
- [x] 1.1 Implement DuckDB/Pandas aggregations for branch/facet quota share, entropy, Gini, and HHI
- [x] 1.2 Calculate fairness floors/ceilings per policy pack and materialize pass/fail flags per metric

## 2. Sparse Density Detection
- [x] 2.1 Generate facet heatmaps highlighting sparse or saturated cells with thresholds
- [x] 2.2 Flag zero-quota leaves under active branches as advisory findings with remediation hints

## 3. Policy Threshold Configuration
- [x] 3.1 Model metric threshold configuration (blocking vs advisory) with owner metadata and rationale enums
- [x] 3.2 Persist metric outcomes and rationales into audit dataset and certificate payload

## 4. Visualization & Reporting
- [x] 4.1 Produce visual assets (charts/heatmaps) for inclusion in human reports
- [x] 4.2 Attach fairness summary section to executive report and note status badges per metric
