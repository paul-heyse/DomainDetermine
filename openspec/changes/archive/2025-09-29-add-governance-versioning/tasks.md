## 1. Version Policy Automation

- [x] 1.1 Implement semantic version calculators per artifact with major/minor/patch criteria encoded
- [x] 1.2 Build tooling to bump versions and record change reason codes during publish

## 2. Hashing & Signing

- [x] 2.1 Standardize canonical serialization and hashing per artifact class
- [x] 2.2 Integrate signing workflow (Sigstore/GPG) and hash verification during publish operations

## 3. Dependency Pinning

- [x] 3.1 Enforce upstream ID/hash references in manifests and validate availability before publish
- [x] 3.2 Record parent-child relationships to support rollback impact analysis

## 4. Lineage Graph & Validation

- [x] 4.1 Generate lineage graphs (networkx) for new publishes and persist snapshots for audit
- [x] 4.2 Raise validation errors when lineage contains orphan nodes or hash mismatches
