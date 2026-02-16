# Story 12.1: Bootstrap COA Seed Path

Status: done

## Story

As a Capital OS operator,  
I want a validated bootstrap-only COA seed path from `config/coa.yaml`,  
so that I can initialize/reset accounts quickly before agent-driven API testing.

## Acceptance Criteria

1. Add `coa-validate` behavior that checks:
  - unique `account_id`
  - valid account `type` enum
  - parent references exist
  - account graph is acyclic
2. Add idempotent `coa-seed` behavior for `config/coa.yaml`:
  - create missing accounts
  - update allowed safe fields only
  - never delete accounts
3. Repeated seed runs produce deterministic outcomes and stable summaries.
4. Existing DB accounts not present in `config/coa.yaml` are retained and surfaced as warnings (not errors).
5. Bootstrap flow is documented as initialization/reset only; ongoing account governance remains API/tool-layer driven.
6. Integration coverage validates happy path + validation failure path.

## Tasks / Subtasks

- [x] Task 1: Finalize COA schema/constraint validation (AC: 1, 6)
  - [x] Validate required top-level and account fields with deterministic error messages.
  - [x] Enforce parent reference + cycle detection checks.
  - [x] Add/extend tests for invalid type, duplicate IDs, bad parent refs, and cycles.
- [x] Task 2: Implement deterministic idempotent upsert semantics (AC: 2, 3, 4)
  - [x] Upsert by stable `account_id`.
  - [x] Restrict updates to approved safe fields/policy.
  - [x] Ensure no-delete behavior and warning for extra DB accounts.
- [x] Task 3: Wire command entrypoint for bootstrap usage (AC: 2, 3, 5)
  - [x] Provide CLI/script interface for validate + seed execution.
  - [x] Return deterministic summary output for CI/operator use.
- [x] Task 4: Document bootstrap-only governance boundary (AC: 5)
  - [x] Update docs/runbook to state `config/coa.yaml` is init/reset only.
  - [x] Clarify post-init COA changes use governed API tool path.

## Notes

### Existing Assets To Reuse

- `src/capital_os/db/coa_importer.py`
- `scripts/import_coa.py`
- `tests/integration/test_coa_importer.py`
- `config/coa.yaml`

### File Touchpoints / Implementation Notes

- Import/validation logic:
  - `src/capital_os/db/coa_importer.py`
- CLI/bootstrap entrypoint:
  - `scripts/import_coa.py`
- Seed config:
  - `config/coa.yaml`
- Tests:
  - `tests/integration/test_coa_importer.py`
  - `tests/integration/test_accounts_hierarchy.py`

## Definition of Done

- ACs 1-6 pass with automated tests.
- Seed path is deterministic and idempotent across repeated runs.
- Story status can be moved to `review` with file list and test evidence.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Added explicit COA validate-only entrypoint (`--validate-only`) for bootstrap checks.
- Completed deterministic validation coverage for invalid type, duplicate `account_id`, missing parent reference, and cycles.
- Confirmed idempotent seed behavior with no-delete guarantees and warning visibility for DB-only accounts.
- Added README guidance documenting bootstrap-only usage of `config/coa.yaml` and post-bootstrap governance boundary.
- Verification:
  - `pytest -q tests/integration/test_coa_importer.py` -> `6 passed`
  - `python3 scripts/import_coa.py config/coa.yaml --validate-only` -> `coa validate (ok)`
  - `python3 scripts/import_coa.py config/coa.yaml --dry-run` -> deterministic summary output

### File List

- `_bmad-output/implementation-artifacts/12-1-bootstrap-coa-seed-path.md`
- `src/capital_os/db/coa_importer.py`
- `scripts/import_coa.py`
- `tests/integration/test_coa_importer.py`
- `config/coa.yaml`
- `README.md`
