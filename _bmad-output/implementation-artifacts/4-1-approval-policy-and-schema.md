# Story 4.1: Approval Policy and Schema

Status: done

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

- [x] Task 1: Add approval policy config and domain model (AC: 1, 2)
  - [x] Introduce approval policy representation and load path.
  - [x] Add proposal lifecycle domain states.
- [x] Task 2: Implement threshold gating behavior (AC: 1, 3)
  - [x] Route above-threshold writes to proposal path.
  - [x] Return deterministic proposed response without ledger mutation.
- [x] Task 3: Add schema updates (AC: 2, 3)
  - [x] Extend tool schemas for proposal status and metadata.
- [x] Task 4: Add integration tests (AC: 4)
  - [x] Assert above-threshold produces proposal only.
  - [x] Assert canonical tables unchanged for proposed-only outcome.

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

GPT-5 Codex

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Added configurable approval threshold via `CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT` and domain policy loader.
- Added proposal lifecycle persistence schema (`approval_proposals`, `approval_decisions`) and migration wiring.
- Implemented deterministic proposal response path in `record_transaction_bundle` with no ledger mutation.
- Added integration coverage for above-threshold proposal-only behavior and non-mutation assertions.

### File List

- `src/capital_os/config.py`
- `src/capital_os/domain/approval/policy.py`
- `src/capital_os/domain/approval/repository.py`
- `src/capital_os/domain/ledger/service.py`
- `src/capital_os/schemas/tools.py`
- `migrations/0003_approval_gates.sql`
- `migrations/0003_approval_gates.rollback.sql`
- `tests/conftest.py`
- `tests/integration/test_approval_workflow.py`
