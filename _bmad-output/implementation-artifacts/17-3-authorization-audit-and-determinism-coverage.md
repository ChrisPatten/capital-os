# Story 17.3: Authorization, Audit, and Determinism Coverage

Status: ready-for-dev

## Story

As a family-office risk owner,  
I want duplicate-risk approval behavior to be fully covered for authz, audit, and replay determinism,  
so that the new gate is safe to operate in production without weakening security or traceability guarantees.

## Acceptance Criteria

1. Duplicate-risk proposal and decision flows enforce existing write authorization boundaries (`tools:write`) with no regressions.
2. Duplicate-risk proposal path logs success and validation failures with required fields:
  - `tool_name`
  - `correlation_id`
  - `input_hash`
  - `output_hash`
  - `timestamp`
  - `duration`
3. Approval/reject decision calls for duplicate-risk proposals are event-logged and replay-safe.
4. Event-log fail-closed behavior is preserved: if event persistence fails, write/proposal mutation rolls back.
5. Replay tests prove duplicate-risk proposal payload and hash reproducibility across repeated runs on identical state.
6. Concurrency tests confirm deterministic behavior for serial and concurrent submissions that generate duplicate-risk proposals.
7. Security tests confirm read-only consumers cannot mutate canonical tables through duplicate-risk paths.
8. p95 latency remains within existing ledger-core target budget after duplicate-risk checks.

## Tasks / Subtasks

- [ ] Task 1: Authorization regression coverage (AC: 1, 7)
  - [ ] Add/extend API security tests to verify duplicate-risk paths still require write capabilities.
  - [ ] Validate reader token (`dev-reader-token`) receives 403 on write and approval tool paths.
  - [ ] Confirm DB write-boundary security tests remain green for read-only consumers.
- [ ] Task 2: Event-log coverage expansion (AC: 2, 3, 4)
  - [ ] Add integration tests for duplicate-risk proposal success and validation failure logging.
  - [ ] Add approval/reject log assertions for duplicate-risk-triggered proposals.
  - [ ] Add explicit fail-closed test for duplicate-risk proposal flow when event log insert fails.
- [ ] Task 3: Replay and determinism test expansion (AC: 5, 6)
  - [ ] Add replay tests validating deterministic `output_hash` and payload ordering for duplicate-risk proposals.
  - [ ] Add concurrency tests for simultaneous duplicate-risk-triggering submissions to ensure canonical deterministic outcomes.
- [ ] Task 4: Performance guardrail verification (AC: 8)
  - [ ] Extend/update perf tests to include duplicate-risk match-check overhead.
  - [ ] Assert p95 latency remains < 300ms on reference/fixture dataset profile.
- [ ] Task 5: Documentation and traceability updates (AC: 1–8)
  - [ ] Update `docs/testing-matrix.md` with duplicate-risk coverage mapping.
  - [ ] Update `docs/current-state.md` to reflect duplicate-risk approval behavior and coverage.
  - [ ] Update traceability artifacts if required by current DoD workflow.

## Dev Notes

### Scope Clarification

- This story hardens and proves the behavior introduced by Stories 17.1 and 17.2.
- No new product semantics should be introduced here beyond verification and guardrails.

### Security and Compliance Expectations

- Preserve append-only constraints and fail-closed write behavior.
- Keep duplicate-risk responses free of secrets/sensitive payload leakage beyond approved transaction detail fields.
- Maintain deterministic canonical serialization for all logged and replayed payloads.

### Suggested File Touchpoints

- `tests/integration/test_event_log_coverage.py`
- `tests/integration/test_approval_workflow.py`
- `tests/integration/test_tool_contract_validation.py`
- `tests/security/test_api_security_controls.py`
- `tests/security/test_db_role_boundaries.py`
- `tests/replay/test_output_replay.py`
- `tests/perf/test_tool_latency.py`
- `docs/testing-matrix.md`
- `docs/current-state.md`

### References

- [Source: `_bmad-output/planning-artifacts/epic-17-duplicate-risk-approval-gate.md`]
- [Source: `_bmad-output/implementation-artifacts/17-1-duplicate-risk-detection-rule-in-write-path.md`]
- [Source: `_bmad-output/implementation-artifacts/17-2-proposal-contract-and-approval-decision-expansion.md`]
- [Source: `CONSTITUTION.md`]
