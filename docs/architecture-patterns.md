# Architecture Patterns

## Primary Pattern

- **Domain-first modular monolith** with a thin transport boundary.

## Pattern Characteristics

- API boundary in `src/capital_os/api/` maps HTTP requests to shared runtime execution.
- Shared execution kernel in `src/capital_os/runtime/execute_tool.py` enforces validation, logging, and transaction semantics.
- Tool handlers in `src/capital_os/tools/` provide stable contract-to-domain entry points.
- Domain logic segmented by bounded areas under `src/capital_os/domain/*`.
- Canonical persistence and transaction handling isolated to `src/capital_os/db/*`.
- Determinism/observability concerns isolated to `src/capital_os/observability/*`.

## Data and Consistency Pattern

- Single canonical SQLite store.
- Numbered forward migrations with rollback scripts.
- Append-only enforcement via DB triggers for ledger and audit history.
- Write tool fail-closed behavior when event logging persistence fails.

## Security and Access Pattern

- Header-token authentication + capability authorization for HTTP.
- Trusted local CLI path using the same shared execution runtime.
- Read-only DB boundary support via `query_only` connections.
