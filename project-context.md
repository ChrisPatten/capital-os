# Project Context: Capital OS

Last updated: 2026-02-14

## Mission
Deliver **Capital OS Phase 1: Ledger Core Foundation** as a deterministic, auditable, agent-safe financial truth layer using double-entry accounting and schema-validated tool interfaces.

## Source-of-Truth Order
When instructions conflict, use this precedence:
1. `AGENTS.md` (execution constraints and workflow order for this repo)
2. `ARCHITECTURE.md` (target system design and boundaries)
3. `_bmad-output/implementation-artifacts/tech-spec-ledger-core-foundation-phase-1-slice.md` (implementation slice details)
4. `initial_prd.md` (product requirements and success criteria)
5. `docs/backlog-phase1-prd-closure.md` (post-slice backlog for remaining PRD gaps)
6. `_bmad-output/implementation-artifacts/sprint-status.yaml` (current story/epic tracking)

## Current Reality
- Product code started as greenfield and now has an early implementation scaffold in place.
- Repository still includes substantial BMAD planning/workflow artifacts.
- `sprint-status.yaml` currently tracks Epic 1 posture stories as active/completed, while this repository’s enforced implementation direction remains **ledger-core first** per `AGENTS.md`.

## In-Scope (This Slice)
- Account hierarchy management with cycle rejection.
- `record_transaction_bundle` with strict balancing.
- Idempotency on `(source_system, external_id)`.
- `record_balance_snapshot`.
- `create_or_update_obligation` and active obligation listing behavior.
- Structured request/response validation for tool contracts.
- Event logging for all tool invocations (success and failure).
- Append-only enforcement and DB write-boundary controls.

## Out-of-Scope (This Slice)
- Capital posture computation.
- Spend simulation.
- Debt optimization analysis.
- Approval workflow implementation beyond placeholders.
- UI/dashboard, ingestion pipelines, browser automation, orchestration.

## Required Runtime and Stack
- Python service.
- FastAPI transport with `/health` and `POST /tools/{tool_name}`.
- SQLite file-backed datastore with WAL mode.
- Pytest for unit/integration/replay/security/perf test suites.

## Architecture and Boundary Rules
- Domain-first layout with thin API/tool boundary:
  - `src/capital_os/domain/accounts/*`
  - `src/capital_os/domain/ledger/*`
  - `src/capital_os/tools/*`
  - `src/capital_os/observability/*`
  - `src/capital_os/db/*`
  - `src/capital_os/api/*`
- Canonical ledger truth lives only in SQLite.
- All ledger writes execute inside a single ACID DB transaction.
- Non-service consumers are read-only; no direct mutation path around tools.

## Non-Negotiable Invariants
- Every committed transaction bundle must satisfy `sum(postings.amount) == 0`.
- Defense-in-depth: service validation + DB constraints.
- Transaction/posting/event history is append-only in normal operations.
- DB must block `UPDATE`/`DELETE` on append-only tables.
- Account hierarchy must reject cycles.
- Monetary values normalized to `NUMERIC(20,4)` using round-half-even before persistence/hashing.

## Determinism Rules
- Deterministic output is mandatory.
- Canonical hash inputs require:
  - sorted object keys
  - canonical list ordering
  - decimals normalized to 4dp
  - UTC timestamps with microsecond precision truncation
- Identical stored state + identical inputs must reproduce identical `output_hash`.

## Idempotency Contract
- Uniqueness scope: `(source_system, external_id)`.
- Duplicate submissions return canonical prior result and do not create duplicate rows.
- Concurrent duplicates must yield exactly one canonical commit with retry-safe deterministic conflict handling.

## Tool Contract Baseline
Implement and validate:
- `record_transaction_bundle`
- `record_balance_snapshot`
- `create_or_update_obligation`

Each invocation must log:
- `tool_name`
- `correlation_id`
- `input_hash`
- `output_hash`
- `timestamp`
- `duration`

Write tools are fail-closed: if event-log persistence fails, rollback the write transaction.

## Migration Rules
- Numbered SQL migrations (`0001`, `0002`, ...).
- Reversible migrations with explicit rollback path.
- Initial expected files:
  - `migrations/0001_ledger_core.sql`
  - `migrations/0002_security_and_append_only.sql`

## Quality Gates
- p95 latency target for in-scope tools: `< 300ms` on reference dataset.
- Reference dataset baseline:
  - 100,000 postings
  - 50,000 transactions
  - 5,000 accounts
  - 2,000 obligations
  - 10,000 balance snapshots
  - USD only
- Maintain coverage for:
  - account hierarchy + cycle rejection
  - balanced/unbalanced transaction handling + rollback
  - idempotency retry + concurrent duplicate handling
  - tool schema validation failures
  - event log success/failure coverage
  - append-only guards
  - replay determinism (`output_hash`)
  - DB write-boundary security
  - perf p95 checks

## Execution Workflow
Use this order for day-to-day development:
1. Read `_bmad-output/implementation-artifacts/sprint-status.yaml`.
2. Pick next story by priority, preferring `ready-for-dev`.
3. Execute work from matching `_bmad-output/implementation-artifacts/*.md` story file.
4. Keep story status synchronized back to `sprint-status.yaml`.

