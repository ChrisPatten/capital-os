# Story 2.1: Simulation Engine

Status: done

## Story

As a family-office AI operator,
I want deterministic one-time and recurring spend projections,
so that I can evaluate possible spend changes without mutating canonical ledger state.

## Acceptance Criteria

1. Simulation engine supports one-time spend projection branch.
2. Simulation engine supports recurring spend projection branch.
3. Simulation execution does not mutate canonical ledger tables.
4. Outputs are deterministic for identical inputs and stored state.
5. Tests cover one-time and recurring cases plus non-mutation guarantees.

## Tasks / Subtasks

- [x] Task 1: Implement one-time simulation branch (AC: 1, 4)
  - [x] Add deterministic one-time spend projection logic under `src/capital_os/domain/simulation/`.
  - [x] Normalize money values to `NUMERIC(20,4)` equivalent behavior in projection calculations.
- [x] Task 2: Implement recurring simulation branch (AC: 2, 4)
  - [x] Add recurring cadence handling with deterministic period ordering.
  - [x] Ensure branch output ordering is stable for hashing and replay.
- [x] Task 3: Enforce read-only simulation behavior (AC: 3)
  - [x] Guarantee no write path to canonical ledger tables during simulation.
  - [x] Add explicit integration assertions proving no mutation.
- [x] Task 4: Add deterministic and branch coverage tests (AC: 4, 5)
  - [x] Add/extend `tests/unit/` simulation engine tests.
  - [x] Add/extend integration tests for repeated identical-input equality.

## Dev Notes

### Developer Context Section

- Epic 2 starts non-mutating projection capability.
- Keep computation deterministic and auditable.

### Technical Requirements

- Preserve strict separation between projection logic and ledger writes.
- Ensure branch behavior is replay-safe and stable.

### File Structure Requirements

- Likely touch:
  - `src/capital_os/domain/simulation/*`
  - `tests/unit/*simulation*`
  - `tests/integration/*simulation*`

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

- Implemented deterministic simulation engine with one-time and recurring spend branches.
- Added strict monetary normalization and deterministic ordering across projection output.
- Added non-mutation integration test proving canonical tables are unchanged by simulation.
- Ran adversarial code review and fixed duplicate `spend_id` collision risk via input validation.
- Executed regression suite: `50 passed`.

### File List

- `_bmad-output/implementation-artifacts/2-1-simulation-engine.md`
- `src/capital_os/domain/simulation/__init__.py`
- `src/capital_os/domain/simulation/engine.py`
- `src/capital_os/domain/simulation/service.py`
- `tests/unit/test_simulation_engine.py`
- `tests/integration/test_simulation_non_mutation.py`
