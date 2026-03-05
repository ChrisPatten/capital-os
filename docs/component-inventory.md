# Component Inventory

## Runtime and Transport

- `src/capital_os/api/app.py`: FastAPI app, auth/authz gateway, endpoint mapping.
- `src/capital_os/runtime/execute_tool.py`: canonical execution kernel and result envelope handling.
- `src/capital_os/cli/*`: trusted local operator interface and runtime bootstrap wrappers.

## Domain Components

- `domain/accounts`: account lifecycle and hierarchy constraints.
- `domain/ledger`: transaction recording, invariants, idempotency, repository operations.
- `domain/approval`: proposal/decision workflows.
- `domain/policy` and `domain/periods`: governance and accounting-period controls.
- `domain/query`: read-side query service operations with pagination support.
- `domain/posture`, `domain/simulation`, `domain/debt`: analytical and planning surfaces.
- `domain/reconciliation`: account reconciliation workflows.

## Persistence and Schema

- `db/session.py`: transaction/read-only context and WAL pragmas.
- `db/migrations.py`: forward migration discovery and apply tracking.
- `migrations/*.sql`: schema evolution and trigger/index enforcement.

## Observability and Security

- `observability/event_log.py`: structured event persistence.
- `observability/hashing.py`: deterministic input/output hash generation.
- `security/auth.py` + `security/context.py`: token auth and security context propagation.

## Contract Surface

- `schemas/tools.py`: Pydantic request/response contracts for tool handlers.
- `tools/*.py`: contract-bound tool handler layer.
