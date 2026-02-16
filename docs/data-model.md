# Data Model Reference

As of 2026-02-16. Source migrations:
- `migrations/0001_ledger_core.sql`
- `migrations/0002_security_and_append_only.sql`
- `migrations/0003_approval_gates.sql`
- `migrations/0004_read_query_indexes.sql`
- `migrations/0005_entity_dimension.sql`
- `migrations/0006_periods_policies.sql`
- `migrations/0007_query_surface_indexes.sql`
- `migrations/0008_api_security_runtime_controls.sql`

## Canonical Tables

## `entities`
Purpose:
- Canonical entity dimension for multi-entity financial records.

Key fields:
- `entity_id TEXT PRIMARY KEY`
- `code TEXT NOT NULL UNIQUE`
- `name TEXT NOT NULL`
- `metadata TEXT NOT NULL DEFAULT '{}'`

Constraints:
- Deterministic default row seeded by migration:
  - `entity_id = 'entity-default'`
  - `code = 'DEFAULT'`

## `accounts`
Purpose:
- Chart-of-accounts hierarchy and metadata.

Key fields:
- `account_id TEXT PRIMARY KEY`
- `code TEXT NOT NULL UNIQUE`
- `name TEXT NOT NULL`
- `account_type TEXT CHECK IN ('asset','liability','equity','income','expense')`
- `parent_account_id TEXT REFERENCES accounts(account_id)`
- `metadata TEXT NOT NULL DEFAULT '{}'`
- `entity_id TEXT NOT NULL REFERENCES entities(entity_id)`

Constraints and guards:
- Unique `code`.
- Trigger-based cycle prevention on insert/update of `parent_account_id`.

## `ledger_transactions`
Purpose:
- Header row for each bundle commit with idempotency identity.

Key fields:
- `transaction_id TEXT PRIMARY KEY`
- `source_system TEXT NOT NULL`
- `external_id TEXT NOT NULL`
- `transaction_date TEXT NOT NULL`
- `description TEXT NOT NULL`
- `correlation_id TEXT NOT NULL`
- `input_hash TEXT NOT NULL`
- `output_hash TEXT` (set after canonical response shaping)
- `response_payload TEXT` (serialized canonical response)
- `entity_id TEXT NOT NULL REFERENCES entities(entity_id)`
- `is_adjusting_entry INTEGER NOT NULL DEFAULT 0`
- `adjusting_reason_code TEXT`

Constraints and guards:
- Unique `(source_system, external_id)` for idempotency.
- Append-only trigger blocks most updates/deletes.
- One controlled update shape is allowed to populate `response_payload` and `output_hash` after insert.

## `ledger_postings`
Purpose:
- Double-entry legs for each transaction bundle.

Key fields:
- `posting_id TEXT PRIMARY KEY`
- `transaction_id TEXT REFERENCES ledger_transactions(transaction_id)`
- `account_id TEXT REFERENCES accounts(account_id)`
- `amount NUMERIC NOT NULL`
- `currency TEXT NOT NULL CHECK (currency = 'USD')`
- `memo TEXT`

Constraints and guards:
- FK integrity to transactions and accounts.
- Append-only update/delete blocked by triggers.

## `balance_snapshots`
Purpose:
- Point-in-time externally sourced or reconciled account balances.

Key fields:
- `snapshot_id TEXT PRIMARY KEY`
- `source_system TEXT NOT NULL`
- `account_id TEXT REFERENCES accounts(account_id)`
- `snapshot_date TEXT NOT NULL`
- `balance NUMERIC NOT NULL`
- `currency TEXT NOT NULL CHECK (currency = 'USD')`
- `source_artifact_id TEXT`
- `entity_id TEXT NOT NULL REFERENCES entities(entity_id)`

Constraints:
- Unique `(account_id, snapshot_date)`.
- Supports upsert semantics in repository/service layer.

## `obligations`
Purpose:
- Recurring or custom expected obligations used for planning context.

Key fields:
- `obligation_id TEXT PRIMARY KEY`
- `source_system TEXT NOT NULL`
- `name TEXT NOT NULL`
- `account_id TEXT REFERENCES accounts(account_id)`
- `cadence TEXT CHECK IN ('monthly','annual','custom')`
- `expected_amount NUMERIC NOT NULL`
- `variability_flag INTEGER NOT NULL DEFAULT 0`
- `next_due_date TEXT NOT NULL`
- `metadata TEXT NOT NULL DEFAULT '{}'`
- `active INTEGER NOT NULL DEFAULT 1`
- `entity_id TEXT NOT NULL REFERENCES entities(entity_id)`

Constraints:
- Unique `(source_system, name, account_id)`.
- Service layer update path reactivates records by setting `active = 1`.

## `event_log`
Purpose:
- Immutable audit trail of tool invocation outcomes.

Key fields:
- `event_id TEXT PRIMARY KEY`
- `tool_name TEXT NOT NULL`
- `correlation_id TEXT NOT NULL`
- `input_hash TEXT NOT NULL`
- `output_hash TEXT NOT NULL`
- `event_timestamp TEXT NOT NULL`
- `duration_ms INTEGER NOT NULL`
- `status TEXT NOT NULL`
- `error_code TEXT`
- `error_message TEXT`
- `actor_id TEXT`
- `authn_method TEXT`
- `authorization_result TEXT`
- `violation_code TEXT`

Constraints and guards:
- Append-only update/delete blocked by triggers.
- Populated by `src/capital_os/observability/event_log.py`.

## `approval_proposals`
Purpose:
- Lifecycle state for approval-gated write requests.

Key fields:
- `proposal_id TEXT PRIMARY KEY`
- `tool_name TEXT NOT NULL`
- `source_system TEXT NOT NULL`
- `external_id TEXT NOT NULL`
- `correlation_id TEXT NOT NULL`
- `input_hash TEXT NOT NULL`
- `policy_threshold_amount NUMERIC NOT NULL`
- `impact_amount NUMERIC NOT NULL`
- `request_payload TEXT NOT NULL`
- `status TEXT CHECK IN ('proposed','rejected','committed')`
- `approved_transaction_id TEXT REFERENCES ledger_transactions(transaction_id)`
- `response_payload TEXT`
- `output_hash TEXT`
- `entity_id TEXT NOT NULL REFERENCES entities(entity_id)`
- `matched_rule_id TEXT REFERENCES policy_rules(rule_id)`
- `required_approvals INTEGER NOT NULL DEFAULT 1`

Constraints and guards:
- Unique `(tool_name, source_system, external_id)` for deterministic proposal replay.
- Delete is blocked by trigger.

## `approval_decisions`
Purpose:
- Append-only audit records for approve/reject actions on proposals.

Key fields:
- `decision_id TEXT PRIMARY KEY`
- `proposal_id TEXT REFERENCES approval_proposals(proposal_id)`
- `action TEXT CHECK IN ('approve','reject')`
- `correlation_id TEXT NOT NULL`
- `reason TEXT`
- `approver_id TEXT`

Constraints and guards:
- Append-only update/delete blocked by triggers.
- Unique distinct approver constraint for non-null `approver_id` on `(proposal_id, action, approver_id)`.

## `accounting_periods`
Purpose:
- Canonical accounting period state for close/lock controls.

Key fields:
- `period_id TEXT PRIMARY KEY`
- `period_key TEXT NOT NULL` (`YYYY-MM`)
- `entity_id TEXT NOT NULL REFERENCES entities(entity_id)`
- `status TEXT CHECK IN ('open','closed','locked')`
- `actor_id TEXT`
- `correlation_id TEXT`
- `closed_at TEXT`
- `locked_at TEXT`

Constraints:
- Unique `(period_key, entity_id)`.

## `policy_rules`
Purpose:
- Deterministic multi-dimensional policy matching for proposal gating.

Key fields:
- `rule_id TEXT PRIMARY KEY`
- `priority INTEGER NOT NULL`
- `tool_name TEXT`
- `entity_id TEXT REFERENCES entities(entity_id)`
- `transaction_category TEXT`
- `risk_band TEXT`
- `velocity_limit_count INTEGER`
- `velocity_window_seconds INTEGER`
- `threshold_amount NUMERIC NOT NULL`
- `required_approvals INTEGER NOT NULL DEFAULT 1`
- `active INTEGER NOT NULL DEFAULT 1`
- `metadata TEXT NOT NULL DEFAULT '{}'`

Constraints:
- Stable evaluation order by `(priority ASC, rule_id ASC)`.
- `required_approvals >= 1`.
- Velocity fields must be provided together when used.

## Service-Layer Invariants
- Balanced transaction bundles required before write:
  - `sum(normalized_posting_amounts) == 0.0000`
- Monetary values normalized using round-half-even at 4 decimal places.
- Transaction idempotency on `(source_system, external_id)` with deterministic replay response.
- Above-threshold transaction requests produce deterministic proposal records and responses.
- Period-closed writes require adjusting-entry tags.
- Period-locked writes require explicit override + approval gating.
- Approval commits and approval event logging are coupled in one DB transaction (fail-closed).

## Read/Write Boundary
- Canonical writes must run through service/tool layer transaction wrappers.
- Read-only consumers use SQLite read-only mode (`mode=ro`) via `read_only_connection()`.
- Security test coverage: `tests/security/test_db_role_boundaries.py`.
