# Epic 2: Spend Simulation (FR-07)

## Goal
Deliver `simulate_spend` as deterministic, non-mutating projection logic.

### Story 2.1: Simulation Engine
- Implement one-time and recurring spend projection branches.
- Verify no mutation of canonical ledger tables.

### Story 2.2: Simulate Spend Tool Contract and Logging
- Add schema, handler, and API wiring for `simulate_spend`.
- Verify success/failure event logging and deterministic output hash.

### Story 2.3: Simulation Performance Guardrails
- Add p95 latency assertions for simulation paths.
- Verify p95 < 300ms on reference dataset.
