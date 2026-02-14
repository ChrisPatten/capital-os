# Epic 3: Debt Optimization Analysis (FR-08)

## Goal
Deliver deterministic debt payoff ranking with scenario sensitivity.

### Story 3.1: Liability Analytics Model
- Define debt scoring inputs and deterministic tie-breakers.
- Add unit tests validating stable ranking output.

### Story 3.2: Analyze Debt Tool
- Implement schema, handler, and service for `analyze_debt`.
- Support optional payoff amount sensitivity branch.

### Story 3.3: Debt Scenario Explainability
- Add deterministic per-liability score component explanation fields.
- Ensure no secret material appears in outputs/logs.
