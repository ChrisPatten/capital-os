# Story 8.2: Consolidated Posture and Inter-Entity Transfer Semantics

Status: done

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

- [x] Task 1: Define schema/contracts and API wiring (AC: 1, 3, 4)
- [x] Task 2: Implement entity consolidation domain logic (AC: 1, 2, 3, 5)
- [x] Task 3: Add deterministic replay + integration coverage (AC: 2, 3, 4, 5)

## Notes

- Depends on Story 8.1 entity dimension migration.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Added `compute_consolidated_posture` tool contract and API registration.
- Implemented deterministic consolidation service with sorted entity ordering and stable output hashing.
- Enforced inter-entity transfer paired semantics in schema validation:
  - exactly two legs per transfer
  - one inbound and one outbound leg
  - mirrored entity/counterparty IDs
  - identical amounts
- Added integration coverage for success path determinism, validation failure logging, and canonical-table non-mutation.
- Added replay coverage to verify deterministic output hash reproduction.

### File List

- `_bmad-output/implementation-artifacts/8-2-consolidated-posture-and-inter-entity-rules.md`
- `src/capital_os/schemas/tools.py`
- `src/capital_os/domain/posture/consolidation.py`
- `src/capital_os/tools/compute_consolidated_posture.py`
- `src/capital_os/api/app.py`
- `src/capital_os/config.py`
- `tests/integration/test_consolidated_posture_tool.py`
- `tests/replay/test_output_replay.py`
- `docs/tool-reference.md`
- `docs/current-state.md`
- `README.md`
- `ARCHITECTURE.md`
