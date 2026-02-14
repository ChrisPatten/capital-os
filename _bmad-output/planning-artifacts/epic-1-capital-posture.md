# Epic 1: Capital Posture Computation (FR-06)

## Goal
Deliver deterministic `compute_capital_posture` with replay-stable `output_hash`.

### Story 1.1: Posture Domain Model and Inputs
- Define posture input model and deterministic account selection rules.
- Add unit tests for edge cases and account-type boundaries.

### Story 1.2: Deterministic Posture Engine
- Implement posture metrics and canonical ordering/normalization.
- Add unit + replay tests for output hash stability.

### Story 1.3: Compute Capital Posture Tool Contract
- Add schema, handler, and API wiring for `compute_capital_posture`.
- Ensure deterministic 422 validation shape and event logging coverage.

### Story 1.4: Posture Performance and Explainability
- Add deterministic explanation payload and p95 latency test.
- Verify p95 < 300ms on reference dataset.
