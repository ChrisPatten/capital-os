# Story 6.2: Transaction and Obligation Query Surface

Status: done

## Story

As a family-office AI operator,
I want deterministic transaction and obligation query tools,
so that I can inspect canonical activity and recurring commitments without direct DB access.

## Acceptance Criteria

1. Implement read tools:
  - `list_transactions(limit?, cursor?)`
  - `get_transaction_by_external_id(source_system, external_id)`
  - `list_obligations(limit?, cursor?, active_only?)`
2. All responses use deterministic ordering with explicit tie-break keys.
3. Cursor pagination is stable and deterministic across repeated identical queries.
4. Validation failures return deterministic 422 payload shape and are event-logged.
5. Successful invocations emit event logs with required fields.
6. Read tools do not mutate canonical ledger tables under any code path.
7. Replay tests prove stable `output_hash` for identical state + input.

## Tasks / Subtasks

- [x] Task 1: Add query schema/contracts for transactions and obligations (AC: 1, 4)
- [x] Task 2: Extend read repository/service with deterministic SQL sort keys and cursor codecs (AC: 2, 3)
- [x] Task 3: Implement tool handlers and API wiring (AC: 1, 4, 5)
- [x] Task 4: Add integration/replay/no-write coverage (AC: 3, 6, 7)

## Completion Notes

- Added deterministic transaction pagination ordered by `(transaction_date DESC, transaction_id ASC)`.
- Added deterministic obligation pagination ordered by `(next_due_date ASC, obligation_id ASC)` with active filter.
- Added event-log coverage and validation-shape coverage for new query tools.
- Added migration `0007_query_surface_indexes.sql` (+ rollback) for query-surface indexes.

## File List

- `_bmad-output/implementation-artifacts/6-2-transaction-and-obligation-query-surface.md`
- `migrations/0007_query_surface_indexes.sql`
- `migrations/0007_query_surface_indexes.rollback.sql`
- `src/capital_os/api/app.py`
- `src/capital_os/db/testing.py`
- `src/capital_os/domain/ledger/repository.py`
- `src/capital_os/domain/query/pagination.py`
- `src/capital_os/domain/query/service.py`
- `src/capital_os/schemas/tools.py`
- `src/capital_os/tools/list_transactions.py`
- `src/capital_os/tools/get_transaction_by_external_id.py`
- `src/capital_os/tools/list_obligations.py`
- `tests/integration/test_epic6_query_surface_tools.py`
- `tests/replay/test_query_surface_replay.py`
- `tests/integration/test_tool_contract_validation.py`
- `tests/integration/test_event_log_coverage.py`
