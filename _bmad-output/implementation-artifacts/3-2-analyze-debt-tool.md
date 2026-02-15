# Story 3.2: Analyze Debt Tool

Status: done

## Story

As a family-office AI operator,
I want a schema-validated `analyze_debt` tool,
so that debt prioritization can be invoked deterministically via the Capital OS API.

## Acceptance Criteria

1. `analyze_debt` request/response schemas are implemented and validated.
2. Tool handler and route wiring are added to `POST /tools/{tool_name}`.
3. Service supports optional payoff amount sensitivity branch.
4. Successful responses include deterministic `output_hash`.
5. Validation failures and success paths are event-logged.

## Tasks / Subtasks

- [x] Task 1: Add `analyze_debt` schemas (AC: 1, 3)
  - [x] Extend `src/capital_os/schemas/tools.py` with debt request/response models.
  - [x] Model optional payoff sensitivity inputs explicitly.
- [x] Task 2: Add tool handler/service wiring (AC: 2, 3, 4)
  - [x] Create `src/capital_os/tools/analyze_debt.py`.
  - [x] Delegate to debt domain service and return deterministic output.
- [x] Task 3: Wire API route and logging (AC: 2, 5)
  - [x] Update `src/capital_os/api/app.py` tool registry.
  - [x] Verify success/failure event logging coverage.
- [x] Task 4: Add validation/integration tests (AC: 1, 5)
  - [x] Extend contract validation tests and event log coverage tests.

## Dev Notes

### Developer Context Section

- This story adds API/tool contract for debt analysis.

### Technical Requirements

- Preserve deterministic serialization and hash input normalization.
- Keep tool layer thin; domain service owns ranking logic.

### File Structure Requirements

- Likely touch:
  - `src/capital_os/schemas/tools.py`
  - `src/capital_os/tools/analyze_debt.py`
  - `src/capital_os/api/app.py`
  - `tests/integration/*`

### References

- [Source: `initial_prd.md`]
- [Source: `ARCHITECTURE.md`]
- [Source: `_bmad-output/planning-artifacts/epic-3-debt-analysis.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Added `AnalyzeDebtIn`/`AnalyzeDebtOut` tool contracts with deterministic decimal normalization.
- Implemented `analyze_debt` tool handler and wired it into `POST /tools/{tool_name}` registry.
- Added integration coverage for success path, validation failures, event logging, and hash determinism.

### File List

- `_bmad-output/implementation-artifacts/3-2-analyze-debt-tool.md`
- `src/capital_os/schemas/tools.py`
- `src/capital_os/tools/analyze_debt.py`
- `src/capital_os/api/app.py`
- `tests/integration/test_analyze_debt_tool.py`
