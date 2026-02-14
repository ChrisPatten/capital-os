# Playbook: Story Execution

Use this for implementation tasks.

## 1. Select Work
1. Open `_bmad-output/implementation-artifacts/sprint-status.yaml`.
2. Pick the highest-priority story in `ready-for-dev`.
3. If none are `ready-for-dev`, work the top story in `in-progress` or `review` only when explicitly requested.

## 2. Load Story Context
1. Open the matching story file in `_bmad-output/implementation-artifacts/`.
2. Confirm scope boundaries against:
   - `AGENTS.md`
   - `ARCHITECTURE.md`
   - `initial_prd.md`

## 3. Implement
1. Keep layering strict:
   - API/tools -> domain services -> repository/DB.
2. For write paths:
   - enforce invariants before commit;
   - use one transaction boundary;
   - emit event log records (success and validation failure paths).
3. Preserve determinism:
   - canonical ordering;
   - 4dp round-half-even normalization;
   - stable output hashing.

## 4. Validate
1. Run targeted tests for changed modules first.
2. Run full `pytest` when possible.
3. If tests cannot run, record exactly what was not executed.

## 5. Update Tracking
1. Update story status in `_bmad-output/implementation-artifacts/sprint-status.yaml`:
   - `in-progress` while actively implementing;
   - `review` when implementation/tests are ready;
   - `done` after acceptance is satisfied.
2. Keep docs in `docs/` synchronized for any contract/schema/behavior change.
