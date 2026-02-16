# Current Implementation State

As of 2026-02-16.

## Delivery Snapshot
- Runtime stack is active: Python 3.11+, FastAPI transport, SQLite canonical store, Pytest suite.
- Ledger core foundations are implemented: accounts, transactions/postings, snapshots, obligations, event log, hashing, idempotency.
- Capital posture tooling from Epic 1 is implemented and tested.
- Spend simulation tooling from Epic 2 is implemented and tested.
- Debt analysis tooling from Epic 3 is implemented and tested.
- Approval-gated write workflow from Epic 4 is implemented and tested.
- Epic 6 read/query surface is implemented (Stories 6.1, 6.2, 6.3).
- Epic 7 reconciliation and truth policy tooling is implemented.
- Epic 8 entity-dimension foundation (Story 8.1) is implemented and in review.
- Epic 9 period controls and policy expansion are implemented.
- Epic 10 API security controls are implemented (authn/authz/correlation/no-egress).
- Sprint tracker status (`_bmad-output/implementation-artifacts/sprint-status.yaml`):
  - `1-1-posture-domain-model-and-inputs`: `done`
  - `1-2-deterministic-posture-engine`: `done`
  - `1-3-compute-capital-posture-tool-contract`: `done`
  - `1-4-posture-performance-and-explainability`: `done`
  - `2-1-simulation-engine`: `done`
  - `2-2-simulate-spend-tool-contract-and-logging`: `done`
  - `2-3-simulation-performance-guardrails`: `done`
  - `3-1-liability-analytics-model`: `done`
  - `3-2-analyze-debt-tool`: `done`
  - `3-3-debt-scenario-explainability`: `done`
  - `4-1-approval-policy-and-schema`: `done`
  - `4-2-proposal-and-approval-tools`: `done`
  - `4-3-approval-transactionality-and-audit`: `done`
  - Epic 4: `done`
  - `5-1-traceability-matrix`: `done`
  - `5-2-migration-reversibility-ci-gate`: `done`
  - `5-3-determinism-regression-suite-expansion`: `done`
  - Epic 5: `done`
  - `epic-6`: `done`
  - `6-1-read-query-tooling-foundation`: `done`
  - `6-2-transaction-and-obligation-query-surface`: `done`
  - `6-3-config-and-proposal-read-surface`: `done`
  - `epic-8`: `in-progress`
  - `8-1-entity-dimension-schema-migration`: `review`
  - `8-2-consolidated-posture-and-inter-entity-rules`: `ready-for-dev`
  - `8-3-multi-entity-scale-and-regression-tests`: `ready-for-dev`
  - `epic-9`: `done`
  - `9-1-period-close-lock-and-adjustments`: `done`
  - `9-2-policy-engine-expansion`: `done`
  - `9-3-multi-party-approval-and-latency-budget`: `done`
  - `epic-10`: `done`
  - `10-1-authentication-baseline`: `done`
  - `10-2-tool-level-authorization-and-correlation`: `done`
  - `10-3-no-egress-enforcement-and-security-coverage`: `done`
  - `epic-7`: `done`
  - `7-1-reconciliation-domain-and-tool`: `done`
  - `7-2-truth-selection-policy-wiring`: `done`
  - `7-3-reconciliation-tests-and-determinism`: `done`

## Implemented Service Surface
- API entrypoint: `src/capital_os/api/app.py`
- Routes:
  - `GET /health`
  - `POST /tools/{tool_name}`
- Registered tools:
  - `record_transaction_bundle`
  - `record_balance_snapshot`
  - `create_or_update_obligation`
  - `compute_capital_posture`
  - `simulate_spend`
  - `analyze_debt`
  - `approve_proposed_transaction`
  - `reject_proposed_transaction`
  - `list_accounts`
  - `get_account_tree`
  - `get_account_balances`
  - `list_transactions`
  - `get_transaction_by_external_id`
  - `list_obligations`
  - `list_proposals`
  - `get_proposal`
  - `get_config`
  - `propose_config_change`
  - `approve_config_change`
  - `reconcile_account`
  - `close_period`
  - `lock_period`

## Domain and Persistence Modules
- Accounts domain:
  - `src/capital_os/domain/accounts/service.py`
- Ledger domain:
  - `src/capital_os/domain/ledger/service.py`
  - `src/capital_os/domain/ledger/repository.py`
  - `src/capital_os/domain/ledger/invariants.py`
  - `src/capital_os/domain/ledger/idempotency.py`
- Posture domain:
  - `src/capital_os/domain/posture/models.py`
  - `src/capital_os/domain/posture/engine.py`
  - `src/capital_os/domain/posture/service.py`
- Simulation domain:
  - `src/capital_os/domain/simulation/engine.py`
  - `src/capital_os/domain/simulation/service.py`
- Debt domain:
  - `src/capital_os/domain/debt/engine.py`
  - `src/capital_os/domain/debt/service.py`
- Approval domain:
  - `src/capital_os/domain/approval/policy.py`
  - `src/capital_os/domain/approval/repository.py`
  - `src/capital_os/domain/approval/service.py`
- Period domain:
  - `src/capital_os/domain/periods/service.py`
- Policy domain:
  - `src/capital_os/domain/policy/service.py`
- Observability:
  - `src/capital_os/observability/hashing.py`
  - `src/capital_os/observability/event_log.py`
- DB/session:
- `src/capital_os/db/session.py`
- Security runtime:
  - `src/capital_os/security/auth.py`
  - `src/capital_os/security/no_egress.py`
  - `src/capital_os/security/context.py`

## Database and Migrations
- Core schema migration: `migrations/0001_ledger_core.sql`
- Security and append-only migration: `migrations/0002_security_and_append_only.sql`
- Approval gates migration: `migrations/0003_approval_gates.sql`
- Read query index migration: `migrations/0004_read_query_indexes.sql`
- Entity dimension migration: `migrations/0005_entity_dimension.sql`
- Period/policy expansion migration: `migrations/0006_periods_policies.sql`
- Query-surface index migration: `migrations/0007_query_surface_indexes.sql`
- API security runtime controls migration: `migrations/0008_api_security_runtime_controls.sql`
- Rollback scripts are present:
  - `migrations/0001_ledger_core.rollback.sql`
  - `migrations/0002_security_and_append_only.rollback.sql`
  - `migrations/0003_approval_gates.rollback.sql`
  - `migrations/0004_read_query_indexes.rollback.sql`
  - `migrations/0005_entity_dimension.rollback.sql`
  - `migrations/0006_periods_policies.rollback.sql`
  - `migrations/0007_query_surface_indexes.rollback.sql`
- Migration reversibility check script:
  - `scripts/check_migration_cycle.py`

Implemented schema elements include:
- `accounts`
- `ledger_transactions`
- `ledger_postings`
- `balance_snapshots`
- `obligations`
- `event_log`
- `approval_proposals`
- `approval_decisions`
- `entities`
- `accounting_periods`
- `policy_rules`

Implemented DB protections include:
- Account cycle prevention triggers on `accounts`.
- Append-only triggers on `ledger_transactions`, `ledger_postings`, and `event_log`.
- Unique idempotency key on `(source_system, external_id)` for `ledger_transactions`.
- Unique proposal key on `(tool_name, source_system, external_id)` for approval-gated writes.

## Determinism and Invariants (Current Behavior)
- Monetary normalization uses round-half-even to 4 decimal places.
- Transaction bundles enforce balanced postings in service logic.
- Tool payload hashing normalizes key ordering, decimals, and date/time formatting.
- Duplicate `(source_system, external_id)` transaction requests return idempotent replay response.
- Above-threshold transaction requests return deterministic `status="proposed"` responses and do not mutate canonical ledger tables.
- Approval decision paths (`approve` / `reject`) are deterministic and auditable.
- Tool events are persisted for success and validation failures.

## Known Gaps Against AGENTS.md "Phase 1 Scope (In)"
- Full stress/perf validation against the reference dataset scale in AGENTS.md is not yet present; current perf tests are smoke-level.
- Some append-only enforcement allows one controlled update on `ledger_transactions` to persist `response_payload` and `output_hash` post-insert (intended for idempotent replay support).
- Full reference-dataset performance validation remains pending.

## CI and Traceability Additions
- CI workflow: `.github/workflows/ci.yml`
- Traceability matrix: `docs/traceability-matrix.md`
- Determinism replay expansion: `tests/replay/test_output_replay.py`
