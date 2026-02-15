# Current Implementation State

As of 2026-02-15.

## Delivery Snapshot
- Runtime stack is active: Python 3.11+, FastAPI transport, SQLite canonical store, Pytest suite.
- Ledger core foundations are implemented: accounts, transactions/postings, snapshots, obligations, event log, hashing, idempotency.
- Capital posture tooling from Epic 1 is implemented and tested.
- Spend simulation tooling from Epic 2 is implemented and tested.
- Debt analysis tooling from Epic 3 is implemented and tested.
- Approval-gated write workflow from Epic 4 is implemented and tested.
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
- Observability:
  - `src/capital_os/observability/hashing.py`
  - `src/capital_os/observability/event_log.py`
- DB/session:
  - `src/capital_os/db/session.py`

## Database and Migrations
- Core schema migration: `migrations/0001_ledger_core.sql`
- Security and append-only migration: `migrations/0002_security_and_append_only.sql`
- Approval gates migration: `migrations/0003_approval_gates.sql`
- Rollback scripts are present:
  - `migrations/0001_ledger_core.rollback.sql`
  - `migrations/0002_security_and_append_only.rollback.sql`
  - `migrations/0003_approval_gates.rollback.sql`
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
- Explicit no-egress runtime enforcement tests are not yet present.

## CI and Traceability Additions
- CI workflow: `.github/workflows/ci.yml`
- Traceability matrix: `docs/traceability-matrix.md`
- Determinism replay expansion: `tests/replay/test_output_replay.py`
