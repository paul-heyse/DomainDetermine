## Why
Recent governance additions introduced three issues: `BackupCoordinator.last_backup()` chooses the maximum backup ID lexicographically rather than the most recent snapshot, compromising disaster recovery; the event log uses a hard-coded default signing secret that allows forged signatures; and `DiffStorage` writes artifact IDs directly to filesystem paths, risking invalid path characters. These bugs undermine rollback, tamper detection, and artifact storage safety.

## What Changes
- Correct `BackupCoordinator.last_backup()` to return the most recent backup by snapshot timestamp, independent of backup ID ordering.
- Require an explicit signing secret for `GovernanceEventLog`, removing the default fallback and failing fast if none is provided.
- Sanitize artifact IDs when building diff storage paths to prevent path traversal and OS incompatibilities.
- Add regression tests covering these scenarios and update documentation where necessary.

## Impact
- Affected specs: governance
- Affected code: `src/DomainDetermine/governance/backup.py`, `src/DomainDetermine/governance/event_log.py`, `src/DomainDetermine/governance/diffs.py`, associated tests
