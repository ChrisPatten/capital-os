# Comprehensive Analysis (Core)

## Configuration Patterns

- Environment-driven configuration in `src/capital_os/config.py`.
- Primary env vars include:
  - `CAPITAL_OS_DB_URL`
  - `CAPITAL_OS_BALANCE_SOURCE_POLICY`
  - `CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT`
  - `CAPITAL_OS_AUTH_TOKENS_JSON`
  - `CAPITAL_OS_TOOL_CAPABILITIES_JSON`

## Authentication and Authorization

- HTTP authn via `x-capital-auth-token` header.
- Capability-based authz mapped per tool in config defaults or overridden via JSON env config.
- Auth failures and authz denials emit structured event log entries.

## Entry Points and Execution Surface

- ASGI entry: `src/capital_os/main.py` exposing FastAPI `app`.
- HTTP adapter: `src/capital_os/api/app.py`.
- Shared execution engine: `src/capital_os/runtime/execute_tool.py`.
- CLI entrypoint: `capital_os.cli.main:app` (`capital-os` command).

## Shared Code and Domain Reuse

- Shared domain utilities and services under `src/capital_os/domain/*`.
- Shared deterministic hashing and event logging utilities under `src/capital_os/observability/*`.
- Shared DB transaction and read-only contexts under `src/capital_os/db/session.py`.

## Async/Event and Audit Signals

- Event logging is persisted in `event_log` for both success and failure paths.
- Duration and hash fields are computed per invocation for deterministic replay and auditability.
- No external queue/event bus layer is detected in this repository slice.

## CI/CD and Operational Automation

- CI workflow present at `.github/workflows/ci.yml`.
- Migration cycle check script: `scripts/check_migration_cycle.py`.
- Runtime control and smoke scripts: `scripts/serve_with_idle_shutdown.py`, `scripts/mvp_smoke.py`.
- Make targets orchestrate bootstrap, run, health, stop, and smoke sequences.
