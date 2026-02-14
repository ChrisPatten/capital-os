---
title: 'Ledger Core Foundation (Phase 1 Slice)'
slug: 'ledger-core-foundation-phase-1-slice'
created: '2026-02-14T16:19:51Z'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - 'Python'
  - 'PostgreSQL (Docker)'
  - 'Docker Compose'
  - 'Pytest'
files_to_modify:
  - 'docker-compose.yml'
  - 'src/capital_os/config.py'
  - 'src/capital_os/api/app.py'
  - 'src/capital_os/db/session.py'
  - 'src/capital_os/domain/accounts/models.py'
  - 'src/capital_os/domain/accounts/service.py'
  - 'src/capital_os/domain/ledger/models.py'
  - 'src/capital_os/domain/ledger/invariants.py'
  - 'src/capital_os/domain/ledger/idempotency.py'
  - 'src/capital_os/domain/ledger/service.py'
  - 'src/capital_os/domain/ledger/repository.py'
  - 'src/capital_os/tools/record_transaction_bundle.py'
  - 'src/capital_os/tools/record_balance_snapshot.py'
  - 'src/capital_os/tools/create_or_update_obligation.py'
  - 'src/capital_os/observability/event_log.py'
  - 'src/capital_os/observability/hashing.py'
  - 'src/capital_os/schemas/tools.py'
  - 'migrations/0001_ledger_core.sql'
  - 'migrations/0002_security_and_append_only.sql'
  - 'tests/integration/test_accounts_hierarchy.py'
  - 'tests/integration/test_record_transaction_bundle.py'
  - 'tests/integration/test_idempotency_external_id.py'
  - 'tests/integration/test_event_log_coverage.py'
  - 'tests/integration/test_tool_contract_validation.py'
  - 'tests/integration/test_append_only_guards.py'
  - 'tests/perf/test_tool_latency.py'
  - 'tests/replay/test_output_replay.py'
  - 'tests/security/test_db_role_boundaries.py'
code_patterns:
  - 'Confirmed Clean Slate: no pre-existing application service code in repository root'
  - 'Domain-first Python package layout: domain modules with thin tool/API boundary'
  - 'PostgreSQL as canonical ledger state with ACID transaction boundaries'
  - 'Deterministic output shaping (canonical ordering, normalized hashes)'
  - 'Idempotent write contract via (source_system, external_id) uniqueness and retry-safe responses'
test_patterns:
  - 'Pytest-based unit tests for invariant and financial math behavior'
  - 'Integration tests against Dockerized Postgres for schema and write semantics'
  - 'Concurrency tests for idempotency race handling'
  - 'Replay and determinism tests keyed by correlation_id/input_hash/output_hash'
  - 'Performance tests validating p95 latency targets'
---

# Tech-Spec: Ledger Core Foundation (Phase 1 Slice)

**Created:** 2026-02-14T16:19:51Z

## Overview

### Problem Statement

We need a canonical, auditable double-entry ledger core that enforces balancing and idempotency so downstream capital tooling can rely on deterministic financial state.

### Solution

Build a greenfield Python service implementing ledger-core capabilities on PostgreSQL running in Docker, with strict transaction invariants and tool-layer validation.

### Scope

**In Scope:**
- Account hierarchy management.
- Balanced transaction bundle recording.
- Idempotent transaction recording via `(source_system, external_id)`.
- Balance snapshot recording and retrieval.
- Core schema and constraints for ledger entities.

**Out of Scope:**
- Capital posture, simulation, and debt analysis tools.
- Approval workflow implementation.
- UI, ingestion pipelines, and agent orchestration.

## Context for Development

### Codebase Patterns

Confirmed Clean Slate for product code: there is no existing application service implementation in the repository root yet. Existing content is BMAD workflow/configuration assets plus the PRD. Implementation will be greenfield with a domain-first Python package layout and a thin tool/API boundary.

Patterns to follow:
- PostgreSQL is the canonical ledger store and all write paths execute inside ACID transactions.
- Financial invariants are enforced in service validation and DB constraints.
- Tool outputs are deterministic by design via canonical ordering and normalized hashing inputs.
- Idempotency is first-class for write tools through `(source_system, external_id)` uniqueness and deterministic retry responses.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `initial_prd.md` | Source requirements and scope baseline for Capital OS Phase 1. |
| `_bmad-output/implementation-artifacts/tech-spec-ledger-core-foundation-phase-1-slice.md` | Finalized implementation specification baseline. |
| `_bmad/bmm/config.yaml` | Workflow configuration including output paths and communication settings. |

### Files to Modify/Create

| File | Purpose |
| ---- | ------- |
| `docker-compose.yml` | Local PostgreSQL runtime with pinned image and health checks. |
| `src/capital_os/config.py` | Environment/config loading for service and DB settings. |
| `src/capital_os/api/app.py` | Tool API bootstrap and health endpoint surface. |
| `src/capital_os/db/session.py` | Connection/session and transaction boundary management. |
| `src/capital_os/domain/accounts/models.py` | Account hierarchy domain entities and persistence mapping. |
| `src/capital_os/domain/accounts/service.py` | Account create/list/tree behavior. |
| `src/capital_os/domain/ledger/models.py` | Transaction/posting/snapshot/obligation models. |
| `src/capital_os/domain/ledger/invariants.py` | Balance and precision invariant checks. |
| `src/capital_os/domain/ledger/idempotency.py` | Idempotency key handling and retry semantics. |
| `src/capital_os/domain/ledger/service.py` | Atomic ledger write orchestration. |
| `src/capital_os/domain/ledger/repository.py` | Ledger persistence queries and deterministic reads. |
| `src/capital_os/tools/record_transaction_bundle.py` | Balanced transaction bundle tool contract and handler. |
| `src/capital_os/tools/record_balance_snapshot.py` | Balance snapshot tool contract and handler. |
| `src/capital_os/tools/create_or_update_obligation.py` | Obligation write/update tool contract and handler. |
| `src/capital_os/observability/event_log.py` | Structured tool invocation logging. |
| `src/capital_os/observability/hashing.py` | Stable hashing utilities for inputs/outputs. |
| `src/capital_os/schemas/tools.py` | Request/response contracts and validation schemas for ledger-core tools. |
| `migrations/0001_ledger_core.sql` | Initial schema and constraints for ledger core entities. |
| `migrations/0002_security_and_append_only.sql` | Role grants/revokes and append-only trigger/policy enforcement. |
| `tests/integration/*.py` | Integration coverage for schema, invariants, idempotency, logging. |
| `tests/unit/*.py` | Fast unit checks for invariant logic and normalization behavior. |
| `tests/perf/*.py` | Performance checks for tool latency targets. |
| `tests/replay/*.py` | Replayability and output hash consistency validation. |
| `tests/security/*.py` | DB privilege boundary and write-role enforcement tests. |

### Technical Decisions

- Use PostgreSQL as canonical ledger datastore.
- Run PostgreSQL in Docker with pinned image tag `postgres:16.4-alpine` for local/dev/CI parity.
- Implement application/service logic in Python.
- Use pytest as the baseline test runner across unit/integration/perf/replay suites.
- Prioritize strict invariant enforcement and deterministic behavior at the ledger boundary.
- ADR-001: Structure Python service as domain-first modules (`accounts`, `transactions`, `snapshots`) with a thin tool/API boundary.
- ADR-002: Execute all ledger mutations inside ACID Postgres transactions.
- ADR-003: Enforce `(source_system, external_id)` idempotency with DB uniqueness plus deterministic service responses on retries.
- ADR-004: Enforce balancing invariants at both service validation and DB layers for defense-in-depth.
- ADR-005: Pin Dockerized Postgres image/version for reproducible local and CI behavior.
- ADR-006: Tool transport/runtime is FastAPI HTTP JSON (`POST /tools/{tool_name}`) for all in-scope ledger-core tools.
- ADR-007: Idempotency uniqueness scope is `(source_system, external_id)` with a required `source_system` input field.
- ADR-008: Event logging is fail-closed for write tools: if event log persistence fails, the write transaction is rolled back.
- ADR-009: Monetary storage uses `NUMERIC(20,4)` with round-half-even normalization at service boundary.
- ADR-010: Timestamp normalization is UTC-only with ISO-8601 serialization and microsecond precision truncation.
- ADR-011: Migration convention is forward-only numbered SQL files (`0001`, `0002`, ...), each with explicit rollback script or rollback section tested in CI.
- `project-context.md` not found; no additional repository-specific coding conventions are imposed.

### Tool API Contracts (In Scope)

Runtime/Transport:
- FastAPI JSON endpoints with schema-validated request/response payloads.
- Endpoint pattern: `POST /tools/record_transaction_bundle`, `POST /tools/record_balance_snapshot`, `POST /tools/create_or_update_obligation`.

`record_transaction_bundle` request:
- `source_system` (string, required)
- `external_id` (string, required)
- `date` (ISO-8601 timestamp, required)
- `description` (string, required)
- `postings` (array, min 2, required) with each posting:
  - `account_id` (UUID, required)
  - `amount` (decimal string, required)
  - `currency` (3-letter code, required, must be `USD` in MVP)
  - `memo` (string, optional)
- `correlation_id` (UUID/string, required)

`record_transaction_bundle` response:
- `status` (`committed` or `idempotent-replay`)
- `transaction_id` (UUID)
- `posting_ids` (ordered array of UUIDs in canonical order)
- `correlation_id`
- `output_hash`

`record_balance_snapshot` request:
- `source_system` (string, required)
- `account_id` (UUID, required)
- `snapshot_date` (date, required)
- `balance` (decimal string, required)
- `currency` (3-letter code, required, must be `USD` in MVP)
- `source_artifact_id` (string, optional)
- `correlation_id` (UUID/string, required)

`record_balance_snapshot` response:
- `status` (`recorded` or `updated`)
- `snapshot_id` (UUID)
- `account_id`
- `snapshot_date`
- `correlation_id`
- `output_hash`

`create_or_update_obligation` request:
- `source_system` (string, required)
- `name` (string, required)
- `account_id` (UUID, required)
- `cadence` (`monthly`|`annual`|`custom`, required)
- `expected_amount` (decimal string, required)
- `variability_flag` (boolean, optional)
- `next_due_date` (date, required)
- `metadata` (object, optional)
- `correlation_id` (UUID/string, required)

`create_or_update_obligation` response:
- `status` (`created` or `updated`)
- `obligation_id` (UUID)
- `correlation_id`
- `output_hash`

### Invariants and Determinism Rules

- `sum(postings.amount) == 0` is required for every committed transaction.
- Transaction, posting, and event_log history are append-only; DB-level triggers block UPDATE/DELETE in normal operation.
- `external_id` must be unique per `(source_system, external_id)` for idempotent writes.
- Monetary values are persisted as `NUMERIC(20,4)` and normalized with round-half-even before hashing and storage.
- Tool outputs use canonical ordering for deterministic hashing and replay.
- Hash inputs must normalize decimal formatting, UTC timestamps (microsecond precision), and key ordering.
- Balance snapshots are reconciliation observations; posted ledger entries remain canonical truth.
- Account hierarchy must reject cycles at write time (service validation + recursive DB check).
- Idempotent race handling uses unique-index conflict resolution with transactional retry-safe read-after-conflict behavior.

## Implementation Plan

### Tasks

- [ ] Task 1: Establish runtime and service bootstrap
  - File: `docker-compose.yml`
  - Action: Define PostgreSQL service with pinned image, health check, persistent volume, and exposed local port.
  - Notes: Use `postgres:16.4-alpine` and keep config stable for local and CI parity.
  - File: `src/capital_os/config.py`
  - Action: Implement typed configuration loader for DB URL, service env, and ledger settings (precision, idempotency scope).
  - Notes: Fail fast on missing required env vars.
  - File: `src/capital_os/api/app.py`
  - Action: Create FastAPI bootstrap, `/health`, and JSON tool endpoints for in-scope ledger-core tools.
  - Notes: Keep boundary thin; delegate domain logic to services.
  - File: `src/capital_os/db/session.py`
  - Action: Add connection/session factory and explicit transaction wrapper utility.
  - Notes: Provide single transaction boundary helper for write tools.
  - File: `src/capital_os/schemas/tools.py`
  - Action: Implement request/response schemas for all in-scope tools.
  - Notes: Reject invalid payloads with machine-readable validation errors.

- [ ] Task 2: Create initial ledger-core schema and constraints
  - File: `migrations/0001_ledger_core.sql`
  - Action: Create tables for accounts, transactions, postings, balance_snapshots, obligations, and event_log.
  - Notes: Include FK integrity, `NUMERIC(20,4)` constraints, and idempotency uniqueness on `(source_system, external_id)`.
  - File: `migrations/0002_security_and_append_only.sql`
  - Action: Add append-only triggers for transaction/posting/event tables and role grants/revokes for service vs agent roles.
  - Notes: Block UPDATE/DELETE in normal operation and deny direct writes for non-service role.
  - File: `src/capital_os/domain/ledger/models.py`
  - Action: Add model mappings and canonical field names matching migration schema.
  - Notes: Keep naming deterministic and explicit.
  - File: `src/capital_os/domain/accounts/models.py`
  - Action: Add account hierarchy model fields (`type`, `parent_id`, metadata).
  - Notes: Support deep subtree retrieval.

- [ ] Task 3: Implement account hierarchy services
  - File: `src/capital_os/domain/accounts/service.py`
  - Action: Implement create/list/subtree retrieval with deterministic ordering and cycle prevention.
  - Notes: Enforce valid parent-child relationships, account type constraints, and cycle rejection.
  - File: `src/capital_os/domain/ledger/repository.py`
  - Action: Add account persistence queries and ordered subtree read methods.
  - Notes: Return stable sort order for repeatable outputs.

- [ ] Task 4: Implement balanced transaction bundle recording
  - File: `src/capital_os/tools/record_transaction_bundle.py`
  - Action: Define request/response schema and handler for `record_transaction_bundle`.
  - Notes: Include `source_system`, `external_id`, and correlation support.
  - File: `src/capital_os/domain/ledger/invariants.py`
  - Action: Implement invariant checks for balance sum and decimal precision normalization.
  - Notes: Reject before write if invalid.
  - File: `src/capital_os/domain/ledger/idempotency.py`
  - Action: Implement idempotency lookup/resolution flow for duplicate `(source_system, external_id)`.
  - Notes: On unique-conflict race, read canonical committed row and return deterministic replay response.
  - File: `src/capital_os/domain/ledger/service.py`
  - Action: Implement atomic transaction+postings commit path and rollback on any failure.
  - Notes: Single ACID boundary for all ledger writes.

- [ ] Task 5: Implement snapshots and obligations tools
  - File: `src/capital_os/tools/record_balance_snapshot.py`
  - Action: Implement snapshot upsert/read by canonical key `(account_id, snapshot_date)`.
  - Notes: Preserve deterministic behavior on duplicate submissions.
  - File: `src/capital_os/tools/create_or_update_obligation.py`
  - Action: Implement create/update flow for obligations with cadence and due date fields.
  - Notes: Return deterministic list/query ordering for active obligations.
  - File: `src/capital_os/domain/ledger/repository.py`
  - Action: Add persistence functions for snapshots and obligations.
  - Notes: Keep query contracts explicit and stable.

- [ ] Task 6: Implement structured observability and deterministic hashing
  - File: `src/capital_os/observability/hashing.py`
  - Action: Add canonical input/output hashing utilities with normalized decimals, UTC microsecond timestamps, and sorted keys.
  - Notes: Required for replayability and determinism validation.
  - File: `src/capital_os/observability/event_log.py`
  - Action: Emit event record for each tool invocation (success and validation failure).
  - Notes: Include tool name, correlation_id, input_hash, output_hash, timestamp, duration; write in same DB transaction for write tools.
  - File: `src/capital_os/api/app.py`
  - Action: Wire middleware/hooks to guarantee logging coverage for all tool handlers.
  - Notes: Logging must not be bypassed; write operations are fail-closed if event logging persistence fails.

- [ ] Task 7: Build integration and quality gate suite
  - File: `tests/integration/test_accounts_hierarchy.py`
  - Action: Validate account hierarchy create/list/subtree behavior and deterministic ordering.
  - Notes: Include deep-tree edge case.
  - File: `tests/integration/test_record_transaction_bundle.py`
  - Action: Verify balanced commit success, unbalanced rejection, and rollback on forced failure.
  - Notes: Cover happy path and invariant violations.
  - File: `tests/integration/test_idempotency_external_id.py`
  - Action: Verify duplicate `(source_system, external_id)` returns canonical prior result under retry and concurrency.
  - Notes: Include simultaneous request case.
  - File: `tests/integration/test_event_log_coverage.py`
  - Action: Verify 100% event logging for success and validation failures.
  - Notes: Assert required fields always present and include injected failure-path checks for fail-closed behavior.
  - File: `tests/integration/test_tool_contract_validation.py`
  - Action: Verify request/response schema validation behavior for all in-scope tools.
  - Notes: Assert invalid payloads return deterministic machine-readable errors.
  - File: `tests/integration/test_append_only_guards.py`
  - Action: Verify update/delete attempts fail on append-only tables.
  - Notes: Confirm compensating-entry workflow remains valid.
  - File: `tests/perf/test_tool_latency.py`
  - Action: Add baseline harness for p95 measurement on ledger-core tools.
  - Notes: Use explicit reference dataset defined in this spec.
  - File: `tests/replay/test_output_replay.py`
  - Action: Validate replay from stored state + logged inputs reproduces output hash for implemented tools.
  - Notes: Start with ledger-core tools in scope.
  - File: `tests/security/test_db_role_boundaries.py`
  - Action: Validate write access restrictions using roles created by migration.
  - Notes: Test setup must bootstrap service and non-service DB roles in local/CI before assertions; ensure non-service credentials cannot mutate ledger tables while service role can.

### Acceptance Criteria

- [ ] AC 1: Given Docker is installed and project env vars are set, when runtime is started, then PostgreSQL becomes healthy and the service health endpoint reports DB connectivity.
- [ ] AC 2: Given a clean database, when `0001_ledger_core` migration is applied, then all ledger-core tables and required constraints are created successfully.
- [ ] AC 3: Given a rollback command on `0001_ledger_core` and `0002_security_and_append_only`, when executed after migration up, then schema and security/trigger artifacts revert cleanly without orphaned objects.
- [ ] AC 4: Given valid payloads for all in-scope tool endpoints, when requests are submitted, then they are accepted and responses match documented schemas.
- [ ] AC 5: Given invalid payloads for in-scope tools, when requests are submitted, then machine-readable validation errors are returned with deterministic error shapes.
- [ ] AC 6: Given a valid account hierarchy payload, when account services are called, then account creation and deterministic subtree retrieval succeed.
- [ ] AC 7: Given a hierarchy payload that creates a cycle, when creation/update is attempted, then the request is rejected and no cycle is persisted.
- [ ] AC 8: Given a transaction bundle where posting amounts sum to zero, when `record_transaction_bundle` is called, then transaction and postings commit atomically.
- [ ] AC 9: Given a transaction bundle where posting amounts do not sum to zero, when `record_transaction_bundle` is called, then no ledger mutation occurs and an error is returned.
- [ ] AC 10: Given a previously committed `(source_system, external_id)`, when the same request is retried, then no duplicate is created and the original canonical transaction result is returned.
- [ ] AC 11: Given concurrent requests with the same `(source_system, external_id)`, when processed, then exactly one canonical commit exists and all callers receive deterministic idempotent responses.
- [ ] AC 12: Given monetary input values, when persisted and returned, then values are normalized to `NUMERIC(20,4)` using round-half-even behavior.
- [ ] AC 13: Given a valid snapshot payload, when `record_balance_snapshot` is called, then a canonical snapshot record is persisted and retrievable by `(account_id, snapshot_date)`.
- [ ] AC 14: Given a valid obligation payload, when `create_or_update_obligation` is called, then obligation data persists with cadence metadata and deterministic query ordering.
- [ ] AC 15: Given any implemented tool invocation, when processing completes (success or failure), then an event log record exists with tool name, correlation_id, input_hash, output_hash, timestamp, and duration.
- [ ] AC 16: Given event log persistence fails during a write tool operation, when the request is processed, then the ledger write is rolled back (fail-closed) and no partial mutation is committed.
- [ ] AC 17: Given direct UPDATE/DELETE attempts on append-only ledger tables, when attempted in normal operation, then operations are rejected by DB enforcement.
- [ ] AC 18: Given identical stored state and identical tool inputs, when the same implemented tool is re-run, then output hashing remains stable and replay reproduces the original `output_hash`.
- [ ] AC 19: Given non-service DB credentials, when direct ledger table writes are attempted, then writes are denied by privilege boundaries while service-role writes succeed.
- [ ] AC 20: Given ledger-core tool perf tests on the reference dataset, when measured in CI, then p95 latency for implemented ledger-core tools is < 300ms.
- [ ] AC 21: Given successful tool responses, when fields are serialized for hashing, then key ordering and list ordering follow documented canonical order for deterministic `output_hash` generation.

## Additional Context

### Dependencies

- Docker runtime.
- PostgreSQL container image.
- Python runtime and project dependency management.
- PostgreSQL driver and migration execution tooling.
- FastAPI runtime and schema validation stack.
- Pytest and plugins/utilities for integration, concurrency, and performance tests.

### Testing Strategy

- Unit tests for invariants and normalization logic (`sum=0`, decimal rules, canonical ordering/hashing inputs).
- Integration tests against Dockerized PostgreSQL for account hierarchy, atomic writes, idempotency, snapshots, obligations, and event logging.
- Concurrency integration tests specifically for `(source_system, external_id)` collision behavior.
- Contract tests for tool request/response schema compliance.
- DB enforcement tests for append-only trigger behavior and cycle rejection.
- Replay tests to verify deterministic `output_hash` regeneration from logged inputs and persisted state.
- Security tests for DB role boundary enforcement on canonical ledger tables.
- Performance harness to enforce p95 `< 300ms` for implemented ledger-core tools on the baseline dataset.
- Manual smoke checks: start stack, run migration, call `/health`, execute one valid/one invalid `record_transaction_bundle`, inspect event log rows.

### Reference Dataset (For AC 20)

- 100,000 postings
- 50,000 transactions
- 5,000 accounts
- 2,000 obligations
- 10,000 balance snapshots
- Single-currency (`USD`) dataset for MVP

### Notes

- Highest-risk area: idempotency race handling under concurrent duplicate requests; mitigate with DB uniqueness + transactional conflict handling + concurrency tests.
- Secondary risk: schema churn during early implementation; mitigate by freezing naming and precision conventions before Task 4.
- Audit-risk control: event logging is fail-closed for write operations to prevent untracked mutations.
- This spec intentionally excludes capital posture, spend simulation, debt analysis, and approval workflow implementation; those remain future slices.
- Role/bootstrap requirement: CI test setup must create service and non-service DB roles before security test execution.
