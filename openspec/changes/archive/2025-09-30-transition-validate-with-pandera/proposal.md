## Why

Great Expectations adds operational overhead and pulls in a heavy dependency stack that overlaps with validation guarantees we already provide elsewhere. By pivoting to Pandera for dataframe validation and Pydantic for manifest and API payload schemas we can standardise on the same typed-model approach used in the rest of the codebase, reduce dependency size, and simplify contributor workflows.

## What Changes

- Replace every Great Expectations suite used in ingestion, quality diagnostics, and governance pipelines with Pandera schemas executed during snapshot builds.
- Define Pydantic models for snapshot manifests, registry events, and validation reports so that downstream consumers share a single typed contract.
- Remove Great Expectations from the dependency set, CI hooks, and developer documentation while adding lint/tests around the new Pandera + Pydantic validators.

## Impact

- Affected specs: kos-ingestion, governance
- Affected code: ingestion validation pipeline, governance registry validations, CI config, developer documentation
