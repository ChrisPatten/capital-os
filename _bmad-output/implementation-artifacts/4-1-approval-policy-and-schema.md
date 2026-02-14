# Story 4.1: Approval Policy and Schema

Status: ready-for-dev

## Story

As a family-office AI operator,
I want configurable approval thresholds and proposal lifecycle schema,
so that high-impact writes are gated before ledger mutation.

## Acceptance Criteria

1. Approval threshold policy is configurable and enforced.
2. Proposal entity lifecycle schema is implemented.
3. Above-threshold write requests return `status="proposed"` and do not mutate ledger state.
4. Tests verify policy threshold behavior and non-mutation for proposed results.

## Tasks / Subtasks

- [ ] Task 1: Add approval policy config and domain model (AC: 1, 2)
  - [ ] Introduce approval policy representation and load path.
  - [ ] Add proposal lifecycle domain states.
- [ ] Task 2: Implement threshold gating behavior (AC: 1, 3)
  - [ ] Route above-threshold writes to proposal path.
  - [ ] Return deterministic proposed response without ledger mutation.
- [ ] Task 3: Add schema updates (AC: 2, 3)
  - [ ] Extend tool schemas for proposal status and metadata.
- [ ] Task 4: Add integration tests (AC: 4)
  - [ ] Assert above-threshold produces proposal only.
  - [ ] Assert canonical tables unchanged for proposed-only outcome.

## Dev Notes

### Developer Context Section

- Epic 4 introduces approval-gated writes with auditable proposal lifecycle.

### Technical Requirements

- Proposal path must be deterministic and idempotent-safe.
- No silent mutation when policy requires approval.

### File Structure Requirements

- Likely touch:
  - approval/policy domain modules
  - tool schemas and integration tests

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

- `_bmad-output/implementation-artifacts/4-1-approval-policy-and-schema.md`
