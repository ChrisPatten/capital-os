# Capital OS Backlog: Phase 1 PRD Closure

Date: 2026-02-14
Scope: Close remaining gaps between implemented ledger-core slice and full `initial_prd.md` Phase 1 outcomes.

## Prioritization Logic
- Build deterministic read/computation foundation first.
- Reuse shared posture math for simulation and debt ranking.
- Add approval gating after proposal math is stable.
- Keep ledger mutation paths unchanged unless explicitly required by approval workflow.

## Epic E1: Capital Posture Computation (FR-06)
Priority: P0
Goal: Deliver deterministic `compute_capital_posture` tool with replay-stable `output_hash`.

### Story E1-S1: Posture Domain Model + Inputs
Why: Establish explicit metric definitions before implementation.
Deliverables:
- Add posture input model (liquidity accounts, burn windows, reserve policy config).
- Add deterministic selection rules for account inclusion/exclusion.
Acceptance Criteria:
- Given identical DB state and config, selected input set is byte-stable.
- Unit tests cover selection edge cases and account-type boundaries.

### Story E1-S2: Deterministic Posture Engine
Why: Implement core business value metrics.
Deliverables:
- Implement `fixed_burn`, `variable_burn`, `volatility_buffer`, `reserve_target`, `liquidity`, `liquidity_surplus`, `reserve_ratio`, `risk_band`.
- Implement round-half-even normalization and canonical output ordering.
Acceptance Criteria:
- Unit tests cover formula correctness and boundary conditions.
- Replay tests prove stable `output_hash` for repeated runs on same state.

### Story E1-S3: Tool/API Contract
Why: Expose capability through existing tool transport.
Deliverables:
- Add schema for `compute_capital_posture` request/response.
- Add tool handler and route wiring in `POST /tools/{tool_name}`.
Acceptance Criteria:
- Invalid payloads return deterministic 422 shape and are event-logged.
- Successful invocations include required event fields and `output_hash`.

### Story E1-S4: Performance + Explainability
Why: Meet SLO and auditability.
Deliverables:
- Add explanation payload (contributing balances/assumptions).
- Add perf test for p95 < 300ms on reference dataset.
Acceptance Criteria:
- Perf test passes in CI target environment.
- Explanation fields are deterministic and hash-safe.

Dependencies:
- Blocks E2 and E3.

## Epic E2: Spend Simulation (FR-07)
Priority: P1
Goal: Deliver `simulate_spend` as non-mutating projection logic.

### Story E2-S1: Simulation Engine
Why: Compute impact without touching canonical ledger tables.
Deliverables:
- Implement simulation calculations over posture model and horizon.
- Support recurring and one-time spend branches.
Acceptance Criteria:
- Integration test verifies no writes to ledger/snapshot/obligation tables.
- Deterministic projections for same inputs and state.

### Story E2-S2: Tool/API Contract + Logging
Why: Complete tool-layer behavior and observability.
Deliverables:
- Add schema + handler for `simulate_spend`.
- Ensure success/failure event log coverage.
Acceptance Criteria:
- Validation failure is 422 with machine-readable detail + event log.
- Successful result includes deterministic `output_hash`.

### Story E2-S3: Performance Guardrails
Why: Prevent regression under larger datasets.
Deliverables:
- Add p95 latency assertions and baseline test fixture.
Acceptance Criteria:
- p95 < 300ms on reference dataset profile.

Dependencies:
- Depends on E1.

## Epic E3: Debt Optimization Analysis (FR-08)
Priority: P1
Goal: Deliver deterministic debt payoff ranking with scenario sensitivity.

### Story E3-S1: Liability Analytics Model
Why: Standardize debt scoring inputs.
Deliverables:
- Define liability metrics (rate, minimum payment, term/due profile, balance).
- Add deterministic tie-breakers for ranking.
Acceptance Criteria:
- Unit tests validate ranking determinism for tied scores.
- Output ordering is canonical and replay-stable.

### Story E3-S2: `analyze_debt` Tool
Why: Expose optimization behavior to agent tooling.
Deliverables:
- Implement tool schema, handler, domain service.
- Add optional `payoff_amount` sensitivity branch.
Acceptance Criteria:
- Same input/state yields identical ordering and `output_hash`.
- Event logging coverage includes failures and successes.

### Story E3-S3: Scenario Explanation
Why: Make ranking auditable and decision-usable.
Deliverables:
- Include per-liability explanation fields for score components.
Acceptance Criteria:
- Explanation payload contains no secrets and is deterministic.

Dependencies:
- Depends on E1.

## Epic E4: Approval-Gated Writes (FR-11)
Priority: P2
Goal: Enforce proposal/approval workflow for high-impact mutations.

### Story E4-S1: Approval Policy + Schema
Why: Define exact gating behavior to avoid ambiguous commit paths.
Deliverables:
- Add configurable `approval_threshold_amount`.
- Add proposal entity schema and lifecycle states.
Acceptance Criteria:
- Write above threshold returns `status=\"proposed\"` and does not mutate ledger.
- Below-threshold behavior remains unchanged and deterministic.

### Story E4-S2: Proposal + Approval Tools
Why: Complete governance path.
Deliverables:
- Implement `propose_transaction_bundle` (or integrated proposal response path).
- Implement `approve_proposed_transaction` and `reject_proposed_transaction`.
Acceptance Criteria:
- Approval call is idempotent.
- Exactly one canonical commit occurs after approval.

### Story E4-S3: Transactional Guarantees + Audit
Why: Protect financial integrity under failures/concurrency.
Deliverables:
- Ensure approval commit + event log are single-transaction fail-closed.
- Add concurrency tests for duplicate approve/replay behavior.
Acceptance Criteria:
- No partial writes on failure injection.
- Full traceability from proposal to final commit via correlation/proposal IDs.

Dependencies:
- Depends on E1, E2, E3 completion for consistent impact projections.

## Epic E5: PRD DoD and CI Hardening
Priority: P1
Goal: Prove “Phase 1 complete” against PRD success criteria.

### Story E5-S1: Traceability Matrix in Repo
Deliverables:
- Add a maintained mapping doc: SC/FR/NFR -> tests/files.
Acceptance Criteria:
- Every in-scope PRD criterion points to executable test coverage.

### Story E5-S2: Migration Forward/Rollback CI Gate
Deliverables:
- Add CI job proving migration apply + rollback + re-apply.
Acceptance Criteria:
- CI fails on non-reversible migration defects.

### Story E5-S3: Determinism Regression Suite
Deliverables:
- Extend replay tests across new tools (posture/simulate/debt/approval).
Acceptance Criteria:
- Hash reproducibility holds across repeated seeded runs.

Dependencies:
- Depends on E1-E4 implementation details.

## Recommended Execution Order (Critical Path)
1. E1 Capital Posture (P0)
2. E2 Spend Simulation (P1)
3. E3 Debt Analysis (P1)
4. E5 CI/DoD Hardening (P1, starts in parallel after E1 baseline)
5. E4 Approval-Gated Writes (P2, after projection tools stabilize)

## Definition of “Backlog Complete”
- All stories have owners, estimates, and acceptance tests linked.
- Critical path stories are marked ready with no unresolved dependency ambiguity.
- PRD gap set is reduced to zero for FR-06, FR-07, FR-08, FR-11 and related SC/NFR items.
