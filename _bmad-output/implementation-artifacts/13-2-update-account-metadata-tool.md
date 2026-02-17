# Story 13.2: Update Account Metadata Tool

Status: ready-for-dev

## Story

As a family-office AI operator,
I want an `update_account_metadata` tool endpoint,
so that I can enrich or modify account metadata at runtime without direct DB access.

## Acceptance Criteria

1. `POST /tools/update_account_metadata` accepts `account_id` (required), `metadata` (required, JSON object), and required `correlation_id`.
2. Metadata uses **merge-patch** semantics (RFC 7396): provided keys overwrite existing, unmentioned keys are preserved, keys set to `null` are removed.
3. Successful update returns full updated metadata, `account_id`, `status: "committed"`, `correlation_id`, `output_hash`.
4. 400 if `account_id` does not exist.
5. 422 on invalid schema (missing required fields, `metadata` not an object).
6. Write is event-logged with `input_hash` and `output_hash` per observability contract.
7. Tool requires `tools:write` capability; `dev-reader-token` gets 403.
8. `x-correlation-id` header enforcement applies (same as all other tools).
9. `skills/CLAUDE_SKILL.md` updated: documents `update_account_metadata` tool, schema, example curl.
10. `skills/CODEX_SKILL.md` updated: same changes as AC 9.
11. `docs/tool-reference.md` updated with full `update_account_metadata` entry.

## Tasks / Subtasks

- [ ] Task 1: Define schemas (AC: 1, 5)
  - [ ] Add `UpdateAccountMetadataIn` to `src/capital_os/schemas/tools.py` with fields: `account_id` (str, required), `metadata` (dict, required), `correlation_id` (str, required)
  - [ ] Add `UpdateAccountMetadataOut` with fields: `account_id` (str), `metadata` (dict — full merged result), `status` (str), `correlation_id` (str), `output_hash` (str)
- [ ] Task 2: Add domain service function (AC: 2, 3, 4, 6)
  - [ ] Create `update_account_metadata()` in `src/capital_os/domain/accounts/service.py`
  - [ ] Implement merge-patch: read current metadata, apply patch (overwrite provided keys, remove null keys, preserve unmentioned), write back
  - [ ] Validate account_id existence — raise descriptive error if not found
  - [ ] Add event logging via `log_event()` within same transaction boundary
  - [ ] Add deterministic input/output hashing
  - [ ] Return structured output with full merged metadata
- [ ] Task 3: Create tool handler (AC: 1, 2, 3, 4)
  - [ ] Create `src/capital_os/tools/update_account_metadata.py` following existing handler pattern
  - [ ] Handler validates input via schema, calls service, returns response
  - [ ] Map account-not-found to 400 with descriptive message
- [ ] Task 4: Wire API registration (AC: 7, 8)
  - [ ] Add `"update_account_metadata": update_account_metadata.handle` to `TOOL_HANDLERS` in `src/capital_os/api/app.py`
  - [ ] Add `"update_account_metadata"` to `WRITE_TOOLS` set
  - [ ] Add `"update_account_metadata": "tools:write"` to `DEFAULT_TOOL_CAPABILITIES` in `src/capital_os/config.py`
- [ ] Task 5: Integration tests (AC: 1–8)
  - [ ] Happy path: add new metadata keys to account with empty metadata
  - [ ] Merge-patch: partial update preserves existing keys
  - [ ] Merge-patch: overwrite existing key with new value
  - [ ] Merge-patch: set key to null removes it from metadata
  - [ ] Full round-trip: create account with metadata via create_account, then update, verify merged result
  - [ ] Nonexistent account_id → 400
  - [ ] Missing required fields → 422
  - [ ] metadata not an object → 422
  - [ ] Auth enforcement: missing token → 401
  - [ ] Authz enforcement: reader token → 403
  - [ ] Missing correlation_id → 422
- [ ] Task 6: Replay/determinism test (AC: 3, 6)
  - [ ] Verify identical inputs on identical state produce identical `output_hash`
  - [ ] Verify event log contains matching `input_hash` and `output_hash`
- [ ] Task 7: Update agent skill files (AC: 9, 10, 11)
  - [ ] Update `skills/CLAUDE_SKILL.md` — add `update_account_metadata` to tool documentation, add curl example
  - [ ] Update `skills/CODEX_SKILL.md` — same changes
  - [ ] Update `docs/tool-reference.md` — add full `update_account_metadata` entry with schema, behavior, merge-patch semantics, error semantics

## Dev Notes

### Developer Context Section

- This is the second story in Epic 13. It may depend on Story 13.1 for integration tests that create accounts first, then update metadata.
- Account metadata is stored as a JSON TEXT column in the `accounts` table. It is mutable — not subject to the append-only invariant (that applies to transactions, postings, and event logs).
- The UPDATE on the metadata column is architecturally sound but must still be event-logged for audit trail.

### Technical Requirements

- Merge-patch (RFC 7396): simple JSON object merge. Nested objects are replaced wholesale (not deep-merged). This matches the simplest useful semantics.
- Deterministic hashing: metadata must be serialized with sorted keys for canonical representation.
- Fail-closed: if event log write fails, the metadata UPDATE rolls back too.

### Architecture Compliance

- Strict layering: tool handler → domain service → repository/DB. No direct SQL from handler.
- The metadata UPDATE is the only mutable field on accounts. All other account fields are effectively immutable post-creation.
- Event log captures before/after state for auditability.

### File Structure Requirements

- New: `src/capital_os/tools/update_account_metadata.py`
- New: `tests/integration/test_update_account_metadata.py`
- New: `tests/replay/test_update_account_metadata_determinism.py`
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
- Integration tests should create accounts first (using create_account from 13.1 or direct DB setup) then test metadata updates.

### Previous Story Intelligence

- Story 13.1 (Create Account Tool) establishes the account creation path. If 13.1 is complete, integration tests here can use `create_account` to set up test fixtures.
- If 13.1 is not yet complete, tests should use the existing `create_account_entry()` service function or direct DB setup.

### References

- [Source: `ARCHITECTURE.md`]
- [Source: `CONSTITUTION.md`]
- [Source: `_bmad-output/planning-artifacts/epic-13-account-management-tooling.md`]
- [RFC 7396: JSON Merge Patch](https://tools.ietf.org/html/rfc7396)
- Pattern reference: `src/capital_os/tools/reconcile_account.py` (write tool with account lookup)
