# Capital OS Backlog: Phase 1 PRD Closure

Date: 2026-02-15
Scope: Close remaining gaps between implemented ledger-core slice and full `initial_prd.md` Phase 1 outcomes.

Update (2026-02-15): PRD delta requirements from `prd_update_0215.md` are tracked in `docs/backlog-phase1-delta-0215.md` and supersede this file for new agent-enablement scope.

## Execution Status Snapshot (2026-02-15)
- Epic E1 (Capital Posture): implemented.
- Epic E2 (Spend Simulation): implemented.
- Epic E3 (Debt Analysis): implemented.
- Epics E4-E5: backlog/ready-for-dev per `_bmad-output/implementation-artifacts/sprint-status.yaml`.

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
3. E5 CI/DoD Hardening (P1, starts in parallel after E1 baseline)
4. E4 Approval-Gated Writes (P2, after projection tools stabilize)

## Definition of “Backlog Complete”
- All stories have owners, estimates, and acceptance tests linked.
- Critical path stories are marked ready with no unresolved dependency ambiguity.
- PRD gap set is reduced to zero for FR-06, FR-07, FR-08, FR-11 and related SC/NFR items.
---

## Epic E16: Obligation Lifecycle (2026-02-24)

Priority: P1
Goal: Close the obligation lifecycle gap — obligations had no mechanism to be cleared once paid.

### Story E16-S1: `create_or_update_obligation` — active flag support
Why: Agents need to deactivate obligations via the standard upsert path without a separate tool.
Deliverables:
- Add optional `active: bool = True` field to `CreateOrUpdateObligationIn`.
- Update `upsert_obligation` repository to honor `active` instead of hard-coding `active=1`.
- Propagate `active` field through service response and `CreateOrUpdateObligationOut`.
- Migration `0009_obligation_fulfillment.sql`: add `fulfilled_by_transaction_id TEXT` and `fulfilled_at TEXT` columns.
Acceptance Criteria:
- Calling `create_or_update_obligation` with `active: false` sets `active=0` in the DB.
- Existing behavior (no `active` field) defaults to `active=1` — no regression.
- `CreateOrUpdateObligationOut` returns current `active` state.
Status: done (2026-02-24)

### Story E16-S2: `fulfill_obligation` tool
Why: First-class tool for marking an obligation paid, optionally linking the payment transaction.
Deliverables:
- `FulfillObligationIn` schema: `obligation_id`, optional `fulfilled_by_transaction_id`, optional `fulfilled_at`, `correlation_id`.
- `FulfillObligationOut` schema: `status` (`fulfilled` | `already_fulfilled`), `obligation_id`, `fulfilled_by_transaction_id`, `fulfilled_at`, `correlation_id`, `output_hash`.
- `fulfill_obligation` repository function: sets `active=0`, writes `fulfilled_by_transaction_id` and `fulfilled_at`; idempotent (returns `already_fulfilled` if already inactive).
- Domain service: wraps DB call, emits event log, produces deterministic `output_hash`.
- Tool handler: `src/capital_os/tools/fulfill_obligation.py`.
- Registered in `execute_tool.py` (`WRITE_TOOLS`, `TOOL_HANDLERS`), `config.py` (`tools:write`), and `mcp/server.py`.
Acceptance Criteria:
- Calling `fulfill_obligation` on an active obligation sets `active=0` and records `fulfilled_by_transaction_id`.
- Second call returns `status=already_fulfilled` without mutation.
- Event log is written on both success and failure paths.
- `fulfilled_by_transaction_id` is optional; omit to deactivate without linking a transaction.
Status: done (2026-02-24)

---

## Epic E17: DB Config Env Var Compatibility (2026-02-26)

Priority: P2
Goal: Improve operator compatibility by supporting `CAPITAL_OS_DB_PATH` interchangeably with `CAPITAL_OS_DB_URL`.

### Story E17-S1: `CAPITAL_OS_DB_PATH` support with precedence + warning
Why: Different deployment environments provide either URL-style DSNs or direct file paths; the app should accept both without manual translation.
Deliverables:
- Add config loading support for `CAPITAL_OS_DB_PATH` alongside `CAPITAL_OS_DB_URL`.
- Treat `CAPITAL_OS_DB_PATH` and `CAPITAL_OS_DB_URL` as interchangeable inputs for SQLite configuration.
- If both are set, `CAPITAL_OS_DB_PATH` takes precedence and the tool emits a warning.
- Accept `CAPITAL_OS_DB_PATH` values in either form:
- `sqlite:///...` URL form
- direct filesystem path form
- Automatically normalize both forms to the canonical SQLite connection configuration used by the app.
Acceptance Criteria:
- Setting only `CAPITAL_OS_DB_URL` continues to work with no behavior change.
- Setting only `CAPITAL_OS_DB_PATH` works for both `sqlite:///...` and direct file path values.
- When both env vars are set, runtime uses `CAPITAL_OS_DB_PATH` and emits a warning indicating precedence.
- Normalization behavior is deterministic and covered by tests.
Status: backlog

---

## Epic E18: Account Deactivation + Cleanup Workflow (2026-02-26)

Priority: P2
Goal: Provide a safe, auditable way to deactivate accounts created in error and clean up related records with explicit confirmation.

### Story E18-S1: Confirmed account deactivation / cleanup flow
Why: Operators need a recovery path for mistakenly created accounts without ad hoc DB edits.
Deliverables:
- Define an admin-safe tool/workflow to deactivate an account created inadvertently.
- Include a required confirmation step before executing destructive or high-impact cleanup behavior.
- Support cleanup handling for related records (transactions, postings, snapshots, obligations, and dependent references) with deterministic rules.
- Specify and implement how cleanup interacts with append-only/audit constraints (for example: compensating entries / tombstones / archival flags / restricted hard-delete in controlled path).
- Emit structured event logs for preview, confirmation, success, and failure paths.
Acceptance Criteria:
- First call returns a preview/impact summary and a confirmation requirement (no mutation yet).
- Second confirmed call executes exactly once (idempotent confirmation token or equivalent) and records an audit trail.
- Related ledger/snapshot/obligation data is handled per the defined cleanup policy with no orphaned references.
- Behavior is deterministic and covered by integration tests, including cancellation / non-confirmed path.
- No direct manual DB mutation is required for the operator workflow.
Status: backlog
