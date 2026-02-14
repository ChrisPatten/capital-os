# Story 3.3: Debt Scenario Explainability

Status: ready-for-dev

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

- [ ] Task 1: Extend debt response contract with explanations (AC: 1, 2)
  - [ ] Add explicit explanation section to debt response schema.
  - [ ] Keep key ordering and value normalization deterministic.
- [ ] Task 2: Populate explanation payload (AC: 1, 2)
  - [ ] Add score component attribution in debt domain outputs.
  - [ ] Ensure canonical ordering of liabilities and components.
- [ ] Task 3: Enforce no-secret output/logging policy (AC: 3)
  - [ ] Validate that secret fields are not emitted to tool outputs/events.
- [ ] Task 4: Add tests (AC: 4)
  - [ ] Extend replay tests for output hash stability with explanations.
  - [ ] Add explicit assertions for no secret leakage.

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

TBD

### Debug Log References

- Story prepared via create-story workflow intent.

### Completion Notes List

- Story created and marked ready-for-dev.

### File List

- `_bmad-output/implementation-artifacts/3-3-debt-scenario-explainability.md`
