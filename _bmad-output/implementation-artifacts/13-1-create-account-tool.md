# Story 13.1: Create Account Tool

Status: done

## Story

As a family-office AI operator,
I want a `create_account` tool endpoint,
so that I can add new accounts to the chart of accounts at runtime without manual YAML imports.

## Acceptance Criteria

1. `POST /tools/create_account` accepts `code`, `name`, `account_type` (required) plus optional `parent_account_id`, `entity_id`, `metadata`, and required `correlation_id`.
2. Tool validates input schema — 422 on invalid type, missing required fields, or unknown keys.
3. Tool validates `parent_account_id` exists if provided — 400 with clear error on missing parent.
4. Tool validates `entity_id` exists if provided — 400 with clear error on missing entity.
5. Duplicate `code` returns 400 with clear error (not silent upsert).
6. Account hierarchy cycle rejection works end-to-end — DB trigger fires, service returns 400.
7. Successful creation returns `account_id`, `status: "committed"`, `correlation_id`, `output_hash`.
8. Write is event-logged with `input_hash` and `output_hash` per observability contract.
9. Tool requires `tools:write` capability; `dev-reader-token` gets 403.
10. `x-correlation-id` header enforcement applies (same as all other tools).
11. `skills/CLAUDE_SKILL.md` updated: documents `create_account` tool, schema, example curl, and removes/replaces "Account IDs come from the seeded COA (don't invent new ones)" guidance.
12. `skills/CODEX_SKILL.md` updated: same changes as AC 11.
13. `docs/tool-reference.md` updated with full `create_account` entry.

## Tasks / Subtasks

- [x]Task 1: Define schemas (AC: 1, 2)
  - [x]Add `CreateAccountIn` to `src/capital_os/schemas/tools.py` with fields: `code` (str, required), `name` (str, required), `account_type` (Literal["asset","liability","equity","income","expense"], required), `parent_account_id` (str | None), `entity_id` (str | None), `metadata` (dict | None), `correlation_id` (str, required)
  - [x]Add `CreateAccountOut` with fields: `account_id` (str), `status` (str), `correlation_id` (str), `output_hash` (str)
- [x]Task 2: Enhance domain service (AC: 3, 4, 7, 8)
  - [x]Refactor `create_account_entry()` in `src/capital_os/domain/accounts/service.py` to add event logging via `log_event()`
  - [x]Add deterministic input/output hashing (sorted keys, canonical ordering, 4dp decimals)
  - [x]Add parent_account_id existence check before DB insert
  - [x]Add entity_id existence check before DB insert
  - [x]Return structured output with `account_id`, `status`, `correlation_id`, `output_hash`
- [x]Task 3: Create tool handler (AC: 1, 2, 3, 4, 5, 6)
  - [x]Create `src/capital_os/tools/create_account.py` following existing handler pattern
  - [x]Handler validates input via schema, calls service, returns response
  - [x]Map DB-level errors (UNIQUE constraint on code, cycle trigger) to 400 with descriptive messages
- [x]Task 4: Wire API registration (AC: 9, 10)
  - [x]Add `"create_account": create_account.handle` to `TOOL_HANDLERS` in `src/capital_os/api/app.py`
  - [x]Add `"create_account"` to `WRITE_TOOLS` set
  - [x]Add `"create_account": "tools:write"` to `DEFAULT_TOOL_CAPABILITIES` in `src/capital_os/config.py`
- [x]Task 5: Integration tests (AC: 1–10)
  - [x]Happy path: create account with each of the 5 account types (asset, liability, equity, income, expense)
  - [x]Create account with parent_account_id (valid hierarchy)
  - [x]Create account with metadata
  - [x]Create account with entity_id
  - [x]Duplicate code rejection → 400
  - [x]Cycle rejection via parent_account_id → 400
  - [x]Nonexistent parent_account_id → 400
  - [x]Nonexistent entity_id → 400
  - [x]Missing required fields → 422
  - [x]Invalid account_type → 422
  - [x]Auth enforcement: missing token → 401
  - [x]Authz enforcement: reader token → 403
  - [x]Missing correlation_id → 422
- [x]Task 6: Replay/determinism test (AC: 7, 8)
  - [x]Verify identical inputs produce identical `output_hash`
  - [x]Verify event log contains matching `input_hash` and `output_hash`
- [x]Task 7: Update agent skill files (AC: 11, 12, 13)
  - [x]Update `skills/CLAUDE_SKILL.md` — add `create_account` to tool documentation, add curl example, replace "don't invent new account IDs" with guidance on using `create_account`
  - [x]Update `skills/CODEX_SKILL.md` — same changes
  - [x]Update `docs/tool-reference.md` — add full `create_account` entry with schema, behavior, error semantics

## Dev Notes

### Developer Context Section

- The domain infrastructure for account creation exists (`domain/accounts/service.py` has `create_account_entry()`, repository has `create_account()`), but it lacks event logging, hashing, and is not wired to a tool endpoint.
- The DB schema already enforces cycle rejection via triggers in migration 0001.
- This story follows the exact same tool-creation pattern used across all 23 existing tools.

### Technical Requirements

- Deterministic hashing: use `compute_input_hash()` / `compute_output_hash()` from observability module.
- Event logging: call `log_event()` within the same transaction boundary as the account insert.
- Fail-closed: if event log write fails, the entire transaction (including account creation) rolls back.
- Monetary precision is not directly relevant here, but metadata JSON must use canonical serialization for hashing.

### Architecture Compliance

- Strict layering: tool handler → domain service → repository. No direct DB access from handler.
- Tool handler is a thin adapter — validation and business logic live in the service layer.
- All errors surfaced through structured responses, not raw exceptions.

### File Structure Requirements

- New: `src/capital_os/tools/create_account.py`
- New: `tests/integration/test_create_account.py`
- New: `tests/replay/test_create_account_determinism.py`
- Modify: `src/capital_os/schemas/tools.py`
- Modify: `src/capital_os/domain/accounts/service.py`
- Modify: `src/capital_os/api/app.py`
- Modify: `src/capital_os/config.py`
- Modify: `skills/CLAUDE_SKILL.md`
- Modify: `skills/CODEX_SKILL.md`
- Modify: `docs/tool-reference.md`

### Testing Requirements

- All new tests must pass deterministically on function-scoped DB reset.
- Replay test must prove output_hash stability across runs.
- Security tests must verify auth and authz enforcement.

### References

- [Source: `ARCHITECTURE.md`]
- [Source: `CONSTITUTION.md`]
- [Source: `_bmad-output/planning-artifacts/epic-13-account-management-tooling.md`]
- Pattern reference: `src/capital_os/tools/record_transaction_bundle.py` (canonical write tool example)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List
- Added `CreateAccountIn`/`CreateAccountOut` schemas to `schemas/tools.py`
- Enhanced `domain/accounts/service.py` with event logging, deterministic hashing, parent/entity existence validation, and IntegrityError mapping
- Created thin tool handler at `tools/create_account.py`
- Registered in `app.py` (TOOL_HANDLERS, WRITE_TOOLS) and `config.py` (DEFAULT_TOOL_CAPABILITIES)
- 15 integration tests covering happy path (all 5 types, parent hierarchy, metadata), validation (missing fields, invalid type, extra fields, missing correlation_id), business rules (duplicate code, nonexistent parent, nonexistent entity, cycle rejection), security (401/403), and event log verification
- 2 replay/determinism tests verifying output_hash reproducibility and event log hash consistency
- Updated `skills/CLAUDE_SKILL.md`, `skills/CODEX_SKILL.md`, `docs/tool-reference.md` with create_account documentation and curl examples
- Updated `docs/current-state.md`, `docs/testing-matrix.md`, `docs/traceability-matrix.md`
- Full test suite: 149 tests pass

### Verification
```bash
pytest tests/integration/test_create_account_tool.py tests/replay/test_create_account_replay.py -v  # 17 passed
pytest  # 149 passed
```

### File List
- `src/capital_os/tools/create_account.py` (new)
- `src/capital_os/schemas/tools.py` (modified)
- `src/capital_os/domain/accounts/service.py` (modified)
- `src/capital_os/api/app.py` (modified)
- `src/capital_os/config.py` (modified)
- `tests/integration/test_create_account_tool.py` (new)
- `tests/replay/test_create_account_replay.py` (new)
- `skills/CLAUDE_SKILL.md` (modified)
- `skills/CODEX_SKILL.md` (modified)
- `docs/tool-reference.md` (modified)
- `docs/current-state.md` (modified)
- `docs/testing-matrix.md` (modified)
- `docs/traceability-matrix.md` (modified)
- `_bmad-output/planning-artifacts/epic-13-account-management-tooling.md` (new)
- `_bmad-output/implementation-artifacts/13-1-create-account-tool.md` (this file)
- `_bmad-output/implementation-artifacts/13-2-update-account-metadata-tool.md` (new)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified)
