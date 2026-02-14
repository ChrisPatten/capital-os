# Constitution

## 1. Purpose
Capital OS exists to provide a deterministic, auditable financial truth layer for agent-assisted family-office operations. In Phase 1, this constitution governs the ledger-core implementation and all changes to it.

## 2. Authority and Scope
- This constitution applies to code, migrations, tests, and operational behavior in this repository.
- In case of conflict, this order applies:
  1. Safety and legal constraints.
  2. This constitution.
  3. Accepted Architecture Decision Records (ADRs).
  4. Implementation convenience.

## 3. Non-Negotiable Principles
- Determinism First: identical persisted state + identical inputs must produce identical outputs and `output_hash`.
- Auditability First: financial writes and tool invocations must be reconstructable and traceable.
- Defense in Depth: invariants are enforced at service and database layers.
- Fail Closed: write-path observability failure causes transaction rollback.
- Least Privilege: only the service/tool layer may mutate canonical ledger tables; non-service consumers must use read-only DB access.
- Explicit Contracts: tool interfaces are schema-validated JSON with stable error shapes.

## 4. Ledger Truth Invariants
- Every committed transaction bundle must satisfy `sum(postings.amount) == 0`.
- Canonical monetary storage is `NUMERIC(20,4)` with round-half-even normalization.
- Timestamp normalization is UTC with microsecond precision truncation.
- Transaction/posting/event history is append-only in normal operation.
- Corrections are represented as compensating entries, never in-place rewrites.
- Account hierarchy must reject cycles.

## 5. Idempotency and Concurrency
- Idempotency scope is `(source_system, external_id)`.
- Duplicate submissions must return canonical prior results and must not create duplicate rows.
- Concurrent duplicate submissions must result in exactly one canonical commit with deterministic replay responses.

## 6. Tool Governance
- In-scope Phase 1 write tools:
  - `record_transaction_bundle`
  - `record_balance_snapshot`
  - `create_or_update_obligation`
- Every invocation (success and failure) must emit an event record containing:
  - `tool_name`
  - `correlation_id`
  - `input_hash`
  - `output_hash`
  - `timestamp`
  - `duration`
- Validation failures must return machine-readable 4xx responses.

## 7. Security and Boundary Rules
- No direct agent writes to ledger tables.
- No secret material in event payloads.
- Capital OS production runtime must make zero outbound network calls.
- DB enforcement must reject direct `UPDATE`/`DELETE` on append-only tables.

## 8. Migration and Change Control
- Schema changes must be versioned with numbered SQL migrations (`0001`, `0002`, ...).
- Migrations must include tested rollback capability.
- No merge of schema-affecting changes without integration tests.
- Any change to invariants, hashing, or idempotency semantics requires an ADR.

## 9. Testing and Quality Gates
- Required test categories for Phase 1:
  - unit (invariants and normalization)
  - integration (writes, idempotency, hierarchy, validation, append-only)
  - replay (hash reproducibility)
  - security (write boundaries)
  - performance (p95 latency)
- Financial correctness tests are merge-blocking.
- Determinism regressions are merge-blocking.
- Security boundary regressions are merge-blocking.

## 10. Performance Baseline
- p95 latency target for implemented ledger-core tools is `< 300ms` on the reference dataset:
  - 100,000 postings
  - 50,000 transactions
  - 5,000 accounts
  - 2,000 obligations
  - 10,000 balance snapshots
  - USD-only MVP dataset

## 11. Human Oversight and Exceptions
- Any temporary exception must be documented in an ADR with:
  - scope
  - risk
  - expiry date
  - remediation owner
- Emergency operational fixes may bypass process only when required to protect data integrity; follow-up ADR and tests are required before next release.

## 12. Ratification
- Initial ratification date: 2026-02-14.
- This constitution is a living control document and must be kept aligned with `initial_prd.md` and `_bmad-output/implementation-artifacts/tech-spec-ledger-core-foundation-phase-1-slice.md`.
