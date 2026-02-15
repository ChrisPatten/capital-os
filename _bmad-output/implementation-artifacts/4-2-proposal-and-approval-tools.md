# Story 4.2: Proposal and Approval Tools

Status: done

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

- [x] Task 1: Add proposal/approval schemas and handlers (AC: 1)
  - [x] Define request/response models for proposal and decision actions.
  - [x] Add tool handlers under `src/capital_os/tools/`.
- [x] Task 2: Implement idempotent approval service path (AC: 2, 3)
  - [x] Enforce exactly one canonical commit under duplicate concurrency.
  - [x] Return prior canonical result for duplicates.
- [x] Task 3: Wire API routes and logging (AC: 1, 4)
  - [x] Register tools in API handler map.
  - [x] Verify structured logging on success/failure.
- [x] Task 4: Add concurrency/idempotency tests (AC: 2, 3)
  - [x] Add integration tests for duplicate approve and retry safety.

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

GPT-5 Codex

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Added `approve_proposed_transaction` and `reject_proposed_transaction` tool schemas and handlers.
- Implemented approval/rejection service paths with deterministic replay-safe responses.
- Wired tools into FastAPI tool registry and event logging.
- Added concurrency test coverage proving duplicate concurrent approvals produce exactly one canonical transaction commit.

### File List

- `src/capital_os/domain/approval/service.py`
- `src/capital_os/tools/approve_proposed_transaction.py`
- `src/capital_os/tools/reject_proposed_transaction.py`
- `src/capital_os/api/app.py`
- `src/capital_os/schemas/tools.py`
- `tests/integration/test_approval_workflow.py`
- `tests/integration/test_tool_contract_validation.py`
- `tests/integration/test_event_log_coverage.py`
