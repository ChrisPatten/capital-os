# Story 8.1: Entity Dimension Schema and Migration

Status: review

## Story

As a family-office AI operator,  
I want canonical ledger records to include an `entity_id` dimension with deterministic defaults,  
so that multi-entity capabilities can be built without breaking existing single-entity workflows.

## Acceptance Criteria

1. Add `entities` table to canonical schema.
2. Propagate `entity_id` to core tables:
  - `accounts`
  - `ledger_transactions`
  - `balance_snapshots`
  - `obligations`
  - `approval_proposals`
3. Seed deterministic default entity mapping for existing/single-entity workflows.
4. Preserve append-only protections and prevent unsafe entity mutation in approval-gated rows.
5. Add integration coverage for default and explicit entity propagation.
6. Migration apply -> rollback -> re-apply cycle remains green.

## Tasks / Subtasks

- [x] Task 1: Add migration and rollback artifacts (AC: 1, 2, 3, 6)
  - [x] Add `migrations/0005_entity_dimension.sql`.
  - [x] Add `migrations/0005_entity_dimension.rollback.sql`.
  - [x] Ensure migration cycle includes the new migration.
- [x] Task 2: Propagate entity defaults in write path (AC: 2, 3, 4)
  - [x] Add domain constant for deterministic default entity id.
  - [x] Update ledger/approval repositories to persist entity id deterministically.
  - [x] Extend write tool input contracts with defaulted `entity_id`.
- [x] Task 3: Add integration coverage (AC: 4, 5, 6)
  - [x] Add `tests/integration/test_entity_dimension_migration.py`.
  - [x] Extend migration fixtures to include `0005` in apply/rollback path.
  - [x] Verify full test suite and migration cycle checks.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Implemented entity dimension migration with deterministic default entity seed (`entity-default`).
- Added `entity_id` columns across canonical tables and approval proposals with FK enforcement to `entities`.
- Updated append-only ledger transaction update trigger to enforce `entity_id` immutability.
- Added proposal-level entity immutability trigger.
- Extended write contracts/repositories so omitted `entity_id` uses deterministic default while explicit entity IDs persist.
- Added dedicated integration tests for default propagation, explicit entity propagation, and immutability enforcement.
- Verified migration cycle and full regression suite: `93 passed`.

### File List

- `_bmad-output/implementation-artifacts/8-1-entity-dimension-schema-migration.md`
- `migrations/0001_ledger_core.rollback.sql`
- `migrations/0005_entity_dimension.sql`
- `migrations/0005_entity_dimension.rollback.sql`
- `src/capital_os/domain/entities/__init__.py`
- `src/capital_os/domain/entities/constants.py`
- `src/capital_os/domain/approval/repository.py`
- `src/capital_os/domain/ledger/repository.py`
- `src/capital_os/domain/ledger/service.py`
- `src/capital_os/schemas/tools.py`
- `tests/conftest.py`
- `tests/integration/test_entity_dimension_migration.py`
