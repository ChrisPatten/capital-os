# Story 1.1: Posture Domain Model and Inputs

Status: done

## Story

As a family-office AI operator,
I want a deterministic posture input model and account-selection rules,
so that capital posture calculations are replayable, auditable, and consistent across runs.

## Acceptance Criteria

1. A posture input model is defined in domain code with explicit fields for:
  - liquidity account set
  - burn analysis window
  - reserve policy parameters
  - currency scope (USD only in this slice)
2. Account selection rules are deterministic and documented (same state/config -> same ordered inputs).
3. Selection logic rejects invalid account inclusion cases (unknown account, disallowed account type, duplicate identifiers).
4. Monetary and timestamp input normalization follows existing deterministic rules already used by the ledger layer.
5. Unit tests cover edge cases and account-type boundaries for posture input selection.
6. No write-path behavior regresses for existing ledger tools and tests remain green.

## Tasks / Subtasks

- [x] Task 1: Add posture domain input model and config container (AC: 1, 4)
  - [x] Create `src/capital_os/domain/posture/__init__.py`
  - [x] Create `src/capital_os/domain/posture/models.py` with typed structures for posture inputs
  - [x] Reuse existing normalization behavior from `src/capital_os/observability/hashing.py` and `src/capital_os/domain/ledger/invariants.py`
- [x] Task 2: Implement deterministic account selection (AC: 2, 3)
  - [x] Create `src/capital_os/domain/posture/service.py`
  - [x] Add deterministic ordering and validation rules for included accounts
  - [x] Ensure selection logic is read-only and does not mutate canonical tables
- [x] Task 3: Add repository read helpers for posture inputs (AC: 1, 2, 3)
  - [x] Extend `src/capital_os/domain/ledger/repository.py` with read queries needed by posture input selection
  - [x] Keep query ordering deterministic and explicit
- [x] Task 4: Add tests for boundaries and determinism (AC: 2, 3, 5, 6)
  - [x] Add `tests/unit/test_posture_inputs.py`
  - [x] Add/extend integration coverage for account selection against realistic account hierarchies
  - [x] Verify full suite passes and no regression in existing tests

## Dev Notes

### Developer Context Section

- This story builds the foundation for Epic 1 and unblocks:
  - Story 1.2 (`deterministic-posture-engine`)
  - Story 1.3 (`compute-capital-posture-tool-contract`)
- Keep this story strictly focused on model + deterministic input selection, not posture formula outputs.
- Preserve current domain-first layering:
  - API/tools -> domain services -> repository/DB
- Do not introduce new write endpoints or schema migrations in this story unless absolutely required.

### Technical Requirements

- Python 3.11+.
- Keep existing stack patterns used in this repository:
  - FastAPI transport remains unchanged in this story.
  - SQLite remains canonical store.
  - Pydantic v2 style models for validation where appropriate.
- Determinism rules are non-negotiable:
  - sorted/canonical ordering
  - stable decimal normalization
  - UTC timestamp handling

### Architecture Compliance

- Respect `ARCHITECTURE.md` scope and constraints:
  - maintain deterministic behavior
  - preserve append-only/audit guarantees indirectly by avoiding new mutation paths here
  - maintain single-source truth in SQLite
- Keep tool boundary thin; this story should remain mostly domain/repository/test work.

### Library and Framework Requirements

- Use currently configured project dependencies from `pyproject.toml`:
  - `fastapi>=0.116.0`
  - `pydantic>=2.11.0`
  - `pytest>=8.3.0` (dev)
- Do not add new third-party dependencies for this story without explicit need.

### File Structure Requirements

- New posture code should live under:
  - `src/capital_os/domain/posture/`
- Reuse existing modules where practical:
  - `src/capital_os/domain/ledger/repository.py`
  - `src/capital_os/domain/ledger/invariants.py`
  - `src/capital_os/observability/hashing.py`
- Tests should align with existing layout:
  - unit tests in `tests/unit/`
  - integration tests in `tests/integration/`

### Testing Requirements

- Add explicit determinism tests:
  - same DB state + config returns byte-stable selection payload.
- Add negative tests:
  - invalid account references
  - invalid account types
  - duplicate accounts in selection request
- Run full test suite and ensure no regression in existing 14 passing tests.

### Git Intelligence Summary

- Recent commits indicate the baseline is already migrated to SQLite and ledger-core is stable.
- Follow existing code patterns; avoid structural divergence in new posture module organization.

### Project Context Reference

- `project-context.md` not found in this repository.
- Primary sources used:
  - `initial_prd.md` (FR-06 determinism and posture requirement)
  - `ARCHITECTURE.md` (layering and deterministic constraints)
  - `_bmad-output/planning-artifacts/epic-1-capital-posture.md` (story objective)

### References

- [Source: `initial_prd.md`]
- [Source: `ARCHITECTURE.md`]
- [Source: `_bmad-output/planning-artifacts/epic-1-capital-posture.md`]
- [Source: `pyproject.toml`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Create-story workflow executed in YOLO mode per SM activation rule.
- Added posture input domain models with deterministic timestamp and money normalization.
- Implemented read-only deterministic account selection for liquidity inputs.
- Added repository helper for deterministic account lookup by IDs.
- Added posture unit/integration tests and ran full pytest suite.
- Code review auto-fix pass: expanded disallowed account-type boundary tests and added byte-stable determinism assertion.

### Implementation Plan

- Model posture input selection with explicit liquidity account set, burn window, reserve policy, and USD scope.
- Enforce deterministic ordering and validation in a posture domain service with read-only DB access.
- Extend ledger repository with deterministic read helper queries for selected accounts.
- Add unit and integration tests covering normalization, deterministic ordering, and invalid account selection cases.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Completed Story 1.1 implementation for deterministic posture input modeling and account selection.
- Added duplicate, unknown-account, and disallowed-type validation paths for liquidity account selection.
- Verified deterministic ordering by `code, account_id` across selection responses.
- Executed full regression suite successfully (`21 passed`).
- Addressed review findings: account-type boundary coverage expanded across non-liquidity account types.
- Addressed review findings: repeated-run byte-stable posture input output assertion added.
- Re-ran full regression suite after review fixes (`25 passed`).

### File List

- `_bmad-output/implementation-artifacts/1-1-posture-domain-model-and-inputs.md`
- `src/capital_os/domain/ledger/repository.py`
- `src/capital_os/domain/posture/__init__.py`
- `src/capital_os/domain/posture/models.py`
- `src/capital_os/domain/posture/service.py`
- `tests/integration/test_posture_account_selection.py`
- `tests/unit/test_posture_inputs.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-14: Implemented posture domain input models, deterministic read-only account selection, repository read helpers, and posture test coverage.
- 2026-02-14: Senior code review fixes applied (determinism assertion + account-type boundary test expansion); status set to done.

## Senior Developer Review (AI)

### Review Date

2026-02-14

### Reviewer

GPT-5 Codex (Senior Developer Review Workflow)

### Outcome

Approve

### Findings and Resolution

- [x] [HIGH] Expand account-type boundary coverage beyond `income` in posture selection integration tests (`tests/integration/test_posture_account_selection.py`).
- [x] [MEDIUM] Add explicit byte-stable determinism assertion for same state/config repeated posture selection output (`tests/integration/test_posture_account_selection.py`).
- [x] [MEDIUM] Align story File List with actual changed files by including sprint tracker update (`_bmad-output/implementation-artifacts/sprint-status.yaml`).
