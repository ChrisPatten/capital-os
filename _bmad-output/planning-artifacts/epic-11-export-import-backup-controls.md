# Epic 11: Export, Import, and Backup Controls (FR-31..FR-33)

## Goal
Deliver controlled data portability and recoverability with audit-grade integrity.

### Story 11.1: Ledger Export with Integrity Markers
- Implement `export_ledger(date_range, format)`.
- Include deterministic hash integrity markers in export artifacts.

### Story 11.2: Controlled Import for Transaction Bundles
- Implement `import_transaction_bundles(dry_run, strict)`.
- Ensure deterministic validation outcomes and rollback-safe behavior.

### Story 11.3: Admin Backup and Restore
- Add snapshot backup and restore operations (admin only).
- Emit immutable audit events for backup/restore lifecycle.
