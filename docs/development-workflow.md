# Development Workflow

As of 2026-02-15.

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
- Apply migrations in order:
  - `migrations/0001_ledger_core.sql`
  - `migrations/0002_security_and_append_only.sql`
  - `migrations/0003_approval_gates.sql`
  - `migrations/0004_read_query_indexes.sql`
  - `migrations/0005_entity_dimension.sql`
- Rollback scripts exist for each forward migration:
  - `migrations/0005_entity_dimension.rollback.sql`
  - `migrations/0004_read_query_indexes.rollback.sql`
  - `migrations/0003_approval_gates.rollback.sql`
  - `migrations/0002_security_and_append_only.rollback.sql`
  - `migrations/0001_ledger_core.rollback.sql`
- Reversibility cycle check (local reproduction for CI gate):
  - `python scripts/check_migration_cycle.py --db-path /tmp/capital-os-migration-cycle.db`

In test setup (`tests/conftest.py`):
- Session scope applies forward migrations once.
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
  - Seeded repeat-run determinism checks for posture/simulate/debt/approval flows.
- Security:
  - Read-only DB connection cannot mutate ledger tables.
- Performance:
  - p95 smoke tests for `record_transaction_bundle`, `compute_capital_posture`, and `simulate_spend`.

## CI Workflow
- Workflow file: `.github/workflows/ci.yml`
- Jobs:
  - `tests`: full pytest suite.
  - `migration-reversibility`: migration apply/rollback/re-apply gate via `scripts/check_migration_cycle.py`.
  - `determinism-regression`: replay/hash regression suite (`tests/replay/test_output_replay.py`).

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
From `sprint-status.yaml` on 2026-02-15:
- Epics 1-5 stories: `done`.
