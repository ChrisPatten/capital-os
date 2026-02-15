# Epic 8: Multi-Entity Core (FR-21..FR-23, NFR-10)

## Goal
Introduce multi-entity ledger support with deterministic consolidated behavior.

### Story 8.1: Entity Dimension Schema and Migration
- Add `entities` model and `entity_id` association across canonical tables.
- Migrate existing single-entity data with deterministic default mapping.

### Story 8.2: Consolidated Posture and Inter-Entity Transfer Semantics
- Implement `compute_consolidated_posture(entity_ids[])`.
- Enforce paired inter-entity transfer model and consolidated neutrality.

### Story 8.3: Multi-Entity Scale and Regression Coverage
- Add performance/regression tests for >=25 entities.
- Verify no >20% degradation from baseline.
