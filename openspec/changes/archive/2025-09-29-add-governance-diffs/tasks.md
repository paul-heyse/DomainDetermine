## 1. Diff Strategy Definition
- [x] 1.1 Document diff metrics for each artifact class (KOS, coverage, mapping, overlay, eval suites, prompt pack, run bundles, certificates)
- [x] 1.2 Formalize machine-readable schema for diff outputs (JSON) and human-readable summaries (markdown/HTML)

## 2. Diff Generation Pipeline
- [x] 2.1 Implement automated diff generation during publish, using deepdiff/pandas and custom logic per artifact
- [x] 2.2 Store diffs alongside manifests in the registry and version them with hashes

## 3. Approval & Gate Integration
- [x] 3.1 Surface diff summaries in approval workflows with thresholds for blocking/advisory alerts
- [x] 3.2 Trigger governance events when diffs exceed configured drift thresholds (e.g., coverage share delta > X%)

## 4. Audit Automation
- [x] 4.1 Expose diff APIs for automation (CLI/REST) and integrate with Module 5/6 auditors for cross-module checks
- [x] 4.2 Add regression tests ensuring diffs correctly capture changes across representative artifacts
