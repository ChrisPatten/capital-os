# Capital OS Backlog: PRD Delta 0215 (Family Office Agent Enablement)

Date: 2026-02-15
Source: `prd_update_0215.md`
Goal: Convert FR-13..FR-33 and NFR-08..NFR-12 into implementation-ready backlog, architecture changes, and technical specs.

## Scope Summary
- Add deterministic read/query tools for agents without direct DB access.
- Add reconciliation + source-of-truth selection policy.
- Add multi-entity model and consolidated calculations.
- Add accounting period close/lock and adjusting-entry governance.
- Expand policy engine beyond amount threshold.
- Add API authentication/authorization and mandatory correlation IDs.
- Add export/import/backup controls with integrity guarantees.

## Epic Plan (New)

### Epic 6: Read/Query Surface (FR-13..FR-18, NFR-08)
Priority: P0
Objective: Complete deterministic read surface with stable cursor pagination.
Stories:
- 6.1 Read Query Tooling Foundation (accounts, account_tree, balances + pagination contract)
- 6.2 Transaction + Obligation Query Surface
- 6.3 Proposal + Config Query Surface and Config Change Approval Entry Points

### Epic 7: Reconciliation and Truth Policy (FR-19..FR-20)
Priority: P0
Objective: Reconcile ledger vs snapshot with proposed-only adjustments.
Stories:
- 7.1 Reconciliation Domain + `reconcile_account` tool
- 7.2 Configurable `balance_source_policy` wiring (`ledger_only|snapshot_only|best_available`)
- 7.3 Determinism/replay tests for reconciliation outputs and proposal payloads

### Epic 8: Multi-Entity Core (FR-21..FR-23, NFR-10)
Priority: P0
Objective: Introduce `entity_id` dimension and consolidated neutrality rules.
Stories:
- 8.1 Schema migrations for entity dimension and FK propagation
- 8.2 Consolidated posture + inter-entity transfer paired semantics
- 8.3 Scale and regression suite for >=25 entities

### Epic 9: Period Control + Policy Engine Expansion (FR-24..FR-27, NFR-12)
Priority: P1
Objective: Enforce close/lock semantics and generalized policy gates.
Stories:
- 9.1 `close_period`, `lock_period`, and adjusting-entry tagging with reason codes
- 9.2 Policy rule model (category/entity/velocity/risk_band/tool_type)
- 9.3 Multi-party approval support with p95 policy overhead <50ms

### Epic 10: API Security and Runtime Guardrails (FR-28..FR-30, NFR-09, NFR-11)
Priority: P0
Objective: Secure all tool calls with authn/authz and no-egress controls.
Stories:
- 10.1 Authentication baseline and identity propagation
- 10.2 Tool-level authorization + required `correlation_id`
- 10.3 No-egress enforcement + telemetry-backed security tests

### Epic 11: Export/Import/Backup Controls (FR-31..FR-33)
Priority: P1
Objective: Controlled data portability and recoverability.
Stories:
- 11.1 `export_ledger(date_range, format)` with hash-integrity markers
- 11.2 `import_transaction_bundles(dry_run, strict)` with deterministic validation output
- 11.3 Admin-only backup/restore operations with audit trail

## Architecture Additions

### Data Model Changes
- Add `entities` table and `entity_id` foreign keys on:
  - `accounts`
  - `transactions`
  - `balance_snapshots`
  - `obligations`
  - `proposals` (if not already present)
- Add period-control table(s):
  - `accounting_periods` (period_key, status, closed_at, locked_at, actor)
- Add policy tables:
  - `policy_rules`
  - `policy_approvals` (supports multi-party state machine)
- Extend event log fields for auth context:
  - `actor_id`, `authn_method`, `authorization_result`

### Domain Services
- `domain/query/` for deterministic read services and cursor codecs.
- `domain/reconciliation/` for delta computation and suggested-adjustment generation.
- `domain/entities/` for entity normalization and inter-entity transfer enforcement.
- `domain/periods/` for close/lock checks in write path.
- `domain/policy/` for rule evaluation + proposal gating.
- `domain/security/` for authn/authz context adapters.

### API/Tool Surface Additions
- Read/query tools:
  - `list_accounts`, `get_account_tree`, `get_account_balances`
  - `list_transactions`, `get_transaction_by_external_id`
  - `list_obligations`, `list_proposals`, `get_proposal`
  - `get_config`, `propose_config_change`, `approve_config_change`
- Governance/security tools:
  - `reconcile_account`, `close_period`, `lock_period`
- Portability/admin tools:
  - `export_ledger`, `import_transaction_bundles`
  - backup/restore admin endpoints/tools

### Determinism and Replay Extensions
- Cursor format must be canonical (opaque but deterministic encoding of sort keys).
- All read endpoints enforce explicit default sort order and tie-break keys.
- Reconciliation suggestion payloads must be hash-stable and never auto-commit.
- Entity consolidation must exclude inter-entity transfer double counting by invariant rule.

## Migration Plan
- `0003_read_query_indexes.sql`: deterministic query indexes and cursor-support keys.
- `0004_entity_dimension.sql`: entities table + entity_id propagation.
- `0005_periods_policies.sql`: period control + policy rule tables.
- `0006_security_runtime_controls.sql`: auth context columns, correlation constraints, security triggers.
- `0007_export_import_backup.sql`: export job metadata, import audit tables, backup metadata.

Each migration requires forward + rollback test coverage in CI.

## Spec Breakdown by Requirement
- FR-13..18: Epic 6
- FR-19..20: Epic 7
- FR-21..23: Epic 8
- FR-24..27: Epic 9
- FR-28..30: Epic 10
- FR-31..33: Epic 11
- NFR-08: Epic 6 test gates
- NFR-09/NFR-11: Epic 10 test gates
- NFR-10: Epic 8 perf and scale suite
- NFR-12: Epic 9 latency suite

## Recommended Execution Sequence
1. Epic 10 (authn/authz/correlation/no-egress guardrails first)
2. Epic 6 (read surface needed by agent operations)
3. Epic 7 (reconciliation from read foundation)
4. Epic 8 (entity dimension before consolidated posture)
5. Epic 9 (period and policy expansion)
6. Epic 11 (portability/admin controls)

## Definition of Ready for Implementation
- Story-level acceptance criteria include deterministic ordering and hash requirements.
- Every new tool has explicit success and validation-failure event logging criteria.
- Migration rollback path specified and testable.
- Security model identifies actor, capability, and denial behavior for each tool.
