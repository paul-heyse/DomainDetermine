## 1. Capability Scaffold
- [x] 1.1 Define coverage auditor service interfaces and dependency graph (Module 1/2 ingestion, policy packs, baselines)
- [x] 1.2 Model audit run manifests linking kos_snapshot_id, plan_version, and signing keys

## 2. Structural Integrity Checks
- [x] 2.1 Implement concept existence/deprecation validation against Module 1 tables
- [x] 2.2 Validate path_to_root referential integrity and facet vocabulary conformity

## 3. Audit Artifacts
- [x] 3.1 Produce audit dataset (denormalized table) with metric placeholders and lineage metadata
- [x] 3.2 Generate machine-readable coverage certificate (JSON/YAML) plus signature envelope

## 4. Governance & Quality Gates
- [x] 4.1 Encode blocking vs advisory gate schema with owner metadata and waiver recording
- [x] 4.2 Integrate sign-off workflow with governance registry (reviewer identity, timestamps)
