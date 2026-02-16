# Story 10.1: Authentication Baseline

Status: done

## Story

As a platform operator,
I want all tool invocations to require authenticated identity context,
so that every action in Capital OS can be attributed, governed, and audited.

## Acceptance Criteria

1. `POST /tools/{tool_name}` rejects unauthenticated requests with deterministic `401` response shape.
2. Authenticated requests carry normalized actor context (`actor_id`, `authn_method`) through request handling and event logging.
3. Existing tool behavior and deterministic output hashing remain unchanged for valid authenticated calls.
4. Authentication failures are event-logged with required correlation/hash metadata and no secret material.
5. `/health` behavior remains accessible per current operational convention and is explicitly documented/tested.

## Tasks / Subtasks

- [ ] Task 1: Add authentication contract and request-context schema wiring (AC: 1, 2)
  - [ ] Extend API/tool request handling to require and validate auth identity metadata.
  - [ ] Normalize actor context into a canonical request context object.
- [ ] Task 2: Enforce auth at API boundary before tool dispatch (AC: 1, 3, 5)
  - [ ] Add deterministic auth guard in FastAPI app layer.
  - [ ] Ensure `/health` route behavior is explicitly preserved.
- [ ] Task 3: Persist actor context in observability pipeline (AC: 2, 4)
  - [ ] Extend structured event payload and DB persistence for actor context fields.
  - [ ] Ensure failures are logged without credentials/tokens.
- [ ] Task 4: Add integration tests for auth baseline behavior (AC: 1, 2, 3, 4, 5)
  - [ ] Add unauthorized/authorized tool invocation coverage.
  - [ ] Add event-log assertions for auth success/failure paths.

## Notes

### File Touchpoints / Implementation Notes

- API boundary and request context:
  - `src/capital_os/api/app.py`
  - `src/capital_os/main.py`
- Tool contract/auth field schema updates:
  - `src/capital_os/schemas/tools.py`
- Event logging extensions for actor context:
  - `src/capital_os/observability/event_log.py`
  - `src/capital_os/observability/hashing.py`
- Persistence layer updates (if new actor columns required):
  - `migrations/0008_api_security_runtime_controls.sql` (new)
  - `migrations/0008_api_security_runtime_controls.rollback.sql` (new)
  - `src/capital_os/domain/ledger/repository.py`
- Tests:
  - `tests/integration/test_tool_contract_validation.py`
  - `tests/integration/test_event_log_coverage.py`
  - `tests/security/test_db_role_boundaries.py`

- Keep deterministic error payloads and replay-stable logging semantics.
- Do not log bearer tokens, API keys, raw headers, or secret material.
