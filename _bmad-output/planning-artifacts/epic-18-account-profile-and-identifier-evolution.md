# Epic 18: Account Profile and Identifier Evolution

## Goal
Support routine account renaming and external identifier/suffix changes as first-class, safe write operations without mutating ledger history or account primary keys.

## Why This Epic Exists
- Operators need to rename accounts over time for clarity and institution naming changes.
- Financial institutions can change account suffix/reference formats after onboarding.
- Current tooling supports metadata updates, but does not provide explicit profile rename behavior or identifier history tracking.
- We must preserve ledger immutability and auditability while enabling normal account maintenance.

## Scope Boundaries
- In scope:
  - `update_account_profile` write tool for standard single-account profile updates
  - `display_name` updates as routine mutable account behavior
  - Optional external identifier/suffix change handling with append-only history
  - Event logging, deterministic hashing, and idempotency for profile updates
  - Direct SQL access pattern for history reads (no read tool in this slice)
- Out of scope:
  - Bulk rename/update workflows
  - Account deletion or primary-key changes
  - Rewriting historical transactions/postings to reflect new names
  - Dedicated `get_account_history` read tool

## Story 18.1: Standard `update_account_profile` Tool
Create a first-class tool endpoint for routine account profile edits (including name changes).

Acceptance Criteria:
- `POST /tools/update_account_profile` supports single-account updates with required `correlation_id`.
- `display_name` updates are supported as normal behavior.
- Validation and error semantics follow existing write-tool conventions (422 schema errors, 400 domain errors).
- Tool is authn/authz protected (`tools:write`) and event-logged.

## Story 18.2: External Identifier/Suffix Evolution with Append-Only History
Add append-only history for externally meaningful account identifiers when they change.

Acceptance Criteria:
- External identifier changes create append-only history records (no destructive rewrite).
- Existing active identifier record is closed with `valid_to`; new one is inserted with `valid_from`.
- No mutation of ledger transaction/posting records.
- History remains queryable by direct SQL only in Phase 1.

## Story 18.3: Determinism, Concurrency, and Audit Hardening
Prove deterministic behavior and retry-safe operation under duplicate/update contention.

Acceptance Criteria:
- Idempotent retries (`source_system`, `external_id`) return canonical prior result.
- Concurrent duplicate profile-update attempts produce exactly one canonical commit outcome.
- Replay tests confirm stable `output_hash` for identical state/input.
- Event logging covers success and failure; write path is fail-closed on log persistence failure.

## Dependencies
- Builds on existing account domain/repository and write-tool execution path.
- Reuses current authn/authz, event logging, and deterministic hashing infrastructure.

## Exit Criteria
1. Operators can rename an account safely via `update_account_profile`.
2. External identifier/suffix changes are captured append-only with validity windows.
3. Ledger/posting history remains immutable.
4. Determinism, security, and observability constraints remain satisfied.
