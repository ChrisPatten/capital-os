# PRD Traceability Matrix

As of 2026-02-15. Source requirements: `initial_prd.md`.

This document maps PRD criteria to implementation and executable coverage.

## Success Criteria (SC)

| Criterion | Requirement | Implementation | Executable Coverage | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| SC-01 | Committed transactions always balance | `src/capital_os/domain/ledger/invariants.py`, `src/capital_os/domain/ledger/service.py` | `tests/unit/test_invariants.py`, `tests/integration/test_record_transaction_bundle.py` | Covered | Unbalanced bundles reject before commit.
| SC-02 | Deterministic hash-stable outputs | `src/capital_os/observability/hashing.py`, `src/capital_os/tools/*.py` | `tests/replay/test_output_replay.py`, `tests/replay/test_reconciliation_replay.py`, `tests/unit/test_hashing.py` | Covered | Seeded replay checks include posture/simulate/debt/approval/reconciliation.
| SC-03 | 100% tool invocation trace logging | `src/capital_os/observability/event_log.py`, `src/capital_os/api/app.py` | `tests/integration/test_event_log_coverage.py` | Covered | Success and validation failures are asserted.
| SC-04 | Replayability by logged input/state | `src/capital_os/domain/ledger/idempotency.py`, `src/capital_os/domain/approval/service.py` | `tests/replay/test_output_replay.py`, `tests/integration/test_idempotency_external_id.py`, `tests/integration/test_approval_workflow.py` | Covered | Duplicate keys and approval decision replay are deterministic.
| SC-05 | Above-threshold writes are proposed-only until approval | `src/capital_os/domain/approval/policy.py`, `src/capital_os/domain/approval/service.py` | `tests/integration/test_approval_workflow.py` | Covered | No canonical ledger write before approval.
| SC-06 | Runtime boundary: no external network calls | Runtime code layout under `src/capital_os/` | N/A | Gap | Remediation: add egress-deny test harness in a future security story.
| SC-07 | p95 <300ms for compute/simulate/analyze | `tests/perf/test_tool_latency.py` | `tests/perf/test_tool_latency.py` | Partial | Smoke-level perf exists; full reference dataset perf run still pending.

## Functional Requirements (FR)

| Criterion | Requirement | Implementation | Executable Coverage | Status |
| --- | --- | --- | --- | --- |
| FR-01 | Account hierarchy management | `src/capital_os/domain/accounts/service.py`, `src/capital_os/domain/ledger/repository.py` | `tests/integration/test_accounts_hierarchy.py` | Covered |
| FR-02 | Record balanced transaction bundles | `src/capital_os/domain/ledger/service.py` | `tests/integration/test_record_transaction_bundle.py` | Covered |
| FR-03 | Idempotent transaction recording | `src/capital_os/domain/ledger/idempotency.py` | `tests/integration/test_idempotency_external_id.py` | Covered |
| FR-04 | Record balance snapshots | `src/capital_os/domain/ledger/service.py`, `src/capital_os/tools/record_balance_snapshot.py` | `tests/integration/test_snapshot_and_obligation_tools.py` | Covered |
| FR-05 | Track obligations create/update behavior | `src/capital_os/domain/ledger/service.py`, `src/capital_os/tools/create_or_update_obligation.py` | `tests/integration/test_snapshot_and_obligation_tools.py` | Covered |
| FR-06 | Compute capital posture | `src/capital_os/domain/posture/*`, `src/capital_os/tools/compute_capital_posture.py` | `tests/unit/test_posture_engine.py`, `tests/integration/test_event_log_coverage.py`, `tests/replay/test_output_replay.py` | Covered |
| FR-07 | Simulate spend without mutation | `src/capital_os/domain/simulation/*`, `src/capital_os/tools/simulate_spend.py` | `tests/unit/test_simulation_engine.py`, `tests/integration/test_simulation_non_mutation.py`, `tests/replay/test_output_replay.py` | Covered |
| FR-08 | Debt optimization analysis | `src/capital_os/domain/debt/*`, `src/capital_os/tools/analyze_debt.py` | `tests/unit/test_debt_engine.py`, `tests/integration/test_analyze_debt_tool.py`, `tests/replay/test_output_replay.py` | Covered |
| FR-09 | Schema-validated tool API | `src/capital_os/schemas/tools.py`, `src/capital_os/api/app.py` | `tests/integration/test_tool_contract_validation.py` | Covered |
| FR-10 | Tool invocation logging | `src/capital_os/observability/event_log.py` | `tests/integration/test_event_log_coverage.py` | Covered |
| FR-11 | Approval gates for high-impact writes | `src/capital_os/domain/approval/*` | `tests/integration/test_approval_workflow.py`, `tests/replay/test_output_replay.py` | Covered |
| FR-12 | Privilege boundaries | `src/capital_os/db/session.py` (read-only mode) | `tests/security/test_db_role_boundaries.py` | Covered |

## Non-Functional Requirements (NFR)

| Criterion | Requirement | Implementation | Executable Coverage | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| NFR-01 | Determinism | `src/capital_os/observability/hashing.py`, deterministic tool payload shaping | `tests/replay/test_output_replay.py`, `tests/unit/test_hashing.py` | Covered | Seeded repeat-run checks run in CI determinism job.
| NFR-02 | ACID transactionality | `src/capital_os/db/session.py`, write services in single transactions | `tests/integration/test_record_transaction_bundle.py`, `tests/integration/test_approval_workflow.py` | Covered | Failure injection verifies rollback semantics.
| NFR-03 | Performance p95 <300ms | Tool handlers under `src/capital_os/tools/` | `tests/perf/test_tool_latency.py` | Partial | Full reference dataset CI perf gate remains a future hardening item.
| NFR-04 | Observability via correlation_id | `src/capital_os/observability/event_log.py` | `tests/integration/test_event_log_coverage.py` | Covered | Correlation ID persisted for success and validation failures.
| NFR-05 | Safety/isolation (no outbound network) | Service-only architecture | N/A | Gap | Remediation: add explicit no-egress runtime test and CI network policy.
| NFR-06 | Reversible migrations in CI | `migrations/*.sql`, `migrations/*.rollback.sql`, `scripts/check_migration_cycle.py`, `.github/workflows/ci.yml` | CI `migration-reversibility` job | Covered | Apply -> rollback -> re-apply enforced in CI.
| NFR-07 | Financial math branch coverage target | Unit test modules under `tests/unit/` | Existing unit suite | Gap | Remediation: add coverage tooling + branch threshold gate.
| NFR-12 | Policy engine latency overhead <50ms p95 | `src/capital_os/domain/policy/service.py` | `tests/perf/test_tool_latency.py::test_policy_evaluation_overhead_p95_under_50ms` | Covered | Measured as policy evaluation overhead gate.

## Remediation Backlog (Open Gaps)

1. Add egress-deny runtime enforcement tests for SC-06 / NFR-05.
2. Add full reference-dataset performance gate for SC-07 / NFR-03.
3. Add branch coverage threshold enforcement for NFR-07.

## Delta FR Coverage (0215)

| Criterion | Requirement | Implementation | Executable Coverage | Status |
| --- | --- | --- | --- | --- |
| FR-13 | List accounts via deterministic read tool | `src/capital_os/tools/list_accounts.py`, `src/capital_os/domain/query/service.py`, `src/capital_os/domain/ledger/repository.py` | `tests/integration/test_read_query_tools.py`, `tests/replay/test_read_query_replay.py` | Covered |
| FR-14 | Query account hierarchy tree deterministically | `src/capital_os/tools/get_account_tree.py`, `src/capital_os/domain/query/service.py`, `src/capital_os/domain/ledger/repository.py` | `tests/integration/test_read_query_tools.py`, `tests/replay/test_read_query_replay.py` | Covered |
| FR-15 | Query account balances with source policy controls | `src/capital_os/tools/get_account_balances.py`, `src/capital_os/domain/query/service.py`, `src/capital_os/domain/ledger/repository.py` | `tests/integration/test_read_query_tools.py`, `tests/replay/test_read_query_replay.py`, `tests/integration/test_tool_contract_validation.py` | Covered |
| FR-19 | Reconcile account balances with proposed-only adjustments | `src/capital_os/tools/reconcile_account.py`, `src/capital_os/domain/reconciliation/service.py`, `src/capital_os/domain/ledger/repository.py` | `tests/integration/test_reconcile_account_tool.py`, `tests/replay/test_reconciliation_replay.py` | Covered |
| FR-20 | Configurable truth-selection policy wiring | `src/capital_os/config.py`, `src/capital_os/domain/query/service.py`, `src/capital_os/tools/get_account_balances.py` | `tests/integration/test_read_query_tools.py`, `tests/integration/test_tool_contract_validation.py` | Covered |
| FR-24 | Period close controls and adjusting-entry governance | `src/capital_os/domain/periods/service.py`, `src/capital_os/tools/close_period.py`, `src/capital_os/domain/ledger/service.py`, `src/capital_os/schemas/tools.py` | `tests/integration/test_period_policy_controls.py`, `tests/integration/test_tool_contract_validation.py` | Covered |
| FR-25 | Period lock controls and override gating | `src/capital_os/domain/periods/service.py`, `src/capital_os/tools/lock_period.py`, `src/capital_os/domain/ledger/service.py` | `tests/integration/test_period_policy_controls.py`, `tests/integration/test_event_log_coverage.py` | Covered |
| FR-26 | Expanded policy engine dimensions | `src/capital_os/domain/policy/service.py`, `migrations/0006_periods_policies.sql` | `tests/integration/test_period_policy_controls.py`, `tests/perf/test_tool_latency.py` | Covered |
| FR-27 | Multi-party approval workflow semantics | `src/capital_os/domain/approval/service.py`, `src/capital_os/domain/approval/repository.py`, `migrations/0006_periods_policies.sql` | `tests/integration/test_period_policy_controls.py`, `tests/integration/test_approval_workflow.py` | Covered |
