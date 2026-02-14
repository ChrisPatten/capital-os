# ADR-001: SQLite as Canonical Ledger Store for Phase 1

- Status: Accepted
- Date: 2026-02-14
- Deciders: Capital OS Architecture
- Related: `ARCHITECTURE.md`, `CONSTITUTION.md`, `initial_prd.md`, `_bmad-output/implementation-artifacts/tech-spec-ledger-core-foundation-phase-1-slice.md`

## Context

Capital OS Phase 1 requires a deterministic, auditable ledger core with strict invariants, idempotency, append-only controls, and replay-safe hashing.

The earlier direction referenced PostgreSQL role-based boundaries and Dockerized runtime assumptions. The current implementation and specification baseline have been migrated to SQLite.

## Decision

Use SQLite (file-backed) as the canonical ledger datastore for Phase 1, with:

- WAL mode enabled.
- Foreign key enforcement enabled.
- Busy timeout configured for retry-safe concurrency behavior.
- Service/tool-layer-only mutation model.
- Read-only connection mode for non-service consumers.

## Rationale

- Simpler local and CI runtime with fewer moving parts.
- Deterministic behavior is easier to preserve with single-file canonical state.
- Phase 1 scope does not require distributed DB features.
- ACID transactions, unique constraints, triggers, and recursive queries satisfy current invariants and idempotency needs.

## Consequences

- Security boundary is enforced via connection mode and file permissions, not DB roles.
- SQL and migration strategy must remain SQLite-compatible.
- Append-only controls rely on SQLite triggers.
- Test harness uses SQLite-native setup/reset flows.

## Guardrails

- Keep all ledger writes inside one DB transaction.
- Preserve append-only enforcement on transaction/posting/event tables.
- Maintain deterministic hashing and replay invariants.
- Any change to idempotency, invariants, or hashing semantics requires a new ADR.

## Follow-ups

- Re-evaluate datastore choice in future phases if workload or operational constraints outgrow SQLite.
