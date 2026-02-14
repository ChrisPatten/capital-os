# AGENTS.md

## Purpose
This repository is implementing **Capital OS Phase 1: Ledger Core Foundation**.
The goal is to deliver a deterministic, auditable, agent-safe financial truth layer (double-entry ledger) with schema-validated tool interfaces.

Primary context sources:
- `initial_prd.md`
- `_bmad-output/implementation-artifacts/tech-spec-ledger-core-foundation-phase-1-slice.md`

## Current Status
- Product code is greenfield.
- Existing repository content is primarily BMAD workflow/configuration artifacts plus planning docs.
- Build the Phase 1 service and tests from scratch following the constraints below.

## Backlog References
Use these files as the canonical backlog and execution queue:
- Sprint tracker and status source of truth:
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Story implementation briefs (ready-for-dev and in-progress work):
  - `_bmad-output/implementation-artifacts/*.md`
- Epic planning source:
  - `_bmad-output/planning-artifacts/epic-*.md`
- PRD gap-closure backlog plan:
  - `docs/backlog-phase1-prd-closure.md`

Agent workflow order:
1. Read `_bmad-output/implementation-artifacts/sprint-status.yaml` first.
2. Pick the next story in priority order (prefer `ready-for-dev`).
3. Execute against the corresponding story file in `_bmad-output/implementation-artifacts/`.
4. Keep status changes synchronized back to `sprint-status.yaml`.

## Phase 1 Scope (In)
- Account hierarchy management.
- Balanced transaction bundle recording.
- Idempotent transaction recording using `(source_system, external_id)`.
- Balance snapshot recording/retrieval.
- Obligation create/update and active listing behavior.
- Structured tool API contracts with validation.
- Event logging for all tool invocations (success and failure).
- DB security boundaries and append-only enforcement.

## Out of Scope (Do Not Implement In This Slice)
- Capital posture computation.
- Spend simulation.
- Debt optimization analysis.
- Approval workflow beyond schema placeholders.
- Ingestion pipelines, UI/dashboard, browser automation, orchestration.

## Required Stack and Runtime
- Python service code.
- FastAPI transport (`POST /tools/{tool_name}` + `/health`).
- SQLite (file-backed, WAL mode) as the canonical datastore.
- Pytest for unit/integration/replay/security/perf tests.

## Architecture Rules
- Use a domain-first layout with a thin API/tool boundary:
  - `src/capital_os/domain/accounts/*`
  - `src/capital_os/domain/ledger/*`
  - `src/capital_os/tools/*`
- `src/capital_os/observability/*`
- `src/capital_os/db/*`
- `src/capital_os/api/*`
- All ledger mutations must run inside a single ACID DB transaction.
- Canonical ledger state lives in SQLite only.
- Writes must occur only through the Capital OS service/tool layer; non-service consumers use read-only DB access.

## Hard Invariants
- Every committed transaction bundle must satisfy `sum(postings.amount) == 0`.
- Use defense-in-depth:
  - service-level validation
  - DB constraints/enforcement
- Transaction/posting/event history is append-only in normal operations.
- Block `UPDATE`/`DELETE` on append-only tables via DB enforcement.
- Account hierarchy must reject cycles.
- Monetary values use `NUMERIC(20,4)` with round-half-even normalization before persistence/hashing.

## Determinism and Replay
- Deterministic output is non-negotiable.
- Normalize hash inputs:
  - sorted object keys
  - canonical list ordering
  - decimals normalized to 4 dp
  - UTC timestamps with microsecond precision truncation
- Identical stored state + identical inputs must reproduce identical `output_hash`.

## Idempotency Contract
- Scope uniqueness to `(source_system, external_id)`.
- For duplicates:
  - return canonical prior result
  - do not create duplicate ledger rows
- Concurrency behavior:
  - exactly one canonical commit
  - conflict handling must be retry-safe and deterministic

## Tool Contract Requirements (Phase 1)
Implement and validate:
- `record_transaction_bundle`
- `record_balance_snapshot`
- `create_or_update_obligation`

Each tool invocation must emit structured event log fields:
- `tool_name`
- `correlation_id`
- `input_hash`
- `output_hash`
- `timestamp`
- `duration`

Logging requirements:
- Success paths: always logged.
- Validation failures: always logged.
- Write tools: **fail-closed** if event log persistence fails (rollback write transaction).

## Migration and Schema Rules
- Use numbered SQL migrations (`0001`, `0002`, ...).
- Keep migrations reversible (explicit rollback path/script) and test rollback in CI.
- Initial expected migration files:
  - `migrations/0001_ledger_core.sql`
  - `migrations/0002_security_and_append_only.sql`

## Performance and Quality Gates
- p95 latency target for implemented ledger-core tools: `< 300ms` on reference dataset.
- Reference dataset baseline:
  - 100,000 postings
  - 50,000 transactions
  - 5,000 accounts
  - 2,000 obligations
  - 10,000 balance snapshots
  - USD only
- Financial invariants and deterministic hashing logic should be heavily unit-tested.

## Testing Expectations
At minimum, maintain coverage for:
- integration: account hierarchy behavior and cycle rejection
- integration: balanced/unbalanced transaction handling and rollback semantics
- integration: idempotency retry and concurrent duplicate handling
- integration: tool schema validation failure shape
- integration: event-log coverage (success + failure)
- integration: append-only guards
- replay: output hash reproducibility
- security: DB write-boundary enforcement (read-only consumers cannot mutate canonical tables)
- perf: p95 latency checks

## Implementation Priorities
1. Runtime/bootstrap (config, DB session, API shell, schemas).
2. Core schema and DB constraints.
3. Account hierarchy service.
4. Transaction bundle + invariants + idempotency.
5. Snapshot and obligation tools.
6. Deterministic hashing + event logging.
7. Full test suite and CI quality gates.

## Non-Negotiable Safety/Compliance Constraints
- Append-only auditability model.
- No secret material in event payloads.
- No bypass around tool-layer validation for writes.
- Preserve deterministic behavior over convenience refactors.
