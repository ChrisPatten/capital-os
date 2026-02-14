# Story 4.3: Approval Transactionality and Audit

Status: ready-for-dev

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

- [ ] Task 1: Enforce transactional write+log coupling (AC: 1, 2)
  - [ ] Ensure event insert occurs in same DB transaction as approval write.
  - [ ] Roll back canonical write on event log persistence failure.
- [ ] Task 2: Harden concurrency behavior (AC: 3, 4)
  - [ ] Add deterministic conflict handling for replay/duplicate approvals.
  - [ ] Verify exactly-one canonical commit semantics under race conditions.
- [ ] Task 3: Add integration/security tests (AC: 2, 3, 4)
  - [ ] Extend event log failure rollback tests.
  - [ ] Extend concurrency and append-only guard tests.

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

TBD

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Story created and marked ready-for-dev.

### File List

- `_bmad-output/implementation-artifacts/4-3-approval-transactionality-and-audit.md`
