# Story 1.4: Posture Performance and Explainability

Status: ready-for-dev

## Story

As a family-office AI operator,
I want posture outputs to be explainable and fast,
so that decisions are auditable and tool responses meet latency expectations.

## Acceptance Criteria

1. `compute_capital_posture` includes deterministic explanation fields that show key contributing balances/assumptions.
2. Explanation payload is hash-safe and contains no secrets.
3. Performance tests validate p95 latency `< 300ms` on the defined reference dataset profile.
4. Replay behavior remains stable with explanation fields included.
5. Test suite includes explicit assertions for explainability determinism and performance budget.

## Tasks / Subtasks

- [ ] Task 1: Define explainability payload contract (AC: 1, 2)
  - [ ] Add explicit explanation section to posture response schema
  - [ ] Ensure ordered, deterministic representation
- [ ] Task 2: Populate explanation from engine inputs/outputs (AC: 1, 4)
  - [ ] Include contributing account totals and reserve assumptions
  - [ ] Exclude sensitive material or raw secrets
- [ ] Task 3: Add performance harness assertions (AC: 3, 5)
  - [ ] Extend `tests/perf/test_tool_latency.py` for posture tool p95 path
  - [ ] Use reference dataset scale assumptions from architecture/PRD
- [ ] Task 4: Add replay checks including explanation payload (AC: 4, 5)
  - [ ] Extend `tests/replay/test_output_replay.py` assertions
  - [ ] Confirm output hash stability with explanation section present

## Dev Notes

### Developer Context Section

- This story finalizes Epic 1 quality gates.
- Scope includes output transparency and speed, not new business metrics.
- Avoid verbose explanation payloads that increase token and latency cost without decision value.

### Technical Requirements

- Explanation fields must be deterministic and minimal.
- Maintain stable key ordering and numeric normalization for hash reproducibility.
- Performance measurement should reflect realistic dataset setup used by repo tests.

### Architecture Compliance

- Preserve observability and determinism strategy from `ARCHITECTURE.md`.
- Do not compromise layering to optimize prematurely.
- Keep performance improvements local and measurable.

### Library and Framework Requirements

- Reuse existing pytest performance marker and harness pattern.
- Avoid introducing benchmarking dependencies unless necessary.

### File Structure Requirements

- Likely touch:
  - `src/capital_os/schemas/tools.py`
  - posture domain/service modules
  - `tests/perf/test_tool_latency.py`
  - `tests/replay/test_output_replay.py`
  - integration validation tests as needed

### Testing Requirements

- Deterministic explanation payload assertions.
- Perf p95 assertion for posture.
- Full suite regression pass.

### Previous Story Intelligence

- Story 1.3 contract wiring is prerequisite.
- Keep explanation payload aligned with response schema introduced in Story 1.3.

### References

- [Source: `initial_prd.md`]
- [Source: `ARCHITECTURE.md`]
- [Source: `tests/perf/test_tool_latency.py`]
- [Source: `tests/replay/test_output_replay.py`]
- [Source: `_bmad-output/planning-artifacts/epic-1-capital-posture.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Create-story workflow executed in YOLO mode per SM activation rule.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `_bmad-output/implementation-artifacts/1-4-posture-performance-and-explainability.md`
