# Story 5.1: Traceability Matrix

Status: done

## Story

As a delivery lead,
I want explicit PRD criterion-to-code/test traceability,
so that Phase 1 completion can be audited against SC/FR/NFR requirements.

## Acceptance Criteria

1. A traceability matrix maps SC/FR/NFR items to implementation artifacts.
2. Each in-scope Phase 1 criterion has executable coverage reference.
3. Gaps are explicitly called out with remediation notes.
4. Traceability document is versioned in repo and reviewable in PRs.

## Tasks / Subtasks

- [x] Task 1: Build SC/FR/NFR inventory (AC: 1)
  - [x] Extract criterion IDs from PRD and related planning docs.
- [x] Task 2: Map criteria to code/tests (AC: 1, 2)
  - [x] Link each criterion to source files and test files.
- [x] Task 3: Record gaps and remediation path (AC: 3)
  - [x] Add explicit unresolved items and planned closures.
- [x] Task 4: Commit matrix artifact and checks (AC: 4)
  - [x] Add doc under `docs/` and include in review workflow.

## Dev Notes

### Developer Context Section

- Epic 5 validates overall Phase 1 definition-of-done.

### Technical Requirements

- Keep mappings concrete and verifiable.
- Prefer deterministic references (file paths and test names).

### File Structure Requirements

- Likely touch:
  - `docs/*traceability*`

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

- Added `docs/traceability-matrix.md` with SC/FR/NFR mappings to implementation and executable test coverage.
- Recorded open PRD gaps with remediation notes (egress testing, full-scale perf gate, branch coverage threshold).
- Updated documentation index and testing matrix references.

### File List

- `_bmad-output/implementation-artifacts/5-1-traceability-matrix.md`
- `docs/traceability-matrix.md`
- `docs/testing-matrix.md`
- `docs/README.md`
