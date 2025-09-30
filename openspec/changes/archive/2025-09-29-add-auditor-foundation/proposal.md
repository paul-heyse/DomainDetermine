## Why
Module 5 needs a formal coverage auditing foundation so we can certify plans before spending on data. We currently lack structural validation, audit datasets, or certificate artifacts, blocking downstream governance and stakeholder confidence.

## What Changes
- Define the coverage auditor capability scope, including mission, inputs/outputs, and versioned artifact requirements aligned with Module 1 and 2 contracts.
- Introduce structural and referential integrity checks with reproducible execution (concept existence, deprecation, path validations, facet vocab compliance).
- Specify audit dataset and certificate artifacts with linkage to KOS snapshots, plan versions, and signing requirements.
- Establish quality gate taxonomy (blocking vs advisory) and waiver/sign-off workflow to integrate with governance.

## Impact
- Affected specs: auditor
- Affected code: coverage auditor pipeline orchestration, structural check runners, manifest/certificate emitters, governance registry hooks
