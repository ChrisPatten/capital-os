# Architecture

## Executive Summary

Capital OS is implemented as a domain-first Python modular monolith centered on deterministic financial tooling. Transport adapters (HTTP and CLI) route through a shared execution runtime that enforces schema validation, event logging, and database transaction boundaries.

## Technology Stack

- Python `>=3.11`
- FastAPI + Uvicorn
- Pydantic v2 model contracts
- SQLite canonical ledger store with WAL mode
- Pytest test matrix across unit/integration/replay/security/perf

## Architecture Pattern

- Domain-first modular monolith
- Thin transport adapters
- Shared runtime execution kernel
- Deterministic hashing + auditable event logging

## Component Overview

- `api/`: HTTP boundary, auth/authz checks, transport error mapping.
- `runtime/`: canonical tool dispatch and failure semantics.
- `tools/`: tool handlers with schema-to-domain bridging.
- `domain/`: business invariants and financial logic.
- `db/`: transaction/session controls and migrations.
- `observability/`: input/output hashing and event logging.
- `security/`: token authentication and capability authorization.

## Data Architecture

- Canonical ledger data in SQLite tables with ACID transactions.
- Migration chain (`0001`..`0010`) with explicit rollback scripts.
- Append-only triggers guard mutation of ledger and audit history.
- Read-only query path provided via `query_only` DB connections.

## API Design

- `GET /health`: readiness without implicit DB creation.
- `POST /tools/{tool_name}`: unified tool invocation endpoint.
- Strict payload contract validation through Pydantic models.
- Deterministic error status mapping for transport-level consistency.

## Security Architecture

- Header-token authn (`x-capital-auth-token`) for HTTP requests.
- Capability-based tool authorization mapping.
- Structured event logs for auth/authz failures and normal flows.
- Trusted local CLI path (`capital-os`) using the same runtime invariants.

## Source Tree and Entry Points

- ASGI app export: `src/capital_os/main.py`
- HTTP app: `src/capital_os/api/app.py`
- Runtime dispatcher: `src/capital_os/runtime/execute_tool.py`
- CLI entrypoint: `src/capital_os/cli/main.py`

## Testing Strategy

- Unit tests for deterministic and invariant logic.
- Integration tests for tool flows, rollback semantics, and append-only controls.
- Replay tests for deterministic output-hash reproducibility.
- Security tests for auth and read-only DB boundaries.
- Performance tests for latency and scale behavior.

## Deployment and Operations

- Runtime orchestration through Make targets and helper scripts.
- Dockerized MCP integration path for containerized usage.
- Health/readiness and deterministic smoke workflow available (`make mvp-smoke`).
