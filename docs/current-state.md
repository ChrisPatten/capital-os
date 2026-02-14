# Current Implementation State

As of 2026-02-14.

## Delivery Snapshot
- Runtime stack is active: Python 3.11+, FastAPI transport, SQLite canonical store, Pytest suite.
- Ledger core foundations are implemented: accounts, transactions/postings, snapshots, obligations, event log, hashing, idempotency.
- Capital posture tooling from Epic 1 is also implemented and tested, even though original Phase 1 scope text focused on ledger core.
- Sprint tracker status (`_bmad-output/implementation-artifacts/sprint-status.yaml`):
  - `1-1-posture-domain-model-and-inputs`: `done`
  - `1-2-deterministic-posture-engine`: `done`
  - `1-3-compute-capital-posture-tool-contract`: `done`
  - `1-4-posture-performance-and-explainability`: `review`
  - Epics 2-5: backlog

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
- Observability:
  - `src/capital_os/observability/hashing.py`
  - `src/capital_os/observability/event_log.py`
- DB/session:
  - `src/capital_os/db/session.py`

## Database and Migrations
- Core schema migration: `migrations/0001_ledger_core.sql`
- Security and append-only migration: `migrations/0002_security_and_append_only.sql`
- Rollback scripts are present:
  - `migrations/0001_ledger_core.rollback.sql`
  - `migrations/0002_security_and_append_only.rollback.sql`

Implemented schema elements include:
- `accounts`
- `ledger_transactions`
- `ledger_postings`
- `balance_snapshots`
- `obligations`
- `event_log`

Implemented DB protections include:
- Account cycle prevention triggers on `accounts`.
- Append-only triggers on `ledger_transactions`, `ledger_postings`, and `event_log`.
- Unique idempotency key on `(source_system, external_id)` for `ledger_transactions`.

## Determinism and Invariants (Current Behavior)
- Monetary normalization uses round-half-even to 4 decimal places.
- Transaction bundles enforce balanced postings in service logic.
- Tool payload hashing normalizes key ordering, decimals, and date/time formatting.
- Duplicate `(source_system, external_id)` transaction requests return idempotent replay response.
- Tool events are persisted for success and validation failures.

## Known Gaps Against AGENTS.md "Phase 1 Scope (In)"
- Full stress/perf validation against the reference dataset scale in AGENTS.md is not yet present; current perf tests are smoke-level.
- No CI workflow files are present yet for migration forward/rollback enforcement.
- Some append-only enforcement allows one controlled update on `ledger_transactions` to persist `response_payload` and `output_hash` post-insert (intended for idempotent replay support).

## Not Implemented Yet (Backlog)
- Epic 2: spend simulation.
- Epic 3: debt optimization analysis.
- Epic 4: approval-gated write workflow.
- Epic 5: traceability matrix and CI hardening work.
