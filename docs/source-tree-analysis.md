# Source Tree Analysis

## Top-Level Structure

```text
capital-os/
├── src/capital_os/           # Application code
│   ├── api/                  # FastAPI transport boundary
│   ├── runtime/              # Shared tool execution path
│   ├── tools/                # Tool handlers (contract boundary)
│   ├── domain/               # Domain services and invariants
│   ├── db/                   # Connection/session/migration helpers
│   ├── observability/        # Hashing and event log facilities
│   ├── security/             # Authn/authz context and policy checks
│   ├── schemas/              # Pydantic request/response models
│   ├── cli/                  # Trusted local CLI operator channel
│   └── main.py               # ASGI app export entry point
├── migrations/               # Numbered SQL migrations + rollbacks
├── tests/                    # Unit, integration, replay, security, perf
├── scripts/                  # Migration/bootstrap/runtime helper scripts
├── config/                   # COA and runtime config artifacts
├── docs/                     # Documentation and process references
└── mcp/                      # MCP integration runtime components
```

## Critical Folders and Purpose

- `src/capital_os/api`: request parsing, auth gates, HTTP status mapping.
- `src/capital_os/runtime`: deterministic tool dispatch, validation error normalization, event log fail-closed behavior.
- `src/capital_os/tools`: per-tool payload adaptation into domain services.
- `src/capital_os/domain`: business rules (ledger invariants, approvals, posture, reconciliation, query).
- `src/capital_os/db`: transaction contexts, read-only boundary, migration application.
- `migrations`: canonical schema evolution path with explicit rollback files.
- `tests`: enforcement of invariants, replay determinism, role boundaries, and latency thresholds.

## Entry Points

- HTTP API entry: `src/capital_os/api/app.py`
- ASGI export: `src/capital_os/main.py`
- CLI entrypoint: `src/capital_os/cli/main.py`
- Migration bootstrap script: `scripts/apply_migrations.py`

## Integration Paths

- HTTP and CLI both delegate to the shared runtime executor.
- Runtime executor calls tool handlers, then domain services under DB transaction context.
- Domain/query read paths use read-only DB connections for write-boundary enforcement.
- Observability components (hashing/event log) are shared across transport channels.
