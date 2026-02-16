# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Capital OS is a deterministic, auditable financial truth layer built around a double-entry ledger with schema-validated tool APIs for agent use. Currently in Phase 1 (Ledger Core Foundation).

**Tech stack:** Python 3.11+, FastAPI, SQLite (WAL mode), Pytest.

## Common Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run performance tests only
pytest -m performance

# Run a single test file
pytest tests/unit/test_invariants.py

# Run a single test by name
pytest -k "test_balanced_postings"

# Bootstrap database (migrate + seed COA)
make init

# Start runtime (idempotent if already healthy)
make run

# Start with idle auto-shutdown (default 300s)
CAPITAL_OS_IDLE_SECONDS=300 make serve-idle

# Health check / stop
make health
make stop

# Full deterministic MVP smoke test (reset -> migrate -> seed -> serve -> assertions -> stop)
make mvp-smoke

# Apply migrations manually
python3 scripts/apply_migrations.py

# Check migration reversibility (local CI gate reproduction)
python scripts/check_migration_cycle.py --db-path /tmp/capital-os-migration-cycle.db

# Validate COA seed without applying
python3 scripts/import_coa.py config/coa.yaml --validate-only
```

## Architecture

**Strict layering:** API/tools -> domain services -> repository/DB. No direct API-to-DB bypass.

```
src/capital_os/
  api/app.py             # FastAPI: GET /health, POST /tools/{tool_name}
  tools/                 # Thin handlers mapping tool contracts to domain services
  domain/                # Business logic organized by subdomain
    accounts/service.py  # Hierarchy rules, cycle rejection
    ledger/              # Transaction recording, idempotency, invariants, repository
    posture/             # Capital posture computation
    simulation/          # Spend simulation
    debt/                # Debt analysis
    approval/            # Approval workflow (propose/approve/reject)
    entities/            # Multi-entity dimension
    periods/             # Period management (close/lock)
    policy/              # Policy rules
    reconciliation/      # Account reconciliation
    query/               # Read query surface
  db/session.py          # SQLite connection, transaction boundary helper
  observability/         # Event log + deterministic input/output hashing
  schemas/               # Pydantic request/response contracts
  security/              # Auth (header token), authz (capability-based), correlation IDs
  config.py              # Typed env-driven settings
```

## Non-Negotiable Invariants

These are enforced at both service and DB layers (defense-in-depth):

- **Balanced bundles:** Every committed transaction bundle must satisfy `sum(postings.amount) == 0`.
- **Append-only:** Transaction, posting, and event-log history cannot be UPDATEd or DELETEd. Corrections use compensating entries.
- **Idempotency:** Scoped to `(source_system, external_id)`. Duplicates return the canonical prior result.
- **Monetary precision:** `NUMERIC(20,4)` with round-half-even normalization before persistence and hashing.
- **Determinism:** Identical persisted state + identical inputs must produce identical `output_hash`. Hash inputs use sorted keys, canonical list ordering, 4dp decimals, UTC timestamps with microsecond truncation.
- **Fail-closed writes:** If event-log persistence fails, the entire write transaction rolls back.
- **Cycle rejection:** Account hierarchy must reject cycles.

## Authentication & Authorization

All tool calls require `x-capital-auth-token` header and `x-correlation-id` header.

Default dev tokens (in `config.py`):
- `dev-admin-token` — capabilities: `tools:read`, `tools:write`, `tools:approve`, `tools:admin`
- `dev-reader-token` — capabilities: `tools:read`

Each tool maps to a required capability (e.g., `record_transaction_bundle` requires `tools:write`).

## Database & Migrations

- SQLite file at `data/capital_os.db` (configurable via `CAPITAL_OS_DB_URL`).
- Numbered SQL migrations in `migrations/` (0001–0008), each with a `.rollback.sql` counterpart.
- Migrations must be reversible and tested via `scripts/check_migration_cycle.py`.
- Tests use function-scoped DB reset (delete + re-migrate) for deterministic isolation.

## CI Quality Gates

Defined in `.github/workflows/ci.yml`. All are merge-blocking:
1. **tests** — full pytest suite
2. **migration-reversibility** — apply/rollback/re-apply cycle
3. **determinism-regression** — replay hash reproducibility
4. **security-auth-surface** — auth/authz/correlation enforcement
5. **epic8-multi-entity-gates** — multi-entity replay and performance

## Test Organization

```
tests/
  unit/          # Invariants, normalization, hashing
  integration/   # Writes, idempotency, hierarchy, validation, append-only, approval
  replay/        # Output hash reproducibility (determinism regression)
  security/      # Write-boundary enforcement, auth surface
  perf/          # p95 latency validation (<300ms target)
  support/       # Test helpers and fixtures
  conftest.py    # DB setup: session-scoped migration, function-scoped reset
```

## Document Precedence

When instructions conflict, follow this order:
1. `CONSTITUTION.md` (non-negotiable principles)
2. `AGENTS.md` (execution constraints)
3. `ARCHITECTURE.md` (system design)
4. `_bmad-output/implementation-artifacts/tech-spec-*.md` (implementation details)
5. `initial_prd.md` (product requirements)

## Sprint Workflow

1. Read `_bmad-output/implementation-artifacts/sprint-status.yaml` for current status.
2. Pick next story by priority, preferring `ready-for-dev`.
3. Execute from the corresponding story file in `_bmad-output/implementation-artifacts/`.
4. Sync status back to `sprint-status.yaml`.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `CAPITAL_OS_DB_URL` | `sqlite:///./data/capital_os.db` | Database connection |
| `CAPITAL_OS_AUTH_TOKEN` | `dev-admin-token` | Auth token for curl/smoke tests |
| `CAPITAL_OS_BALANCE_SOURCE_POLICY` | `best_available` | `ledger_only`, `snapshot_only`, or `best_available` |
| `CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT` | `1000.0000` | Threshold for approval workflow |
| `CAPITAL_OS_AUTH_TOKENS_JSON` | (built-in dev tokens) | JSON override for token->identity map |
| `CAPITAL_OS_TOOL_CAPABILITIES_JSON` | (built-in defaults) | JSON override for tool->capability map |
| `CAPITAL_OS_IDLE_SECONDS` | `300` | Idle auto-shutdown for `make serve-idle` |

## Runtime State

Runtime files are written under `.run/` (gitignored):
- `.run/capital-os.pid` — server process ID
- `.run/capital-os.url` — server base URL
- `.run/uvicorn.log` — server logs
