# Story 15.1: Shared Tool Executor and Adapter Refactor

Status: ready-for-dev

## Story

As a Capital OS maintainer,  
I want HTTP and CLI transports to call a shared tool execution path,  
so that tool semantics stay identical across adapters and do not drift over time.

## Acceptance Criteria

1. A shared runtime tool execution entrypoint exists (e.g., `src/capital_os/runtime/execute_tool.py`) and is used by `src/capital_os/api/app.py` for tool dispatch.
2. The shared executor preserves existing schema validation, deterministic hashing, event logging, and write fail-closed behavior.
3. HTTP adapter continues to enforce authn/authz before invoking the shared executor.
4. A trusted CLI execution context can invoke the shared executor without auth/authz checks.
5. Trusted CLI bypasses only auth/authz; it still enforces validation, DB invariants, append-only protections, and transactional behavior.
6. Event logs for CLI invocations record channel-distinguishing context fields (`authn_method`, `actor_id`, `authorization_result`) without requiring auth headers.
7. Existing HTTP integration tests continue to pass with no behavior regression for canonical response payloads.

## Tasks / Subtasks

- [ ] Task 1: Introduce shared executor module and result envelope (AC: 1, 2)
  - [ ] Create `src/capital_os/runtime/execute_tool.py` with shared dispatch entrypoint
  - [ ] Define internal result structure for success/error outcomes that adapters map to transport semantics
- [ ] Task 2: Refactor HTTP adapter to use shared executor (AC: 1, 2, 3, 7)
  - [ ] Keep authn/authz logic in `src/capital_os/api/app.py`
  - [ ] Delegate tool execution to shared runtime entrypoint after HTTP-specific checks
  - [ ] Preserve existing HTTP status/error shapes
- [ ] Task 3: Add trusted execution context support (AC: 4, 5, 6)
  - [ ] Define context factory for local CLI channel (e.g., `authn_method=trusted_cli`)
  - [ ] Ensure observability/event logging accepts injected context consistently
- [ ] Task 4: Regression tests for HTTP behavior parity (AC: 2, 7)
  - [ ] Run/extend tests to verify no payload/hash regressions after adapter refactor

## Dev Notes

### Technical Requirements

- Shared executor must not become an alternative domain API; it is a transport-agnostic orchestration layer around existing tool handlers and contracts.
- Avoid duplicating validation or hashing logic in adapters.
- Preserve write-tool fail-closed behavior if event log persistence fails.

### Architecture Compliance

- Transport adapters (`api`, `cli`) handle channel concerns only.
- Domain/tool logic remains authoritative for business rules and DB mutations.

### File Structure Requirements

- New: `src/capital_os/runtime/execute_tool.py`
- New: `src/capital_os/runtime/__init__.py` (if package needed)
- Modify: `src/capital_os/api/app.py`
- Modify: `src/capital_os/observability/event_log.py` (only if context wiring changes are needed)
- Modify/add tests under `tests/integration/`

### References

- [Source: `_bmad-output/planning-artifacts/epic-15-cli-operator-interface.md`]
- [Source: `_bmad-output/implementation-artifacts/tech-spec-cli-operator-interface-delta-0223.md`]
- [Source: `project-context.md`]
