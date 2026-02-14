# Story 3.1: Liability Analytics Model

Status: ready-for-dev

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

- [ ] Task 1: Define liability score model (AC: 1)
  - [ ] Add domain structures/functions in `src/capital_os/domain/debt/`.
  - [ ] Include explicit score components used for ranking.
- [ ] Task 2: Implement deterministic tie-breakers (AC: 2, 3)
  - [ ] Add canonical ordering fallback fields.
  - [ ] Ensure sorting remains stable across runs.
- [ ] Task 3: Add unit tests for ranking determinism (AC: 4)
  - [ ] Create tests for ties, mixed liabilities, and repeat-run equality.

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

TBD

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Story created and marked ready-for-dev.

### File List

- `_bmad-output/implementation-artifacts/3-1-liability-analytics-model.md`
