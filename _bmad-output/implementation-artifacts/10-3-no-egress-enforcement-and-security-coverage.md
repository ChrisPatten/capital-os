# Story 10.3: No-Egress Enforcement and Security Test Coverage

Status: done

## Story

As a security owner,
I want runtime no-egress enforcement with verifiable security coverage,
so that Capital OS cannot perform outbound network calls and remains within isolation boundaries.

## Acceptance Criteria

1. Runtime guardrails block outbound network egress from tool execution paths by default.
2. Blocked egress attempts produce deterministic, non-secret error telemetry and event-log evidence.
3. Security tests prove no-egress enforcement across representative tool execution paths.
4. Security suite demonstrates 100% tool-surface auth/authz coverage assertions for implemented tools.
5. CI includes enforceable gates for no-egress and auth coverage checks.

## Tasks / Subtasks

- [ ] Task 1: Implement runtime no-egress guard mechanism (AC: 1, 2)
  - [ ] Add central outbound-call guard usable by API/tool execution runtime.
  - [ ] Ensure explicit allowlist policy is empty by default for Phase 1.
- [ ] Task 2: Instrument blocked-egress telemetry and event logging (AC: 2)
  - [ ] Emit deterministic violation event fields without leaking payload secrets.
  - [ ] Preserve fail-closed semantics for write-tool logging failures.
- [ ] Task 3: Add security/integration test suite for no-egress and auth coverage (AC: 3, 4)
  - [ ] Add tests that simulate outbound socket/http attempts and assert denial.
  - [ ] Add coverage assertions that all implemented tools require auth + authorization.
- [ ] Task 4: Wire CI quality gates and documentation updates (AC: 5)
  - [ ] Add CI job or gate step for security isolation/auth coverage.
  - [ ] Update traceability/testing docs with new controls.

## Notes

### File Touchpoints / Implementation Notes

- Runtime control points:
  - `src/capital_os/main.py`
  - `src/capital_os/api/app.py`
  - `src/capital_os/config.py`
- Observability and structured security telemetry:
  - `src/capital_os/observability/event_log.py`
- Security and integration tests:
  - `tests/security/test_no_egress_enforcement.py` (new)
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

- Aligns to open SC-06 / NFR-05 gaps currently documented in `docs/traceability-matrix.md`.
- Ensure no test introduces real outbound network dependence.
