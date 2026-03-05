# Story 18.1: Standard `update_account_profile` Tool

Status: done

## Story

As a family-office AI operator,
I want a standard `update_account_profile` tool endpoint,
so that I can rename accounts and maintain user-facing profile fields over time without direct DB access.

## Acceptance Criteria

1. `POST /tools/update_account_profile` accepts `account_id` (required), `display_name` (optional), `institution_name` (optional), `institution_suffix` (optional), `source_system` (required), `external_id` (required), and `correlation_id` (required).
2. At least one mutable profile field must be present; otherwise request fails with 422.
3. Account existence validation returns 400 when `account_id` does not exist.
4. Successful update returns `account_id`, updated profile fields, `status: "committed"`, `correlation_id`, `output_hash`.
5. Tool is event-logged with deterministic `input_hash` and `output_hash`.
6. Tool requires `tools:write`; reader token receives 403.
7. `x-correlation-id` header enforcement applies.
8. Tool is idempotent on `(source_system, external_id)` and returns canonical prior result for duplicates.

## Tasks / Subtasks

- [x] Task 1: Define input/output schemas (AC: 1, 2, 4)
  - [x] Add `UpdateAccountProfileIn` in `src/capital_os/schemas/tools.py`
  - [x] Add `UpdateAccountProfileOut` in `src/capital_os/schemas/tools.py`
- [x] Task 2: Implement domain service entrypoint (AC: 3, 4, 5, 8)
  - [x] Add `update_account_profile()` in `src/capital_os/domain/accounts/service.py`
  - [x] Validate account existence and mutable-field presence
  - [x] Integrate deterministic hash computation and event logging in single transaction
  - [x] Enforce idempotency behavior with canonical duplicate response
- [x] Task 3: Add tool handler and registration (AC: 1, 6, 7)
  - [x] Add `src/capital_os/tools/update_account_profile.py`
  - [x] Register handler in runtime registry (`src/capital_os/runtime/execute_tool.py`)
  - [x] Add tool capability mapping in `src/capital_os/config.py`
- [x] Task 4: Add integration coverage (AC: 1-8)
  - [x] Happy path rename and profile update
  - [x] Missing account -> 400
  - [x] Empty mutable payload -> 422
  - [x] authn/authz enforcement
  - [x] idempotent duplicate request behavior

## Dev Notes

### Architecture Compliance
- Keep strict layering: handler -> domain service -> repository/DB.
- Never modify `account_id` or mutate ledger/posting history.
- Write fails closed if event log persistence fails.

### File Structure Requirements
- New: `src/capital_os/tools/update_account_profile.py`
- New: `tests/integration/test_update_account_profile_tool.py`
- Modify: `src/capital_os/schemas/tools.py`
- Modify: `src/capital_os/domain/accounts/service.py`
- Modify: `src/capital_os/api/app.py`
- Modify: `src/capital_os/config.py`

### References
- [Source: `ARCHITECTURE.md`]
- [Source: `CONSTITUTION.md`]
- [Source: `_bmad-output/planning-artifacts/epic-18-account-profile-and-identifier-evolution.md`]

## Dev Agent Record

### Completion Notes List
- Added `update_account_profile` tool input/output schemas with "at least one mutable field" validation.
- Implemented profile update service logic with deterministic hashing, event logging, and idempotent replay via `(tool_name, source_system, external_id)` uniqueness in `approval_proposals`.
- Added repository helpers to fetch and update account profile state.
- Registered `update_account_profile` as a write tool in runtime + capability config.
- Added integration and replay tests covering happy path, validation/auth errors, idempotent replay, and output hash determinism.
- Senior review fixes applied:
  - Enforced `x-correlation-id` header for `update_account_profile` and required body/header correlation match.
  - Moved idempotency key claim ahead of mutable account/history writes to guarantee one canonical commit under duplicates.
  - Expanded integration tests for correlation header missing/mismatch behavior.

### File List
- Modified: `src/capital_os/api/app.py`
- Modified: `src/capital_os/domain/accounts/service.py`
- Modified: `src/capital_os/config.py`
- Modified: `src/capital_os/runtime/execute_tool.py`
- Modified: `src/capital_os/schemas/tools.py`
- Modified: `src/capital_os/domain/ledger/repository.py`
- Added: `src/capital_os/tools/update_account_profile.py`
- Added: `tests/integration/test_update_account_profile_tool.py`
- Added: `tests/integration/test_update_account_profile_security.py`
- Added: `tests/replay/test_update_account_profile_determinism.py`
- Added: `tests/replay/test_update_account_profile_replay.py`

### Verification
```bash
pytest tests/integration/test_update_account_profile_tool.py tests/replay/test_update_account_profile_determinism.py -q
pytest tests/security/test_api_security_controls.py::test_tool_surface_has_authn_and_authz_coverage tests/integration/test_cli_commands.py -k "tool_schema" -q
pytest tests/integration/test_update_account_profile_tool.py tests/integration/test_update_account_profile_security.py tests/replay/test_update_account_profile_determinism.py tests/replay/test_update_account_profile_replay.py -q
```

## Senior Developer Review (AI)

Review Date: 2026-03-05  
Reviewer: Chris Patten (Codex)

Findings resolved in this pass:
- [HIGH] AC7 header enforcement gap: fixed with explicit `x-correlation-id` requirement + body/header match validation for `update_account_profile`.
- [HIGH] Idempotency race risk under contention: fixed by claiming `(tool_name, source_system, external_id)` proposal row before mutable state updates.
- [HIGH] Story file/doc mismatch for modified files: corrected via explicit `File List`.
- [MEDIUM] Incomplete change traceability: corrected with expanded file list and verification command updates.
- [LOW] Missing AC7-specific test: fixed with header-required + mismatch tests.

Outcome: Approved, all high/medium issues fixed.
