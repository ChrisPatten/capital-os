# Story 9.1: Period Close/Lock and Adjusting Entries

Status: done

## Story

As a controller,  
I want accounting periods that can be closed/locked with governed adjusting entries,  
so that historical financial statements are protected while permitted corrections remain auditable.

## Acceptance Criteria

1. Implement `close_period(period_key)` and `lock_period(period_key)` tools with deterministic idempotent responses.
2. Writes into closed periods are blocked unless explicitly marked as adjusting entries with reason codes.
3. Writes into locked periods are blocked unless an elevated override path is used.
4. Period operations and blocked-write outcomes remain fully event-logged and replay-stable.

## Tasks / Subtasks

- [x] Task 1: Add period-control schema and migration rollback support (AC: 1, 2, 3)
- [x] Task 2: Add period domain service + `close_period`/`lock_period` tool handlers (AC: 1, 4)
- [x] Task 3: Enforce close/lock behavior in transaction write path with adjusting-entry reason tagging (AC: 2, 3, 4)
- [x] Task 4: Add integration/replay tests for period controls and write-path enforcement (AC: 1, 2, 3, 4)

## Notes

- Depends on existing approval-gate semantics in Epic 4.
- Must preserve deterministic hashing and fail-closed write logging behavior.

## Dev Agent Record

- Added migration `migrations/0006_periods_policies.sql` (+ rollback) with `accounting_periods` table and adjusting-entry columns.
- Implemented period domain/service and tool handlers:
  - `src/capital_os/domain/periods/service.py`
  - `src/capital_os/tools/close_period.py`
  - `src/capital_os/tools/lock_period.py`
- Enforced closed/locked period write constraints in transaction recording path.
- Added test coverage:
  - `tests/integration/test_period_policy_controls.py`
  - `tests/integration/test_event_log_coverage.py`
  - `tests/integration/test_tool_contract_validation.py`
