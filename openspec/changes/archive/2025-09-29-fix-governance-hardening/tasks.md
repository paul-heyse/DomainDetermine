## 1. Backup Ordering
- [x] 1.1 Update `BackupCoordinator.last_backup` to return the manifest with the latest snapshot_time
- [x] 1.2 Add tests proving proper ordering under non-lexicographic backup IDs

## 2. Event Log Secret Enforcement
- [x] 2.1 Remove default secret fallback and require explicit secret configuration
- [x] 2.2 Add tests ensuring missing secret raises clear errors and signatures differ per secret

## 3. Diff Storage Hardening
- [x] 3.1 Sanitize artifact IDs when creating diff storage paths (disallow path traversal/invalid characters)
- [x] 3.2 Add regression tests confirming sanitized paths on different OS-friendly formats

## 4. Documentation & Validation
- [x] 4.1 Update governance module documentation to reflect secret handling
- [x] 4.2 Run lint/tests covering governance modules and update change logs
