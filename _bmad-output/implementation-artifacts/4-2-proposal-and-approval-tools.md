# Story 4.2: Proposal and Approval Tools

Status: ready-for-dev

## Story

As a family-office AI operator,
I want proposal and approve/reject tool flows,
so that approval-gated writes can complete with deterministic idempotent behavior.

## Acceptance Criteria

1. Proposal and approve/reject tool contracts are implemented and validated.
2. Approval path supports idempotency and exactly one canonical commit.
3. Duplicate approval/retry behavior returns deterministic canonical result.
4. Success and failure paths are event-logged with required fields.

## Tasks / Subtasks

- [ ] Task 1: Add proposal/approval schemas and handlers (AC: 1)
  - [ ] Define request/response models for proposal and decision actions.
  - [ ] Add tool handlers under `src/capital_os/tools/`.
- [ ] Task 2: Implement idempotent approval service path (AC: 2, 3)
  - [ ] Enforce exactly one canonical commit under duplicate concurrency.
  - [ ] Return prior canonical result for duplicates.
- [ ] Task 3: Wire API routes and logging (AC: 1, 4)
  - [ ] Register tools in API handler map.
  - [ ] Verify structured logging on success/failure.
- [ ] Task 4: Add concurrency/idempotency tests (AC: 2, 3)
  - [ ] Add integration tests for duplicate approve and retry safety.

## Dev Notes

### Developer Context Section

- This story operationalizes approval execution semantics.

### Technical Requirements

- Maintain deterministic conflict handling under concurrency.
- Preserve append-only audit guarantees for resulting writes.

### File Structure Requirements

- Likely touch:
  - `src/capital_os/tools/*approval*`
  - approval domain/service modules
  - integration/concurrency tests

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

- `_bmad-output/implementation-artifacts/4-2-proposal-and-approval-tools.md`
