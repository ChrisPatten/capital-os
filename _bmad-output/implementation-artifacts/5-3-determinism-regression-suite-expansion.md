# Story 5.3: Determinism Regression Suite Expansion

Status: done

## Story

As a platform quality owner,
I want expanded replay/hash regression coverage across all Phase 1 tools,
so that deterministic behavior is continuously enforced.

## Acceptance Criteria

1. Replay/hash reproducibility tests are extended for all newly added tools.
2. Seeded repeat-run hash equality is validated.
3. Determinism regressions fail CI clearly.
4. Test coverage documentation identifies deterministic guarantees by tool.

## Tasks / Subtasks

- [x] Task 1: Expand replay test matrix (AC: 1, 2)
  - [x] Extend replay suites to include simulation, debt, and approval tool outputs.
  - [x] Verify same input/state yields same output hash.
- [x] Task 2: Add seeded repeat-run checks (AC: 2)
  - [x] Introduce seeded run loops for deterministic equality assertions.
- [x] Task 3: Wire determinism checks into CI gate (AC: 3)
  - [x] Ensure failures are explicit and actionable.
- [x] Task 4: Document deterministic coverage (AC: 4)
  - [x] Summarize tool-by-tool determinism checks in project docs.

## Dev Notes

### Developer Context Section

- Final hardening story for deterministic behavior enforcement.

### Technical Requirements

- Canonicalization rules must remain consistent with hashing contract.
- Keep tests stable and repeatable under CI constraints.

### File Structure Requirements

- Likely touch:
  - `tests/replay/*`
  - CI config and docs

### References

- [Source: `initial_prd.md`]
- [Source: `docs/backlog-phase1-prd-closure.md`]
- [Source: `_bmad-output/planning-artifacts/epic-5-dod-and-ci-hardening.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Expanded replay suite in `tests/replay/test_output_replay.py` with seeded repeat-run checks.
- Added deterministic replay assertions for approval decisions (`approve_proposed_transaction`, `reject_proposed_transaction`).
- Added CI job `determinism-regression` and documented tool-by-tool deterministic guarantees.

### File List

- `_bmad-output/implementation-artifacts/5-3-determinism-regression-suite-expansion.md`
- `tests/replay/test_output_replay.py`
- `.github/workflows/ci.yml`
- `docs/testing-matrix.md`
