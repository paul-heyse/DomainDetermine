## 1. Registry Scope & Taxonomy

- [x] 1.1 Enumerate governed artifacts (KOS snapshots, coverage plans, mappings, overlay, eval suites, prompt pack, run bundles, certificates)
- [x] 1.2 Define unique ID format and namespace rules for each artifact class

## 2. Metadata Schema

- [x] 2.1 Model core manifest fields (type, version, hash, title, summary, upstream links, policy pack hash, license tag)
- [x] 2.2 Capture approvals, reviewers, waiver references, environment fingerprint, and parent relationships

## 3. Lifecycle Policy

- [x] 3.1 Codify propose → build → audit → approve → sign → publish flow with role matrix and major/minor/patch rules
- [x] 3.2 Document linkage requirements (upstream pins, hash validation) and integrate with Module 5 blocking/advisory gates

## 4. Rollback & Waiver Handling

- [x] 4.1 Establish waiver metadata (owner, justification, expiry) and registry persistence
- [x] 4.2 Define rollback semantics (current pointer management, downstream warnings) and disaster recovery expectations
