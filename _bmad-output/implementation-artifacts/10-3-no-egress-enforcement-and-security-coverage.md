# Story 10.3: Security Coverage Adjustment and No-Egress Rollback

Status: done

## Story

As a security owner,
I want authentication, authorization, and correlation controls retained while no-egress controls are removed,
so that runtime environment management and dependency/test execution can proceed without in-process network interception.

## Acceptance Criteria

1. Runtime no-egress guardrails are removed from the tool execution path.
2. API security controls for authentication, authorization, and correlation ID remain enforced.
3. Security tests cover auth/authz/correlation behavior without asserting network-egress blocking.
4. CI gate for security coverage runs auth surface tests without no-egress checks.

## Tasks / Subtasks

- [x] Task 1: Remove runtime no-egress guard mechanism from API/tool execution path (AC: 1)
  - [x] Remove no-egress wrapper/installation calls and blocked-egress error handling.
- [x] Task 2: Preserve auth/authz/correlation enforcement semantics (AC: 2)
  - [x] Keep security context propagation and deterministic auth-related error/event behavior.
- [x] Task 3: Update security test suite to auth surface coverage (AC: 3)
  - [x] Remove no-egress assertions and keep full tool-surface auth/authz coverage checks.
- [x] Task 4: Update CI and documentation to reflect rollback (AC: 4)
  - [x] Replace no-egress-specific security job/test references with auth-surface coverage.

## Notes

### File Touchpoints / Implementation Notes

- Runtime control points:
  - `src/capital_os/main.py`
  - `src/capital_os/api/app.py`
  - `src/capital_os/config.py`
- Observability and structured security telemetry:
  - `src/capital_os/observability/event_log.py`
- Security and integration tests:
  - `tests/security/test_api_security_controls.py`
  - `tests/security/test_db_role_boundaries.py`
  - `tests/integration/test_event_log_coverage.py`
  - `tests/integration/test_tool_contract_validation.py`
- Replay/perf regression sanity:
  - `tests/replay/test_output_replay.py`
  - `tests/perf/test_tool_latency.py`
- CI/docs updates:
  - `.github/workflows/ci.yml`
  - `docs/testing-matrix.md`
  - `docs/traceability-matrix.md`

- Rollback enacted on 2026-02-16; SC-06 and NFR-05 are marked removed in traceability artifacts.
