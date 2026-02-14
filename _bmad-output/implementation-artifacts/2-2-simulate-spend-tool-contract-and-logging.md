# Story 2.2: Simulate Spend Tool Contract and Logging

Status: done

## Story

As a family-office AI operator,
I want a schema-validated `simulate_spend` tool with deterministic observability,
so that simulation results are API-accessible and auditable.

## Acceptance Criteria

1. `simulate_spend` request/response schemas are defined and validated.
2. Tool is wired into `POST /tools/{tool_name}` routing and delegates to simulation service.
3. Success and validation failure are always event-logged with required fields.
4. Successful responses include deterministic `output_hash`.
5. Tests cover contract validation, success logging, and failure logging.

## Tasks / Subtasks

- [x] Task 1: Add schema contract for `simulate_spend` (AC: 1, 4)
  - [x] Extend `src/capital_os/schemas/tools.py` with explicit request/response models.
  - [x] Ensure deterministic field ordering and defaults.
- [x] Task 2: Implement tool handler (AC: 2, 4)
  - [x] Create `src/capital_os/tools/simulate_spend.py`.
  - [x] Validate payload and call simulation domain service.
- [x] Task 3: Wire API route and logging (AC: 2, 3)
  - [x] Update `src/capital_os/api/app.py` handler map.
  - [x] Ensure existing structured event logging captures success and failure.
- [x] Task 4: Add integration tests (AC: 3, 5)
  - [x] Extend `tests/integration/test_tool_contract_validation.py`.
  - [x] Extend `tests/integration/test_event_log_coverage.py`.

## Dev Notes

### Developer Context Section

- This story exposes simulation through the tool boundary.
- Keep API boundary thin and domain-first.

### Technical Requirements

- Deterministic error payload shape for validation failures.
- Required event fields: tool_name, correlation_id, input_hash, output_hash, timestamp, duration.

### File Structure Requirements

- Likely touch:
  - `src/capital_os/schemas/tools.py`
  - `src/capital_os/tools/simulate_spend.py`
  - `src/capital_os/api/app.py`
  - `tests/integration/*`

### References

- [Source: `initial_prd.md`]
- [Source: `ARCHITECTURE.md`]
- [Source: `_bmad-output/planning-artifacts/epic-2-spend-simulation.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Added `simulate_spend` request/response schemas and deterministic output structure.
- Implemented `simulate_spend` tool handler with structured success event logging and deterministic `output_hash`.
- Wired `simulate_spend` into `/tools/{tool_name}` API routing.
- Added integration tests for deterministic validation failure shape and success/failure event log coverage.
- Executed regression suite: `53 passed`.

### File List

- `_bmad-output/implementation-artifacts/2-2-simulate-spend-tool-contract-and-logging.md`
- `src/capital_os/schemas/tools.py`
- `src/capital_os/tools/simulate_spend.py`
- `src/capital_os/api/app.py`
- `tests/integration/test_tool_contract_validation.py`
- `tests/integration/test_event_log_coverage.py`
