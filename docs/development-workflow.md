# Development Workflow

As of 2026-02-14.

## Environment and Startup
- Python requirement: `>=3.11` (`pyproject.toml`).
- Install dependencies (example):
  - `pip install -e ".[dev]"`
- Default DB URL is configured in `src/capital_os/config.py`:
  - `sqlite:///./data/capital_os.db`
- Override with:
  - `export CAPITAL_OS_DB_URL=sqlite:///./data/capital_os.db`
- Run API:
  - `uvicorn capital_os.main:app --reload`

## Migration Workflow
- Apply core schema:
  - `migrations/0001_ledger_core.sql`
- Apply security/append-only controls:
  - `migrations/0002_security_and_append_only.sql`
- Rollback scripts exist and are used by tests:
  - `migrations/0002_security_and_append_only.rollback.sql`
  - `migrations/0001_ledger_core.rollback.sql`

In test setup (`tests/conftest.py`):
- Session scope applies both forward migrations once.
- Function scope resets DB by rollback then re-apply for test isolation.

## Test Execution
- Run all tests:
  - `pytest`
- Run only performance tests:
  - `pytest -m performance`

Current test coverage areas:
- Unit:
  - Ledger invariants and normalization.
  - Posture model/engine behavior and deterministic output hash.
- Integration:
  - Account hierarchy and cycle rejection.
  - Balanced/unbalanced transaction handling.
  - Idempotency replay behavior.
  - Tool validation error shape.
  - Event logging on success and validation failures.
  - Append-only trigger enforcement.
- Replay:
  - Stable `output_hash` for repeated identical inputs.
- Security:
  - Read-only DB connection cannot mutate ledger tables.
- Performance:
  - p95 smoke tests for `record_transaction_bundle` and `compute_capital_posture`.

## Agent Backlog Workflow
Canonical files:
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/*.md`
- `_bmad-output/planning-artifacts/epic-*.md`
- `docs/backlog-phase1-prd-closure.md`

Execution order for agents:
1. Read `_bmad-output/implementation-artifacts/sprint-status.yaml`.
2. Select next story by priority, preferring `ready-for-dev`.
3. Execute against the corresponding story artifact.
4. Synchronize story status updates back into `sprint-status.yaml`.

## Current Priority Queue
From `sprint-status.yaml` on 2026-02-14:
- Epic 1 Story `1-4-posture-performance-and-explainability`: `review`.
- Epics 2-5 stories are `backlog`.
