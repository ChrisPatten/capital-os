# Story 18.2: Account Identifier History and Suffix Changes

Status: ready-for-dev

## Story

As a family-office AI operator,
I want external account identifier/suffix changes to be tracked append-only,
so that institution-driven reference changes are auditable without rewriting history.

## Acceptance Criteria

1. When `institution_suffix` or external identifier changes, system appends a new identifier-history row tied to `account_id`.
2. Prior active identifier row is closed with `valid_to`; new row opens with `valid_from`.
3. Identifier-history writes occur in the same transaction as profile update and event log write.
4. Existing transactions/postings are never updated as part of identifier changes.
5. Direct SQL query patterns for identifier history are documented (no read tool added).
6. Replay tests verify deterministic output hashing for equivalent identifier-change inputs.

## Tasks / Subtasks

- [ ] Task 1: Add migration for identifier-history table (AC: 1, 2)
  - [ ] Create numbered migration for `account_identifier_history`
  - [ ] Include rollback path and migration test updates
- [ ] Task 2: Add repository/service persistence logic (AC: 1, 2, 3, 4)
  - [ ] Close existing active history row on change
  - [ ] Insert new active history row with validity window
  - [ ] Keep logic no-op when identifier values are unchanged
- [ ] Task 3: Add deterministic + transactional tests (AC: 3, 4, 6)
  - [ ] Transaction rollback on injected event log failure
  - [ ] Determinism/replay coverage for changed vs unchanged identifiers
- [ ] Task 4: Add SQL operator guidance (AC: 5)
  - [ ] Document history query examples in `docs/tool-reference.md` or ops doc

## Dev Notes

### Architecture Compliance
- History table is append-only in normal operation.
- Enforce defense in depth: service-level checks plus DB constraints where practical.
- Keep `update_account_profile` as the only mutation gateway for this behavior.

### File Structure Requirements
- New: `migrations/00xx_account_identifier_history.sql`
- New: `tests/integration/test_account_identifier_history.py`
- New: `tests/replay/test_account_identifier_history_replay.py`
- Modify: `src/capital_os/domain/accounts/repository.py`
- Modify: `src/capital_os/domain/accounts/service.py`
- Modify: `docs/tool-reference.md`

### References
- [Source: `AGENTS.md`]
- [Source: `CONSTITUTION.md`]
- [Source: `_bmad-output/planning-artifacts/epic-18-account-profile-and-identifier-evolution.md`]
