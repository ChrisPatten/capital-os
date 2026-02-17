# Skill: Capital OS (Ledger Core) — Agent Operating Guide

## What this tool is
Capital OS is a local-first, deterministic ledger core exposed via:
- `GET /health`
- `POST /tools/{tool_name}`

All mutations must happen through tool endpoints (never through direct SQLite writes).

## How to start/stop it (Make-driven)
This repo is designed for an agent to run Make targets:
- `make init` — migrations + initial COA seed from `coa.yaml` (idempotent)
- `make serve-idle` — starts API only if not already healthy; auto-stops after inactivity
- `make stop` — stops server

### Required idempotent start sequence
1) Call `GET /health`
2) If not OK, run `make serve-idle`
3) Call `GET /health` again and proceed only when `status=="ok"` 

## Authentication & authorization
Every tool call must include:
- Header: `x-capital-auth-token: <token>` 
- Body field: `correlation_id` (required; validated at API boundary) 

Default dev tokens (if env not overridden):
- `dev-admin-token` has read/write/approve/admin
- `dev-reader-token` has read-only

If a tool returns `403`, you lack the capability for that tool (do not retry blindly).

## Core rules you must follow
- USD only for postings/snapshots.
- `record_transaction_bundle` must have ≥2 postings and MUST balance: sum(amount)==0 after 4dp normalization. 
- Idempotency key for transaction bundles is `(source_system, external_id)`; duplicates return deterministic replay (`status="idempotent-replay"`). 
- Always generate a unique `correlation_id` per call.
- Do not include secrets or secret-like strings in payloads. 

## The "MVP ready" way to put data in
### Step 0 — Bootstrap COA + create accounts as needed
Run `make init` to seed the initial chart of accounts, then verify with `list_accounts` or `get_account_tree`.

To add new accounts at runtime, use `create_account`:
- Required: `code`, `name`, `account_type` (asset/liability/equity/income/expense)
- Optional: `parent_account_id`, `entity_id`, `metadata`
- Returns `account_id` on success

### Step 1 — Snapshot-first (lowest friction)
Use `record_balance_snapshot` to store balances (upsert by `(account_id, snapshot_date)`).

### Step 2 — Obligations (due dates + expected amounts)
Use `create_or_update_obligation` (upsert by `(source_system, name, account_id)`).

### Step 3 — Transactions (double-entry)
Use `record_transaction_bundle`.
If it returns `status="proposed"`, it did NOT write ledger rows; you must follow with:
- `approve_proposed_transaction` OR
- `reject_proposed_transaction` 

## Standard request pattern
For any tool call:
- Construct JSON body strictly matching the tool schema (unknown keys are forbidden).
- Include `correlation_id`.
- Send to `POST /tools/<tool_name>` with auth header.

## Error handling
- 401: missing/invalid token → stop, fix token.
- 403: capability denied → stop, use correct token or remove action.
- 422: schema/validation error → fix payload; do not assume partial writes.
- 400: tool execution error → treat as no commit unless you received an explicit committed status.

## Account management tools
- `create_account` — Create new accounts in the chart of accounts at runtime (requires `tools:write`)
- `update_account_metadata` — Update account metadata fields (coming soon)

Example — create a new cash account:
```bash
curl -sS -H "x-capital-auth-token: $TOKEN" \
  -H "content-type: application/json" \
  "$CAPOS/tools/create_account" \
  -d '{
    "code": "1310",
    "name": "New Checking Account",
    "account_type": "asset",
    "parent_account_id": "acct-checking",
    "metadata": {"institution": "Chase"},
    "correlation_id": "capos.create_account.20260216.a1"
  }'
```

## Useful read tools (verification)
- `get_account_tree` — confirm COA structure
- `list_accounts` — confirm accounts and IDs
- `get_account_balances` — as-of balances with policy selection (ledger vs snapshot vs best_available)
- `list_obligations` — upcoming obligations
- `list_transactions` / `get_transaction_by_external_id` — verify postings and idempotency behavior

## Minimal data contracts (what you should store)
- Account IDs come from the seeded COA or from `create_account` tool calls. Use `create_account` to add new accounts at runtime.
- Snapshots: `(account_id, snapshot_date, balance)`
- Obligations: `(name, account_id, cadence, expected_amount, next_due_date)`
- Transactions: `(source_system, external_id, date, description, postings[])`

## Notes on determinism
- Keep date/times explicit (UTC recommended).
- Keep decimals to 4dp (strings are OK; service normalizes).
- Keep stable ordering in postings lists when generating ids for external_id hashing (avoid accidental churn).

