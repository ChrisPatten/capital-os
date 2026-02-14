# Story 2.3: Simulation Performance Guardrails

Status: done

## Story

As a family-office AI operator,
I want simulation performance validated against the latency budget,
so that deterministic simulation remains operationally usable at target dataset scale.

## Acceptance Criteria

1. Performance tests include `simulate_spend` p95 latency assertions.
2. p95 latency remains `< 300ms` on the defined reference dataset profile.
3. Test output is deterministic/repeatable enough for CI guardrail use.
4. Test suite includes explicit pass/fail thresholds for simulation paths.

## Tasks / Subtasks

- [x] Task 1: Extend perf harness for simulation (AC: 1, 4)
  - [x] Update `tests/perf/test_tool_latency.py` for `simulate_spend` path.
  - [x] Add clear p95 threshold assertion.
- [x] Task 2: Align fixture profile to reference dataset (AC: 2)
  - [x] Use defined profile assumptions from architecture/PRD.
  - [x] Ensure warm-up/setup behavior is stable.
- [x] Task 3: Add CI-safe determinism checks (AC: 3)
  - [x] Keep measurement approach consistent across runs.
  - [x] Document acceptable variance assumptions in-test comments if needed.

## Dev Notes

### Developer Context Section

- Performance gates are acceptance constraints, not optional diagnostics.

### Technical Requirements

- Avoid flaky assertions; enforce deterministic harness setup.
- Keep perf checks scoped to simulation tool paths.

### File Structure Requirements

- Likely touch:
  - `tests/perf/test_tool_latency.py`

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

- Added `simulate_spend` performance test to `tests/perf/test_tool_latency.py`.
- Implemented explicit `p95 < 300ms` assertion for simulation tool path.
- Added repeat-run output hash equality assertion as CI anti-flake determinism guard.
- Executed regression suite: `54 passed`.

### File List

- `_bmad-output/implementation-artifacts/2-3-simulation-performance-guardrails.md`
- `tests/perf/test_tool_latency.py`
