# Story 8.3: Multi-Entity Scale and Regression Tests

Status: done

## Story

As a platform maintainer,  
I want multi-entity scale and regression coverage,  
so that Epic 8 behavior remains deterministic and performant at realistic family-office complexity.

## Acceptance Criteria

1. Add multi-entity performance suite covering at least 25 entities.
2. Verify no more than 20% degradation from defined baseline for covered operations.
3. Add regression tests for entity-isolated and consolidated deterministic outputs.
4. CI includes Epic 8 multi-entity regression/perf gates.

## Tasks / Subtasks

- [x] Task 1: Add scale dataset generator and perf harness (AC: 1, 2)
- [x] Task 2: Add deterministic regression cases for multi-entity flows (AC: 3)
- [x] Task 3: Wire CI gates and thresholds (AC: 2, 4)

## Notes

- Depends on Story 8.1 and 8.2.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Added reusable deterministic multi-entity dataset generator for posture/consolidation tests.
- Added multi-entity replay regression suite covering:
  - per-entity isolated posture hash stability
  - consolidated multi-entity hash stability
  - output invariance under shuffled entity/transfer ordering
- Added performance harness for `compute_consolidated_posture` at 25 entities with:
  - p95 `< 300ms` gate
  - measured-run median degradation budget (`<=20%`) against an in-test baseline window
- Added CI job `epic8-multi-entity-gates` to run Epic 8 replay and performance gates.

### File List

- `_bmad-output/implementation-artifacts/8-3-multi-entity-scale-and-regression-tests.md`
- `tests/support/multi_entity.py`
- `tests/replay/test_multi_entity_replay.py`
- `tests/perf/test_multi_entity_scale.py`
- `.github/workflows/ci.yml`
- `docs/testing-matrix.md`
- `docs/current-state.md`
