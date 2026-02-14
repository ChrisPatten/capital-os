# Data Model Reference

As of 2026-02-14. Source migrations:
- `migrations/0001_ledger_core.sql`
- `migrations/0002_security_and_append_only.sql`

## Canonical Tables

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

Constraints and guards:
- Append-only update/delete blocked by triggers.
- Populated by `src/capital_os/observability/event_log.py`.

## Service-Layer Invariants
- Balanced transaction bundles required before write:
  - `sum(normalized_posting_amounts) == 0.0000`
- Monetary values normalized using round-half-even at 4 decimal places.
- Transaction idempotency on `(source_system, external_id)` with deterministic replay response.

## Read/Write Boundary
- Canonical writes must run through service/tool layer transaction wrappers.
- Read-only consumers use SQLite read-only mode (`mode=ro`) via `read_only_connection()`.
- Security test coverage: `tests/security/test_db_role_boundaries.py`.
