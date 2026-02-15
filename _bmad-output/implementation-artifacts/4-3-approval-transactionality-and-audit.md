# Story 4.3: Approval Transactionality and Audit

Status: done

## Story

As a family-office AI operator,
I want approval writes and event logging to commit atomically,
so that auditability remains fail-closed under concurrency and replay.

## Acceptance Criteria

1. Approval-related write paths persist event logs in the same write transaction.
2. Event log failure causes write rollback (fail-closed behavior).
3. Concurrency tests cover duplicate approve/replay edge cases.
4. Append-only and determinism guarantees remain intact.

## Tasks / Subtasks

- [x] Task 1: Enforce transactional write+log coupling (AC: 1, 2)
  - [x] Ensure event insert occurs in same DB transaction as approval write.
  - [x] Roll back canonical write on event log persistence failure.
- [x] Task 2: Harden concurrency behavior (AC: 3, 4)
  - [x] Add deterministic conflict handling for replay/duplicate approvals.
  - [x] Verify exactly-one canonical commit semantics under race conditions.
- [x] Task 3: Add integration/security tests (AC: 2, 3, 4)
  - [x] Extend event log failure rollback tests.
  - [x] Extend concurrency and append-only guard tests.

## Dev Notes

### Developer Context Section

- This story finalizes approval safety and audit transactionality.

### Technical Requirements

- Fail-closed logging behavior is mandatory for write tools.
- Preserve append-only protections under all approval paths.

### File Structure Requirements

- Likely touch:
  - approval domain/service and db transaction code
  - integration/security/concurrency tests

### References

- [Source: `initial_prd.md`]
- [Source: `ARCHITECTURE.md`]
- [Source: `_bmad-output/planning-artifacts/epic-4-approval-gates.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Approval commit and event logging execute in one transaction boundary.
- Added failure-injection integration test demonstrating fail-closed rollback when approval-event persistence fails.
- Added append-only protections for `approval_decisions` and delete protection for `approval_proposals`.
- Verified deterministic replay and exactly-one commit semantics under concurrent duplicate approvals.

### File List

- `src/capital_os/domain/approval/service.py`
- `migrations/0003_approval_gates.sql`
- `migrations/0003_approval_gates.rollback.sql`
- `tests/integration/test_approval_workflow.py`
- `tests/integration/test_event_log_coverage.py`
