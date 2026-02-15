# Story 5.2: Migration Reversibility CI Gate

Status: done

## Story

As a platform engineer,
I want CI to enforce migration apply/rollback/re-apply cycles,
so that schema changes remain reversible and safe.

## Acceptance Criteria

1. CI job applies migrations on clean DB.
2. CI job rolls migrations back to baseline.
3. CI job re-applies migrations successfully after rollback.
4. CI fails on rollback or re-apply defects.
5. Workflow is documented for local reproduction.

## Tasks / Subtasks

- [x] Task 1: Add migration cycle CI job (AC: 1, 2, 3, 4)
  - [x] Configure pipeline job to apply, rollback, and re-apply.
  - [x] Ensure non-zero exit on any phase failure.
- [x] Task 2: Add test fixtures/scripts as needed (AC: 1, 2, 3)
  - [x] Provide deterministic DB setup for migration cycle testing.
- [x] Task 3: Document local reproduction steps (AC: 5)
  - [x] Add concise docs for running migration cycle checks locally.

## Dev Notes

### Developer Context Section

- Supports PRD closure requirement on migration reversibility confidence.

### Technical Requirements

- Must exercise real migration SQL scripts (`0001`, `0002`, ...).
- Keep CI runtime reasonable while preserving confidence.

### File Structure Requirements

- Likely touch:
  - CI workflow config files
  - migration test scripts/docs

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

- Added `scripts/check_migration_cycle.py` to enforce apply -> rollback -> re-apply checks against real SQL migration scripts.
- Added CI workflow job `migration-reversibility` in `.github/workflows/ci.yml`.
- Documented local reproduction command in `docs/development-workflow.md`.

### File List

- `_bmad-output/implementation-artifacts/5-2-migration-reversibility-ci-gate.md`
- `scripts/check_migration_cycle.py`
- `.github/workflows/ci.yml`
- `docs/development-workflow.md`
