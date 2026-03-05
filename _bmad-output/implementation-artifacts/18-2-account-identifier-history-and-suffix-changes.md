# Story 18.2: Account Identifier History and Suffix Changes

Status: done

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

- [x] Task 1: Add migration for identifier-history table (AC: 1, 2)
  - [x] Create numbered migration for `account_identifier_history`
  - [x] Include rollback path and migration test updates
- [x] Task 2: Add repository/service persistence logic (AC: 1, 2, 3, 4)
  - [x] Close existing active history row on change
  - [x] Insert new active history row with validity window
  - [x] Keep logic no-op when identifier values are unchanged (idempotent replay path)
- [x] Task 3: Add deterministic + transactional tests (AC: 3, 4, 6)
  - [x] Determinism/replay coverage for changed vs unchanged identifiers
  - [x] Integration coverage validates identifier history transitions
- [x] Task 4: Add SQL operator guidance (AC: 5)
  - [x] Document history query examples in `docs/tool-reference.md`

## Dev Notes

### Architecture Compliance
- History table is append-only in normal operation.
- Enforce defense in depth: service-level checks plus DB constraints where practical.
- Keep `update_account_profile` as the only mutation gateway for this behavior.

### File Structure Requirements
- New: `migrations/00xx_account_identifier_history.sql`
- New: `tests/integration/test_account_identifier_history.py`
- New: `tests/replay/test_account_identifier_history_replay.py`
- Modify: `src/capital_os/domain/ledger/repository.py`
- Modify: `src/capital_os/domain/accounts/service.py`
- Modify: `docs/tool-reference.md`

### References
- [Source: `AGENTS.md`]
- [Source: `CONSTITUTION.md`]
- [Source: `_bmad-output/planning-artifacts/epic-18-account-profile-and-identifier-evolution.md`]

## Dev Agent Record

### Completion Notes List
- Added migration pair `0010_account_identifier_history.sql` and `0010_account_identifier_history.rollback.sql`.
- Implemented repository helpers to fetch active history, close active history, and insert new history records.
- Wired history transitions into `update_account_profile` so identifier changes are recorded in the same transaction as profile updates and event logs.
- Added integration and replay tests for first insert, active-row rollover, and idempotent replay behavior.
- Added direct SQL query guidance to `docs/tool-reference.md` for history reads.
- Senior review fixes applied:
  - Updated identifier-history integration tests to include required `x-correlation-id` header for `update_account_profile`.
  - Added fail-closed rollback test proving profile/history/proposal writes are rolled back when event log persistence fails.
  - Added append-only guard triggers for `account_identifier_history` with constrained close-row update semantics (`valid_to` NULL -> non-NULL only), plus DELETE prohibition.

### Verification
```bash
pytest tests/integration/test_account_identifier_history.py tests/replay/test_account_identifier_history_replay.py tests/integration/test_update_account_profile_tool.py tests/replay/test_update_account_profile_determinism.py -q
python3 scripts/check_migration_cycle.py --db-path /tmp/capital_os_migration_cycle.db --migrations-dir migrations
```

### File List
- Modified: `migrations/0010_account_identifier_history.sql`
- Modified: `migrations/0010_account_identifier_history.rollback.sql`
- Modified: `src/capital_os/domain/ledger/repository.py`
- Modified: `src/capital_os/domain/accounts/service.py`
- Modified: `docs/tool-reference.md`
- Added: `tests/integration/test_account_identifier_history.py`
- Added: `tests/replay/test_account_identifier_history_replay.py`

## Senior Developer Review (AI)

Review Date: 2026-03-05  
Reviewer: Chris Patten (Codex)

Findings resolved in this pass:
- [HIGH] Story verification command failures due to header contract drift: fixed by updating identifier-history integration tests to send `x-correlation-id`.
- [HIGH] Story file/path mismatch (`domain/accounts/repository.py`): corrected to actual implementation path `domain/ledger/repository.py`.
- [HIGH] AC3 transactional proof gap: added explicit rollback test for forced event-log failure.
- [MEDIUM] Missing append-only guard on history table: added update/delete triggers with closure-only update allowance.
- [MEDIUM] Incomplete traceability: added explicit `File List`.

Outcome: Approved, all high/medium issues fixed.
