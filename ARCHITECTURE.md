# Architecture

## 1. System Goal
Phase 1 provides a canonical ledger core with deterministic tool interfaces for account hierarchy, balanced transaction recording, snapshots, obligations, and audit-grade observability.

## 2. Scope Boundary
In scope:
- Account hierarchy management.
- `record_transaction_bundle`.
- `record_balance_snapshot`.
- `create_or_update_obligation`.
- `compute_capital_posture`.
- `compute_consolidated_posture`.
- `simulate_spend`.
- Event logging, idempotency, append-only controls, and write boundaries.

Out of scope in this slice:
- Debt analysis.
- Approval workflow implementation.
- UI/ingestion/orchestration layers.

## 3. High-Level Components
- API Layer (`src/capital_os/api/app.py`):
  - FastAPI app, `/health`, and `POST /tools/{tool_name}` endpoints.
  - Validates request/response schema contracts.
- Tool Layer (`src/capital_os/tools/*`):
  - Thin handlers mapping tool contracts to domain services.
  - No business rules beyond contract translation and error mapping.
- Domain Services:
  - Accounts (`src/capital_os/domain/accounts/service.py`): hierarchy rules and cycle rejection.
  - Ledger (`src/capital_os/domain/ledger/service.py`): atomic write orchestration.
  - Posture (`src/capital_os/domain/posture/service.py`): deterministic capital posture computation.
  - Simulation (`src/capital_os/domain/simulation/service.py`): deterministic non-mutating spend projection.
- Domain Rules (`src/capital_os/domain/ledger/invariants.py`):
  - Balanced postings and monetary normalization checks.
- Idempotency (`src/capital_os/domain/ledger/idempotency.py`):
  - Duplicate detection and deterministic replay behavior.
- Repository (`src/capital_os/domain/ledger/repository.py`):
  - Persistence and deterministic read/query ordering.
- Observability:
  - Hashing (`src/capital_os/observability/hashing.py`): canonical input/output hashing.
  - Event Log (`src/capital_os/observability/event_log.py`): complete invocation logging.
- Database Access (`src/capital_os/db/session.py`):
  - Session lifecycle and explicit transaction boundary helper.
- Configuration (`src/capital_os/config.py`):
  - Typed env-driven settings.

## 4. Data Architecture
Canonical store: SQLite (file-backed) with WAL mode enabled for concurrency and durability.

Primary entities:
- Accounts (typed hierarchy with parent-child and metadata).
- Transactions (bundle header with idempotency identifiers).
- Postings (double-entry rows associated to transaction).
- Balance Snapshots (point-in-time observation keyed by account/date).
- Obligations (cadence and expected amount metadata).
- Event Log (tool invocation trace records).

Schema/migration expectations:
- `migrations/0001_ledger_core.sql`: core tables, keys, and constraints.
- `migrations/0002_security_and_append_only.sql`: append-only enforcement and write-boundary controls.

## 5. Write Path (Canonical)
1. Request enters tool endpoint.
2. Schema validation executes; invalid payloads return deterministic 4xx and still log event.
3. Domain invariant checks run (including sum-to-zero and normalization).
4. Idempotency check executes on `(source_system, external_id)` where applicable.
5. Service writes inside one ACID transaction.
6. Event log row is persisted in same transaction for write tools.
7. If event log persistence fails, transaction rolls back (fail-closed).
8. Response is serialized in canonical order and hashed.

## 6. Determinism Strategy
- Canonical ordering of response objects/lists.
- Monetary values normalized to 4 decimal places (round-half-even).
- Timestamps normalized to UTC with microsecond precision truncation.
- Hashing uses normalized payloads with sorted keys.
- Replay tests must reproduce original `output_hash` from persisted state + logged inputs.

## 7. Idempotency Strategy
- Unique scope: `(source_system, external_id)`.
- Duplicate requests return existing canonical result.
- Concurrency handling relies on DB uniqueness and retry-safe read-after-conflict behavior.
- Exactly one canonical commit must exist for a duplicate idempotency key race.

## 8. Security and Trust Boundaries
- Only the Capital OS service process/tool layer can mutate canonical ledger tables.
- Non-service/agent consumers must connect with read-only SQLite mode and cannot directly write ledger tables.
- Append-only protections reject direct `UPDATE`/`DELETE` on protected tables.
- Production runtime policy is zero outbound network egress.
- Event payloads must not contain secret material.

## 9. Error Model
- Contract errors: 4xx with machine-readable validation details.
- Domain invariant violations: deterministic error shape, no partial writes.
- Idempotent replay: explicit replay status with canonical IDs/hashes.
- Internal failures: transactional rollback guarantees and traceable event records when possible.

## 10. Operational Characteristics
- Health endpoint verifies service liveness and DB connectivity.
- Observability baseline includes correlation IDs, input/output hashes, and duration.
- Performance SLO for implemented tools: p95 `< 300ms` on reference dataset.

## 11. Testing Architecture
- Unit tests:
  - invariant logic and value normalization
  - canonical hashing behavior
- Integration tests:
  - account hierarchy and cycle rejection
  - balanced/unbalanced transaction handling
  - idempotency duplicate + concurrency paths
  - snapshots and obligations persistence contracts
  - event-log completeness and fail-closed write behavior
  - append-only enforcement
- Replay tests:
  - output hash reproducibility
- Security tests:
  - DB write-boundary enforcement (read-only connection mutation attempts fail)
- Performance tests:
  - tool latency p95 validation

## 12. Reference Dataset for Perf/Replay Baseline
- 100,000 postings
- 50,000 transactions
- 5,000 accounts
- 2,000 obligations
- 10,000 balance snapshots
- Currency scope: USD only for MVP

## 13. Evolution Rules
- Changes to invariants, idempotency semantics, or hashing must be captured in ADRs.
- Baseline datastore decision is captured in `docs/adr/ADR-001-sqlite-canonical-ledger-store.md`.
- New domain capabilities (capital posture, simulation, debt analysis, approvals) should be added as separate architecture slices after this foundation is stable.
- Remaining new domain capabilities (debt analysis and approvals) should be added as separate architecture slices after this foundation is stable.
- Preserve strict layering: API/tools -> domain services -> repository/DB. No direct API-to-DB bypass.
