# Story 3.1: Liability Analytics Model

Status: done

## Story

As a family-office AI operator,
I want deterministic liability scoring and tie-break behavior,
so that debt prioritization results are stable and explainable.

## Acceptance Criteria

1. Liability analytics model defines scoring inputs and weighting logic.
2. Deterministic tie-breakers are implemented for equal-score liabilities.
3. Identical inputs produce identical ranking output order.
4. Unit tests assert stable ranking and tie-break reproducibility.

## Tasks / Subtasks

- [x] Task 1: Define liability score model (AC: 1)
  - [x] Add domain structures/functions in `src/capital_os/domain/debt/`.
  - [x] Include explicit score components used for ranking.
- [x] Task 2: Implement deterministic tie-breakers (AC: 2, 3)
  - [x] Add canonical ordering fallback fields.
  - [x] Ensure sorting remains stable across runs.
- [x] Task 3: Add unit tests for ranking determinism (AC: 4)
  - [x] Create tests for ties, mixed liabilities, and repeat-run equality.

## Dev Notes

### Developer Context Section

- Epic 3 introduces deterministic debt analysis foundation.

### Technical Requirements

- Maintain replay safety and deterministic ordering.
- Avoid hidden randomness in ranking implementation.

### File Structure Requirements

- Likely touch:
  - `src/capital_os/domain/debt/*`
  - `tests/unit/*debt*`

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

- Added debt domain engine and service in `src/capital_os/domain/debt/`.
- Implemented deterministic scoring and canonical tie-breaker ordering.
- Added unit and replay determinism tests for debt ranking behavior.

### File List

- `_bmad-output/implementation-artifacts/3-1-liability-analytics-model.md`
- `src/capital_os/domain/debt/__init__.py`
- `src/capital_os/domain/debt/engine.py`
- `src/capital_os/domain/debt/service.py`
- `tests/unit/test_debt_engine.py`
- `tests/replay/test_output_replay.py`
