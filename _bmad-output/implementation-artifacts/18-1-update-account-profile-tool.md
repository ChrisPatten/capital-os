# Story 18.1: Standard `update_account_profile` Tool

Status: ready-for-dev

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

- [ ] Task 1: Define input/output schemas (AC: 1, 2, 4)
  - [ ] Add `UpdateAccountProfileIn` in `src/capital_os/schemas/tools.py`
  - [ ] Add `UpdateAccountProfileOut` in `src/capital_os/schemas/tools.py`
- [ ] Task 2: Implement domain service entrypoint (AC: 3, 4, 5, 8)
  - [ ] Add `update_account_profile()` in `src/capital_os/domain/accounts/service.py`
  - [ ] Validate account existence and mutable-field presence
  - [ ] Integrate deterministic hash computation and event logging in single transaction
  - [ ] Enforce idempotency behavior with canonical duplicate response
- [ ] Task 3: Add tool handler and registration (AC: 1, 6, 7)
  - [ ] Add `src/capital_os/tools/update_account_profile.py`
  - [ ] Register handler in `src/capital_os/api/app.py`
  - [ ] Add tool capability mapping in `src/capital_os/config.py`
- [ ] Task 4: Add integration coverage (AC: 1-8)
  - [ ] Happy path rename and profile update
  - [ ] Missing account -> 400
  - [ ] Empty mutable payload -> 422
  - [ ] authn/authz enforcement
  - [ ] idempotent duplicate request behavior

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
