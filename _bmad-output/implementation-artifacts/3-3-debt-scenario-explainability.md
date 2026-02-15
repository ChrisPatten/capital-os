# Story 3.3: Debt Scenario Explainability

Status: done

## Story

As a family-office AI operator,
I want deterministic score-component explanations for each liability,
so that debt recommendations are auditable without exposing secret material.

## Acceptance Criteria

1. Debt analysis outputs include deterministic per-liability score component explanations.
2. Explanation payload is hash-safe and stable for replay.
3. Outputs and logs exclude secret/sensitive material.
4. Tests verify explainability determinism and secrecy guardrails.

## Tasks / Subtasks

- [x] Task 1: Extend debt response contract with explanations (AC: 1, 2)
  - [x] Add explicit explanation section to debt response schema.
  - [x] Keep key ordering and value normalization deterministic.
- [x] Task 2: Populate explanation payload (AC: 1, 2)
  - [x] Add score component attribution in debt domain outputs.
  - [x] Ensure canonical ordering of liabilities and components.
- [x] Task 3: Enforce no-secret output/logging policy (AC: 3)
  - [x] Validate that secret fields are not emitted to tool outputs/events.
- [x] Task 4: Add tests (AC: 4)
  - [x] Extend replay tests for output hash stability with explanations.
  - [x] Add explicit assertions for no secret leakage.

## Dev Notes

### Developer Context Section

- Explainability must increase auditability without increasing leakage risk.

### Technical Requirements

- Deterministic output and replay safety are non-negotiable.
- No secret material in response or event payloads.

### File Structure Requirements

- Likely touch:
  - debt domain/service and schemas
  - replay/integration tests

### References

- [Source: `initial_prd.md`]
- [Source: `ARCHITECTURE.md`]
- [Source: `_bmad-output/planning-artifacts/epic-3-debt-analysis.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Added deterministic per-liability score explanations to the debt output contract.
- Added validation guardrails rejecting secret-like identifiers and unknown extra input fields.
- Sanitized validation error payload/event logging in API layer to avoid secret leakage.
- Added replay and integration assertions covering explainability determinism and secrecy guarantees.

### File List

- `_bmad-output/implementation-artifacts/3-3-debt-scenario-explainability.md`
- `src/capital_os/api/app.py`
- `src/capital_os/schemas/tools.py`
- `src/capital_os/domain/debt/engine.py`
- `tests/integration/test_analyze_debt_tool.py`
- `tests/replay/test_output_replay.py`
