# Development Workflow

As of 2026-02-23.

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
- Make-based runtime controls:
  - `make init`
  - `make run`
  - `make serve-idle`
  - `make health`
  - `make stop`
- Runtime state files:
  - `.run/capital-os.pid`
  - `.run/capital-os.url`
  - `.run/last_request.ts`
  - `.run/uvicorn.log`

## CLI Workflow

The `capital-os` CLI is a trusted local operator channel that invokes tools without the HTTP server.

### Installation
```bash
# Editable dev install (recommended)
pip install -e .

# Operator install via pipx
pipx install .

# Fallback — direct module invocation
python -m capital_os.cli.main
```

### Shell Completion Setup
```bash
# Install completion for your shell
capital-os --install-completion bash
capital-os --install-completion zsh
capital-os --install-completion fish

# Display completion script without installing
capital-os --show-completion bash
```

### Selecting a Database (`--db-path`)
All local-mode commands support `--db-path` to point at a specific SQLite file:
```bash
# Use default database (from CAPITAL_OS_DB_URL env or config)
capital-os health

# Target a specific database file
capital-os health --db-path /path/to/capital_os.db
capital-os tool list --db-path /tmp/test.db
capital-os tool call list_accounts --json '{"correlation_id":"c1"}' --db-path /tmp/test.db
```

A missing or non-file path produces structured JSON on stderr and exits with code `1`.

### Common CLI Commands
```bash
# Health check
capital-os health

# List registered tools
capital-os tool list

# Show tool schema
capital-os tool schema record_transaction_bundle

# Invoke a tool — inline JSON
capital-os tool call list_accounts --json '{"correlation_id":"local-001"}'

# Invoke a tool — JSON file
capital-os tool call create_account --json @payload.json

# Invoke a tool — stdin
echo '{"correlation_id":"local-002"}' | capital-os tool call list_accounts

# Start HTTP server
capital-os serve
capital-os serve --host 0.0.0.0 --port 9000
```

### Exit-Code Convention
- `0` — success (result JSON on stdout)
- `1` — failure (structured error JSON on stderr)

## Migration Workflow
- Apply migrations in order:
  - `migrations/0001_ledger_core.sql`
  - `migrations/0002_security_and_append_only.sql`
  - `migrations/0003_approval_gates.sql`
  - `migrations/0004_read_query_indexes.sql`
  - `migrations/0005_entity_dimension.sql`
  - `migrations/0006_periods_policies.sql`
  - `migrations/0007_query_surface_indexes.sql`
  - `migrations/0008_api_security_runtime_controls.sql`
- Rollback scripts exist for each forward migration:
  - `migrations/0008_api_security_runtime_controls.rollback.sql`
  - `migrations/0007_query_surface_indexes.rollback.sql`
  - `migrations/0006_periods_policies.rollback.sql`
  - `migrations/0005_entity_dimension.rollback.sql`
  - `migrations/0004_read_query_indexes.rollback.sql`
  - `migrations/0003_approval_gates.rollback.sql`
  - `migrations/0002_security_and_append_only.rollback.sql`
  - `migrations/0001_ledger_core.rollback.sql`
- Reversibility cycle check (local reproduction for CI gate):
  - `python scripts/check_migration_cycle.py --db-path /tmp/capital-os-migration-cycle.db`

In test setup (`tests/conftest.py`):
- Session scope applies forward migrations once.
- Function scope resets DB by deleting SQLite files and re-applying forward migrations for deterministic isolation.

## COA Bootstrap Workflow (MVP)
- Validate COA seed file:
  - `python3 scripts/import_coa.py config/coa.yaml --validate-only`
- Dry-run COA seed:
  - `python3 scripts/import_coa.py config/coa.yaml --dry-run`
- Apply COA seed:
  - `python3 scripts/import_coa.py config/coa.yaml`
- Governance boundary:
  - `config/coa.yaml` is bootstrap/reset input only.
  - Post-bootstrap account changes should use governed API/tool flows.

## Migration Utility (MVP Runtime Controls)
- Apply forward migrations:
  - `python3 scripts/apply_migrations.py`

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
  - p95 policy evaluation overhead gate (`<50ms`).

## CI Workflow
- Workflow file: `.github/workflows/ci.yml`
- Jobs:
  - `tests`: full pytest suite.
  - `migration-reversibility`: migration apply/rollback/re-apply gate via `scripts/check_migration_cycle.py`.
  - `determinism-regression`: replay/hash regression suite (`tests/replay/test_output_replay.py`).
  - `security-auth-surface`: auth/authz/correlation security checks.
  - `epic8-multi-entity-gates`: multi-entity replay and scale checks.

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
From `sprint-status.yaml` on 2026-02-16:
- Epic 11 stories remain `backlog`.
- Epic 12 stories:
  - `12-1`: `done`
  - `12-2`: `done`
  - `12-3`: `done`
