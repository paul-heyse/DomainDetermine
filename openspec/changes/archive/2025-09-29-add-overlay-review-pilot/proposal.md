## Why
Overlay success hinges on human oversight. We need reviewer workflows, pilot annotation loops, and migration handling for splits/merges so accepted nodes are trustworthy and actionable.

## What Changes
- Deliver reviewer workbench flows that surface proposals, evidence, sibling context, and nearest-neighbor diagnostics for quick decisions with reason codes.
- Define pilot annotation protocol (sample size, IAA metrics, demotion rules) to test annotatability before publishing new nodes.
- Operationalize split/merge handling, including migration instructions and synonym approvals with collision checks.
- Feed accepted decisions back into overlay manifests and Module 2 coverage deltas with quota updates.

## Impact
- Affected specs: overlay
- Affected code: reviewer UI/service, annotation pilot orchestrator, migration utilities, overlay manifest updates, coverage plan delta writers
