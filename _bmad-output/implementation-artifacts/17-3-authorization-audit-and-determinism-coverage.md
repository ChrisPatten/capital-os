# Story 17.3: Authorization, Audit, and Determinism Coverage

Status: done

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

- [x] Task 1: Authorization regression coverage (AC: 1, 7)
  - [x] Add/extend API security tests to verify duplicate-risk paths still require write capabilities.
  - [x] Validate reader token (`dev-reader-token`) receives 403 on write and approval tool paths.
  - [x] Confirm DB write-boundary security tests remain green for read-only consumers.
- [x] Task 2: Event-log coverage expansion (AC: 2, 3, 4)
  - [x] Add integration tests for duplicate-risk proposal success and validation failure logging.
  - [x] Add approval/reject log assertions for duplicate-risk-triggered proposals.
  - [x] Add explicit fail-closed test for duplicate-risk proposal flow when event log insert fails.
- [x] Task 3: Replay and determinism test expansion (AC: 5, 6)
  - [x] Add replay tests validating deterministic `output_hash` and payload ordering for duplicate-risk proposals.
  - [x] Add concurrency tests for simultaneous duplicate-risk-triggering submissions to ensure canonical deterministic outcomes.
- [x] Task 4: Performance guardrail verification (AC: 8)
  - [x] Extend/update perf tests to include duplicate-risk match-check overhead.
  - [x] Assert p95 latency remains < 300ms on reference/fixture dataset profile.
- [x] Task 5: Documentation and traceability updates (AC: 1–8)
  - [x] Update `docs/testing-matrix.md` with duplicate-risk coverage mapping.
  - [x] Update `docs/current-state.md` to reflect duplicate-risk approval behavior and coverage.
  - [x] Update traceability artifacts if required by current DoD workflow.

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

## Dev Agent Record

### Implementation Plan

- Add explicit security regression coverage for duplicate-risk write/proposal/approval paths, including reader-token denial and read-only DB boundary assertions.
- Expand event-log coverage for duplicate-risk success, validation failure, decision logging, and fail-closed rollback behavior.
- Add concurrency and perf guardrails for duplicate-risk proposal path, then update documentation coverage mapping.

### Debug Log

- Added API authz regression test for duplicate-risk write and decision paths under `dev-reader-token`.
- Added DB boundary test to prove read-only connections cannot write approval proposal tables.
- Expanded event-log integration coverage with duplicate-risk validation failure, approve/reject decision logging, and fail-closed rollback when event-log insert aborts.
- Added concurrent duplicate-risk submission test to ensure canonical proposal/output hash behavior.
- Added duplicate-risk proposal-path p95 latency smoke test under performance suite.
- Updated testing matrix and current-state docs to reflect duplicate-risk authz/audit/determinism/perf coverage.
- Ran targeted suite:
- `pytest -q tests/security/test_api_security_controls.py tests/security/test_db_role_boundaries.py tests/integration/test_event_log_coverage.py tests/integration/test_approval_workflow.py tests/replay/test_output_replay.py tests/perf/test_tool_latency.py`

### Completion Notes

- ✅ AC1/AC7: Duplicate-risk write/proposal/decision paths enforce `tools:write`; reader token receives deterministic `403`; read-only DB connections cannot mutate approval tables.
- ✅ AC2/AC3/AC4: Duplicate-risk proposal/decision success and validation failures are event-logged with required hash/correlation fields; fail-closed behavior preserves rollback on event-log persistence failure.
- ✅ AC5/AC6: Replay determinism remains stable and concurrent duplicate-risk submissions return canonical proposal/output hash results.
- ✅ AC8: Duplicate-risk proposal path perf guardrail (`p95 < 300ms`) is covered in perf smoke tests (reference-scale validation remains tracked separately in current-state gaps).

### File List

- tests/security/test_api_security_controls.py
- tests/security/test_db_role_boundaries.py
- tests/integration/test_event_log_coverage.py
- tests/integration/test_approval_workflow.py
- tests/perf/test_tool_latency.py
- docs/testing-matrix.md
- docs/current-state.md
- _bmad-output/implementation-artifacts/17-3-authorization-audit-and-determinism-coverage.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

### Change Log

- 2026-03-05: Added duplicate-risk authz/audit/fail-closed/concurrency/perf coverage and synchronized story/docs/sprint tracking to review.
- 2026-03-05: Senior review fixes applied: tightened duplicate-risk decision event-log field assertions, corrected current-state status sync for Stories 17.1/17.2, and clarified AC8 as smoke-level perf evidence.

### Senior Developer Review (AI)

- Outcome: Changes Requested (addressed in this pass)
- Fixed High findings:
  - Corrected stale status reporting in `docs/current-state.md` for Stories 17.1 and 17.2.
  - Clarified AC8 completion language to match smoke-level perf evidence and avoid over-claiming reference-scale validation.
- Fixed Medium findings:
  - Expanded duplicate-risk decision event-log assertions to include timestamp and duration fields.
  - Added explicit review traceability notes for what was corrected and why.
  - Kept 17.3 file list scoped to files materially changed in this story; cross-story working-tree edits remain tracked in their originating story files.
