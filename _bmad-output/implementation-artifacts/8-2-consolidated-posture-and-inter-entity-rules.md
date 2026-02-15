# Story 8.2: Consolidated Posture and Inter-Entity Transfer Semantics

Status: ready-for-dev

## Story

As a family-office AI operator,  
I want deterministic consolidated posture output across selected entities,  
so that I can evaluate combined financial posture without inter-entity double counting.

## Acceptance Criteria

1. Implement `compute_consolidated_posture(entity_ids[])` deterministic contract.
2. Enforce inter-entity transfer paired semantics for consolidation neutrality.
3. Consolidated outputs include deterministic ordering and stable output hash.
4. Validation failures and success paths are event-logged.
5. Consolidation path does not mutate canonical ledger rows.

## Tasks / Subtasks

- [ ] Task 1: Define schema/contracts and API wiring (AC: 1, 3, 4)
- [ ] Task 2: Implement entity consolidation domain logic (AC: 1, 2, 3, 5)
- [ ] Task 3: Add deterministic replay + integration coverage (AC: 2, 3, 4, 5)

## Notes

- Depends on Story 8.1 entity dimension migration.
