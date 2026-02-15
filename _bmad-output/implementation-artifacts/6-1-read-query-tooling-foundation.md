# Story 6.1: Read Query Tooling Foundation

Status: ready-for-dev

## Story

As a family-office AI operator,
I want deterministic account and balance query tools with stable cursor pagination,
so that I can read canonical financial state safely without direct database access.

## Acceptance Criteria

1. Implement read tools:
  - `list_accounts(limit?, cursor?)`
  - `get_account_tree(root_account_id?)`
  - `get_account_balances(as_of_date, source_policy)`
2. All read responses use deterministic ordering with explicit tie-break keys.
3. Cursor pagination is stable and deterministic across repeated identical queries.
4. `source_policy` supports `ledger_only|snapshot_only|best_available` and returns deterministic output shapes.
5. Validation failures return deterministic 422 payload shape and are event-logged.
6. Successful invocations emit event logs with required fields (`tool_name`, `correlation_id`, `input_hash`, `output_hash`, `timestamp`, `duration`).
7. Read tools do not mutate canonical ledger tables under any code path.
8. Replay tests prove stable `output_hash` for identical state + input.

## Tasks / Subtasks

- [ ] Task 1: Add query schema/contracts (AC: 1, 4, 5)
  - [ ] Extend `src/capital_os/schemas/tools.py` with request/response models for new read tools.
  - [ ] Ensure deterministic field ordering and cursor format contract.
- [ ] Task 2: Implement deterministic query services (AC: 1, 2, 3, 7)
  - [ ] Add `src/capital_os/domain/query/service.py` for ordered query orchestration.
  - [ ] Add canonical cursor encode/decode helper in `src/capital_os/domain/query/pagination.py`.
- [ ] Task 3: Extend repository read methods (AC: 1, 2, 3, 4)
  - [ ] Add deterministic SQL queries and index-backed sort order in `src/capital_os/domain/ledger/repository.py`.
  - [ ] Ensure `best_available` source selection is deterministic when ledger/snapshot data diverge.
- [ ] Task 4: Wire tools and API dispatch (AC: 1, 5, 6)
  - [ ] Add tool handlers under `src/capital_os/tools/` for each read tool.
  - [ ] Register handlers in `src/capital_os/api/app.py`.
- [ ] Task 5: Add tests for determinism and no-write behavior (AC: 2, 3, 7, 8)
  - [ ] Add integration tests in `tests/integration/test_read_query_tools.py`.
  - [ ] Add replay tests in `tests/replay/test_read_query_replay.py`.
  - [ ] Add assertions for event logging in `tests/integration/test_event_log_coverage.py`.

## Dev Notes

### Constraints
- Keep writes impossible from read tool code paths.
- Reuse existing hash/event logging path used by write tools.
- Do not introduce non-deterministic default ordering in SQL.

### Suggested Migration Support
- Add `migrations/0003_read_query_indexes.sql` for query performance and stable cursor sort keys.

### References
- `prd_update_0215.md` (FR-13, FR-14, NFR-08)
- `ARCHITECTURE.md`
- `docs/backlog-phase1-delta-0215.md`

## Definition of Done
- ACs 1-8 pass with automated tests.
- p95 read tool latency remains below baseline threshold on reference dataset.
- Story status moved to `review` with file list and test evidence.
