---
title: 'Family Office Agent Enablement Delta (0215)'
slug: 'family-office-agent-enablement-delta-0215'
created: '2026-02-15T00:00:00Z'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - 'Python'
  - 'FastAPI'
  - 'SQLite (file-backed, WAL)'
  - 'Pytest'
---

# Tech-Spec: Family Office Agent Enablement Delta

## Overview
This delta extends Capital OS from write-focused ledger core into a fully agent-operable system with deterministic read/query APIs, reconciliation controls, multi-entity support, expanded governance, API security enforcement, and controlled export/import/backup operations.

## Required New Tool Surface
- Read/query:
  - `list_accounts`
  - `get_account_tree`
  - `get_account_balances`
  - `list_transactions`
  - `get_transaction_by_external_id`
  - `list_obligations`
  - `list_proposals`
  - `get_proposal`
  - `get_config`
- Governance/config:
  - `propose_config_change`
  - `approve_config_change`
  - `reconcile_account`
  - `close_period`
  - `lock_period`
- Portability/admin:
  - `export_ledger`
  - `import_transaction_bundles`
  - backup/restore operations

## Architecture Changes

### API Layer
- All tools continue through `POST /tools/{tool_name}`.
- Add mandatory request auth context and required `correlation_id` validation.
- Add tool capability checks before handler execution.

### Domain Layer
- New modules:
  - `src/capital_os/domain/query/`
  - `src/capital_os/domain/reconciliation/`
  - `src/capital_os/domain/entities/`
  - `src/capital_os/domain/periods/`
  - `src/capital_os/domain/policy/`
  - `src/capital_os/domain/security/`

### Data Layer
- Add entity dimension and propagate `entity_id` on core financial tables.
- Add period state tables and policy rule/approval tables.
- Add deterministic read indexes for stable cursor pagination.

### Observability
- Keep existing event log invariants.
- Extend event schema to include actor/capability decision metadata.
- Preserve fail-closed behavior for write tools when event logging fails.

## Determinism Rules (Delta)
- Cursor pagination must be deterministic with canonical sort/tie-break ordering.
- Reconciliation outputs and proposed adjustments must be hash-stable.
- Consolidated multi-entity outputs must enforce no double-counting for inter-entity transfers.
- Identical state and input must reproduce identical `output_hash` across all new tools.

## Security and Governance Rules
- 100% of tool calls must pass authn + authz checks.
- Period lock blocks back-dated writes unless elevated approval exists.
- Reconciliation adjustments are proposal-only and never auto-committed.

## Migration Plan
- `0003_read_query_indexes.sql`
- `0004_entity_dimension.sql`
- `0005_periods_policies.sql`
- `0006_security_runtime_controls.sql`
- `0007_export_import_backup.sql`

Each migration requires explicit rollback and CI coverage for apply->rollback->reapply.

## Testing Plan
- Integration: read/query determinism + stable pagination.
- Integration: reconciliation proposal shape and non-commit guarantee.
- Integration: period lock/close and override approval behavior.
- Security: authn/authz coverage + correlation required.
- Replay: hash reproducibility across all new tools.
- Perf: policy latency (<50ms p95 overhead), multi-entity scale (>=25 entities), read tool latency targets.

## Backlog Mapping
- Epic 6: FR-13..FR-18, NFR-08
- Epic 7: FR-19..FR-20
- Epic 8: FR-21..FR-23, NFR-10
- Epic 9: FR-24..FR-27, NFR-12
- Epic 10: FR-28..FR-30, NFR-09, NFR-11
- Epic 11: FR-31..FR-33
