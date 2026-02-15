# Story 7.1: Reconciliation Domain and Tool

Status: done

## Story

As a family-office AI operator,  
I want a deterministic `reconcile_account` tool,  
so that I can compare ledger vs snapshot balances and receive proposal-only adjustment guidance.

## Acceptance Criteria

1. Implement `reconcile_account(account_id, as_of_date, method)` tool.
2. Response includes `ledger_balance`, `snapshot_balance`, and `delta`.
3. Response includes `suggested_adjustment_bundle` only as proposal (`auto_commit=false`).
4. Reconciliation path must not mutate canonical ledger transaction/posting tables.
5. Successful and validation-failure invocations are event-logged.

## Tasks / Subtasks

- [x] Task 1: Add reconciliation domain service (AC: 1, 2, 3, 4)
  - [x] Add `src/capital_os/domain/reconciliation/service.py`.
  - [x] Add repository read helper for single-account reconciliation context.
- [x] Task 2: Add tool contract + API wiring (AC: 1, 2, 5)
  - [x] Extend `src/capital_os/schemas/tools.py` with reconcile request/response models.
  - [x] Add `src/capital_os/tools/reconcile_account.py`.
  - [x] Register `reconcile_account` in `src/capital_os/api/app.py`.
- [x] Task 3: Add integration coverage (AC: 2, 3, 4, 5)
  - [x] Add `tests/integration/test_reconcile_account_tool.py`.
  - [x] Extend event log coverage in `tests/integration/test_event_log_coverage.py`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Implemented non-mutating reconciliation domain logic with deterministic suggested adjustment payload generation.
- Added proposal-only adjustment bundle shape with explicit `auto_commit=false`.
- Added tool routing, schema validation, and event logging for success/validation-failure paths.

### File List

- `_bmad-output/implementation-artifacts/7-1-reconciliation-domain-and-tool.md`
- `src/capital_os/domain/ledger/repository.py`
- `src/capital_os/domain/reconciliation/__init__.py`
- `src/capital_os/domain/reconciliation/service.py`
- `src/capital_os/schemas/tools.py`
- `src/capital_os/tools/reconcile_account.py`
- `src/capital_os/api/app.py`
- `tests/integration/test_reconcile_account_tool.py`
- `tests/integration/test_event_log_coverage.py`
