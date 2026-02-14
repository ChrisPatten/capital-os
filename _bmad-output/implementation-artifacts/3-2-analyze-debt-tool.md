# Story 3.2: Analyze Debt Tool

Status: ready-for-dev

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

- [ ] Task 1: Add `analyze_debt` schemas (AC: 1, 3)
  - [ ] Extend `src/capital_os/schemas/tools.py` with debt request/response models.
  - [ ] Model optional payoff sensitivity inputs explicitly.
- [ ] Task 2: Add tool handler/service wiring (AC: 2, 3, 4)
  - [ ] Create `src/capital_os/tools/analyze_debt.py`.
  - [ ] Delegate to debt domain service and return deterministic output.
- [ ] Task 3: Wire API route and logging (AC: 2, 5)
  - [ ] Update `src/capital_os/api/app.py` tool registry.
  - [ ] Verify success/failure event logging coverage.
- [ ] Task 4: Add validation/integration tests (AC: 1, 5)
  - [ ] Extend contract validation tests and event log coverage tests.

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

TBD

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Story created and marked ready-for-dev.

### File List

- `_bmad-output/implementation-artifacts/3-2-analyze-debt-tool.md`
