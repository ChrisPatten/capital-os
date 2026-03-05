# Data Models (Core)

## Canonical Ledger and Domain Tables

- `accounts`
- `ledger_transactions`
- `ledger_postings`
- `balance_snapshots`
- `obligations`
- `event_log`
- `approval_proposals`
- `approval_decisions`
- `entities`
- `accounting_periods`
- `policy_rules`
- `account_identifier_history`
- `schema_migrations` (migration tracker)

## Key Relationship Overview

- `ledger_postings.transaction_id` references `ledger_transactions.transaction_id`.
- `ledger_postings.account_id` references `accounts.account_id`.
- `accounts.parent_account_id` self-references `accounts.account_id` (hierarchy with cycle guard triggers).
- `balance_snapshots.account_id` references `accounts.account_id`.
- `obligations.account_id` references `accounts.account_id`.
- `approval_decisions.proposal_id` references `approval_proposals.proposal_id`.
- `approval_proposals.proposed_transaction_id` references `ledger_transactions.transaction_id`.
- Entity-aware indexes and constraints are layered through later migrations.

## Invariant and Security Enforcement

- Append-only trigger guards exist for ledger/audit history tables.
- Account hierarchy cycle-prevention triggers are defined in initial schema migration.
- Period and policy controls are introduced in `0006_periods_policies.sql`.
- API security/event-log indexing is extended in `0008_api_security_runtime_controls.sql`.
- Identifier history append-only controls are introduced in `0010_account_identifier_history.sql`.

## Query and Performance Indexing

Read/query optimization migrations include:

- `0004_read_query_indexes.sql`
- `0007_query_surface_indexes.sql`
- entity and security indexes in `0005`/`0008`/`0010`

## Migration Strategy

- Forward migrations: numbered `migrations/0001...0010_*.sql`
- Rollback scripts: paired `*.rollback.sql`
- Runtime application: `src/capital_os/db/migrations.py` with `schema_migrations` tracking and idempotent apply behavior.
