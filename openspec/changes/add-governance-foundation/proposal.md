## Why
Module 7 needs a governance backbone so every artifact across the pipeline is versioned, traceable, and auditable. Without a registry data model and lifecycle policy we cannot safely publish coverage, mapping, overlay, or eval deliverables.

## What Changes
- Define the governance registry scope, mission, and object taxonomy covering modules 1–6 plus prompt packs, run bundles, and certificates.
- Establish metadata schema capturing IDs, semantic versioning, hashes, upstream links, approvals, waivers, and environment fingerprints.
- Specify the release lifecycle (propose → build → audit → approve → sign → publish) and role requirements for major/minor/patch changes.
- Set baseline blocking/advisory gate definitions, waiver handling, and rollback expectations to integrate with Module 5 auditors.

## Impact
- Affected specs: governance
- Affected code: registry service contracts, manifest schemas, signing utilities, governance CLI/API, waiver management
