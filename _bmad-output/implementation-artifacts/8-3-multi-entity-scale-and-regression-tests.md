# Story 8.3: Multi-Entity Scale and Regression Tests

Status: ready-for-dev

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

- [ ] Task 1: Add scale dataset generator and perf harness (AC: 1, 2)
- [ ] Task 2: Add deterministic regression cases for multi-entity flows (AC: 3)
- [ ] Task 3: Wire CI gates and thresholds (AC: 2, 4)

## Notes

- Depends on Story 8.1 and 8.2.
